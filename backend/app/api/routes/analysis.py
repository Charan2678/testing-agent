from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Query
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.database.repositories.workflow_repo import WorkflowRepository
from backend.app.database.repositories.testcase_repo import TestCaseRepository
from backend.app.database.repositories.application_repo import ApplicationRepository
from backend.app.services.ai_analysis_service import AIAnalysisService, active_analyses
from backend.app.api.schemas.workflow import WorkflowResponse, WorkflowStepResponse
from backend.app.api.schemas.testcase import TestCaseResponse, TestStepResponse, TestCaseCreate

router = APIRouter(tags=["AI Analysis & Test Cases"])

# 1. Trigger AI Analysis
@router.post("/applications/{id}/analyze", status_code=status.HTTP_202_ACCEPTED)
async def start_application_analysis(
    id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    app_repo = ApplicationRepository(db)
    app = app_repo.get_by_id(id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    service = AIAnalysisService(db)
    background_tasks.add_task(service.execute_analysis, id)

    return {
        "message": f"AI analysis initiated for application '{app.name}'",
        "status": "ANALYZING",
        "application_id": id
    }

@router.get("/applications/{id}/analysis-status")
def get_analysis_status(id: int, db: Session = Depends(get_db)):
    app_repo = ApplicationRepository(db)
    app = app_repo.get_by_id(id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    state = active_analyses.get(id)
    if state:
        return state

    wf_repo = WorkflowRepository(db)
    tc_repo = TestCaseRepository(db)
    existing_wfs = wf_repo.get_by_application(id)
    existing_tcs = tc_repo.get_by_application(id)

    if existing_wfs or existing_tcs:
        return {
            "status": "COMPLETED",
            "stage": "Workflows and test cases ready",
            "workflows_count": len(existing_wfs),
            "test_cases_count": len(existing_tcs),
            "activity_log": ["Previously analyzed records available in database."]
        }

    return {
        "status": "IDLE",
        "stage": "No analysis currently active",
        "workflows_count": 0,
        "test_cases_count": 0,
        "activity_log": []
    }

# 2. Workflows Endpoints
@router.get("/applications/{id}/workflows", response_model=List[WorkflowResponse])
def get_application_workflows(id: int, db: Session = Depends(get_db)):
    wf_repo = WorkflowRepository(db)
    workflows = wf_repo.get_by_application(id)
    result = []
    for wf in workflows:
        result.append(WorkflowResponse(
            id=wf.id,
            application_id=wf.application_id,
            name=wf.name,
            description=wf.description,
            risk_level=wf.risk_level,
            discovered_at=wf.discovered_at,
            steps_count=len(wf.steps),
            steps=wf.steps
        ))
    return result

@router.get("/workflows/{id}", response_model=WorkflowResponse)
def get_workflow(id: int, db: Session = Depends(get_db)):
    wf_repo = WorkflowRepository(db)
    wf = wf_repo.get_by_id(id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return WorkflowResponse(
        id=wf.id,
        application_id=wf.application_id,
        name=wf.name,
        description=wf.description,
        risk_level=wf.risk_level,
        discovered_at=wf.discovered_at,
        steps_count=len(wf.steps),
        steps=wf.steps
    )

@router.get("/workflows/{id}/steps", response_model=List[WorkflowStepResponse])
def get_workflow_steps(id: int, db: Session = Depends(get_db)):
    wf_repo = WorkflowRepository(db)
    steps = wf_repo.get_steps(id)
    return steps

# 3. Test Cases Endpoints
@router.post("/applications/{id}/generate-tests", status_code=status.HTTP_202_ACCEPTED)
async def generate_tests(
    id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    return await start_application_analysis(id, background_tasks, db)

@router.get("/applications/{id}/test-cases", response_model=List[TestCaseResponse])
def get_application_test_cases(
    id: int,
    workflow_id: Optional[int] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db)
):
    tc_repo = TestCaseRepository(db)
    test_cases = tc_repo.get_by_application(
        application_id=id,
        workflow_id=workflow_id,
        category=category,
        priority=priority
    )
    result = []
    for tc in test_cases:
        result.append(TestCaseResponse(
            id=tc.id,
            application_id=tc.application_id,
            workflow_id=tc.workflow_id,
            name=tc.name,
            description=tc.description,
            category=tc.category,
            priority=tc.priority,
            preconditions=tc.preconditions or [],
            status=tc.status,
            created_at=tc.created_at,
            updated_at=tc.updated_at,
            steps_count=len(tc.steps),
            steps=tc.steps
        ))
    return result

@router.get("/test-cases/{id}", response_model=TestCaseResponse)
def get_test_case(id: int, db: Session = Depends(get_db)):
    tc_repo = TestCaseRepository(db)
    tc = tc_repo.get_by_id(id)
    if not tc:
        raise HTTPException(status_code=404, detail="Test case not found")
    return TestCaseResponse(
        id=tc.id,
        application_id=tc.application_id,
        workflow_id=tc.workflow_id,
        name=tc.name,
        description=tc.description,
        category=tc.category,
        priority=tc.priority,
        preconditions=tc.preconditions or [],
        status=tc.status,
        created_at=tc.created_at,
        updated_at=tc.updated_at,
        steps_count=len(tc.steps),
        steps=tc.steps
    )

@router.get("/test-cases/{id}/steps", response_model=List[TestStepResponse])
def get_test_case_steps(id: int, db: Session = Depends(get_db)):
    tc_repo = TestCaseRepository(db)
    steps = tc_repo.get_steps(id)
    return steps

@router.post("/applications/{id}/test-cases", response_model=TestCaseResponse, status_code=status.HTTP_201_CREATED)
def create_application_test_case(
    id: int,
    payload: TestCaseCreate,
    db: Session = Depends(get_db)
):
    app_repo = ApplicationRepository(db)
    app = app_repo.get_by_id(id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    tc_repo = TestCaseRepository(db)
    tc = tc_repo.create_test_case(
        application_id=id,
        name=payload.name,
        category=payload.category,
        priority=payload.priority,
        workflow_id=payload.workflow_id,
        description=payload.description,
        preconditions=payload.preconditions,
        status=payload.status
    )
    for idx, s in enumerate(payload.steps):
        tc_repo.add_step(
            test_case_id=tc.id,
            sequence=s.sequence or (idx + 1),
            action=s.action,
            target=s.target,
            value=s.value,
            expected_result=s.expected_result,
            source_page_id=s.source_page_id,
            source_element_id=s.source_element_id
        )

    full_tc = tc_repo.get_by_id(tc.id)
    return TestCaseResponse(
        id=full_tc.id,
        application_id=full_tc.application_id,
        workflow_id=full_tc.workflow_id,
        name=full_tc.name,
        description=full_tc.description,
        category=full_tc.category,
        priority=full_tc.priority,
        preconditions=full_tc.preconditions or [],
        status=full_tc.status,
        created_at=full_tc.created_at,
        updated_at=full_tc.updated_at,
        steps_count=len(full_tc.steps),
        steps=full_tc.steps
    )
