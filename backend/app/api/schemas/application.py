from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from backend.app.api.schemas.environment import EnvironmentResponse

class ApplicationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, example="CRM Platform")
    description: Optional[str] = Field(default=None, example="Internal sales and customer management tool")

class ApplicationCreate(ApplicationBase):
    pass

class ApplicationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None

class ApplicationResponse(ApplicationBase):
    id: int
    created_at: datetime
    updated_at: datetime
    environments: List[EnvironmentResponse] = []

    class Config:
        from_attributes = True
