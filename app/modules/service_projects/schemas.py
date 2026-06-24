"""
app/modules/service_projects/schemas.py

Key bridges vs original:
  ServiceTypeCreate/Out  : +code, +unit
  MilestoneCreate        : title accepted (frontend); description kept for back-compat
  MilestoneOut           : service_project_id (alias project_id), title, line_total
  ServiceProjectCreate   : title in milestones, apply_tva
  ServiceProjectOut      : project_number (alias reference), apply_tva, timestamps
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.modules.service_projects.models import ServiceCategory, ServiceProjectStatus


# ── ServiceType ───────────────────────────────────────────────────────────────

class ServiceTypeCreate(BaseModel):
    code:        Optional[str]     = None        # auto-generated from name if omitted
    name:        str
    unit:        str               = "forfait"
    category:    ServiceCategory   = ServiceCategory.other
    description: Optional[str]    = None
    unit_price:  Optional[Decimal] = None
    is_active:   bool              = True

    @field_validator("code", mode="before")
    @classmethod
    def upper_code(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().upper() if v else None


class ServiceTypeUpdate(BaseModel):
    name:        Optional[str]             = None
    unit:        Optional[str]             = None
    category:    Optional[ServiceCategory] = None
    description: Optional[str]            = None
    unit_price:  Optional[Decimal]         = None
    is_active:   Optional[bool]            = None


class ServiceTypeOut(BaseModel):
    id:          int
    code:        str
    name:        str
    unit:        str
    category:    ServiceCategory
    description: Optional[str]
    unit_price:  Optional[Decimal]
    is_active:   bool
    created_at:  datetime

    model_config = {"from_attributes": True}


# ── ServiceMilestone ──────────────────────────────────────────────────────────

class MilestoneCreate(BaseModel):
    service_type_id: Optional[int]  = None
    title:           Optional[str]  = None    # frontend sends this
    description:     Optional[str]  = None    # legacy; falls back to title
    quantity:        Decimal         = Decimal("1")
    unit_price:      Decimal         = Decimal("0")
    sort_order:      int             = 0

    @model_validator(mode="after")
    def ensure_description(self) -> "MilestoneCreate":
        """Backend stores in description; title is the new name for it."""
        if self.title and not self.description:
            self.description = self.title
        elif self.description and not self.title:
            self.title = self.description
        return self


class MilestoneUpdate(BaseModel):
    title:       Optional[str]     = None
    description: Optional[str]     = None
    quantity:    Optional[Decimal] = None
    unit_price:  Optional[Decimal] = None
    progress:    Optional[int]     = Field(None, ge=0, le=100)
    sort_order:  Optional[int]     = None


class MilestoneOut(BaseModel):
    id:                 int
    # Frontend expects service_project_id; model has project_id
    service_project_id: int            = Field(validation_alias="project_id")
    service_type_id:    Optional[int]  = None
    title:              str            = ""
    description:        Optional[str]  = None
    quantity:           Decimal
    unit_price:         Decimal
    line_total:         Decimal        = Decimal("0")
    progress:           int
    sort_order:         int
    service_type:       Optional[ServiceTypeOut] = None

    model_config = {"from_attributes": True, "populate_by_name": True}

    @model_validator(mode="before")
    @classmethod
    def backfill_fields(cls, obj):
        """Fill title from description and line_total from total for old rows."""
        if hasattr(obj, "__dict__"):          # SQLAlchemy ORM instance
            if not obj.title and obj.description:
                obj.title = obj.description
            lt = getattr(obj, "line_total", None)
            t  = getattr(obj, "total", None)
            if (lt is None or lt == 0) and t:
                obj.line_total = t
        return obj


# ── ServiceProject ────────────────────────────────────────────────────────────

class ServiceProjectCreate(BaseModel):
    title:           str
    customer_id:     int
    service_type_id: Optional[int]         = None
    category:        ServiceCategory       = ServiceCategory.other
    currency:        str                   = "XAF"
    site_address:    Optional[str]         = None
    start_date:      Optional[str]         = None   # "YYYY-MM-DD" string from frontend
    end_date:        Optional[str]         = None
    technician:      Optional[str]         = None
    apply_tva:       bool                  = False
    tax_type:        str                   = "none"   # none | tva | retenue
    tax_rate:        float                 = 0         # percent
    price_inclusive: bool                  = False     # entered prices are TTC
    notes:           Optional[str]         = None
    milestones:      List[MilestoneCreate] = []


class ServiceProjectUpdate(BaseModel):
    title:           Optional[str]                  = None
    customer_id:     Optional[int]                  = None
    service_type_id: Optional[int]                  = None
    category:        Optional[ServiceCategory]       = None
    status:          Optional[ServiceProjectStatus]  = None
    site_address:    Optional[str]                  = None
    start_date:      Optional[str]                  = None
    end_date:        Optional[str]                  = None
    technician:      Optional[str]                  = None
    apply_tva:       Optional[bool]                 = None
    tax_type:        Optional[str]                  = None
    tax_rate:        Optional[float]                = None
    price_inclusive: Optional[bool]                 = None
    discount_amount: Optional[Decimal]              = None
    notes:           Optional[str]                  = None
    cancel_reason:   Optional[str]                  = None


class SkipBrPayload(BaseModel):
    reason: Optional[str] = None


class ServiceProjectOut(BaseModel):
    id:             int
    # Frontend expects project_number; model column is reference
    project_number: str                 = Field(validation_alias="reference")
    customer_id:    int
    title:          str
    status:         ServiceProjectStatus
    category:       ServiceCategory

    currency:        str = "XAF"
    subtotal:        Decimal
    discount_amount: Decimal
    tax_amount:      Decimal
    retenue_amount:  Decimal = Decimal("0")
    total:           Decimal
    tax_type:        str   = "none"
    tax_rate:        Decimal = Decimal("0")
    price_inclusive: bool  = False

    site_address: Optional[str]
    start_date:   Optional[datetime]
    end_date:     Optional[datetime]
    technician:   Optional[str]
    notes:        Optional[str]

    apply_tva:   bool = False

    skip_br:             bool
    skip_br_reason:      Optional[str]
    skip_br_approved_by: Optional[int] = None

    proposal_sent_at: Optional[datetime] = None
    signed_at:        Optional[datetime] = None
    bl_sent_at:       Optional[datetime] = None
    br_received_at:   Optional[datetime] = None
    invoiced_at:      Optional[datetime] = None

    milestones:  List[MilestoneOut] = []
    created_at:  datetime
    updated_at:  datetime

    model_config = {"from_attributes": True, "populate_by_name": True}
