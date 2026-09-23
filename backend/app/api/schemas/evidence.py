from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel
from backend.app.database.models.models import EvidenceType

class EvidenceBase(BaseModel):
    type: EvidenceType
    file_path: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

class EvidenceResponse(EvidenceBase):
    id: int
    exploration_run_id: int
    created_at: datetime

    class Config:
        from_attributes = True
