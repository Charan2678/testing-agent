from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.app.database.models.models import (
    ExplorationRun, ExplorationStatus, Evidence, EvidenceType
)
from backend.app.api.schemas.exploration import ExplorationCreate

class ExplorationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_run(self, data: ExplorationCreate) -> ExplorationRun:
        run = ExplorationRun(
            application_id=data.application_id,
            environment_id=data.environment_id,
            target_url=data.target_url,
            status=ExplorationStatus.PENDING,
            pages_discovered=0,
            actions_discovered=0,
            error_count=0
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get_run(self, run_id: int) -> Optional[ExplorationRun]:
        return self.db.query(ExplorationRun).filter(ExplorationRun.id == run_id).first()

    def get_all_runs(self, application_id: Optional[int] = None, skip: int = 0, limit: int = 50) -> List[ExplorationRun]:
        query = self.db.query(ExplorationRun)
        if application_id:
            query = query.filter(ExplorationRun.application_id == application_id)
        return query.order_by(ExplorationRun.id.desc()).offset(skip).limit(limit).all()

    def start_run(self, run_id: int) -> Optional[ExplorationRun]:
        run = self.get_run(run_id)
        if run:
            run.status = ExplorationStatus.RUNNING
            run.started_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(run)
        return run

    def complete_run(self, run_id: int, status: ExplorationStatus = ExplorationStatus.COMPLETED) -> Optional[ExplorationRun]:
        run = self.get_run(run_id)
        if run:
            run.status = status
            run.completed_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(run)
        return run

    def update_metrics(self, run_id: int, pages_count: int, actions_count: int, error_count: int) -> Optional[ExplorationRun]:
        run = self.get_run(run_id)
        if run:
            run.pages_discovered = pages_count
            run.actions_discovered = actions_count
            run.error_count = error_count
            self.db.commit()
            self.db.refresh(run)
        return run

    def add_evidence(
        self,
        run_id: int,
        evidence_type: EvidenceType,
        file_path: Optional[str] = None,
        url: Optional[str] = None,
        description: Optional[str] = None,
        metadata_json: Optional[Dict[str, Any]] = None
    ) -> Evidence:
        evidence = Evidence(
            exploration_run_id=run_id,
            type=evidence_type,
            file_path=file_path,
            url=url,
            description=description,
            metadata_json=metadata_json,
            created_at=datetime.utcnow()
        )
        self.db.add(evidence)
        self.db.commit()
        self.db.refresh(evidence)
        return evidence

    def get_evidence_by_run(self, run_id: int, evidence_type: Optional[EvidenceType] = None) -> List[Evidence]:
        query = self.db.query(Evidence).filter(Evidence.exploration_run_id == run_id)
        if evidence_type:
            query = query.filter(Evidence.type == evidence_type)
        return query.order_by(Evidence.created_at.asc()).all()
