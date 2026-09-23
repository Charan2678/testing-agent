from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.app.database.models.models import GeneratedTest

class GeneratedTestRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_generated_test(
        self,
        test_case_id: int,
        file_path: str,
        generated_code: str,
        framework: str = "playwright",
        language: str = "python"
    ) -> GeneratedTest:
        latest = self.get_latest_by_test_case(test_case_id)
        next_version = (latest.generation_version + 1) if latest else 1

        record = GeneratedTest(
            test_case_id=test_case_id,
            framework=framework,
            language=language,
            file_path=file_path,
            generated_code=generated_code,
            generation_version=next_version,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_latest_by_test_case(self, test_case_id: int) -> Optional[GeneratedTest]:
        return (
            self.db.query(GeneratedTest)
            .filter(GeneratedTest.test_case_id == test_case_id)
            .order_by(desc(GeneratedTest.generation_version))
            .first()
        )

    def get_by_test_case_all(self, test_case_id: int) -> List[GeneratedTest]:
        return (
            self.db.query(GeneratedTest)
            .filter(GeneratedTest.test_case_id == test_case_id)
            .order_by(desc(GeneratedTest.generation_version))
            .all()
        )

    def get_by_id(self, id: int) -> Optional[GeneratedTest]:
        return self.db.query(GeneratedTest).filter(GeneratedTest.id == id).first()
