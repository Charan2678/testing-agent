from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class TestStepBase(BaseModel):
    sequence: int = Field(..., example=1)
    action: str = Field(..., example="click")
    target: str = Field(..., example="#submit-btn")
    value: Optional[str] = Field(None, example="admin@example.com")
    expected_result: Optional[str] = Field(None, example="User reaches dashboard with status 200")
    source_page_id: Optional[int] = None
    source_element_id: Optional[int] = None

class TestStepResponse(TestStepBase):
    id: int
    test_case_id: int

    class Config:
        from_attributes = True

class TestCaseBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, example="TC-001 Valid Login")
    description: Optional[str] = Field(None, example="Verify that existing user can log in with valid credentials")
    category: str = Field(default="functional", example="smoke")  # smoke, functional, e2e, negative, boundary, authentication, authorization, form validation
    priority: str = Field(default="medium", example="high")  # critical, high, medium, low
    preconditions: List[str] = Field(default_factory=list, example=["User credentials exist in database"])
    status: str = Field(default="active")

class TestCaseCreate(TestCaseBase):
    workflow_id: Optional[int] = None
    steps: List[TestStepBase] = []

class TestCaseResponse(TestCaseBase):
    id: int
    application_id: int
    workflow_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    steps_count: int = 0
    steps: List[TestStepResponse] = []

    class Config:
        from_attributes = True

# --- STRICT AI STRUCTURED OUTPUT SCHEMAS ---

class AIWorkflowStepModel(BaseModel):
    sequence: int
    action: str
    expected_behavior: str
    target_page_url: str  # Must match an observed page URL
    target_element_selector: Optional[str] = None  # Must match an observed element selector if applicable

class AIWorkflowModel(BaseModel):
    name: str
    description: str
    risk_level: str = "medium"  # critical, high, medium, low
    steps: List[AIWorkflowStepModel]

class AITestStepModel(BaseModel):
    sequence: int
    action: str  # navigate, click, fill, select, assert
    target: str  # page URL or CSS selector
    value: Optional[str] = None
    expected_result: str
    source_page_url: str
    source_element_selector: Optional[str] = None

class AITestCaseModel(BaseModel):
    name: str
    workflow_name: str
    category: str  # smoke, functional, e2e, negative, boundary, authentication, form validation, navigation
    priority: str  # critical, high, medium, low
    description: str
    preconditions: List[str]
    steps: List[AITestStepModel]

class AIAnalysisOutput(BaseModel):
    summary: str
    workflows: List[AIWorkflowModel]
    test_cases: List[AITestCaseModel]
