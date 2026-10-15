from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import auth, users, wards
from app.core.config import settings
from app.core.db import engine

app = FastAPI(title="Latur Municipal Corporation — Water Distribution API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins.split(","),
                   allow_methods=["*"], allow_headers=["*"])

api = APIRouter(prefix="/api/v1")
api.include_router(auth.router, tags=["auth"])  # first: /users/me before /users/{id}
api.include_router(users.router, tags=["users"])
api.include_router(wards.router, tags=["wards"])
app.include_router(api)


@app.get("/health")
def health():
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}
    except Exception:
        return {"status": "degraded", "database": "unavailable"}
