"""TEHTEK — Users Controller. Auth, roles, refresh tokens, audit logging."""
import json
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import AuditAction, UserStatus
from app.core.security import (
    create_access_token, generate_refresh_token, hash_password,
    hash_refresh_token, refresh_token_expiry, validate_password_strength,
    verify_password, generate_reset_token,
)
from app.modules.users.models import (
    Permission, RefreshToken, Role, RolePermission,
    User, UserAuditLog, UserRole, PermissionFlagUser
)

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


# ── Audit helpers ─────────────────────────────────────────────────────────────

def log_audit(
    db: Session,
    action: str,
    success: bool,
    user_id: Optional[int] = None,
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    detail: Optional[dict] = None,
) -> None:
    """UR-003, UR-006: Insert-only audit record. Never update/delete."""
    db.add(UserAuditLog(
        user_id=user_id,
        actor_id=actor_id,
        action=action,
        success=success,
        ip_address=ip_address,
        user_agent=user_agent,
        detail=json.dumps(detail) if detail else None,
    ))
    db.flush()


def _ip(request: Optional[Request]) -> Optional[str]:
    if not request:
        return None
    forwarded = request.headers.get("X-Forwarded-For")
    return forwarded.split(",")[0].strip() if forwarded else request.client.host


def _ua(request: Optional[Request]) -> Optional[str]:
    return request.headers.get("User-Agent") if request else None


# ── Login ─────────────────────────────────────────────────────────────────────

def login(
    db: Session,
    email: str,
    password: str,
    request: Optional[Request] = None,
) -> dict:
    """UR-002: lockout after 5 failures. UR-003: all attempts logged."""
    user = db.query(User).filter(
        User.email == email, User.deleted_at.is_(None)
    ).first()

    def fail(msg: str):
        if user:
            user.failed_login_count += 1
            if user.failed_login_count >= MAX_FAILED_ATTEMPTS:
                user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
                log_audit(db, AuditAction.account_locked, True,
                          user_id=user.id, ip_address=_ip(request), user_agent=_ua(request))
            db.flush()
        log_audit(db, AuditAction.login_failed, False,
                  user_id=user.id if user else None,
                  ip_address=_ip(request), user_agent=_ua(request),
                  detail={"reason": msg})
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=msg)

    if not user:
        fail("Invalid credentials")

    if user.locked_until and user.locked_until > datetime.utcnow():
        fail("Account temporarily locked. Try again later.")

    if user.status != UserStatus.active:
        fail("Account is not active")

    if not verify_password(password, user.hashed_password):
        fail("Invalid credentials")

    # Success — reset counters
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login = datetime.utcnow()

    # Issue tokens
    access_token = create_access_token(
        user.id, user.company_id, user.branch_id, user.is_superadmin
    )
    raw_refresh, refresh_hash = generate_refresh_token()
    db.add(RefreshToken(
        token_hash=refresh_hash,
        user_id=user.id,
        expires_at=refresh_token_expiry(),
        ip_address=_ip(request),
        user_agent=_ua(request),
    ))
    log_audit(db, AuditAction.login_success, True,
              user_id=user.id, actor_id=user.id,
              ip_address=_ip(request), user_agent=_ua(request))
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
        "must_change_password": user.must_change_password,
        "user": user,
    }


# ── Refresh (single-use rotation) ────────────────────────────────────────────

def refresh_tokens(
    db: Session,
    raw_refresh_token: str,
    request: Optional[Request] = None,
) -> dict:
    """UR-008: rotation. UR-009: replay → invalidate ALL sessions."""
    token_hash = hash_refresh_token(raw_refresh_token)
    stored = db.query(RefreshToken).filter_by(token_hash=token_hash).first()

    if not stored:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Replay attack detected (UR-009)
    if stored.is_used:
        # Revoke ALL refresh tokens for this user
        db.query(RefreshToken).filter_by(
            user_id=stored.user_id, revoked_at=None
        ).update({"revoked_at": datetime.utcnow()})
        log_audit(db, AuditAction.token_replay_detected, True,
                  user_id=stored.user_id,
                  ip_address=_ip(request), user_agent=_ua(request),
                  detail={"token_id": stored.id})
        db.commit()
        raise HTTPException(
            status_code=401,
            detail="Security alert: session invalidated. Please log in again."
        )

    if stored.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh token expired")

    if stored.revoked_at:
        raise HTTPException(status_code=401, detail="Refresh token revoked")

    user = db.query(User).filter_by(id=stored.user_id).first()
    if not user or user.status != UserStatus.active:
        raise HTTPException(status_code=401, detail="User not active")

    # Mark old token as used, issue new pair
    stored.is_used = True
    access_token = create_access_token(
        user.id, user.company_id, user.branch_id, user.is_superadmin
    )
    raw_new, new_hash = generate_refresh_token()
    db.add(RefreshToken(
        token_hash=new_hash,
        user_id=user.id,
        expires_at=refresh_token_expiry(),
        ip_address=_ip(request),
        user_agent=_ua(request),
    ))
    log_audit(db, AuditAction.token_refreshed, True,
              user_id=user.id, actor_id=user.id,
              ip_address=_ip(request), user_agent=_ua(request))
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": raw_new,
        "token_type": "bearer",
    }


# ── Logout ────────────────────────────────────────────────────────────────────

def logout(db: Session, user: User, raw_refresh_token: str, request=None) -> None:
    token_hash = hash_refresh_token(raw_refresh_token)
    stored = db.query(RefreshToken).filter_by(token_hash=token_hash).first()
    if stored:
        stored.revoked_at = datetime.utcnow()
    log_audit(db, AuditAction.logout, True,
              user_id=user.id, actor_id=user.id,
              ip_address=_ip(request), user_agent=_ua(request))
    db.commit()


# ── Password reset (UR-010) ───────────────────────────────────────────────────

def request_password_reset(db: Session, email: str) -> Optional[str]:
    """Returns raw token to be sent via email/SMS. None if user not found (silent fail)."""
    user = db.query(User).filter(
        User.email == email, User.deleted_at.is_(None)
    ).first()
    if not user:
        return None  # Don't reveal whether email exists
    token, expiry = generate_reset_token()
    user.reset_token = token
    user.reset_token_expiry = expiry
    log_audit(db, AuditAction.password_reset_requested, True, user_id=user.id)
    db.commit()
    return token


def confirm_password_reset(db: Session, token: str, new_password: str) -> None:
    if not validate_password_strength(new_password):
        raise HTTPException(400, "Password too weak (min 8 chars, 1 uppercase, 1 digit)")
    user = db.query(User).filter(
        User.reset_token == token,
        User.reset_token_expiry > datetime.utcnow(),
    ).first()
    if not user:
        raise HTTPException(400, "Invalid or expired reset token")
    user.hashed_password = hash_password(new_password)
    user.reset_token = None
    user.reset_token_expiry = None
    log_audit(db, AuditAction.password_reset_completed, True, user_id=user.id)
    db.commit()


# ── Users CRUD ────────────────────────────────────────────────────────────────

def create_user(db: Session, data: dict, actor: User) -> User:
    if not validate_password_strength(data.get("password", "")):
        raise HTTPException(400, "Password too weak (min 8 chars, 1 uppercase, 1 digit)")
    payload = {k: v for k, v in data.items() if k != "password"}
    payload["hashed_password"] = hash_password(data["password"])
    payload["created_by"] = actor.id
    # Non-superadmin can only create users in their own company (ACC-004)
    if not actor.is_superadmin:
        payload["company_id"] = actor.company_id
    user = User(**payload)
    db.add(user)
    db.flush()
    log_audit(db, AuditAction.user_created, True,
              user_id=user.id, actor_id=actor.id,
              detail={"email": user.email})
    db.commit()
    db.refresh(user)
    return user


def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(
        User.id == user_id, User.deleted_at.is_(None)
    ).first()


def list_users(db: Session, actor: User, skip: int = 0, limit: int = 50):
    q = db.query(User).filter(User.deleted_at.is_(None))
    if not actor.is_superadmin:
        q = q.filter(User.company_id == actor.company_id)
    return q.offset(skip).limit(limit).all()


def update_user(db: Session, user: User, data: dict, actor: User) -> User:
    # UR-004: protect superadmin
    if user.is_superadmin and actor.id != user.id:
        raise HTTPException(403, "Cannot modify superadmin account")
    for k, v in data.items():
        setattr(user, k, v)
    user.updated_at = datetime.utcnow()
    log_audit(db, AuditAction.user_updated, True,
              user_id=user.id, actor_id=actor.id)
    db.commit()
    db.refresh(user)
    return user


def suspend_user(db: Session, user: User, actor: User) -> User:
    if user.is_superadmin:
        raise HTTPException(403, "Cannot suspend superadmin")
    user.status = UserStatus.suspended
    user.updated_at = datetime.utcnow()
    log_audit(db, AuditAction.user_suspended, True,
              user_id=user.id, actor_id=actor.id)
    db.commit()
    return user


def soft_delete_user(db: Session, user: User, actor: User) -> None:
    if user.is_superadmin:
        raise HTTPException(403, "Cannot delete superadmin")
    user.deleted_at = datetime.utcnow()
    log_audit(db, AuditAction.user_deleted, True,
              user_id=user.id, actor_id=actor.id)
    db.commit()


# ── Roles ─────────────────────────────────────────────────────────────────────

def assign_roles(db: Session, user: User, role_ids: list[int], actor: User) -> User:
    # Remove existing, add new
    db.query(UserRole).filter_by(user_id=user.id).delete()
    for rid in role_ids:
        db.add(UserRole(user_id=user.id, role_id=rid, granted_by=actor.id))
    log_audit(db, AuditAction.role_assigned, True,
              user_id=user.id, actor_id=actor.id,
              detail={"role_ids": role_ids})
    db.commit()
    db.refresh(user)
    return user


def get_user_audit_log(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return (
        db.query(UserAuditLog)
        .filter(UserAuditLog.user_id == user_id)
        .order_by(UserAuditLog.created_at.desc())
        .offset(skip).limit(limit).all()
    )


# -- Superadmin seed ----------------------------------------------------------

def seed_superadmin(db: Session, company_id: int) -> bool:
    """
    Creates the superadmin on first launch if they don't exist.
    Returns True if created, False if already existed.
    """
    existing = db.query(User).filter_by(email=settings.SUPERADMIN_EMAIL).first()
    if existing:
        return False

    if not validate_password_strength(settings.SUPERADMIN_PASSWORD):
        raise ValueError(
            "SUPERADMIN_PASSWORD is too weak -- min 8 chars, 1 uppercase, 1 digit"
        )

    db.add(User(
        email=settings.SUPERADMIN_EMAIL,
        phone=settings.SUPERADMIN_PHONE or None,
        hashed_password=hash_password(settings.SUPERADMIN_PASSWORD),
        first_name=settings.SUPERADMIN_FIRST_NAME,
        last_name=settings.SUPERADMIN_LAST_NAME,
        user_type="internal",
        status=UserStatus.active,
        company_id=company_id,
        is_superadmin=True,
        must_change_password=True,  # force password update on first login
    ))
    db.commit()
    return True
