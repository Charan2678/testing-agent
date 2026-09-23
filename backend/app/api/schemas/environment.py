from datetime import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl, Field
from backend.app.database.models.models import EnvironmentType

class EnvironmentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, example="Development")
    base_url: str = Field(..., min_length=1, max_length=500, example="http://localhost:3000")
    environment_type: EnvironmentType = Field(default=EnvironmentType.DEV)

class EnvironmentCreate(EnvironmentBase):
    pass

class EnvironmentResponse(EnvironmentBase):
    id: int
    application_id: int
    created_at: datetime

    class Config:
        from_attributes = True
