"""
middleware.py — Audit log middleware.
FR-AUDIT-01: Every write operation (POST/PUT/PATCH/DELETE) is logged to audit_logs
with user identity, IP address, and timestamp.
"""
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

import logging
from app.core.security import decode_token
from app.db.session import AsyncSessionLocal
from app.db.models import AuditLog
from app.config import get_settings

logger = logging.getLogger(__name__)

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Paths that do NOT need audit entries (health checks, docs, static)
SKIP_PATHS = {"/api/health", "/api/docs", "/api/redoc", "/api/openapi.json"}


class AuditLogMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        if request.method not in WRITE_METHODS:
            return response
        if request.url.path in SKIP_PATHS:
            return response
        if response.status_code >= 400:
            # Still log failed writes for security auditing
            pass

        # Extract user identity from token (best-effort; no exception raised here)
        user_id = None
        token = request.cookies.get("access_token")
        if token:
            payload = decode_token(token)
            if payload and payload.get("sub"):
                try:
                    user_id = uuid.UUID(payload["sub"])
                except ValueError:
                    pass

        # Derive action string from method + path
        action = _derive_action(request.method, request.url.path)
        entity_type, entity_id = _extract_entity(request.url.path)

        # Write audit record asynchronously
        try:
            async with AsyncSessionLocal() as session:
                log = AuditLog(
                    user_id=user_id,
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    ip_address=_get_client_ip(request),
                )
                session.add(log)
                await session.commit()
        except Exception as e:
            # Audit log failure must never crash the request, but we must log it
            logger.error(f"AuditLogMiddleware failed to write log: {e}")

        return response


def _derive_action(method: str, path: str) -> str:
    """Map HTTP method + path to a semantic action string."""
    clean_path = path.replace("/api/", "").strip("/")
    segments = [s for s in clean_path.split("/") if s]
    
    # Explicit semantic action mappings for compliance and clarity
    if method == "POST" and clean_path == "auth/login":
        return "auth.login"
    if method == "POST" and clean_path == "auth/logout":
        return "auth.logout"
    if method == "POST" and clean_path == "auth/register":
        return "auth.register"
        
    if method == "POST" and clean_path == "batches":
        return "batch.create"
    if method == "DELETE" and len(segments) == 2 and segments[0] == "batches":
        return "batch.delete"
    if method == "POST" and len(segments) == 3 and segments[0] == "batches" and segments[2] == "process":
        return "batch.process"
    if method == "POST" and len(segments) == 3 and segments[0] == "batches" and segments[2] == "marking-config":
        return "batch.update_marking_config"
        
    if method == "POST" and len(segments) == 3 and segments[0] == "submissions" and segments[2] == "annotations":
        return "annotation.create"
    if method == "DELETE" and len(segments) == 2 and segments[0] == "annotations":
        return "annotation.delete"
    if method == "PUT" and len(segments) == 3 and segments[0] == "submissions" and segments[2] == "marks":
        return "submission.update_marks"
        
    if method == "POST" and clean_path == "admin/users":
        return "admin.user_create"
    if method == "DELETE" and len(segments) == 3 and segments[0] == "admin" and segments[1] == "users":
        return "admin.user_delete"
    if method == "PATCH" and len(segments) == 4 and segments[0] == "admin" and segments[1] == "users" and segments[3] == "role":
        return "admin.user_update_role"
        
    # Fallback to generic dot-notation without UUIDs
    no_uuid_segments = [s for s in segments if not _is_uuid(s)]
    resource = ".".join(no_uuid_segments[-2:]) if len(no_uuid_segments) >= 2 else ".".join(no_uuid_segments)
    return f"{method.lower()}.{resource}"


def _get_client_ip(request: Request) -> str:
    """Extract real client IP from X-Forwarded-For (set by Nginx) or direct connection."""
    client_host = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("X-Forwarded-For")
    
    if forwarded_for:
        settings = get_settings()
        trusted_proxies = [p.strip() for p in settings.TRUSTED_PROXIES.split(",")]
        # Only trust X-Forwarded-For if the immediate client is in our trusted proxy list
        if client_host in trusted_proxies:
            return forwarded_for.split(",")[0].strip()
            
    return client_host


def _is_uuid(s: str) -> bool:
    try:
        uuid.UUID(s)
        return True
    except ValueError:
        return False


def _extract_entity(path: str) -> tuple[str | None, uuid.UUID | None]:
    """Extract entity type and ID from URL path segments like /api/v1/batches/{uuid}."""
    segments = [s for s in path.split("/") if s]
    entity_type = None
    entity_id = None
    for i, seg in enumerate(segments):
        if _is_uuid(seg):
            entity_id = uuid.UUID(seg)
            # The segment before the UUID is the entity type
            if i > 0:
                entity_type = segments[i - 1]
            break
    return entity_type, entity_id
