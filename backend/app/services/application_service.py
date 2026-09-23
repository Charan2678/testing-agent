from typing import List, Optional
from sqlalchemy.orm import Session
from backend.app.database.repositories.application_repo import ApplicationRepository
from backend.app.api.schemas.application import ApplicationCreate, ApplicationUpdate
from backend.app.api.schemas.environment import EnvironmentCreate
from backend.app.database.models.models import Application, Environment

class ApplicationService:
    def __init__(self, db: Session):
        self.repo = ApplicationRepository(db)

    def list_applications(self, skip: int = 0, limit: int = 100) -> List[Application]:
        return self.repo.get_all(skip, limit)

    def get_application(self, application_id: int) -> Optional[Application]:
        return self.repo.get_by_id(application_id)

    def create_application(self, app_data: ApplicationCreate) -> Application:
        return self.repo.create(app_data)

    def update_application(self, application_id: int, app_data: ApplicationUpdate) -> Optional[Application]:
        return self.repo.update(application_id, app_data)

    def delete_application(self, application_id: int) -> bool:
        return self.repo.delete(application_id)

    def list_environments(self, application_id: int) -> List[Environment]:
        return self.repo.get_environments(application_id)

    def create_environment(self, application_id: int, env_data: EnvironmentCreate) -> Environment:
        return self.repo.create_environment(application_id, env_data)
