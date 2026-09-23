from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.services.application_service import ApplicationService
from backend.app.database.repositories.page_repo import PageRepository
from backend.app.api.schemas.application import (
    ApplicationCreate, ApplicationUpdate, ApplicationResponse
)
from backend.app.api.schemas.environment import (
    EnvironmentCreate, EnvironmentResponse
)
from backend.app.api.schemas.page import PageResponse

router = APIRouter(prefix="/applications", tags=["Applications"])

@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(app_data: ApplicationCreate, db: Session = Depends(get_db)):
    service = ApplicationService(db)
    return service.create_application(app_data)

@router.get("", response_model=List[ApplicationResponse])
def list_applications(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    service = ApplicationService(db)
    return service.list_applications(skip=skip, limit=limit)

@router.get("/{id}", response_model=ApplicationResponse)
def get_application(id: int, db: Session = Depends(get_db)):
    service = ApplicationService(db)
    app = service.get_application(id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return app

@router.put("/{id}", response_model=ApplicationResponse)
def update_application(id: int, app_data: ApplicationUpdate, db: Session = Depends(get_db)):
    service = ApplicationService(db)
    app = service.update_application(id, app_data)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return app

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(id: int, db: Session = Depends(get_db)):
    service = ApplicationService(db)
    success = service.delete_application(id)
    if not success:
        raise HTTPException(status_code=404, detail="Application not found")
    return None

# Environment endpoints
@router.post("/{id}/environments", response_model=EnvironmentResponse, status_code=status.HTTP_201_CREATED)
def create_environment(id: int, env_data: EnvironmentCreate, db: Session = Depends(get_db)):
    service = ApplicationService(db)
    app = service.get_application(id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return service.create_environment(id, env_data)

@router.get("/{id}/environments", response_model=List[EnvironmentResponse])
def list_environments(id: int, db: Session = Depends(get_db)):
    service = ApplicationService(db)
    app = service.get_application(id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return service.list_environments(id)

# Application map pages endpoint
@router.get("/{id}/pages", response_model=List[PageResponse])
def list_application_pages(id: int, db: Session = Depends(get_db)):
    page_repo = PageRepository(db)
    pages = page_repo.get_pages_by_app(id)
    results = []
    for p in pages:
        p_dict = {
            "id": p.id,
            "application_id": p.application_id,
            "environment_id": p.environment_id,
            "url": p.url,
            "title": p.title,
            "status_code": p.status_code,
            "page_type": p.page_type,
            "first_seen_at": p.first_seen_at,
            "last_seen_at": p.last_seen_at,
            "elements_count": len(p.elements)
        }
        results.append(PageResponse(**p_dict))
    return results
