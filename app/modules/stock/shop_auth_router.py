"""
TEHTEK Shop — Customer portal auth (no staff auth required).

Endpoints:
  POST /api/v1/shop/auth/register  — create a portal account
  POST /api/v1/shop/auth/login     — login, get access + refresh tokens
  POST /api/v1/shop/auth/refresh   — rotate refresh token
  POST /api/v1/shop/auth/logout    — revoke refresh token
  GET  /api/v1/shop/auth/me        — current customer profile
  PATCH /api/v1/shop/auth/me       — update profile
  GET  /api/v1/shop/auth/orders    — customer's shop orders
"""
import json
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, field_validator, model_validator
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.enums import CustomerType, SequenceType, UserType
from app.core.security import (
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expiry,
    validate_password_strength,
    verify_password,
)
from app.modules.companies.controller import next_sequence
from app.modules.companies.models import Company
from app.modules.customers.models import Customer
from app.modules.stock.shop_order_models import ShopOrder
from app.modules.users.models import RefreshToken, User

router = APIRouter(prefix="/api/v1/shop/auth", tags=["shop-customer-auth"])

_TOKEN_TYPE   = "shop_customer"
_TOKEN_EXPIRE = 60 * 24  # 24 h for portal customers


# ── JWT ───────────────────────────────────────────────────────────────────────

def _create_access_token(user_id: int, customer_id: int) -> str:
    payload = {
        "sub":         str(user_id),
        "customer_id": customer_id,
        "token_type":  _TOKEN_TYPE,
        "exp":         datetime.utcnow() + timedelta(minutes=_TOKEN_EXPIRE),
        "type":        "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _get_customer(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> tuple:
    """Dependency — verify Bearer is a shop_customer token, return (user, customer)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Non authentifié")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("token_type") != _TOKEN_TYPE:
            raise HTTPException(403, "Type de token invalide")
        user_id     = int(payload["sub"])
        customer_id = int(payload["customer_id"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(401, "Token invalide ou expiré")

    user     = db.query(User).filter(User.id == user_id,         User.deleted_at.is_(None)).first()
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.deleted_at.is_(None)).first()
    if not user or not customer:
        raise HTTPException(401, "Compte introuvable")
    return user, customer


# ── Helpers ───────────────────────────────────────────────────────────────────

def _synthetic_email(phone: str) -> str:
    """Generate a placeholder email for phone-only accounts (never shown to user)."""
    normalized = phone.strip().replace("+", "").replace(" ", "").replace("-", "")
    return f"tel_{normalized}@tehtek.portal"


# ── Schemas ───────────────────────────────────────────────────────────────────

class RegisterIn(BaseModel):
    first_name: str
    last_name:  str
    email:      Optional[EmailStr] = None  # email OR phone required
    phone:      Optional[str] = None
    password:   str

    @model_validator(mode="after")
    def require_email_or_phone(self):
        if not self.email and not self.phone:
            raise ValueError("Email ou numéro de téléphone requis")
        return self


class LoginIn(BaseModel):
    """identifier = email address OR phone number."""
    identifier: str
    password:   str


class RefreshIn(BaseModel):
    refresh_token: str

class ProfilePatch(BaseModel):
    first_name: Optional[str] = None
    last_name:  Optional[str] = None
    phone:      Optional[str] = None
    whatsapp:   Optional[str] = None
    address:    Optional[str] = None
    city:       Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _issue(user: User, customer: Customer, db: Session) -> dict:
    access            = _create_access_token(user.id, customer.id)
    raw_refresh, h    = generate_refresh_token()
    db.add(RefreshToken(
        token_hash=h,
        user_id=user.id,
        expires_at=refresh_token_expiry(days=30),
    ))
    db.commit()
    return {"access_token": access, "refresh_token": raw_refresh, "token_type": "bearer"}


def _profile(c: Customer) -> dict:
    return {
        "id":            c.id,
        "customer_code": c.customer_code,
        "first_name":    c.first_name,
        "last_name":     c.last_name,
        "email":         c.email,
        "phone":         c.phone,
        "whatsapp":      c.whatsapp,
        "address":       c.address,
        "city":          c.city,
        "country":       c.country,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    """Create a portal customer account (email OR phone required)."""
    if not validate_password_strength(body.password):
        raise HTTPException(400, "Mot de passe trop faible (8 caractères min, 1 majuscule, 1 chiffre)")

    # Determine the email stored in the users table
    # — real email if provided, synthetic placeholder if phone-only
    user_email = str(body.email) if body.email else _synthetic_email(body.phone)

    # Conflict checks
    if db.query(User).filter(User.email == user_email).first():
        raise HTTPException(409, "Un compte existe déjà avec cet email" if body.email else "Un compte existe déjà avec ce numéro")
    if body.phone and db.query(User).filter(User.phone == body.phone).first():
        raise HTTPException(409, "Un compte existe déjà avec ce numéro de téléphone")

    company = db.query(Company).filter(Company.code == "TEHTEK").first()
    if not company:
        raise HTTPException(500, "Erreur de configuration serveur")

    user = User(
        email=user_email,
        phone=body.phone or None,
        hashed_password=hash_password(body.password),
        first_name=body.first_name,
        last_name=body.last_name,
        user_type=UserType.external,
        status="active",
        company_id=company.id,
    )
    db.add(user)
    db.flush()

    code     = next_sequence(db, SequenceType.customer_code)
    customer = Customer(
        company_id=company.id,
        customer_code=code,
        user_id=user.id,
        first_name=body.first_name,
        last_name=body.last_name,
        email=str(body.email) if body.email else None,  # real email only
        phone=body.phone or None,
        customer_type=CustomerType.retail,
        status="active",
        risk_level="low",
        kyc_status="not_submitted",
        kyc_level="basic",
        country="Cameroon",
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)

    tokens = _issue(user, customer, db)
    return {**tokens, "customer": _profile(customer)}


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    """Login by email or phone number."""
    identifier = body.identifier.strip()
    base_q = db.query(User).filter(
        User.user_type == UserType.external,
        User.deleted_at.is_(None),
    )

    if "@" in identifier:
        # Email login
        user = base_q.filter(User.email == identifier).first()
    else:
        # Phone login — try phone field, then synthetic email
        user = base_q.filter(User.phone == identifier).first()
        if not user:
            user = base_q.filter(User.email == _synthetic_email(identifier)).first()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(401, "Identifiant ou mot de passe incorrect")

    customer = db.query(Customer).filter(
        Customer.user_id == user.id,
        Customer.deleted_at.is_(None),
    ).first()
    if not customer:
        raise HTTPException(401, "Profil client introuvable")

    tokens = _issue(user, customer, db)
    return {**tokens, "customer": _profile(customer)}


@router.post("/refresh")
def refresh(body: RefreshIn, db: Session = Depends(get_db)):
    """Rotate refresh token (single-use)."""
    h  = hash_refresh_token(body.refresh_token)
    rt = db.query(RefreshToken).filter(
        RefreshToken.token_hash == h,
        RefreshToken.is_used == False,  # noqa: E712
    ).first()
    if not rt or rt.expires_at < datetime.utcnow():
        raise HTTPException(401, "Refresh token invalide ou expiré")

    rt.is_used = True
    db.flush()

    user     = db.query(User).filter(User.id == rt.user_id).first()
    customer = db.query(Customer).filter(
        Customer.user_id == rt.user_id,
        Customer.deleted_at.is_(None),
    ).first()
    if not user or not customer:
        raise HTTPException(401, "Compte introuvable")

    return _issue(user, customer, db)


@router.post("/logout")
def logout(body: RefreshIn, db: Session = Depends(get_db)):
    """Revoke refresh token."""
    h  = hash_refresh_token(body.refresh_token)
    rt = db.query(RefreshToken).filter(RefreshToken.token_hash == h).first()
    if rt:
        rt.is_used    = True
        rt.revoked_at = datetime.utcnow()
        db.commit()
    return {"ok": True}


@router.get("/me")
def get_me(auth=Depends(_get_customer)):
    _, customer = auth
    return _profile(customer)


@router.patch("/me")
def update_me(
    body: ProfilePatch,
    auth=Depends(_get_customer),
    db: Session = Depends(get_db),
):
    _, customer = auth
    for field in ("first_name", "last_name", "phone", "whatsapp", "address", "city"):
        val = getattr(body, field)
        if val is not None:
            setattr(customer, field, val)
    db.commit()
    db.refresh(customer)
    return _profile(customer)


@router.get("/orders")
def get_my_orders(auth=Depends(_get_customer), db: Session = Depends(get_db)):
    """
    Return the last 50 shop orders matching the customer's confirmed identifiers.
    - email match  → orders placed with the same email address
    - phone match  → orders placed with the same phone number
    Only fields actually set on the customer profile are used for matching.
    """
    _, customer = auth

    # Build OR filter using only the confirmed identifiers
    filters = []
    if customer.email:
        filters.append(ShopOrder.customer_email == customer.email)
    if customer.phone:
        filters.append(ShopOrder.customer_phone == customer.phone)

    if not filters:
        return []

    orders = (
        db.query(ShopOrder)
        .filter(or_(*filters))
        .order_by(ShopOrder.created_at.desc())
        .limit(50)
        .all()
    )
    result = []
    for o in orders:
        try:
            items = json.loads(o.items_json) if o.items_json else []
        except Exception:
            items = []
        result.append({
            "order_ref":      o.order_ref,
            "status":         o.status,
            "payment_status": o.payment_status,
            "payment_method": o.payment_method,
            "subtotal":       float(o.subtotal),
            "items":          items,
            "created_at":     o.created_at.isoformat(),
        })
    return result


# ── Customer shipments ────────────────────────────────────────────────────────

@router.get("/shipments")
def get_my_shipments(auth=Depends(_get_customer), db: Session = Depends(get_db)):
    """Return all cargo shipments belonging to the authenticated customer."""
    from app.modules.cargo.models import Shipment, TrackingEvent
    _, customer = auth
    shipments = (
        db.query(Shipment)
        .filter_by(customer_id=customer.id)
        .order_by(Shipment.created_at.desc())
        .limit(100)
        .all()
    )
    result = []
    for s in shipments:
        last_event = (
            db.query(TrackingEvent)
            .filter_by(shipment_id=s.id, is_public=True)
            .order_by(TrackingEvent.created_at.desc())
            .first()
        )
        result.append({
            "id":               s.id,
            "tracking_number":  s.tracking_number,
            "status":           s.status,
            "shipment_type":    s.shipment_type,
            "route":            s.route_legacy,
            "sender_name":      s.sender_name,
            "receiver_name":    s.receiver_name,
            "receiver_country": s.receiver_country,
            "weight_kg":        float(s.weight_kg) if s.weight_kg else None,
            "declared_value":   float(s.declared_value) if s.declared_value else None,
            "declared_value_currency": s.declared_value_currency,
            "created_at":       s.created_at.isoformat(),
            "last_event":       last_event.event_type if last_event else None,
            "last_event_at":    last_event.created_at.isoformat() if last_event else None,
            "last_location":    last_event.location if last_event else None,
        })
    return result


@router.get("/shipments/{tracking_number}")
def get_my_shipment(tracking_number: str, auth=Depends(_get_customer), db: Session = Depends(get_db)):
    """Return a specific shipment with full tracking timeline (customer must own it)."""
    from app.modules.cargo.models import Shipment, TrackingEvent, ShipmentItem
    _, customer = auth
    shipment = db.query(Shipment).filter_by(
        tracking_number=tracking_number.upper(),
        customer_id=customer.id,
    ).first()
    if not shipment:
        raise HTTPException(404, "Expédition introuvable")

    events = (
        db.query(TrackingEvent)
        .filter_by(shipment_id=shipment.id, is_public=True)
        .order_by(TrackingEvent.created_at.asc())
        .all()
    )
    items = (
        db.query(ShipmentItem)
        .filter_by(shipment_id=shipment.id)
        .order_by(ShipmentItem.sort_order)
        .all()
    )

    return {
        "id":               shipment.id,
        "tracking_number":  shipment.tracking_number,
        "status":           shipment.status,
        "shipment_type":    shipment.shipment_type,
        "route":            shipment.route_legacy,
        "priority":         shipment.priority,
        "sender_name":      shipment.sender_name,
        "sender_phone":     shipment.sender_phone,
        "receiver_name":    shipment.receiver_name,
        "receiver_phone":   shipment.receiver_phone,
        "receiver_country": shipment.receiver_country,
        "receiver_address": shipment.receiver_address,
        "weight_kg":        float(shipment.weight_kg) if shipment.weight_kg else None,
        "declared_value":   float(shipment.declared_value) if shipment.declared_value else None,
        "declared_value_currency": shipment.declared_value_currency,
        "content_description": shipment.content_description,
        "delivery_type":    shipment.delivery_type,
        "insurance_status": shipment.insurance_status,
        "created_at":       shipment.created_at.isoformat(),
        "items": [
            {
                "description":   it.description,
                "quantity":      float(it.quantity),
                "unit":          it.unit,
                "weight_kg":     float(it.weight_kg) if it.weight_kg else None,
                "tracking_number": it.tracking_number,
            }
            for it in items
        ],
        "events": [
            {
                "event_type":  e.event_type,
                "description": e.description,
                "location":    e.location,
                "timestamp":   e.created_at.isoformat(),
                "photos":      e.photos or [],
            }
            for e in events
        ],
    }


@router.get("/shipments/{tracking_number}/invoice")
def get_my_shipment_invoice(tracking_number: str, auth=Depends(_get_customer), db: Session = Depends(get_db)):
    """Return the invoice for a customer's shipment (if one exists)."""
    from app.modules.cargo.models import Shipment
    from app.modules.finance.models import Invoice, Payment
    _, customer = auth
    shipment = db.query(Shipment).filter_by(
        tracking_number=tracking_number.upper(),
        customer_id=customer.id,
    ).first()
    if not shipment:
        raise HTTPException(404, "Expédition introuvable")

    inv = (
        db.query(Invoice)
        .filter_by(ref_model="shipment", ref_id=shipment.id)
        .filter(Invoice.status != "cancelled")
        .order_by(Invoice.id.desc())
        .first()
    )
    if not inv:
        raise HTTPException(404, "Aucune facture pour cette expédition")

    payments = db.query(Payment).filter_by(invoice_id=inv.id).all()
    return {
        "id":             inv.id,
        "invoice_number": inv.invoice_number,
        "status":         inv.status,
        "total":          float(inv.total),
        "paid_amount":    float(inv.paid_amount or 0),
        "balance_due":    float(inv.balance_due or 0),
        "currency":       inv.currency,
        "created_at":     inv.created_at.isoformat(),
        "payments": [
            {
                "amount":         float(p.amount),
                "currency":       p.currency,
                "payment_method": p.payment_method,
                "confirmed_at":   p.confirmed_at.isoformat() if p.confirmed_at else None,
            }
            for p in payments
        ],
    }


# ── Pickup requests ───────────────────────────────────────────────────────────

class PickupRequestIn(BaseModel):
    address:             str
    city:                Optional[str] = None
    content_description: Optional[str] = None
    estimated_weight_kg: Optional[float] = None
    destination_country: Optional[str] = None
    receiver_name:       Optional[str] = None
    receiver_phone:      Optional[str] = None
    preferred_date:      Optional[str] = None   # YYYY-MM-DD
    notes:               Optional[str] = None


@router.post("/pickup-requests", status_code=201)
def create_pickup_request(body: PickupRequestIn, auth=Depends(_get_customer), db: Session = Depends(get_db)):
    """Customer submits a pickup request."""
    from app.modules.cargo.models import PickupRequest
    from app.core.enums import SequenceType
    _, customer = auth

    number = next_sequence(db, SequenceType.pickup_request)
    req = PickupRequest(
        company_id=customer.company_id,
        customer_id=customer.id,
        pickup_number=number,
        address=body.address.strip(),
        city=body.city,
        notes="\n".join(filter(None, [
            f"Description: {body.content_description}" if body.content_description else None,
            f"Poids estimé: {body.estimated_weight_kg} kg" if body.estimated_weight_kg else None,
            f"Destination: {body.destination_country}" if body.destination_country else None,
            f"Destinataire: {body.receiver_name} {body.receiver_phone or ''}" if body.receiver_name else None,
            f"Date souhaitée: {body.preferred_date}" if body.preferred_date else None,
            body.notes or None,
        ])) or None,
        status="pending",
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return {
        "id":             req.id,
        "pickup_number":  req.pickup_number,
        "status":         req.status,
        "address":        req.address,
        "city":           req.city,
        "created_at":     req.created_at.isoformat(),
    }


@router.get("/pickup-requests")
def list_pickup_requests(auth=Depends(_get_customer), db: Session = Depends(get_db)):
    """List customer's pickup requests."""
    from app.modules.cargo.models import PickupRequest
    _, customer = auth
    reqs = (
        db.query(PickupRequest)
        .filter_by(customer_id=customer.id)
        .order_by(PickupRequest.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id":            r.id,
            "pickup_number": r.pickup_number,
            "status":        r.status,
            "address":       r.address,
            "city":          r.city,
            "notes":         r.notes,
            "created_at":    r.created_at.isoformat(),
            "shipment_id":   r.shipment_id,
        }
        for r in reqs
    ]
