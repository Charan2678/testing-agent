from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class BugEvidenceResponse(BaseModel):
    id: int
    bug_id: int
    type: str
    file_path: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class BugResponse(BaseModel):
    id: int
    application_id: int
    environment_id: Optional[int] = None
    title: str
    summary: Optional[str] = None
    description: Optional[str] = None
    classification: str
    category: str
    severity: str
    priority: str
    status: str
    affected_page: Optional[str] = None
    affected_workflow_id: Optional[int] = None
    affected_test_case_id: Optional[int] = None
    affected_execution_id: Optional[int] = None
    failed_step: Optional[str] = None
    expected_behavior: Optional[str] = None
    actual_behavior: Optional[str] = None
    root_cause: Optional[str] = None
    root_cause_confidence: Optional[int] = 50
    confidence_level: Optional[str] = "LIKELY"
    severity_explanation: Optional[str] = None
    failure_signature: Optional[str] = None
    occurrence_count: int = 1
    created_at: datetime
    updated_at: datetime
    evidence: List[BugEvidenceResponse] = []

    class Config:
        from_attributes = True

class BugStatusUpdate(BaseModel):
    status: str = Field(..., example="TRIAGED")

class BugSummaryResponse(BaseModel):
    has_bugs: bool
    total_bugs: int
    open_bugs: int
    critical_bugs: int
    high_bugs: int
    medium_bugs: int
    low_bugs: int
    resolved_bugs: int

class BugCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    summary: Optional[str] = None
    description: Optional[str] = None
    classification: str = Field(default="APPLICATION_BUG")
    category: str = Field(default="FUNCTIONAL")
    severity: str = Field(default="MEDIUM")
    priority: str = Field(default="MEDIUM")
    affected_page: Optional[str] = None
    expected_behavior: Optional[str] = None
    actual_behavior: Optional[str] = None
    root_cause: Optional[str] = None
