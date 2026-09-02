"""
security.py — JWT creation/verification and bcrypt password hashing.
NFR-SEC-01: JWT HS256, 15-min access token, bcrypt cost factor 12.
"""
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from starlette.concurrency import run_in_threadpool

from app.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=settings.BCRYPT_ROUNDS)


# ── Password ──────────────────────────────────────────────────────────────────

async def hash_password(plain: str) -> str:
    return await run_in_threadpool(pwd_context.hash, plain)


async def verify_password(plain: str, hashed: str) -> bool:
    return await run_in_threadpool(pwd_context.verify, plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(subject: str, role: str) -> str:
    """Create a short-lived access JWT (15 minutes)."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "role": role, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    """Create a long-lived refresh JWT (7 days)."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT; return payload or None."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def hash_token(token: str) -> str:
    """SHA-256 hash of a refresh token for safe DB storage."""
    return hashlib.sha256(token.encode()).hexdigest()
