"""
TEHTEK — Security helpers
JWT creation/verification, bcrypt hashing, refresh token rotation.
Rules: UR-007, UR-008, UR-009, UR-010
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Passwords ─────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def validate_password_strength(password: str) -> bool:
    """UR-005: min 8 chars, 1 uppercase, 1 digit."""
    if len(password) < 8:
        return False
    if not any(c.isupper() for c in password):
        return False
    if not any(c.isdigit() for c in password):
        return False
    return True


# ── Access tokens (JWT) ───────────────────────────────────────────────────────

def create_access_token(
    user_id: int,
    company_id: int,
    branch_id: Optional[int],
    is_superadmin: bool,
    expire_minutes: Optional[int] = None,
) -> str:
    """UR-007: 60 min lifetime (staff). Payload includes company_id + branch_id."""
    expire = datetime.utcnow() + timedelta(
        minutes=expire_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(user_id),
        "company_id": company_id,
        "branch_id": branch_id,
        "is_superadmin": is_superadmin,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Returns decoded payload or raises JWTError."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


# ── Refresh tokens ────────────────────────────────────────────────────────────

def generate_refresh_token() -> tuple[str, str]:
    """
    UR-008: Generate a cryptographically random refresh token.
    Returns (raw_token, token_hash).
    Store only the hash. Send the raw token to the client.
    """
    raw = secrets.token_urlsafe(64)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def refresh_token_expiry(days: Optional[int] = None) -> datetime:
    return datetime.utcnow() + timedelta(days=days or settings.REFRESH_TOKEN_EXPIRE_DAYS)


# ── Password reset tokens ─────────────────────────────────────────────────────

def generate_reset_token() -> tuple[str, datetime]:
    """UR-010: single-use, 30-min expiry."""
    token = secrets.token_urlsafe(32)
    expiry = datetime.utcnow() + timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES)
    return token, expiry
