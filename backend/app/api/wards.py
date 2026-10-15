from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import accessible_ward_ids, audit, require, require_ward_access
from app.core.db import get_db
from app.models import User, Ward
from app.schemas import WardIn, WardOut

router = APIRouter()


@router.get("/wards", response_model=list[WardOut])
def list_wards(user: User = Depends(require("wards.view")), db: Session = Depends(get_db)):
    q = select(Ward).order_by(Ward.code)
    ids = accessible_ward_ids(db, user)
    if ids is not None:
        q = q.where(Ward.id.in_(ids))
    return db.scalars(q).all()


@router.get("/wards/{wid}", response_model=WardOut)
def get_ward(wid: int, user: User = Depends(require("wards.view")), db: Session = Depends(get_db)):
    ward = db.get(Ward, wid)
    if not ward:
        raise HTTPException(404, "Ward not found")
    require_ward_access(db, user, wid)
    return ward


@router.post("/wards", response_model=WardOut, status_code=201)
def create_ward(body: WardIn, request: Request, actor: User = Depends(require("wards.manage")),
                db: Session = Depends(get_db)):
    ward = Ward(**body.model_dump())
    db.add(ward)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Ward code already exists")
    audit(db, "ward.created", actor, "ward", ward.id, request=request)
    db.commit()
    return ward
