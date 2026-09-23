import os
import json
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from backend.app.database.models.models import (
    TestExecution,
    TestCase,
    Bug,
    BugEvidence,
    ExecutionStatus,
    EvidenceType
)
from backend.app.database.repositories.bug_repo import BugRepository
from backend.app.database.repositories.execution_repo import ExecutionRepository
from backend.app.bug_engine.classifier import FailureClassifier
from backend.app.bug_engine.root_cause_analyzer import RootCauseAnalyzer
from backend.app.core.logging import logger

class BugService:
    """
    Orchestrates failure classification, duplicate detection, AI root-cause analysis,
    and defect lifecycle persistence.
    """

    def __init__(self, db: Session):
        self.db = db
        self.bug_repo = BugRepository(db)
        self.exec_repo = ExecutionRepository(db)
        self.classifier = FailureClassifier()
        self.analyzer = RootCauseAnalyzer()

    async def analyze_failed_execution(self, execution_id: int) -> Optional[Bug]:
        """
        Analyzes a completed test execution:
        - Classifies failure type (Application Bug vs Test Bug vs Environment Failure).
        - If Application Bug: performs deduplication and AI root cause analysis.
        - Persists defect record and evidence.
        """
        execution = self.exec_repo.get_execution(execution_id)
        if not execution:
            raise ValueError(f"TestExecution #{execution_id} not found.")

        # Only analyze failed or error executions
        if execution.status not in (ExecutionStatus.FAILED, ExecutionStatus.ERROR):
            logger.info(f"Execution #{execution_id} status is '{execution.status}'. Skipping bug creation.")
            return None

        test_case = execution.test_case
        if not test_case:
            raise ValueError(f"Execution #{execution_id} has no linked TestCase.")

        app_id = test_case.application_id

        # 1. Gather raw execution evidence
        steps = self.exec_repo.get_execution_steps(execution_id)
        evidence_records = self.exec_repo.get_execution_evidence(execution_id)

        failed_step = next((s for s in steps if s.status == "failed"), None)
        failed_step_seq = failed_step.sequence if failed_step else 1
        failed_step_action = failed_step.action if failed_step else "unknown"
        failed_step_target = failed_step.target if failed_step else ""
        failed_step_value = None
        expected_result = ""

        if failed_step and failed_step.test_step:
            failed_step_value = failed_step.test_step.value
            expected_result = failed_step.test_step.expected_result or ""

        # Load console and network log contents if available
        console_logs: List[Dict[str, Any]] = []
        network_failures: List[Dict[str, Any]] = []

        for ev in evidence_records:
            if ev.type == EvidenceType.CONSOLE_LOG and ev.file_path and os.path.exists(ev.file_path):
                try:
                    with open(ev.file_path, "r", encoding="utf-8") as f:
                        console_logs = json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to read console logs: {e}")

            if ev.type == EvidenceType.NETWORK_LOG and ev.file_path and os.path.exists(ev.file_path):
                try:
                    with open(ev.file_path, "r", encoding="utf-8") as f:
                        network_failures = json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to read network logs: {e}")

        # 2. Classify failure
        class_res = self.classifier.classify(
            application_id=app_id,
            error_message=execution.error_message or (failed_step.error_message if failed_step else ""),
            failed_step_action=failed_step_action,
            failed_step_target=failed_step_target,
            console_logs=console_logs,
            network_failures=network_failures,
            final_url=execution.final_url
        )

        # Update execution classification
        execution.classification = class_res.classification
        self.db.commit()

        logger.info(
            f"Execution #{execution_id} classified as: {class_res.classification} "
            f"(Application defect: {class_res.is_application_defect})"
        )

        # 3. Guard: Only create a Bug if it's an authentic APPLICATION_BUG
        if not class_res.is_application_defect:
            logger.info(
                f"Execution #{execution_id} is a {class_res.classification} ({class_res.reason}). "
                f"No application defect created to prevent false defect pollution."
            )
            return None

        # 4. Duplicate Bug Detection
        existing_bug = self.bug_repo.find_by_signature(app_id, class_res.failure_signature)
        if existing_bug:
            logger.info(
                f"Found existing open bug #{existing_bug.id} ('{existing_bug.title}') matching signature {class_res.failure_signature}. "
                f"Incrementing occurrence count."
            )
            updated_bug = self.bug_repo.increment_occurrence(existing_bug.id, execution_id)
            return updated_bug

        # 5. AI Root Cause Analysis
        ai_res = await self.analyzer.analyze(
            test_case_name=test_case.name,
            test_category=test_case.category,
            failed_step_sequence=failed_step_seq,
            failed_step_action=failed_step_action,
            failed_step_target=failed_step_target,
            failed_step_value=failed_step_value,
            expected_result=expected_result,
            error_message=execution.error_message or (failed_step.error_message if failed_step else ""),
            final_url=execution.final_url or "",
            console_logs=console_logs,
            network_failures=network_failures,
            preliminary_classification=class_res.classification,
            preliminary_category=class_res.category
        )

        # 6. Create Bug Record
        bug = self.bug_repo.create_bug(
            application_id=app_id,
            environment_id=execution.environment_id,
            title=ai_res.title,
            summary=ai_res.summary,
            description=ai_res.description,
            classification=class_res.classification,
            category=ai_res.category,
            severity=ai_res.severity,
            priority=ai_res.priority,
            status="OPEN",
            affected_page=execution.final_url,
            affected_workflow_id=test_case.workflow_id,
            affected_test_case_id=test_case.id,
            affected_execution_id=execution.id,
            failed_step=f"Step #{failed_step_seq}: {failed_step_action.upper()} on {failed_step_target}",
            expected_behavior=ai_res.expected_behavior,
            actual_behavior=ai_res.actual_behavior,
            root_cause=ai_res.root_cause,
            root_cause_confidence=ai_res.confidence_score,
            confidence_level=ai_res.confidence_level,
            severity_explanation=ai_res.severity_explanation,
            failure_signature=class_res.failure_signature
        )

        # 7. Attach evidence from execution to bug
        for ev in evidence_records:
            self.bug_repo.add_evidence(
                bug_id=bug.id,
                evidence_type=ev.type,
                file_path=ev.file_path,
                description=ev.description
            )

        logger.info(f"Successfully recorded new defect BUG #{bug.id}: '{bug.title}'")
        return bug
