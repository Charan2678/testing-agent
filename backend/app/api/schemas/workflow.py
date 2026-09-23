from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class WorkflowStepBase(BaseModel):
    sequence: int = Field(..., example=1)
    action: str = Field(..., example="Navigate to Login")
    expected_behavior: Optional[str] = Field(None, example="Login page renders with username and password fields")
    page_id: Optional[int] = None
    element_id: Optional[int] = None

class WorkflowStepResponse(WorkflowStepBase):
    id: int
    workflow_id: int

    class Config:
        from_attributes = True

class WorkflowBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, example="Authentication Flow")
    description: Optional[str] = Field(None, example="Handles user login, credential validation, and guest bypass")
    risk_level: str = Field(default="medium", example="high")  # critical, high, medium, low

class WorkflowCreate(WorkflowBase):
    steps: List[WorkflowStepBase] = []

class WorkflowResponse(WorkflowBase):
    id: int
    application_id: int
    discovered_at: datetime
    steps_count: int = 0
    steps: List[WorkflowStepResponse] = []

    class Config:
        from_attributes = True
