from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from backend.app.database.models.models import TestCase, TestStep

class TestCaseRepository:
    __test__ = False

    def __init__(self, db: Session):
        self.db = db

    def create_test_case(
        self,
        application_id: int,
        name: str,
        category: str,
        priority: str,
        workflow_id: Optional[int] = None,
        description: Optional[str] = None,
        preconditions: Optional[List[str]] = None,
        status: str = "active"
    ) -> TestCase:
        test_case = TestCase(
            application_id=application_id,
            workflow_id=workflow_id,
            name=name,
            description=description,
            category=category.lower(),
            priority=priority.lower(),
            preconditions=preconditions or [],
            status=status,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.db.add(test_case)
        self.db.commit()
        self.db.refresh(test_case)
        return test_case

    def add_step(
        self,
        test_case_id: int,
        sequence: int,
        action: str,
        target: str,
        expected_result: str,
        value: Optional[str] = None,
        source_page_id: Optional[int] = None,
        source_element_id: Optional[int] = None
    ) -> TestStep:
        step = TestStep(
            test_case_id=test_case_id,
            sequence=sequence,
            action=action,
            target=target,
            value=value,
            expected_result=expected_result,
            source_page_id=source_page_id,
            source_element_id=source_element_id
        )
        self.db.add(step)
        self.db.commit()
        self.db.refresh(step)
        return step

    def get_by_id(self, test_case_id: int) -> Optional[TestCase]:
        return self.db.query(TestCase).filter(TestCase.id == test_case_id).first()

    def get_by_application(
        self,
        application_id: int,
        workflow_id: Optional[int] = None,
        category: Optional[str] = None,
        priority: Optional[str] = None
    ) -> List[TestCase]:
        query = self.db.query(TestCase).filter(TestCase.application_id == application_id)
        if workflow_id:
            query = query.filter(TestCase.workflow_id == workflow_id)
        if category:
            query = query.filter(TestCase.category == category.lower())
        if priority:
            query = query.filter(TestCase.priority == priority.lower())
        return query.order_by(TestCase.id.asc()).all()

    def get_steps(self, test_case_id: int) -> List[TestStep]:
        return self.db.query(TestStep).filter(
            TestStep.test_case_id == test_case_id
        ).order_by(TestStep.sequence.asc()).all()

    def delete_by_application(self, application_id: int):
        self.db.query(TestCase).filter(TestCase.application_id == application_id).delete()
        self.db.commit()
