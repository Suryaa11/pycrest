from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class AuditLogItem(BaseModel):
    id: str
    action: str
    actor_id: str
    actor_role: str
    entity_type: str
    entity_id: str
    created_at: datetime
    details: Optional[dict] = None

class AuditLogResponse(BaseModel):
    items: List[AuditLogItem]
    total: int
    page: Optional[int] = None
    page_size: Optional[int] = None
