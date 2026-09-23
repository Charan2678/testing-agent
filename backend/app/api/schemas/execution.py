from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class GeneratedTestResponse(BaseModel):
    id: int
    test_case_id: int
    framework: str
    language: str
    file_path: str
    generated_code: str
    generation_version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TestExecutionStepResponse(BaseModel):
    id: int
    execution_id: int
    test_step_id: Optional[int] = None
    sequence: int
    action: str
    target: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    actual_result: Optional[str] = None

    class Config:
        from_attributes = True

class ExecutionEvidenceResponse(BaseModel):
    id: int
    execution_id: int
    type: str
    file_path: Optional[str] = None
    description: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

class TestExecutionResponse(BaseModel):
    id: int
    test_case_id: int
    environment_id: Optional[int] = None
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    final_url: Optional[str] = None
    created_at: datetime
    steps: List[TestExecutionStepResponse] = []
    evidence: List[ExecutionEvidenceResponse] = []

    class Config:
        from_attributes = True

class ExecutionSummaryResponse(BaseModel):
    has_executions: bool
    total_executions: int
    passed: int
    failed: int
    blocked: int
    skipped: int
    errors: int
    pass_rate: float
    avg_duration_ms: int
