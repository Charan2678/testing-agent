from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from backend.app.database.models.models import Workflow, WorkflowStep

class WorkflowRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_workflow(
        self,
        application_id: int,
        name: str,
        description: Optional[str] = None,
        risk_level: str = "medium"
    ) -> Workflow:
        workflow = Workflow(
            application_id=application_id,
            name=name,
            description=description,
            risk_level=risk_level.lower(),
            discovered_at=datetime.utcnow()
        )
        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(workflow)
        return workflow

    def add_step(
        self,
        workflow_id: int,
        sequence: int,
        action: str,
        expected_behavior: Optional[str] = None,
        page_id: Optional[int] = None,
        element_id: Optional[int] = None
    ) -> WorkflowStep:
        step = WorkflowStep(
            workflow_id=workflow_id,
            sequence=sequence,
            page_id=page_id,
            element_id=element_id,
            action=action,
            expected_behavior=expected_behavior
        )
        self.db.add(step)
        self.db.commit()
        self.db.refresh(step)
        return step

    def get_by_id(self, workflow_id: int) -> Optional[Workflow]:
        return self.db.query(Workflow).filter(Workflow.id == workflow_id).first()

    def get_by_application(self, application_id: int) -> List[Workflow]:
        return self.db.query(Workflow).filter(
            Workflow.application_id == application_id
        ).order_by(Workflow.id.asc()).all()

    def get_steps(self, workflow_id: int) -> List[WorkflowStep]:
        return self.db.query(WorkflowStep).filter(
            WorkflowStep.workflow_id == workflow_id
        ).order_by(WorkflowStep.sequence.asc()).all()

    def delete_by_application(self, application_id: int):
        self.db.query(Workflow).filter(Workflow.application_id == application_id).delete()
        self.db.commit()
