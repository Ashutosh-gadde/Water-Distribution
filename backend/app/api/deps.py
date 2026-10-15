from datetime import timedelta
from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db, utcnow
from app.core.permissions import ALL_JURISDICTION, Role, has_permission
from app.models import AuditLog, AuthSession, User, UserWardAssignment

bearer = HTTPBearer(auto_error=False)


def audit(db: Session, action: str, actor: User | None = None, entity: str | None = None,
          entity_id=None, detail: str | None = None, request: Request | None = None):
    db.add(AuditLog(actor_id=actor.id if actor else None, action=action, entity=entity,
                    entity_id=str(entity_id) if entity_id is not None else None,
                    detail=detail, ip=request.client.host if request and request.client else None))


def current_user(cred: HTTPAuthorizationCredentials | None = Depends(bearer),
                 db: Session = Depends(get_db)) -> User:
    from app.core.security import decode_access_token
    unauth = HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated",
                           headers={"WWW-Authenticate": "Bearer"})
    if not cred:
        raise unauth
    payload = decode_access_token(cred.credentials)
    if not payload:
        raise unauth
    sess = db.get(AuthSession, payload["sid"])
    if not sess or sess.revoked_at or sess.expires_at < utcnow() or sess.user_id != int(payload["sub"]):
        raise unauth
    user = db.get(User, sess.user_id)
    if not user or not user.is_active:
        raise unauth
    return user


def require(perm: str) -> Callable:
    def dep(user: User = Depends(current_user)) -> User:
        if not has_permission(user.role, perm):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return user
    return dep


def accessible_ward_ids(db: Session, user: User) -> set[int] | None:
    """None means every ward; otherwise the set of currently assigned ward ids."""
    if Role(user.role) in ALL_JURISDICTION:
        return None
    rows = db.scalars(select(UserWardAssignment.ward_id).where(
        UserWardAssignment.user_id == user.id, UserWardAssignment.ended_at.is_(None)))
    return set(rows)


def require_ward_access(db: Session, user: User, ward_id: int):
    ids = accessible_ward_ids(db, user)
    if ids is not None and ward_id not in ids:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ward is outside your jurisdiction")
