"""TEHTEK — public contact form for teh-cargo.com.

No auth: this is the website's own form (ACC-008 public route). It stores the
enquiry and pings the owner on WhatsApp, reusing the notification path the
assistant already uses in production — the backend has no mail transport, and a
WhatsApp ping reaches Benjamin faster than an email would anyway.

Abuse control is deliberately modest, matching the traffic of a one-city
shipping business: a hidden honeypot field plus a per-IP rate limit.
"""
import time
from datetime import datetime
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import Session

from app.core.database import Base, get_db

router = APIRouter(prefix="/api/v1/cargo", tags=["cargo-public"])

MAX_PER_HOUR = 5
_hits: dict[str, list[float]] = {}
_hits_lock = Lock()


class CargoWebEnquiry(Base):
    """A message left on the public site. Table created by create_all."""
    __tablename__ = "cargo_web_enquiries"

    id         = Column(Integer, primary_key=True)
    name       = Column(String(200), nullable=False)
    contact    = Column(String(255), nullable=False)   # phone or email, as typed
    mode       = Column(String(20),  nullable=True)    # sea | air | vehicle | other
    message    = Column(Text,        nullable=False)
    lang       = Column(String(5),   nullable=True)
    source_ip  = Column(String(64),  nullable=True)
    handled_at = Column(DateTime,    nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class EnquiryIn(BaseModel):
    name:    str = Field(min_length=1, max_length=200)
    contact: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1, max_length=4000)
    mode:    str | None = Field(default=None, max_length=20)
    lang:    str | None = Field(default=None, max_length=5)
    website: str | None = None   # honeypot — hidden in the form, bots fill it


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return (fwd.split(",")[0].strip() if fwd else None) or (
        request.client.host if request.client else "unknown"
    )


def _rate_limited(ip: str) -> bool:
    now = time.time()
    with _hits_lock:
        seen = [t for t in _hits.get(ip, []) if now - t < 3600]
        if len(seen) >= MAX_PER_HOUR:
            _hits[ip] = seen
            return True
        seen.append(now)
        _hits[ip] = seen
    return False


@router.post("/web-enquiry", status_code=201)
def create_web_enquiry(body: EnquiryIn, request: Request, db: Session = Depends(get_db)):
    # A filled honeypot is a bot: answer 201 so it never learns it was caught.
    if body.website:
        return {"ok": True}

    ip = _client_ip(request)
    if _rate_limited(ip):
        raise HTTPException(429, "Trop de messages envoyés. Réessayez plus tard.")

    row = CargoWebEnquiry(
        name=body.name.strip(),
        contact=body.contact.strip(),
        mode=(body.mode or None),
        message=body.message.strip(),
        lang=(body.lang or None),
        source_ip=ip,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    try:
        from app.modules.whatsapp.assistant import _notify_admin
        _notify_admin(
            "🌐 teh-cargo.com — nouveau message\n"
            f"Nom : {row.name}\n"
            f"Contact : {row.contact}\n"
            f"Type : {row.mode or '—'}\n\n"
            f"{row.message[:600]}"
        )
    except Exception:
        # The enquiry is already saved; a failed ping must not lose it.
        pass

    return {"ok": True, "id": row.id}
