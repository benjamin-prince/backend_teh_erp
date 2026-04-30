"""
TEHTEK — FastAPI Dependencies
get_current_user: applied at ROUTER level on every protected router (ACC-007).
require_permission: checks a specific permission key.
company_scope: enforces company_id + branch_id on queries (ACC-004).
"""
from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.core.enums import UserStatus

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    """
    ACC-007: Applied at router level — EVERY protected router uses this.
    Pattern:
        router = APIRouter(dependencies=[Depends(get_current_user)])

    Validates JWT, checks user is active and not locked.
    Returns the user ORM object.
    """
    from app.modules.users.models import User  # avoid circular import

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(credentials.credentials)
        if payload.get("type") != "access":
            raise credentials_exception
        user_id: Optional[int] = int(payload.get("sub"))
        if user_id is None:
            raise credentials_exception
    except (JWTError, ValueError):
        raise credentials_exception

    user = (
        db.query(User)
        .filter(User.id == user_id, User.deleted_at.is_(None))
        .first()
    )
    if user is None:
        raise credentials_exception

    # Account must be active (not suspended/inactive/locked)
    if user.status != UserStatus.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active",
        )

    # Check lockout (UR-002)
    if user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is temporarily locked. Try again later.",
        )

    return user


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: Session = Depends(get_db),
):
    """For public routes that optionally benefit from auth context (e.g. tracking)."""
    if not credentials:
        return None
    try:
        return get_current_user(credentials, db)
    except HTTPException:
        return None


def require_superadmin(current_user=Depends(get_current_user)):
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required",
        )
    return current_user


def require_permission(permission_key: str):
    """
    Factory: returns a FastAPI dependency that checks a specific permission.
    Usage: Depends(require_permission("cargo:dispatch"))

    Permission resolution (ACC-003):
      1. Superadmin → always granted
      2. Union of all role permissions
      3. Individual permission_flags can add or restrict
    """
    def checker(current_user=Depends(get_current_user)):
        if current_user.is_superadmin:
            return current_user

        # Collect all permission keys from all roles
        granted_keys = set()
        for user_role in current_user.roles:
            for rp in user_role.role.permissions:
                granted_keys.add(rp.permission.key)

        # Apply individual permission_flags (can add OR restrict)
        for flag in current_user.permission_flags:
            if flag.granted:
                granted_keys.add(flag.permission_key)
            else:
                granted_keys.discard(flag.permission_key)

        if permission_key not in granted_keys:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission_key}' required",
            )
        return current_user

    return checker


def enforce_company_scope(current_user, query, model):
    """
    ACC-004: Scope every query to user.company_id (and branch_id if set).
    Superadmin bypasses scoping.
    """
    if current_user.is_superadmin:
        return query
    query = query.filter(model.company_id == current_user.company_id)
    if current_user.branch_id and hasattr(model, "branch_id"):
        query = query.filter(
            (model.branch_id == current_user.branch_id) | (model.branch_id.is_(None))
        )
    return query
