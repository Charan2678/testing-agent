from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from backend.app.database.models.models import Bug, BugEvidence, EvidenceType

class BugRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_bug(
        self,
        application_id: int,
        title: str,
        summary: str,
        description: str,
        classification: str = "APPLICATION_BUG",
        category: str = "FUNCTIONAL",
        severity: str = "MEDIUM",
        priority: str = "MEDIUM",
        status: str = "OPEN",
        environment_id: Optional[int] = None,
        affected_page: Optional[str] = None,
        affected_workflow_id: Optional[int] = None,
        affected_test_case_id: Optional[int] = None,
        affected_execution_id: Optional[int] = None,
        failed_step: Optional[str] = None,
        expected_behavior: Optional[str] = None,
        actual_behavior: Optional[str] = None,
        root_cause: Optional[str] = None,
        root_cause_confidence: int = 50,
        confidence_level: str = "LIKELY",
        severity_explanation: Optional[str] = None,
        failure_signature: Optional[str] = None
    ) -> Bug:
        bug = Bug(
            application_id=application_id,
            environment_id=environment_id,
            title=title,
            summary=summary,
            description=description,
            classification=classification,
            category=category,
            severity=severity,
            priority=priority,
            status=status,
            affected_page=affected_page,
            affected_workflow_id=affected_workflow_id,
            affected_test_case_id=affected_test_case_id,
            affected_execution_id=affected_execution_id,
            failed_step=failed_step,
            expected_behavior=expected_behavior,
            actual_behavior=actual_behavior,
            root_cause=root_cause,
            root_cause_confidence=root_cause_confidence,
            confidence_level=confidence_level,
            severity_explanation=severity_explanation,
            failure_signature=failure_signature,
            occurrence_count=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.db.add(bug)
        self.db.commit()
        self.db.refresh(bug)
        return bug

    def get_by_id(self, bug_id: int) -> Optional[Bug]:
        return self.db.query(Bug).filter(Bug.id == bug_id).first()

    def get_by_application(
        self,
        application_id: int,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[Bug]:
        query = self.db.query(Bug).filter(Bug.application_id == application_id)
        if status and status.lower() != "all":
            query = query.filter(Bug.status == status.upper())
        if severity and severity.lower() != "all":
            query = query.filter(Bug.severity == severity.upper())
        if category and category.lower() != "all":
            query = query.filter(Bug.category == category.upper())
        return query.order_by(desc(Bug.created_at)).limit(limit).all()

    def find_by_signature(self, application_id: int, failure_signature: str) -> Optional[Bug]:
        """Finds existing open bug matching the failure signature for deduplication."""
        return (
            self.db.query(Bug)
            .filter(
                Bug.application_id == application_id,
                Bug.failure_signature == failure_signature,
                Bug.status.in_(["OPEN", "TRIAGED", "IN_PROGRESS"])
            )
            .first()
        )

    def increment_occurrence(self, bug_id: int, execution_id: int) -> Optional[Bug]:
        bug = self.get_by_id(bug_id)
        if not bug:
            return None
        bug.occurrence_count += 1
        bug.affected_execution_id = execution_id
        bug.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(bug)
        return bug

    def update_status(self, bug_id: int, new_status: str) -> Optional[Bug]:
        bug = self.get_by_id(bug_id)
        if not bug:
            return None
        bug.status = new_status.upper()
        bug.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(bug)
        return bug

    def add_evidence(
        self,
        bug_id: int,
        evidence_type: EvidenceType,
        file_path: str,
        description: Optional[str] = None
    ) -> BugEvidence:
        evidence = BugEvidence(
            bug_id=bug_id,
            type=evidence_type,
            file_path=file_path,
            description=description,
            created_at=datetime.utcnow()
        )
        self.db.add(evidence)
        self.db.commit()
        self.db.refresh(evidence)
        return evidence

    def get_summary_by_application(self, application_id: int) -> Dict[str, Any]:
        """Calculates real, non-mocked defect metrics."""
        bugs = self.get_by_application(application_id, limit=1000)
        total = len(bugs)
        if total == 0:
            return {
                "has_bugs": False,
                "total_bugs": 0,
                "open_bugs": 0,
                "critical_bugs": 0,
                "high_bugs": 0,
                "medium_bugs": 0,
                "low_bugs": 0,
                "resolved_bugs": 0
            }

        open_count = sum(1 for b in bugs if b.status in ("OPEN", "TRIAGED", "IN_PROGRESS"))
        resolved_count = sum(1 for b in bugs if b.status in ("FIXED", "CLOSED", "RETESTED"))
        critical_count = sum(1 for b in bugs if b.severity == "CRITICAL")
        high_count = sum(1 for b in bugs if b.severity == "HIGH")
        medium_count = sum(1 for b in bugs if b.severity == "MEDIUM")
        low_count = sum(1 for b in bugs if b.severity == "LOW")

        return {
            "has_bugs": True,
            "total_bugs": total,
            "open_bugs": open_count,
            "critical_bugs": critical_count,
            "high_bugs": high_count,
            "medium_bugs": medium_count,
            "low_bugs": low_count,
            "resolved_bugs": resolved_count
        }
