from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

# --- CONNECTIONS ---
class DatabaseConnectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, example="CRM Test DB")
    database_type: str = Field(..., example="sqlite")  # postgresql, mysql, sqlite
    database_name: str = Field(..., example="test-app/crm_development.db")
    environment_id: Optional[int] = None
    host: Optional[str] = Field(None, example="127.0.0.1")
    port: Optional[int] = Field(None, example=5432)
    username: Optional[str] = Field(None, example="qa_readonly")
    password: Optional[str] = Field(None, example="secret")
    read_only: bool = Field(True, description="Strict read-only safety flag")

class DatabaseConnectionResponse(BaseModel):
    id: int
    application_id: int
    environment_id: Optional[int] = None
    name: str
    database_type: str
    host: Optional[str] = None
    port: Optional[int] = None
    database_name: str
    username: Optional[str] = None
    read_only: bool
    status: str
    last_tested_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ConnectionTestResponse(BaseModel):
    status: str  # CONNECTED, FAILED, BLOCKED
    message: Optional[str] = None

# --- SCHEMA DISCOVERY ---
class DatabaseColumnResponse(BaseModel):
    id: int
    column_name: str
    data_type: str
    nullable: bool
    is_primary_key: bool
    is_foreign_key: bool
    default_value: Optional[str] = None

    class Config:
        from_attributes = True

class DatabaseRelationshipResponse(BaseModel):
    id: int
    source_column: str
    target_column: str
    relationship_type: str
    related_table_id: Optional[int] = None
    related_table_name: Optional[str] = None

    class Config:
        from_attributes = True

class DatabaseTableResponse(BaseModel):
    id: int
    table_name: str
    row_count: int
    description: Optional[str] = None
    columns: List[DatabaseColumnResponse] = []
    relationships: List[DatabaseRelationshipResponse] = []

    class Config:
        from_attributes = True

class DatabaseSchemaResponse(BaseModel):
    id: int
    schema_name: str
    discovered_at: datetime
    tables: List[DatabaseTableResponse] = []

    class Config:
        from_attributes = True

# --- TEST CASES ---
class DatabaseTestCaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    database_connection_id: int
    category: str = Field(default="DATA_INTEGRITY")  # DATA_INTEGRITY, CRUD_VALIDATION, REFERENTIAL_INTEGRITY, NULLABILITY
    priority: str = Field(default="HIGH")  # CRITICAL, HIGH, MEDIUM, LOW
    validation_definition: Dict[str, Any]
    description: Optional[str] = None
    source_test_case_id: Optional[int] = None

class DatabaseTestCaseResponse(BaseModel):
    id: int
    application_id: int
    environment_id: Optional[int] = None
    database_connection_id: int
    name: str
    description: Optional[str] = None
    category: str
    priority: str
    source_test_case_id: Optional[int] = None
    validation_definition: Dict[str, Any]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

# --- EXECUTIONS & EVIDENCE ---
class DatabaseEvidenceResponse(BaseModel):
    id: int
    sanitized_query: str
    parameters: Optional[Dict[str, Any]] = None
    comparison_summary: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

class DatabaseTestExecutionResponse(BaseModel):
    id: int
    database_test_case_id: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: int
    expected_result: Optional[Dict[str, Any]] = None
    actual_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    evidence: List[DatabaseEvidenceResponse] = []

    class Config:
        from_attributes = True

class DatabaseSummaryResponse(BaseModel):
    connection_id: Optional[int] = None
    name: Optional[str] = None
    database_type: Optional[str] = None
    status: Optional[str] = None
    read_only: Optional[bool] = None
    schemas_count: int = 0
    tables_count: int = 0
    columns_count: int = 0
    relationships_count: int = 0
    test_cases_count: int = 0
    executions_total: int = 0
    executions_passed: int = 0
    executions_failed: int = 0
    executions_blocked: int = 0
    last_tested_at: Optional[str] = None
