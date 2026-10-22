from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, model_validator, EmailStr
from app.core.enums import CustomerType, CustomerStatus, CustomerRiskLevel, KYCStatus, KYCLevel


class CustomerCreate(BaseModel):
    company_id: Optional[int] = None

    # A person is created with one full name; a company with its name. The
    # split first/last pair is still accepted for the shop portal, which
    # collects them separately at sign-up.
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None

    entity_type: str = "individual"
    nui: Optional[str] = None
    bp: Optional[str] = None
    fax: Optional[str] = None

    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None

    address: Optional[str] = None
    city: Optional[str] = None
    country: str = "Cameroon"

    customer_type: CustomerType = CustomerType.retail

    @model_validator(mode="after")
    def _require_a_name(self):
        """A customer must be identifiable: a company by its name, a person by
        theirs. Which one is required depends entirely on the entity type."""
        if self.entity_type == "company":
            if not (self.company_name or "").strip():
                raise ValueError("Company name is required for a company.")
        else:
            has_name = (self.full_name or "").strip() or (self.first_name or "").strip()
            if not has_name:
                raise ValueError("Full name is required for an individual.")
        return self


class CustomerUpdate(BaseModel):
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None

    entity_type: Optional[str] = None
    nui: Optional[str] = None
    bp: Optional[str] = None
    fax: Optional[str] = None

    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None

    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None

    customer_type: Optional[CustomerType] = None

class BlacklistRequest(BaseModel):
    reason: str

class CustomerOut(BaseModel):
    id: int
    customer_code: str
    pending_projects_total: float = 0.0  # uninvoiced active projects (computed)
    outstanding_by_currency: dict = {}       # {"XAF": 1200000, "USD": 2500}
    pending_by_currency: dict = {}
    awaiting_by_currency: dict = {}          # livré / terminé, en attente de paiement
    confirmed_by_currency: dict = {}         # confirmé mais pas encore livré
    payment_sources: list = []               # ventilation par objet source

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: str
    company_name: Optional[str]

    entity_type: str
    nui: Optional[str]
    bp: Optional[str]
    fax: Optional[str]

    email: Optional[str]
    phone: Optional[str]
    whatsapp: Optional[str]

    address: Optional[str]
    city: Optional[str]
    country: Optional[str]

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

class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    currency: Optional[str] = None
    payment_terms: Optional[int] = None
    is_active: Optional[bool] = None

class SupplierOut(BaseModel):
    id: int
    company_id: int
    name: str
    code: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    city: Optional[str]
    country: Optional[str]
    currency: str
    payment_terms: int
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}
