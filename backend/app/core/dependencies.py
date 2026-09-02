"""
dependencies.py — FastAPI dependency injection for authentication and RBAC.
NFR-SEC-02: RBAC enforced on every API endpoint; unauthorized → HTTP 403.
"""
import uuid
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.core.security import decode_token
from app.db.session import get_db
from app.db import models

settings = get_settings()


async def get_current_user(
    access_token: Annotated[str | None, Cookie()] = None,
    authorization: Annotated[str | None, Header()] = None,
    token: Annotated[str | None, Query()] = None,
    db: AsyncSession = Depends(get_db),
) -> models.User:
    """Extract and validate JWT from HttpOnly cookie, Authorization header, or query param; return active User."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
    )
    
    raw_token = access_token
    if not raw_token and authorization:
        if authorization.startswith("Bearer "):
            raw_token = authorization[7:].strip()
        else:
            raw_token = authorization.strip()
    if not raw_token and token:
        raw_token = token.strip()

    if not raw_token:
        raise credentials_exception

    payload = decode_token(raw_token)
    if payload is None or payload.get("type") != "access":
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    result = await db.execute(select(models.User).where(models.User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise credentials_exception
    return user


async def require_instructor(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """Allow instructors and admins."""
    if current_user.role not in ("instructor", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions.")
    return current_user


async def require_admin(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """Allow admins only."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return current_user


# Convenience type aliases
CurrentUser      = Annotated[models.User, Depends(get_current_user)]
InstructorUser   = Annotated[models.User, Depends(require_instructor)]
AdminUser        = Annotated[models.User, Depends(require_admin)]
DBSession        = Annotated[AsyncSession, Depends(get_db)]
