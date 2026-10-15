from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import audit, current_user, require
from app.core.db import get_db, utcnow
from app.core.permissions import can_manage_role
from app.core.security import hash_password, validate_password_strength
from app.models import AuthSession, User, UserWardAssignment, Ward
from app.schemas import AssignIn, UserCreate, UserOut, UserPatch

router = APIRouter()


def _get(db: Session, uid: int) -> User:
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404, "User not found")
    return u


def _guard_target(actor: User, target: User):
    if actor.id != target.id and not can_manage_role(actor.role, target.role):
        raise HTTPException(403, "You cannot manage a user of this level")


@router.get("/users", response_model=list[UserOut])
def list_users(_: User = Depends(require("users.view")), db: Session = Depends(get_db)):
    return db.scalars(select(User).order_by(User.id)).all()


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, request: Request, actor: User = Depends(require("users.manage")),
                db: Session = Depends(get_db)):
    if not can_manage_role(actor.role, body.role):
        raise HTTPException(403, "You cannot create a user of this level")
    if (msg := validate_password_strength(body.password)):
        raise HTTPException(422, msg)
    if body.supervisor_id is not None:
        _get(db, body.supervisor_id)
    wards = []
    for wid in body.ward_ids:
        if not db.get(Ward, wid):
            raise HTTPException(422, f"Ward {wid} does not exist")
        wards.append(wid)
    user = User(**body.model_dump(exclude={"password", "ward_ids", "role"}), role=body.role.value,
                password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Employee ID or email already exists")
    for wid in wards:
        db.add(UserWardAssignment(user_id=user.id, ward_id=wid, assigned_by=actor.id))
    audit(db, "user.created", actor, "user", user.id, f"role={user.role}", request)
    db.commit()
    return user


@router.patch("/users/{uid}", response_model=UserOut)
def patch_user(uid: int, body: UserPatch, request: Request, actor: User = Depends(require("users.manage")),
               db: Session = Depends(get_db)):
    user = _get(db, uid)
    _guard_target(actor, user)
    data = body.model_dump(exclude_unset=True)
    if "role" in data:
        if actor.id == user.id:
            raise HTTPException(403, "You cannot change your own role")
        if not can_manage_role(actor.role, data["role"].value):
            raise HTTPException(403, "You cannot grant a role of this level")
        data["role"] = data["role"].value
    if data.get("is_active") is False and actor.id == user.id:
        raise HTTPException(403, "You cannot deactivate your own account")
    if data.get("supervisor_id") == user.id:
        raise HTTPException(422, "A user cannot supervise themselves")
    for k, v in data.items():
        setattr(user, k, v)
    if data.get("is_active") is False or "role" in data:  # force re-login
        for s in db.scalars(select(AuthSession).where(AuthSession.user_id == user.id,
                                                      AuthSession.revoked_at.is_(None))):
            s.revoked_at = utcnow()
    audit(db, "user.updated", actor, "user", user.id,
          ",".join(f"{k}={v}" for k, v in data.items()), request)
    db.commit()
    return user


@router.get("/users/{uid}/assignments")
def assignments(uid: int, actor: User = Depends(current_user), db: Session = Depends(get_db)):
    from app.core.permissions import has_permission
    if actor.id != uid and not has_permission(actor.role, "users.view"):
        raise HTTPException(403, "Insufficient permissions")
    _get(db, uid)
    rows = db.scalars(select(UserWardAssignment).where(UserWardAssignment.user_id == uid)
                      .order_by(UserWardAssignment.id)).all()
    return [{"id": r.id, "ward_id": r.ward_id, "ward_code": r.ward.code, "started_at": r.started_at,
             "ended_at": r.ended_at} for r in rows]


@router.post("/users/{uid}/assignments", status_code=201)
def assign(uid: int, body: AssignIn, request: Request, actor: User = Depends(require("users.manage")),
           db: Session = Depends(get_db)):
    user = _get(db, uid)
    _guard_target(actor, user)
    if not db.get(Ward, body.ward_id):
        raise HTTPException(422, "Ward does not exist")
    active = db.scalar(select(UserWardAssignment).where(
        UserWardAssignment.user_id == uid, UserWardAssignment.ward_id == body.ward_id,
        UserWardAssignment.ended_at.is_(None)))
    if active:
        raise HTTPException(409, "Already assigned")
    row = UserWardAssignment(user_id=uid, ward_id=body.ward_id, assigned_by=actor.id)
    db.add(row)
    audit(db, "assignment.added", actor, "user", uid, f"ward={body.ward_id}", request)
    db.commit()
    return {"id": row.id}


@router.delete("/users/{uid}/assignments/{ward_id}", status_code=204)
def unassign(uid: int, ward_id: int, request: Request, actor: User = Depends(require("users.manage")),
             db: Session = Depends(get_db)):
    user = _get(db, uid)
    _guard_target(actor, user)
    row = db.scalar(select(UserWardAssignment).where(
        UserWardAssignment.user_id == uid, UserWardAssignment.ward_id == ward_id,
        UserWardAssignment.ended_at.is_(None)))
    if not row:
        raise HTTPException(404, "No active assignment")
    row.ended_at = utcnow()  # history preserved
    audit(db, "assignment.ended", actor, "user", uid, f"ward={ward_id}", request)
    db.commit()
