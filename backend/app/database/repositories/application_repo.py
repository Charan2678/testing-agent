from typing import List, Optional
from sqlalchemy.orm import Session
from backend.app.database.models.models import Application, Environment
from backend.app.api.schemas.application import ApplicationCreate, ApplicationUpdate
from backend.app.api.schemas.environment import EnvironmentCreate

class ApplicationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Application]:
        return self.db.query(Application).offset(skip).limit(limit).all()

    def get_by_id(self, application_id: int) -> Optional[Application]:
        return self.db.query(Application).filter(Application.id == application_id).first()

    def create(self, app_data: ApplicationCreate) -> Application:
        db_app = Application(
            name=app_data.name,
            description=app_data.description
        )
        self.db.add(db_app)
        self.db.commit()
        self.db.refresh(db_app)
        return db_app

    def update(self, application_id: int, app_data: ApplicationUpdate) -> Optional[Application]:
        db_app = self.get_by_id(application_id)
        if not db_app:
            return None
        if app_data.name is not None:
            db_app.name = app_data.name
        if app_data.description is not None:
            db_app.description = app_data.description
        self.db.commit()
        self.db.refresh(db_app)
        return db_app

    def delete(self, application_id: int) -> bool:
        db_app = self.get_by_id(application_id)
        if not db_app:
            return False
        self.db.delete(db_app)
        self.db.commit()
        return True

    # Environment operations
    def get_environments(self, application_id: int) -> List[Environment]:
        return self.db.query(Environment).filter(Environment.application_id == application_id).all()

    def get_environment_by_id(self, environment_id: int) -> Optional[Environment]:
        return self.db.query(Environment).filter(Environment.id == environment_id).first()

    def create_environment(self, application_id: int, env_data: EnvironmentCreate) -> Environment:
        db_env = Environment(
            application_id=application_id,
            name=env_data.name,
            base_url=str(env_data.base_url).rstrip("/"),
            environment_type=env_data.environment_type
        )
        self.db.add(db_env)
        self.db.commit()
        self.db.refresh(db_env)
        return db_env
