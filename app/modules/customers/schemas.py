from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from app.core.enums import CustomerType, CustomerStatus, CustomerRiskLevel, KYCStatus, KYCLevel


class CustomerCreate(BaseModel):
    company_id: Optional[int] = None
    first_name: str
    last_name: str
    company_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: str = "Cameroon"
    customer_type: CustomerType = CustomerType.retail

class CustomerUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    customer_type: Optional[CustomerType] = None

class BlacklistRequest(BaseModel):
    reason: str

class CustomerOut(BaseModel):
    id: int
    customer_code: str
    first_name: str
    last_name: str
    full_name: str
    company_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    customer_type: str
    status: str
    risk_level: str
    is_vip: bool
    kyc_status: str
    kyc_level: str
    credit_balance: float
    outstanding_balance: float
    created_at: datetime
    model_config = {"from_attributes": True}

class KYCSubmit(BaseModel):
    document_type: str
    document_number: Optional[str] = None
    document_url: str

class KYCReview(BaseModel):
    decision: str   # "verified" | "rejected"
    note: Optional[str] = None

class KYCOut(BaseModel):
    id: int
    customer_id: int
    document_type: str
    status: str
    submitted_at: datetime
    reviewed_at: Optional[datetime]
    model_config = {"from_attributes": True}

class ContactCreate(BaseModel):
    name: str
    role: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    is_primary: bool = False

class ContactOut(BaseModel):
    id: int
    name: str
    role: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    is_primary: bool
    model_config = {"from_attributes": True}

class NoteCreate(BaseModel):
    content: str

class NoteOut(BaseModel):
    id: int
    content: str
    created_by: int
    created_at: datetime
    model_config = {"from_attributes": True}

class SupplierCreate(BaseModel):
    company_id: Optional[int] = None
    name: str
    code: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    currency: str = "XAF"
    payment_terms: int = 30

class SupplierOut(BaseModel):
    id: int
    company_id: int
    name: str
    code: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    country: Optional[str]
    currency: str
    is_active: bool
    model_config = {"from_attributes": True}
