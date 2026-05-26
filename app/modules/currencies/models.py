from sqlalchemy import Column, String, Float, Boolean, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class Currency(Base):
    __tablename__ = "currencies"

    code         = Column(String(10), primary_key=True)   # XAF, USD, EUR, CNY
    name         = Column(String(100), nullable=False)
    symbol       = Column(String(10), nullable=True)
    rate_to_xaf  = Column(Float, nullable=False, default=1.0)  # 1 unit of this = X XAF
    is_active    = Column(Boolean, nullable=False, default=True)
    updated_at   = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
