from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from app.core.enums import UserStatus, UserType


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    refresh_token: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

class ChangePassword(BaseModel):
    current_password: str
    new_password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class UserCreate(BaseModel):
    email: EmailStr
    phone: Optional[str] = None
    password: str
    first_name: str
    last_name: str
    user_type: UserType = UserType.internal
    company_id: Optional[int] = None
    branch_id: Optional[int] = None
    department: Optional[str] = None
    job_title: Optional[str] = None

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    branch_id: Optional[int] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    avatar_url: Optional[str] = None
    status: Optional[UserStatus] = None

class UserOut(BaseModel):
    id: int
    email: str
    phone: Optional[str]
    first_name: str
    last_name: str
    full_name: str
    user_type: str
    status: str
    company_id: int
    branch_id: Optional[int]
    department: Optional[str]
    job_title: Optional[str]
    is_superadmin: bool
    last_login: Optional[datetime]
    created_at: datetime
    model_config = {"from_attributes": True}

class MeResponse(UserOut):
    pass

class AssignRoles(BaseModel):
    role_ids: List[int]

class RoleCreate(BaseModel):
    company_id: int
    name: str
    description: Optional[str] = None

class RoleOut(BaseModel):
    id: int
    company_id: int
    name: str
    description: Optional[str]
    is_system: bool
    model_config = {"from_attributes": True}

class AuditLogOut(BaseModel):
    id: int
    user_id: Optional[int]
    actor_id: Optional[int]
    action: str
    success: bool
    ip_address: Optional[str]
    detail: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}
