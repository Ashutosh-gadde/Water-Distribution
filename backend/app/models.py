from sqlalchemy import (Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String,
                        Text, UniqueConstraint, event)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, utcnow

ROLE_CHECK = ("role IN ('super_admin','municipal_admin','water_officer',"
              "'ward_officer','valve_operator')")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint(ROLE_CHECK, name="ck_users_role"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str | None] = mapped_column(String(200), unique=True)
    phone: Mapped[str | None] = mapped_column(String(20))
    department: Mapped[str | None] = mapped_column(String(100))
    designation: Mapped[str | None] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(30), index=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    supervisor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_logins: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[DateTime | None] = mapped_column(DateTime)
    last_login: Mapped[DateTime | None] = mapped_column(DateTime)
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[DateTime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Ward(Base):
    __tablename__ = "wards"
    __table_args__ = (CheckConstraint(
        "verification_status IN ('draft','under_review','verified','rejected')",
        name="ck_wards_verification"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name_en: Mapped[str] = mapped_column(String(150))
    name_mr: Mapped[str | None] = mapped_column(String(150))
    verification_status: Mapped[str] = mapped_column(String(20), default="draft")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=utcnow)


class UserWardAssignment(Base):
    """Assignment history is kept: ending an assignment sets ended_at, never deletes."""
    __tablename__ = "user_ward_assignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    ward_id: Mapped[int] = mapped_column(ForeignKey("wards.id"), index=True)
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    started_at: Mapped[DateTime] = mapped_column(DateTime, default=utcnow)
    ended_at: Mapped[DateTime | None] = mapped_column(DateTime)
    ward = relationship("Ward")


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    refresh_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[DateTime] = mapped_column(DateTime)
    revoked_at: Mapped[DateTime | None] = mapped_column(DateTime)
    ip: Mapped[str | None] = mapped_column(String(64))


class AuditLog(Base):
    """Append-only: ORM updates and deletes are blocked (see listeners below).
    On PostgreSQL a trigger/REVOKE should also enforce this (see docs)."""
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[DateTime] = mapped_column(DateTime, default=utcnow, index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(60), index=True)
    entity: Mapped[str | None] = mapped_column(String(40))
    entity_id: Mapped[str | None] = mapped_column(String(40))
    detail: Mapped[str | None] = mapped_column(Text)
    ip: Mapped[str | None] = mapped_column(String(64))


@event.listens_for(AuditLog, "before_update")
@event.listens_for(AuditLog, "before_delete")
def _audit_immutable(*_):
    raise PermissionError("audit_logs is append-only")
