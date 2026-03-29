from pydantic import BaseModel, EmailStr


class AdminRejectPayload(BaseModel):
    reason: str | None = None


class AdminApprovePayload(BaseModel):
    approved_amount: float | None = None
    interest_rate: float | None = None


class ApplyPenaltyPayload(BaseModel):
    penalty_amount: float
    reason: str | None = None


class ProcessDefaultsPayload(BaseModel):
    grace_days: int | None = None
    penalty_rate: float | None = None
    freeze_after_missed: int | None = None


class StaffCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: str
    phone: str | None = None
    department: str | None = None
    designation: str | None = None
    employee_code: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None


class UserStatusPayload(BaseModel):
    is_active: bool


class StaffUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    password: str | None = None
    role: str | None = None
    is_active: bool | None = None
    phone: str | None = None
    department: str | None = None
    designation: str | None = None
    employee_code: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
