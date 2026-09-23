from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from backend.app.database.models.models import (
    TestExecution,
    TestExecutionStep,
    ExecutionEvidence,
    ExecutionStatus,
    EvidenceType,
    TestCase
)

class ExecutionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_execution(
        self,
        test_case_id: int,
        environment_id: Optional[int] = None,
        status: ExecutionStatus = ExecutionStatus.QUEUED
    ) -> TestExecution:
        execution = TestExecution(
            test_case_id=test_case_id,
            environment_id=environment_id,
            status=status,
            started_at=datetime.utcnow() if status == ExecutionStatus.RUNNING else None,
            created_at=datetime.utcnow()
        )
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        return execution

    def update_execution(
        self,
        execution_id: int,
        status: Optional[ExecutionStatus] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        duration_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        final_url: Optional[str] = None
    ) -> Optional[TestExecution]:
        execution = self.get_execution(execution_id)
        if not execution:
            return None

        if status is not None:
            execution.status = status
        if started_at is not None:
            execution.started_at = started_at
        if completed_at is not None:
            execution.completed_at = completed_at
        if duration_ms is not None:
            execution.duration_ms = duration_ms
        if error_message is not None:
            execution.error_message = error_message
        if final_url is not None:
            execution.final_url = final_url

        self.db.commit()
        self.db.refresh(execution)
        return execution

    def add_step_result(
        self,
        execution_id: int,
        sequence: int,
        action: str,
        target: str,
        test_step_id: Optional[int] = None,
        status: str = "pending",
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        duration_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        actual_result: Optional[str] = None
    ) -> TestExecutionStep:
        step = TestExecutionStep(
            execution_id=execution_id,
            test_step_id=test_step_id,
            sequence=sequence,
            action=action,
            target=target,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            error_message=error_message,
            actual_result=actual_result
        )
        self.db.add(step)
        self.db.commit()
        self.db.refresh(step)
        return step

    def add_evidence(
        self,
        execution_id: int,
        evidence_type: EvidenceType,
        file_path: str,
        description: Optional[str] = None,
        metadata_json: Optional[Dict[str, Any]] = None
    ) -> ExecutionEvidence:
        evidence = ExecutionEvidence(
            execution_id=execution_id,
            type=evidence_type,
            file_path=file_path,
            description=description,
            metadata_json=metadata_json,
            created_at=datetime.utcnow()
        )
        self.db.add(evidence)
        self.db.commit()
        self.db.refresh(evidence)
        return evidence

    def get_execution(self, execution_id: int) -> Optional[TestExecution]:
        return self.db.query(TestExecution).filter(TestExecution.id == execution_id).first()

    def get_execution_steps(self, execution_id: int) -> List[TestExecutionStep]:
        return (
            self.db.query(TestExecutionStep)
            .filter(TestExecutionStep.execution_id == execution_id)
            .order_by(TestExecutionStep.sequence.asc())
            .all()
        )

    def get_execution_evidence(self, execution_id: int) -> List[ExecutionEvidence]:
        return (
            self.db.query(ExecutionEvidence)
            .filter(ExecutionEvidence.execution_id == execution_id)
            .order_by(ExecutionEvidence.created_at.asc())
            .all()
        )

    def get_by_test_case(self, test_case_id: int, limit: int = 50) -> List[TestExecution]:
        return (
            self.db.query(TestExecution)
            .filter(TestExecution.test_case_id == test_case_id)
            .order_by(desc(TestExecution.created_at))
            .limit(limit)
            .all()
        )

    def get_by_application(self, application_id: int, limit: int = 100) -> List[TestExecution]:
        return (
            self.db.query(TestExecution)
            .join(TestCase, TestCase.id == TestExecution.test_case_id)
            .filter(TestCase.application_id == application_id)
            .order_by(desc(TestExecution.created_at))
            .limit(limit)
            .all()
        )

    def get_summary_by_application(self, application_id: int) -> Dict[str, Any]:
        """Calculates real, non-mocked execution metrics for an application."""
        executions = self.get_by_application(application_id, limit=1000)
        total = len(executions)

        if total == 0:
            return {
                "has_executions": False,
                "total_executions": 0,
                "passed": 0,
                "failed": 0,
                "blocked": 0,
                "skipped": 0,
                "errors": 0,
                "pass_rate": 0.0,
                "avg_duration_ms": 0
            }

        passed = sum(1 for e in executions if e.status == ExecutionStatus.PASSED)
        failed = sum(1 for e in executions if e.status == ExecutionStatus.FAILED)
        blocked = sum(1 for e in executions if e.status == ExecutionStatus.BLOCKED)
        skipped = sum(1 for e in executions if e.status == ExecutionStatus.SKIPPED)
        errors = sum(1 for e in executions if e.status == ExecutionStatus.ERROR)

        durations = [e.duration_ms for e in executions if e.duration_ms is not None]
        avg_duration = int(sum(durations) / len(durations)) if durations else 0
        pass_rate = round((passed / total) * 100, 1)

        return {
            "has_executions": True,
            "total_executions": total,
            "passed": passed,
            "failed": failed,
            "blocked": blocked,
            "skipped": skipped,
            "errors": errors,
            "pass_rate": pass_rate,
            "avg_duration_ms": avg_duration
        }
