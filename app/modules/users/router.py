"""
TEHTEK — Users Router
ACC-007: All routes protected EXCEPT the public whitelist (ACC-008).
Public whitelist: login, refresh, password-reset/request, password-reset/confirm
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission, require_superadmin
from app.modules.users import controller, schemas
from app.modules.users.models import Role, User

# ── Public auth router (NO auth dependency — ACC-008 whitelist) ───────────────
auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@auth_router.post("/login", response_model=schemas.TokenResponse)
def login(body: schemas.LoginRequest, request: Request, db: Session = Depends(get_db)):
    result = controller.login(db, body.email, body.password, request)
    return schemas.TokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
    )

@auth_router.post("/refresh", response_model=schemas.TokenResponse)
def refresh(body: schemas.RefreshRequest, request: Request, db: Session = Depends(get_db)):
    return controller.refresh_tokens(db, body.refresh_token, request)

@auth_router.post("/password-reset/request", status_code=202)
def password_reset_request(body: schemas.PasswordResetRequest, db: Session = Depends(get_db)):
    controller.request_password_reset(db, body.email)
    # Always 202 — don't reveal whether email exists
    return {"message": "If that email is registered, a reset link has been sent."}

@auth_router.post("/password-reset/confirm", status_code=200)
def password_reset_confirm(body: schemas.PasswordResetConfirm, db: Session = Depends(get_db)):
    controller.confirm_password_reset(db, body.token, body.new_password)
    return {"message": "Password updated successfully."}


# ── Protected auth routes ─────────────────────────────────────────────────────
protected_auth_router = APIRouter(
    prefix="/api/v1/auth",
    tags=["auth"],
    dependencies=[Depends(get_current_user)],
)

@protected_auth_router.post("/logout", status_code=204)
def logout(
    body: schemas.LogoutRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    controller.logout(db, current_user, body.refresh_token, request)

@protected_auth_router.get("/me", response_model=schemas.MeResponse)
def me(current_user=Depends(get_current_user)):
    return current_user

@protected_auth_router.patch("/me/password", status_code=200)
def change_password(
    body: schemas.ChangePassword,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.core.security import verify_password, hash_password, validate_password_strength
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(400, "Current password is incorrect")
    if not validate_password_strength(body.new_password):
        raise HTTPException(400, "New password too weak (min 8 chars, 1 uppercase, 1 digit)")
    current_user.hashed_password = hash_password(body.new_password)
    db.commit()
    return {"message": "Password changed successfully."}


# ── Users router (all protected) ──────────────────────────────────────────────
users_router = APIRouter(
    prefix="/api/v1/users",
    tags=["users"],
    dependencies=[Depends(get_current_user)],
)

@users_router.post("", response_model=schemas.UserOut, status_code=201)
def create_user(
    body: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("users:create")),
):
    return controller.create_user(db, body.model_dump(), current_user)

@users_router.get("", response_model=list[schemas.UserOut])
def list_users(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("users:read")),
):
    return controller.list_users(db, current_user, skip, limit)

@users_router.get("/{user_id}", response_model=schemas.UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("users:read")),
):
    user = controller.get_user(db, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if not current_user.is_superadmin and user.company_id != current_user.company_id:
        raise HTTPException(403, "Access denied")
    return user

@users_router.patch("/{user_id}", response_model=schemas.UserOut)
def update_user(
    user_id: int,
    body: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("users:update")),
):
    user = controller.get_user(db, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return controller.update_user(db, user, body.model_dump(exclude_none=True), current_user)

@users_router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("users:delete")),
):
    user = controller.get_user(db, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    controller.soft_delete_user(db, user, current_user)

@users_router.put("/{user_id}/roles", response_model=schemas.UserOut)
def assign_roles(
    user_id: int,
    body: schemas.AssignRoles,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("roles:manage")),
):
    user = controller.get_user(db, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return controller.assign_roles(db, user, body.role_ids, current_user)

@users_router.get("/{user_id}/audit-log", response_model=list[schemas.AuditLogOut])
def get_audit_log(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _=Depends(require_permission("audit:read")),
):
    return controller.get_user_audit_log(db, user_id, skip, limit)


# ── Roles router (all protected) ──────────────────────────────────────────────
roles_router = APIRouter(
    prefix="/api/v1/roles",
    tags=["roles"],
    dependencies=[Depends(get_current_user)],
)

@roles_router.post("", response_model=schemas.RoleOut, status_code=201)
def create_role(
    body: schemas.RoleCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("roles:manage")),
):
    if not current_user.is_superadmin:
        body.company_id = current_user.company_id
    role = Role(**body.model_dump())
    db.add(role)
    db.commit()
    db.refresh(role)
    return role

@roles_router.get("", response_model=list[schemas.RoleOut])
def list_roles(
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("roles:manage")),
):
    q = db.query(Role).filter(Role.deleted_at.is_(None))
    if not current_user.is_superadmin:
        q = q.filter(Role.company_id == current_user.company_id)
    return q.all()

@roles_router.delete("/{role_id}", status_code=204)
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_permission("roles:manage")),
):
    role = db.query(Role).filter_by(id=role_id, deleted_at=None).first()
    if not role:
        raise HTTPException(404, "Role not found")
    if role.is_system:
        raise HTTPException(403, "Cannot delete a system role")
    from datetime import datetime
    role.deleted_at = datetime.utcnow()
    db.commit()
