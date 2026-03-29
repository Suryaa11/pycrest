from pydantic import BaseModel

class AdminRejectPayload(BaseModel):
    reason: str | None = None

class AdminApprovePayload(BaseModel):
    approved_amount: float | None = None
    interest_rate: float | None = None
