from pydantic import BaseModel, EmailStr
from typing import Optional

class StaffCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: str
    phone: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None

class UserStatusPayload(BaseModel):
    is_active: bool

class StaffUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
