from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CurrencyCreate(BaseModel):
    code:        str
    name:        str
    symbol:      Optional[str] = None
    rate_to_xaf: float = Field(..., gt=0)


class CurrencyUpdate(BaseModel):
    name:        Optional[str] = None
    symbol:      Optional[str] = None
    rate_to_xaf: Optional[float] = Field(None, gt=0)
    is_active:   Optional[bool] = None


class CurrencyOut(BaseModel):
    code:        str
    name:        str
    symbol:      Optional[str]
    rate_to_xaf: float
    is_active:   bool
    updated_at:  Optional[datetime]

    class Config:
        from_attributes = True
