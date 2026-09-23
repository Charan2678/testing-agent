from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.database.models.models import TestCase, Application, Environment
from backend.app.database.repositories.generated_test_repo import GeneratedTestRepository
from backend.app.database.repositories.execution_repo import ExecutionRepository
from backend.app.test_engine.generator import TestGenerator
from backend.app.test_engine.runner import PlaywrightTestRunner
from backend.app.api.schemas.execution import (
    GeneratedTestResponse,
    TestExecutionResponse,
    TestExecutionStepResponse,
    ExecutionEvidenceResponse,
    ExecutionSummaryResponse
)

router = APIRouter(tags=["Test Executions"])

# --- GENERATION ENDPOINTS ---

@router.post(
    "/test-cases/{id}/generate",
    response_model=GeneratedTestResponse,
    summary="Generate Playwright test script from stored test case"
)
def generate_playwright_test(
    id: int,
    base_url: Optional[str] = Query(None, description="Override target base URL"),
    db: Session = Depends(get_db)
):
    test_case = db.query(TestCase).filter(TestCase.id == id).first()
    if not test_case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"TestCase #{id} not found")

    generator = TestGenerator(db)
    try:
        generated = generator.generate_and_save(test_case_id=id, base_url=base_url)
        return generated
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Playwright test: {str(e)}"
        )

@router.get(
    "/test-cases/{id}/generated-test",
    response_model=GeneratedTestResponse,
    summary="Get latest generated Playwright test script for a test case"
)
def get_latest_generated_test(
    id: int,
    db: Session = Depends(get_db)
):
    repo = GeneratedTestRepository(db)
    generated = repo.get_latest_by_test_case(id)
    if not generated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No generated test found for TestCase #{id}. Generate one first."
        )
    return generated

@router.get(
    "/test-cases/{id}/generated-tests",
    response_model=List[GeneratedTestResponse],
    summary="Get all generated versions for a test case"
)
def get_all_generated_tests(
    id: int,
    db: Session = Depends(get_db)
):
    repo = GeneratedTestRepository(db)
    return repo.get_by_test_case_all(id)


# --- EXECUTION ENDPOINTS ---

@router.post(
    "/test-cases/{id}/execute",
    response_model=TestExecutionResponse,
    summary="Execute validated Playwright test against target application"
)
async def execute_test_case(
    id: int,
    environment_id: Optional[int] = Query(None, description="Target environment ID"),
    base_url: Optional[str] = Query(None, description="Direct target base URL override"),
    db: Session = Depends(get_db)
):
    test_case = db.query(TestCase).filter(TestCase.id == id).first()
    if not test_case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"TestCase #{id} not found")

    runner = PlaywrightTestRunner(db)
    try:
        execution = await runner.execute_test_case(
            test_case_id=id,
            environment_id=environment_id,
            base_url=base_url
        )
        return execution
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution failed: {str(e)}"
        )

@router.get(
    "/test-executions/{id}",
    response_model=TestExecutionResponse,
    summary="Get execution status and details"
)
def get_test_execution(
    id: int,
    db: Session = Depends(get_db)
):
    repo = ExecutionRepository(db)
    execution = repo.get_execution(id)
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"TestExecution #{id} not found")
    return execution

@router.get(
    "/test-executions/{id}/steps",
    response_model=List[TestExecutionStepResponse],
    summary="Get step-by-step results for an execution"
)
def get_execution_steps(
    id: int,
    db: Session = Depends(get_db)
):
    repo = ExecutionRepository(db)
    return repo.get_execution_steps(id)

@router.get(
    "/test-executions/{id}/evidence",
    response_model=List[ExecutionEvidenceResponse],
    summary="Get evidence (screenshots, trace, logs) for an execution"
)
def get_execution_evidence(
    id: int,
    db: Session = Depends(get_db)
):
    repo = ExecutionRepository(db)
    return repo.get_execution_evidence(id)

@router.get(
    "/applications/{id}/test-executions",
    response_model=List[TestExecutionResponse],
    summary="List all executions belonging to an application"
)
def get_application_executions(
    id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    repo = ExecutionRepository(db)
    return repo.get_by_application(id, limit=limit)

@router.get(
    "/applications/{id}/test-executions/summary",
    response_model=ExecutionSummaryResponse,
    summary="Get real execution metrics for an application dashboard (zero mock)"
)
def get_application_execution_summary(
    id: int,
    db: Session = Depends(get_db)
):
    repo = ExecutionRepository(db)
    return repo.get_summary_by_application(id)
