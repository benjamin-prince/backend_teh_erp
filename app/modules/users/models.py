"""TEHTEK — Users Module Models. Rules: UR-001 to UR-010, ACC-007."""
from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey,
    Integer, String, Text, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.enums import UserStatus, UserType


class Permission(Base):
    """Master permission registry. Seeded from TEHTEK_ACCESS_MATRIX.md."""
    __tablename__ = "permissions"
    id          = Column(Integer, primary_key=True)
    key         = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    module      = Column(String(50), nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)
    role_permissions = relationship("RolePermission", back_populates="permission")


class Role(Base):
    __tablename__ = "roles"
    id          = Column(Integer, primary_key=True)
    company_id  = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name        = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_system   = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at  = Column(DateTime, nullable=True)
    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_role_name_per_company"),
    )
    permissions = relationship("RolePermission", back_populates="role")
    user_roles  = relationship("UserRole", back_populates="role")


class RolePermission(Base):
    __tablename__ = "role_permissions"
    id            = Column(Integer, primary_key=True)
    role_id       = Column(Integer, ForeignKey("roles.id"), nullable=False)
    permission_id = Column(Integer, ForeignKey("permissions.id"), nullable=False)
    granted_by    = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )
    role       = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="role_permissions")


class User(Base):
    __tablename__ = "users"
    id              = Column(Integer, primary_key=True)
    email           = Column(String(255), unique=True, nullable=False)
    phone           = Column(String(30), unique=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    first_name      = Column(String(100), nullable=False)
    last_name       = Column(String(100), nullable=False)
    user_type       = Column(String(30), nullable=False, default=UserType.internal)
    status          = Column(String(30), nullable=False, default=UserStatus.pending)
    company_id      = Column(Integer, ForeignKey("companies.id"), nullable=False)
    branch_id       = Column(Integer, ForeignKey("branches.id"), nullable=True)
    department      = Column(String(100), nullable=True)
    job_title       = Column(String(100), nullable=True)
    avatar_url      = Column(String(500), nullable=True)
    is_superadmin   = Column(Boolean, default=False, nullable=False)
    last_login      = Column(DateTime, nullable=True)
    failed_login_count = Column(Integer, default=0, nullable=False)
    locked_until    = Column(DateTime, nullable=True)
    mfa_enabled     = Column(Boolean, default=False)
    mfa_secret      = Column(String(255), nullable=True)
    reset_token     = Column(String(255), nullable=True)
    reset_token_expiry = Column(DateTime, nullable=True)
    created_by      = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at      = Column(DateTime, nullable=True)

    roles            = relationship("UserRole", back_populates="user",
                                    foreign_keys="UserRole.user_id")
    refresh_tokens   = relationship("RefreshToken", back_populates="user")
    audit_logs       = relationship("UserAuditLog", back_populates="user",
                                    foreign_keys="UserAuditLog.user_id")
    permission_flags = relationship("PermissionFlagUser", back_populates="user",
                                    foreign_keys="PermissionFlagUser.user_id")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.active

    __table_args__ = (
        Index("ix_users_company_id", "company_id"),
        Index("ix_users_status", "status"),
    )


class UserRole(Base):
    __tablename__ = "user_roles"
    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    role_id    = Column(Integer, ForeignKey("roles.id"), nullable=False)
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_role"),
    )
    user = relationship("User", back_populates="roles", foreign_keys=[user_id])
    role = relationship("Role", back_populates="user_roles")


class PermissionFlagUser(Base):
    __tablename__ = "permission_flags_user"
    id             = Column(Integer, primary_key=True)
    user_id        = Column(Integer, ForeignKey("users.id"), nullable=False)
    company_id     = Column(Integer, ForeignKey("companies.id"), nullable=False)
    permission_key = Column(String(100), nullable=False)
    granted        = Column(Boolean, default=True)
    granted_by     = Column(Integer, ForeignKey("users.id"), nullable=True)
    reason         = Column(Text, nullable=True)
    expires_at     = Column(DateTime, nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (
        UniqueConstraint("user_id", "permission_key", name="uq_flag_per_user_key"),
    )
    user = relationship("User", back_populates="permission_flags", foreign_keys=[user_id])


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id         = Column(Integer, primary_key=True)
    token_hash = Column(String(255), unique=True, nullable=False)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_used    = Column(Boolean, default=False, nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    user = relationship("User", back_populates="refresh_tokens")
    __table_args__ = (
        Index("ix_refresh_tokens_user_id", "user_id"),
        Index("ix_refresh_tokens_hash", "token_hash"),
    )


class UserAuditLog(Base):
    __tablename__ = "user_audit_logs"
    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=True)
    actor_id   = Column(Integer, ForeignKey("users.id"), nullable=True)
    action     = Column(String(100), nullable=False)
    success    = Column(Boolean, nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    detail     = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    user  = relationship("User", back_populates="audit_logs", foreign_keys=[user_id])
    actor = relationship("User", foreign_keys=[actor_id])
    __table_args__ = (
        Index("ix_audit_user_id", "user_id"),
        Index("ix_audit_action", "action"),
    )
