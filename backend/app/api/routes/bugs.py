from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.database.models.models import Bug, Application, TestExecution
from backend.app.database.repositories.bug_repo import BugRepository
from backend.app.services.bug_service import BugService
from backend.app.api.schemas.bug import (
    BugResponse,
    BugEvidenceResponse,
    BugSummaryResponse,
    BugStatusUpdate,
    BugCreate
)

router = APIRouter(tags=["Bugs & Root Cause Analysis"])

@router.get(
    "/applications/{id}/bugs",
    response_model=List[BugResponse],
    summary="List all defects for an application"
)
def get_application_bugs(
    id: int,
    status: Optional[str] = Query(None, description="Filter by status: OPEN, TRIAGED, IN_PROGRESS, FIXED, CLOSED"),
    severity: Optional[str] = Query(None, description="Filter by severity: CRITICAL, HIGH, MEDIUM, LOW"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    repo = BugRepository(db)
    return repo.get_by_application(
        application_id=id,
        status=status,
        severity=severity,
        category=category,
        limit=limit
    )

@router.get(
    "/applications/{id}/bugs/summary",
    response_model=BugSummaryResponse,
    summary="Get real defect metrics for an application (zero mock)"
)
def get_application_bug_summary(
    id: int,
    db: Session = Depends(get_db)
):
    repo = BugRepository(db)
    return repo.get_summary_by_application(id)

@router.get(
    "/bugs/{id}",
    response_model=BugResponse,
    summary="Get defect details by ID"
)
def get_bug_by_id(
    id: int,
    db: Session = Depends(get_db)
):
    repo = BugRepository(db)
    bug = repo.get_by_id(id)
    if not bug:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Bug #{id} not found")
    return bug

@router.get(
    "/bugs/{id}/evidence",
    response_model=List[BugEvidenceResponse],
    summary="Get all evidence artifacts linked to a defect"
)
def get_bug_evidence(
    id: int,
    db: Session = Depends(get_db)
):
    repo = BugRepository(db)
    bug = repo.get_by_id(id)
    if not bug:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Bug #{id} not found")
    return bug.evidence

@router.post(
    "/test-executions/{id}/analyze",
    response_model=Optional[BugResponse],
    summary="Analyze a failed test execution, classify failure, and generate/update defect"
)
async def analyze_test_execution(
    id: int,
    db: Session = Depends(get_db)
):
    service = BugService(db)
    try:
        bug = await service.analyze_failed_execution(execution_id=id)
        return bug
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bug analysis failed: {str(e)}"
        )

@router.patch(
    "/bugs/{id}",
    response_model=BugResponse,
    summary="Update defect status (OPEN, TRIAGED, IN_PROGRESS, FIXED, CLOSED)"
)
def update_bug_status(
    id: int,
    payload: BugStatusUpdate,
    db: Session = Depends(get_db)
):
    allowed_statuses = ["OPEN", "TRIAGED", "IN_PROGRESS", "FIXED", "RETESTED", "CLOSED"]
    new_status = payload.status.upper()
    if new_status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{payload.status}'. Allowed: {', '.join(allowed_statuses)}"
        )

    repo = BugRepository(db)
    bug = repo.update_status(id, new_status)
    if not bug:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Bug #{id} not found")
    return bug

@router.post(
    "/applications/{id}/bugs",
    response_model=BugResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Manually log a defect for an application"
)
def create_application_bug(
    id: int,
    payload: BugCreate,
    db: Session = Depends(get_db)
):
    import hashlib
    repo = BugRepository(db)
    sig = hashlib.sha256(f"{id}:{payload.affected_page}:{payload.title}".encode("utf-8")).hexdigest()[:16]
    bug = repo.create_bug(
        application_id=id,
        title=payload.title,
        summary=payload.summary or payload.title,
        description=payload.description,
        classification=payload.classification,
        category=payload.category,
        severity=payload.severity,
        priority=payload.priority,
        status="OPEN",
        affected_page=payload.affected_page,
        expected_behavior=payload.expected_behavior,
        actual_behavior=payload.actual_behavior,
        root_cause=payload.root_cause,
        failure_signature=sig
    )
    return bug

@router.post(
    "/applications/{id}/scan-defects",
    response_model=List[BugResponse],
    summary="Scan all executions for defects"
)
async def scan_application_defects(
    id: int,
    db: Session = Depends(get_db)
):
    from backend.app.database.repositories.execution_repo import ExecutionRepository
    exec_repo = ExecutionRepository(db)
    service = BugService(db)
    execs = exec_repo.get_by_application(id, limit=50)
    failed_execs = [e for e in execs if e.status in ["FAILED", "ERROR"]]
    created_or_updated = []
    for f in failed_execs:
        try:
            b = await service.analyze_failed_execution(f.id)
            if b:
                created_or_updated.append(b)
        except Exception:
            pass
    return created_or_updated

