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
