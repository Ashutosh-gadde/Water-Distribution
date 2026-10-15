import hashlib
import secrets
from datetime import timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings
from app.core.db import utcnow

ALGO = "HS256"


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except ValueError:
        return False


_DUMMY = hash_password("dummy-password-for-timing")


def burn_time():
    """Equalise response time for unknown users."""
    verify_password("x", _DUMMY)


def create_access_token(user_id: int, session_id: int) -> str:
    exp = utcnow() + timedelta(minutes=settings.access_token_minutes)
    payload = {"sub": str(user_id), "sid": session_id,
               "exp": exp.replace(tzinfo=timezone.utc)}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGO)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGO])
    except jwt.PyJWTError:
        return None


def new_refresh_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(48)
    return raw, hash_refresh(raw)


def hash_refresh(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def validate_password_strength(pw: str) -> str | None:
    if len(pw) < settings.min_password_length:
        return f"Password must be at least {settings.min_password_length} characters."
    if pw.lower() == pw or pw.upper() == pw or not any(c.isdigit() for c in pw):
        return "Password must mix upper and lower case letters and include a digit."
    return None
