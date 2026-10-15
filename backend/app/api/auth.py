import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import accessible_ward_ids, audit, bearer, current_user
from app.core.config import settings
from app.core.db import get_db, utcnow
from app.core.permissions import PERMISSIONS, Role
from app.core.security import (burn_time, create_access_token, decode_access_token,
                               hash_refresh, new_refresh_token, verify_password)
from app.models import AuthSession, User
from app.schemas import ForgotIn, LoginIn, MeOut, RefreshIn, TokenOut, UserOut

router = APIRouter()
log = logging.getLogger("auth")
BAD = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid employee ID or password")


def _issue(db: Session, user: User, request: Request) -> TokenOut:
    raw, hashed = new_refresh_token()
    sess = AuthSession(user_id=user.id, refresh_hash=hashed, ip=request.client.host if request.client else None,
                       expires_at=utcnow() + timedelta(days=settings.refresh_token_days))
    db.add(sess)
    db.flush()
    return TokenOut(access_token=create_access_token(user.id, sess.id), refresh_token=raw)


@router.post("/auth/login", response_model=TokenOut)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.employee_id == body.employee_id))
    if not user:
        burn_time()
        audit(db, "login.failed", detail=f"unknown:{body.employee_id[:40]}", request=request)
        db.commit()
        raise BAD
    if user.locked_until and user.locked_until > utcnow():
        audit(db, "login.locked", user, "user", user.id, request=request)
        db.commit()
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Account temporarily locked. Try again later.")
    if not verify_password(body.password, user.password_hash):
        user.failed_logins += 1
        if user.failed_logins >= settings.max_failed_logins:
            user.locked_until = utcnow() + timedelta(minutes=settings.lockout_minutes)
            user.failed_logins = 0
        audit(db, "login.failed", user, "user", user.id, request=request)
        db.commit()
        raise BAD
    if not user.is_active:  # same message: do not reveal account state
        audit(db, "login.deactivated", user, "user", user.id, request=request)
        db.commit()
        raise BAD
    user.failed_logins, user.locked_until, user.last_login = 0, None, utcnow()
    tokens = _issue(db, user, request)
    audit(db, "login.success", user, "user", user.id, request=request)
    db.commit()
    return tokens


@router.post("/auth/refresh", response_model=TokenOut)
def refresh(body: RefreshIn, request: Request, db: Session = Depends(get_db)):
    sess = db.scalar(select(AuthSession).where(AuthSession.refresh_hash == hash_refresh(body.refresh_token)))
    if not sess or sess.revoked_at or sess.expires_at < utcnow():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    user = db.get(User, sess.user_id)
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    sess.revoked_at = utcnow()  # rotation: a refresh token is single-use
    tokens = _issue(db, user, request)
    db.commit()
    return tokens


@router.post("/auth/logout", status_code=204)
def logout(request: Request, cred: HTTPAuthorizationCredentials = Depends(bearer),
           user: User = Depends(current_user), db: Session = Depends(get_db)):
    payload = decode_access_token(cred.credentials)
    sess = db.get(AuthSession, payload["sid"])
    sess.revoked_at = utcnow()
    audit(db, "logout", user, "user", user.id, request=request)
    db.commit()


@router.post("/auth/forgot-password", status_code=202)
def forgot_password(body: ForgotIn, request: Request, db: Session = Depends(get_db)):
    # Always the same response so account existence is not revealed. No email provider
    # is configured yet, so nothing is sent; administrators reset passwords manually.
    audit(db, "password.reset_requested", detail=body.employee_id[:40], request=request)
    db.commit()
    log.warning("Password reset requested but no email provider is configured.")
    return {"detail": "If the account exists, an administrator has been notified. "
                      "Self-service reset is not configured."}


@router.get("/users/me", response_model=MeOut)
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    ids = accessible_ward_ids(db, user)
    base = UserOut.model_validate(user).model_dump()
    return MeOut(**base, permissions=sorted(PERMISSIONS[Role(user.role)]),
                 ward_ids=sorted(ids) if ids is not None else [])
