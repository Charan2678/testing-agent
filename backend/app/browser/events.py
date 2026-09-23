from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class ConsoleMessageEvent(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    type: str  # log, warning, error, info, debug
    text: str
    location: Optional[Dict[str, Any]] = None
    args: Optional[List[str]] = None

class NetworkRequestEvent(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    url: str
    method: str
    resource_type: Optional[str] = None
    status: Optional[int] = None
    status_text: Optional[str] = None
    failed: bool = False
    failure_error: Optional[str] = None
    duration_ms: Optional[float] = None
    request_headers: Optional[Dict[str, str]] = None
    response_headers: Optional[Dict[str, str]] = None

class DiscoveredElement(BaseModel):
    element_type: str
    tag_name: str
    selector: str
    text: Optional[str] = None
    name: Optional[str] = None
    placeholder: Optional[str] = None
    role: Optional[str] = None
    is_interactive: bool = True
    attributes: Optional[Dict[str, str]] = None

class DiscoveredPage(BaseModel):
    url: str
    title: Optional[str] = None
    status_code: Optional[int] = None
    screenshot_path: Optional[str] = None
    elements: List[DiscoveredElement] = []
    internal_links: List[str] = []
