from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from backend.app.database.models.models import ActionType

class ElementBase(BaseModel):
    element_type: str = Field(..., example="button")
    tag_name: str = Field(..., example="button")
    selector: str = Field(..., example="#submit-btn")
    text: Optional[str] = None
    name: Optional[str] = None
    placeholder: Optional[str] = None
    role: Optional[str] = None
    is_interactive: bool = True

class ElementResponse(ElementBase):
    id: int
    page_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class ActionBase(BaseModel):
    action_type: ActionType
    action_data: Optional[Dict[str, Any]] = None
    result: Optional[str] = None

class ActionResponse(ActionBase):
    id: int
    page_id: int
    element_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class PageBase(BaseModel):
    url: str
    title: Optional[str] = None
    status_code: Optional[int] = None
    page_type: Optional[str] = "standard"

class PageResponse(PageBase):
    id: int
    application_id: int
    environment_id: int
    first_seen_at: datetime
    last_seen_at: datetime
    elements_count: Optional[int] = 0

    class Config:
        from_attributes = True

class PageDetailResponse(PageResponse):
    elements: List[ElementResponse] = []
    actions: List[ActionResponse] = []
