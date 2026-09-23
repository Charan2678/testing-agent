import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.database.repositories.database_qa_repo import DatabaseQARepository
from backend.app.database.repositories.application_repo import ApplicationRepository
from backend.app.database_qa.connection_manager import DatabaseConnectionManager
from backend.app.database_qa.inspector import DatabaseInspector
from backend.app.database_qa.generator import DatabaseTestCaseGenerator
from backend.app.database_qa.runner import DatabaseTestRunner
from backend.app.api.schemas.database_qa import (
    DatabaseConnectionCreate,
    DatabaseConnectionResponse,
    ConnectionTestResponse,
    DatabaseSchemaResponse,
    DatabaseTestCaseCreate,
    DatabaseTestCaseResponse,
    DatabaseTestExecutionResponse,
    DatabaseSummaryResponse
)

logger = logging.getLogger("autonomous-qa-agent.api.database_qa")

router = APIRouter(tags=["Database QA & Data Integrity"])

# --- CONNECTIONS ---
@router.post(
    "/applications/{id}/databases",
    response_model=DatabaseConnectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register target database connection for application"
)
def create_database_connection(
    id: int,
    payload: DatabaseConnectionCreate,
    db: Session = Depends(get_db)
):
    app_repo = ApplicationRepository(db)
    app = app_repo.get_by_id(id)
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Application #{id} not found")

    repo = DatabaseQARepository(db)
    conn = repo.create_connection(
        application_id=id,
        environment_id=payload.environment_id,
        name=payload.name,
        database_type=payload.database_type,
        database_name=payload.database_name,
        host=payload.host,
        port=payload.port,
        username=payload.username,
        password=payload.password,
        read_only=payload.read_only
    )
    return conn

@router.get(
    "/applications/{id}/databases",
    response_model=List[DatabaseConnectionResponse],
    summary="List database connections for application"
)
def list_application_databases(
    id: int,
    db: Session = Depends(get_db)
):
    repo = DatabaseQARepository(db)
    return repo.get_connections_by_application(id)

@router.post(
    "/applications/{id}/databases/test-connection",
    response_model=ConnectionTestResponse,
    summary="Test target database connection credentials"
)
def test_new_database_connection(
    id: int,
    payload: DatabaseConnectionCreate,
    db: Session = Depends(get_db)
):
    app_repo = ApplicationRepository(db)
    app = app_repo.get_by_id(id)
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Application #{id} not found")

    # Create dummy in-memory model for test
    from backend.app.database.models.models import DatabaseConnection
    dummy_conn = DatabaseConnection(
        application_id=id,
        name=payload.name,
        database_type=payload.database_type,
        database_name=payload.database_name,
        host=payload.host,
        port=payload.port,
        username=payload.username,
        password_encrypted=payload.password,
        read_only=payload.read_only
    )

    env = None
    if payload.environment_id:
        env = next((e for e in app.environments if e.id == payload.environment_id), None)

    status_str, err = DatabaseConnectionManager.test_connection(dummy_conn, env)
    return ConnectionTestResponse(
        status=status_str,
        message=err or "Connection to target database established successfully in READ-ONLY mode."
    )

@router.post(
    "/databases/{id}/test-connection",
    response_model=ConnectionTestResponse,
    summary="Test an existing configured database connection"
)
def test_existing_database_connection(
    id: int,
    db: Session = Depends(get_db)
):
    repo = DatabaseQARepository(db)
    conn = repo.get_connection(id)
    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Database connection #{id} not found")

    status_str, err = DatabaseConnectionManager.test_connection(conn, conn.environment)
    repo.update_connection_status(id, status_str, err)
    return ConnectionTestResponse(
        status=status_str,
        message=err or "Target database connection verified successfully."
    )

# --- SCHEMA DISCOVERY ---
@router.post(
    "/databases/{id}/discover",
    response_model=List[DatabaseSchemaResponse],
    summary="Execute safe schema discovery on target database"
)
def discover_database_schema(
    id: int,
    db: Session = Depends(get_db)
):
    repo = DatabaseQARepository(db)
    conn = repo.get_connection(id)
    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Database connection #{id} not found")

    try:
        engine = DatabaseConnectionManager.get_engine(conn, conn.environment)
        discovered_data = DatabaseInspector.discover_database(engine)
        saved_schemas = repo.save_discovered_schema(id, discovered_data)
        repo.update_connection_status(id, "CONNECTED", None)
        return saved_schemas
    except Exception as e:
        logger.error(f"Schema discovery failed for DB #{id}: {e}")
        repo.update_connection_status(id, "FAILED", str(e)[:200])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Schema discovery failed: {str(e)}"
        )

@router.get(
    "/databases/{id}/schemas",
    response_model=List[DatabaseSchemaResponse],
    summary="Get discovered schema, tables, and relationships for connection"
)
def get_database_schemas(
    id: int,
    db: Session = Depends(get_db)
):
    repo = DatabaseQARepository(db)
    return repo.get_schemas_with_details(id)

@router.get(
    "/databases/{id}/summary",
    response_model=DatabaseSummaryResponse,
    summary="Get database QA summary metrics"
)
def get_database_summary(
    id: int,
    db: Session = Depends(get_db)
):
    repo = DatabaseQARepository(db)
    summary_dict = repo.get_connection_summary(id)
    if not summary_dict:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Database connection #{id} not found")
    return DatabaseSummaryResponse(**summary_dict)

# --- DATABASE TEST CASES ---
@router.post(
    "/applications/{id}/database-test-cases/generate",
    response_model=List[DatabaseTestCaseResponse],
    summary="Synthesize database validation test cases from discovered schema"
)
def generate_database_test_cases(
    id: int,
    connection_id: int,
    db: Session = Depends(get_db)
):
    repo = DatabaseQARepository(db)
    conn = repo.get_connection(connection_id)
    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Database connection #{connection_id} not found")

    schemas = repo.get_schemas_with_details(connection_id)
    if not schemas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No discovered schemas found. Please run schema discovery first."
        )

    test_defs = DatabaseTestCaseGenerator.generate_test_cases(schemas)
    created_cases = []

    for td in test_defs:
        tc = repo.create_test_case(
            application_id=id,
            environment_id=conn.environment_id,
            database_connection_id=conn.id,
            name=td["name"],
            description=td.get("description"),
            category=td.get("category", "DATA_INTEGRITY"),
            priority=td.get("priority", "HIGH"),
            validation_definition=td["validation_definition"]
        )
        created_cases.append(tc)

    return created_cases

@router.post(
    "/applications/{id}/database-test-cases",
    response_model=DatabaseTestCaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Manually create a database integrity test case"
)
def create_database_test_case(
    id: int,
    payload: DatabaseTestCaseCreate,
    db: Session = Depends(get_db)
):
    repo = DatabaseQARepository(db)
    tc = repo.create_test_case(
        application_id=id,
        database_connection_id=payload.database_connection_id,
        name=payload.name,
        category=payload.category,
        priority=payload.priority,
        validation_definition=payload.validation_definition,
        description=payload.description,
        source_test_case_id=payload.source_test_case_id
    )
    return tc

@router.get(
    "/applications/{id}/database-test-cases",
    response_model=List[DatabaseTestCaseResponse],
    summary="List database test cases for application"
)
def list_application_database_test_cases(
    id: int,
    db: Session = Depends(get_db)
):
    repo = DatabaseQARepository(db)
    return repo.get_test_cases_by_application(id)

# --- EXECUTION & EVIDENCE ---
@router.post(
    "/database-test-cases/{id}/execute",
    response_model=DatabaseTestExecutionResponse,
    summary="Execute a single database validation test case"
)
async def execute_database_test_case(
    id: int,
    db: Session = Depends(get_db)
):
    runner = DatabaseTestRunner(db)
    try:
        exec_res = await runner.execute_test_case(id)
        return exec_res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database execution error: {str(e)}"
        )

@router.post(
    "/applications/{id}/database-test-cases/execute-all",
    response_model=List[DatabaseTestExecutionResponse],
    summary="Execute all database test cases for application"
)
async def execute_all_database_test_cases(
    id: int,
    connection_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    repo = DatabaseQARepository(db)
    if connection_id:
        test_cases = repo.get_test_cases_by_connection(connection_id)
    else:
        test_cases = repo.get_test_cases_by_application(id)

    runner = DatabaseTestRunner(db)
    results = []
    for tc in test_cases:
        try:
            res = await runner.execute_test_case(tc.id)
            results.append(res)
        except Exception as e:
            logger.error(f"Error executing DB test #{tc.id}: {e}")

    return results

@router.get(
    "/database-test-cases/{id}/executions",
    response_model=List[DatabaseTestExecutionResponse],
    summary="Get execution history and evidence for database test case"
)
def get_test_case_executions(
    id: int,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    repo = DatabaseQARepository(db)
    return repo.get_executions_by_test_case(id, limit=limit)

@router.get(
    "/database-test-executions/{id}",
    response_model=DatabaseTestExecutionResponse,
    summary="Get detailed execution result and evidence"
)
def get_execution_details(
    id: int,
    db: Session = Depends(get_db)
):
    repo = DatabaseQARepository(db)
    rec = repo.get_execution_details(id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Execution #{id} not found")
    return rec
