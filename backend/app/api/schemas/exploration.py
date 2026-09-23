from datetime import datetime
from typing import Optional, List
from urllib.parse import urlparse
from pydantic import BaseModel, Field, field_validator
from backend.app.database.models.models import ExplorationStatus
from backend.app.api.schemas.evidence import EvidenceResponse

class ExplorationCreate(BaseModel):
    application_id: int
    environment_id: int
    target_url: Optional[str] = None
    max_pages: Optional[int] = Field(default=30, ge=1, le=100)
    max_depth: Optional[int] = Field(default=3, ge=1, le=10)

    @field_validator("target_url")
    @classmethod
    def validate_target_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("Target URL cannot be empty")
        parsed = urlparse(v)
        if parsed.scheme.lower() not in ("http", "https"):
            raise ValueError(f"Target URL must use http or https protocol (got '{parsed.scheme or 'none'}')")
        if not parsed.netloc:
            raise ValueError(f"Target URL must include a valid host: '{v}'")
        return v

class ExplorationResponse(BaseModel):
    id: int
    application_id: int
    environment_id: int
    target_url: Optional[str] = None
    status: ExplorationStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    pages_discovered: int = 0
    actions_discovered: int = 0
    error_count: int = 0

    class Config:
        from_attributes = True

class ExplorationStatusResponse(BaseModel):
    id: int
    status: ExplorationStatus
    pages_discovered: int
    actions_discovered: int
    error_count: int
    current_url: Optional[str] = None
    target_url: Optional[str] = None
    url_source: Optional[str] = None
    activity_log: List[str] = []

class ExplorationDetailResponse(ExplorationResponse):
    evidence: List[EvidenceResponse] = []
