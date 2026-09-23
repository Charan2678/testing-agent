from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.database.repositories.page_repo import PageRepository
from backend.app.api.schemas.page import (
    PageDetailResponse, PageResponse, ElementResponse, ActionResponse
)

router = APIRouter(prefix="/pages", tags=["Pages & Elements"])

@router.get("/{id}", response_model=PageDetailResponse)
def get_page(id: int, db: Session = Depends(get_db)):
    repo = PageRepository(db)
    page = repo.get_page_by_id(id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    return PageDetailResponse(
        id=page.id,
        application_id=page.application_id,
        environment_id=page.environment_id,
        url=page.url,
        title=page.title,
        status_code=page.status_code,
        page_type=page.page_type,
        first_seen_at=page.first_seen_at,
        last_seen_at=page.last_seen_at,
        elements_count=len(page.elements),
        elements=page.elements,
        actions=page.actions
    )

@router.get("/{id}/elements", response_model=List[ElementResponse])
def get_page_elements(id: int, db: Session = Depends(get_db)):
    repo = PageRepository(db)
    page = repo.get_page_by_id(id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return repo.get_elements_by_page(id)

@router.get("/{id}/actions", response_model=List[ActionResponse])
def get_page_actions(id: int, db: Session = Depends(get_db)):
    repo = PageRepository(db)
    page = repo.get_page_by_id(id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return repo.get_actions_by_page(id)
