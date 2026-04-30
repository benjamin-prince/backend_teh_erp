from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, field_validator
from app.core.enums import CompanyType, BranchType, DepartmentType, ApprovalStatus, ApprovalType


class CompanyCreate(BaseModel):
    name: str
    code: str
    company_type: CompanyType = CompanyType.subsidiary
    parent_id: Optional[int] = None
    country: str = "Cameroon"
    currency: str = "XAF"

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    country: Optional[str] = None
    is_active: Optional[bool] = None

class CompanyOut(BaseModel):
    id: int
    name: str
    code: str
    company_type: str
    parent_id: Optional[int]
    country: str
    currency: str
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class BranchCreate(BaseModel):
    company_id: int
    name: str
    code: str
    branch_type: BranchType = BranchType.headquarters
    address: Optional[str] = None
    city: Optional[str] = None
    country: str = "Cameroon"
    phone: Optional[str] = None
    email: Optional[str] = None

class BranchOut(BaseModel):
    id: int
    company_id: int
    name: str
    code: str
    branch_type: str
    city: Optional[str]
    country: str
    is_active: bool
    model_config = {"from_attributes": True}


class DepartmentCreate(BaseModel):
    company_id: int
    name: str
    department_type: DepartmentType = DepartmentType.operations
    manager_id: Optional[int] = None

class DepartmentOut(BaseModel):
    id: int
    company_id: int
    name: str
    department_type: str
    model_config = {"from_attributes": True}


class TeamCreate(BaseModel):
    department_id: int
    name: str
    lead_id: Optional[int] = None

class TeamOut(BaseModel):
    id: int
    department_id: int
    name: str
    model_config = {"from_attributes": True}


class ApprovalCreate(BaseModel):
    company_id: int
    approval_type: ApprovalType
    reason: str
    ref_model: Optional[str] = None
    ref_id: Optional[int] = None
    amount: Optional[float] = None

class ApprovalDecide(BaseModel):
    decision: str   # "approved" | "rejected"
    reason: str

class ApprovalOut(BaseModel):
    id: int
    company_id: int
    approval_type: str
    status: str
    requested_by: int
    approved_by: Optional[int]
    reason: str
    decision_reason: Optional[str]
    ref_model: Optional[str]
    ref_id: Optional[int]
    amount: Optional[float]
    created_at: datetime
    model_config = {"from_attributes": True}


class SequenceOut(BaseModel):
    sequence_type: str
    prefix: str
    current_value: int
    model_config = {"from_attributes": True}
