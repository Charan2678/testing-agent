import asyncio
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Query
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.database.repositories.exploration_repo import ExplorationRepository
from backend.app.database.repositories.application_repo import ApplicationRepository
from backend.app.database.models.models import ExplorationStatus, EvidenceType
from backend.app.services.exploration_service import ExplorationService, active_explorations
from backend.app.api.schemas.exploration import (
    ExplorationCreate, ExplorationResponse, ExplorationStatusResponse, ExplorationDetailResponse
)
from backend.app.api.schemas.evidence import EvidenceResponse

router = APIRouter(prefix="/explorations", tags=["Exploration"])

@router.post("", response_model=ExplorationResponse, status_code=status.HTTP_201_CREATED)
def create_exploration(data: ExplorationCreate, db: Session = Depends(get_db)):
    app_repo = ApplicationRepository(db)
    app = app_repo.get_by_id(data.application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    env = app_repo.get_environment_by_id(data.environment_id)
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")

    expl_repo = ExplorationRepository(db)
    return expl_repo.create_run(data)

@router.get("", response_model=List[ExplorationResponse])
def list_explorations(
    application_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    expl_repo = ExplorationRepository(db)
    return expl_repo.get_all_runs(application_id=application_id, skip=skip, limit=limit)

@router.get("/{id}", response_model=ExplorationDetailResponse)
def get_exploration(id: int, db: Session = Depends(get_db)):
    expl_repo = ExplorationRepository(db)
    run = expl_repo.get_run(id)
    if not run:
        raise HTTPException(status_code=404, detail="Exploration run not found")
    return run

@router.post("/{id}/start", response_model=ExplorationStatusResponse)
async def start_exploration(
    id: int,
    background_tasks: BackgroundTasks,
    max_pages: int = Query(default=30, ge=1, le=100),
    max_depth: int = Query(default=3, ge=1, le=10),
    db: Session = Depends(get_db)
):
    expl_repo = ExplorationRepository(db)
    run = expl_repo.get_run(id)
    if not run:
        raise HTTPException(status_code=404, detail="Exploration run not found")

    if run.status == ExplorationStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Exploration is already running")

    # Launch crawler background task
    service = ExplorationService(db)
    background_tasks.add_task(service.execute_exploration, id, max_pages, max_depth)

    return ExplorationStatusResponse(
        id=id,
        status=ExplorationStatus.RUNNING,
        pages_discovered=run.pages_discovered,
        actions_discovered=run.actions_discovered,
        error_count=run.error_count,
        current_url=None,
        activity_log=["Exploration process initiated."]
    )

@router.get("/{id}/status", response_model=ExplorationStatusResponse)
def get_exploration_status(id: int, db: Session = Depends(get_db)):
    expl_repo = ExplorationRepository(db)
    run = expl_repo.get_run(id)
    if not run:
        raise HTTPException(status_code=404, detail="Exploration run not found")

    active_state = active_explorations.get(id)
    if active_state:
        return ExplorationStatusResponse(
            id=id,
            status=active_state["status"],
            pages_discovered=active_state["pages_discovered"],
            actions_discovered=active_state["actions_discovered"],
            error_count=active_state["error_count"],
            current_url=active_state["current_url"],
            target_url=active_state.get("target_url", run.target_url),
            url_source=active_state.get("url_source"),
            activity_log=active_state["activity_log"][-20:]  # Return last 20 activity entries
        )

    return ExplorationStatusResponse(
        id=id,
        status=run.status,
        pages_discovered=run.pages_discovered,
        actions_discovered=run.actions_discovered,
        error_count=run.error_count,
        current_url=None,
        target_url=run.target_url,
        url_source=None,
        activity_log=[]
    )

@router.get("/{id}/evidence", response_model=List[EvidenceResponse])
def get_exploration_evidence(
    id: int,
    type: Optional[EvidenceType] = None,
    db: Session = Depends(get_db)
):
    expl_repo = ExplorationRepository(db)
    run = expl_repo.get_run(id)
    if not run:
        raise HTTPException(status_code=404, detail="Exploration run not found")
    return expl_repo.get_evidence_by_run(id, evidence_type=type)
