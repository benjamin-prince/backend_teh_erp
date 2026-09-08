"""TEHTEK — public pickup booking for teh-cargo.com.

The website's booking form posts here. Public by design (ACC-008), guarded the
same way as the contact form: hidden honeypot plus a per-IP hourly limit.

The customer also sends the summary themselves on WhatsApp from the site. That
is deliberate: their own message opens the 24-hour window the Cloud API needs
before we can write back, and it reaches the business phone even when the
owner notification cannot be delivered.
"""
import json
import time
from datetime import datetime
from threading import Lock

import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base, get_db

router = APIRouter(prefix="/api/v1/cargo", tags=["cargo-public"])

MAX_PER_HOUR = 8
MAX_PHOTO_BYTES = 8 * 1024 * 1024
_hits: dict[str, list[float]] = {}
_lock = Lock()


class CargoPickupBooking(Base):
    """A pickup requested from the public site. Table created by create_all."""
    __tablename__ = "cargo_pickup_bookings"

    id             = Column(Integer, primary_key=True)
    name           = Column(String(200), nullable=False)
    phone          = Column(String(40),  nullable=False)
    items_json     = Column(Text,        nullable=False)   # [{key,label,qty}]
    photos_json    = Column(Text,        nullable=True)    # ["https://res.cloudinary…"]
    address        = Column(Text,        nullable=True)
    latitude       = Column(Numeric(10, 7), nullable=True)
    longitude      = Column(Numeric(10, 7), nullable=True)
    preferred_date = Column(String(40),  nullable=True)
    notes          = Column(Text,        nullable=True)
    lang           = Column(String(5),   nullable=True)
    status         = Column(String(20),  nullable=False, default="new")  # new|contacted|scheduled|done|cancelled
    source_ip      = Column(String(64),  nullable=True)
    handled_at     = Column(DateTime,    nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow, nullable=False)


class BookingItem(BaseModel):
    key:   str = Field(max_length=40)
    label: str = Field(max_length=200)
    qty:   int = Field(ge=1, le=999)


class BookingIn(BaseModel):
    name:           str = Field(min_length=1, max_length=200)
    phone:          str = Field(min_length=4, max_length=40)
    items:          list[BookingItem] = Field(min_length=1, max_length=20)
    photos:         list[str] = Field(default_factory=list, max_length=5)
    address:        str | None = Field(default=None, max_length=2000)
    latitude:       float | None = None
    longitude:      float | None = None
    preferred_date: str | None = Field(default=None, max_length=40)
    notes:          str | None = Field(default=None, max_length=2000)
    lang:           str | None = Field(default=None, max_length=5)
    website:        str | None = None   # honeypot


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return (fwd.split(",")[0].strip() if fwd else None) or (
        request.client.host if request.client else "unknown"
    )


def _rate_limited(ip: str, budget: int) -> bool:
    now = time.time()
    with _lock:
        seen = [t for t in _hits.get(ip, []) if now - t < 3600]
        if len(seen) >= budget:
            _hits[ip] = seen
            return True
        seen.append(now)
        _hits[ip] = seen
    return False


@router.post("/pickup-photo")
def upload_pickup_photo(request: Request, file: UploadFile = File(...)):
    """One photo of the goods, straight from the customer's phone."""
    if not (settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY
            and settings.CLOUDINARY_API_SECRET):
        raise HTTPException(503, "Stockage des photos indisponible.")
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Seules les images sont acceptées.")
    if _rate_limited(_client_ip(request), MAX_PER_HOUR * 3):
        raise HTTPException(429, "Trop d'envois. Réessayez plus tard.")

    blob = file.file.read(MAX_PHOTO_BYTES + 1)
    if len(blob) > MAX_PHOTO_BYTES:
        raise HTTPException(413, "Photo trop lourde (8 Mo maximum).")

    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
    )
    import io
    result = cloudinary.uploader.upload(
        io.BytesIO(blob),
        folder="tehcargo/pickups",
        resource_type="image",
        transformation=[{"width": 1600, "height": 1600, "crop": "limit", "quality": "auto"}],
    )
    return {"url": result["secure_url"]}


@router.post("/pickup", status_code=201)
def create_pickup(body: BookingIn, request: Request, db: Session = Depends(get_db)):
    if body.website:                      # bot: answer 201, tell it nothing
        return {"ok": True}

    ip = _client_ip(request)
    if _rate_limited(ip, MAX_PER_HOUR):
        raise HTTPException(429, "Trop de demandes envoyées. Réessayez plus tard.")

    if not body.address and (body.latitude is None or body.longitude is None):
        raise HTTPException(400, "Indiquez une adresse ou partagez votre position.")

    row = CargoPickupBooking(
        name=body.name.strip(),
        phone=body.phone.strip(),
        items_json=json.dumps([i.model_dump() for i in body.items], ensure_ascii=False),
        photos_json=json.dumps(body.photos, ensure_ascii=False) if body.photos else None,
        address=(body.address or None),
        latitude=body.latitude,
        longitude=body.longitude,
        preferred_date=(body.preferred_date or None),
        notes=(body.notes or None),
        lang=(body.lang or None),
        source_ip=ip,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    items = " · ".join(f"{i.qty}× {i.label}" for i in body.items)
    where = body.address or ""
    if body.latitude is not None and body.longitude is not None:
        where = (where + "\n" if where else "") + \
                f"https://maps.google.com/?q={body.latitude},{body.longitude}"

    try:
        from app.modules.whatsapp.assistant import _notify_admin
        _notify_admin(
            f"📦 Pick up demandé — #{row.id}\n"
            f"{row.name} · {row.phone}\n"
            f"{items}\n"
            f"{where}\n"
            + (f"Souhaité : {row.preferred_date}\n" if row.preferred_date else "")
            + (f"Photos : {len(body.photos)}\n" if body.photos else "")
            + (f"\n{row.notes}" if row.notes else "")
        )
    except Exception:
        pass   # the booking is saved; a failed ping must never lose it

    return {"ok": True, "id": row.id, "summary": f"{items}\n{where}"}


# ── Admin (ERP) ──────────────────────────────────────────────────────────────
# Read-only listing plus a status change, so the front desk can actually work
# these requests instead of querying the database by hand.

from fastapi import Query
from app.core.dependencies import require_permission
from app.modules.cargo.web_enquiry import CargoWebEnquiry

admin_router = APIRouter(prefix="/api/v1/cargo/admin", tags=["cargo-admin"])

PICKUP_STATUSES = ("new", "contacted", "scheduled", "done", "cancelled")


def _pickup_out(r: CargoPickupBooking) -> dict:
    return {
        "id": r.id, "name": r.name, "phone": r.phone,
        "items": json.loads(r.items_json) if r.items_json else [],
        "photos": json.loads(r.photos_json) if r.photos_json else [],
        "address": r.address,
        "latitude": float(r.latitude) if r.latitude is not None else None,
        "longitude": float(r.longitude) if r.longitude is not None else None,
        "maps_url": (f"https://maps.google.com/?q={r.latitude},{r.longitude}"
                     if r.latitude is not None and r.longitude is not None else None),
        "preferred_date": r.preferred_date, "notes": r.notes, "lang": r.lang,
        "status": r.status,
        "handled_at": r.handled_at.isoformat() if r.handled_at else None,
        "created_at": r.created_at.isoformat(),
    }


@admin_router.get("/pickups")
def list_pickups(status: str | None = Query(default=None),
                 limit: int = Query(default=100, le=500),
                 db: Session = Depends(get_db),
                 _=Depends(require_permission("cargo:shipments"))):
    q = db.query(CargoPickupBooking)
    if status:
        q = q.filter(CargoPickupBooking.status == status)
    rows = q.order_by(CargoPickupBooking.id.desc()).limit(limit).all()
    counts = {s: 0 for s in PICKUP_STATUSES}
    for s, n in (db.query(CargoPickupBooking.status,
                          func.count(CargoPickupBooking.id))
                   .group_by(CargoPickupBooking.status).all()):
        counts[s] = n
    return {"items": [_pickup_out(r) for r in rows], "counts": counts}


class PickupStatusIn(BaseModel):
    status: str


@admin_router.patch("/pickups/{pickup_id}")
def set_pickup_status(pickup_id: int, body: PickupStatusIn,
                      db: Session = Depends(get_db),
                      _=Depends(require_permission("cargo:shipments"))):
    if body.status not in PICKUP_STATUSES:
        raise HTTPException(400, f"Statut invalide. Attendu : {', '.join(PICKUP_STATUSES)}")
    row = db.query(CargoPickupBooking).filter_by(id=pickup_id).first()
    if not row:
        raise HTTPException(404, "Demande introuvable")
    row.status = body.status
    row.handled_at = datetime.utcnow() if body.status != "new" else None
    db.commit()
    db.refresh(row)
    return _pickup_out(row)


@admin_router.get("/enquiries")
def list_enquiries(limit: int = Query(default=100, le=500),
                   db: Session = Depends(get_db),
                   _=Depends(require_permission("cargo:shipments"))):
    rows = (db.query(CargoWebEnquiry)
              .order_by(CargoWebEnquiry.id.desc()).limit(limit).all())
    return {"items": [{
        "id": r.id, "name": r.name, "contact": r.contact, "mode": r.mode,
        "message": r.message, "lang": r.lang,
        "handled_at": r.handled_at.isoformat() if r.handled_at else None,
        "created_at": r.created_at.isoformat(),
    } for r in rows]}


@admin_router.patch("/enquiries/{enquiry_id}")
def toggle_enquiry(enquiry_id: int, db: Session = Depends(get_db),
                   _=Depends(require_permission("cargo:shipments"))):
    row = db.query(CargoWebEnquiry).filter_by(id=enquiry_id).first()
    if not row:
        raise HTTPException(404, "Message introuvable")
    row.handled_at = None if row.handled_at else datetime.utcnow()
    db.commit()
    return {"id": row.id, "handled_at": row.handled_at.isoformat() if row.handled_at else None}
