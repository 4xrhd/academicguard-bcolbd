"""
admin.py — Administration router (admin role only).
FR-ADMIN-01: GET  /admin/users              — List all instructor accounts
FR-ADMIN-01: POST /admin/users/{id}/deactivate — Soft-delete / suspend account
FR-ADMIN-02: GET  /admin/audit-logs         — System-wide audit log with filters
"""
import uuid

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.core.dependencies import AdminUser, DBSession
from app.db.models import AuditLog, User
from app.db.schemas import AuditLogFilter, AuditLogResponse, UserResponse

router = APIRouter()


@router.get("/users", response_model=list[UserResponse])
async def list_users(current_user: AdminUser, db: DBSession):
    """FR-ADMIN-01 — List all user accounts."""
    result = await db.execute(
        select(User).order_by(User.created_at.desc())
    )
    return result.scalars().all()


@router.post("/users/{user_id}/deactivate", status_code=204)
async def deactivate_user(user_id: uuid.UUID, current_user: AdminUser, db: DBSession):
    """FR-ADMIN-01 — Soft-delete (deactivate) an instructor account."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="Cannot deactivate admin accounts.")
    user.is_active = False
    await db.flush()

@router.post("/users/{user_id}/reactivate", status_code=204)
async def reactivate_user(user_id: uuid.UUID, current_user: AdminUser, db: DBSession):
    """FR-ADMIN-01 — Reactivate a suspended instructor account."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.is_active = True
    await db.flush()

@router.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: uuid.UUID, current_user: AdminUser, db: DBSession):
    """FR-ADMIN-01 — Permanently delete an instructor account."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete admin accounts.")
    await db.delete(user)
    await db.flush()


@router.post("/users/{user_id}/change-role")
async def change_user_role(
    user_id: uuid.UUID,
    new_role: str,
    current_user: AdminUser,
    db: DBSession
):
    """Change user account type (role)."""
    # Validate role
    if new_role not in ["instructor", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'instructor' or 'admin'.")
    
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    # Prevent changing own role
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role.")
    
    # Update role
    old_role = user.role
    user.role = new_role
    await db.flush()
    
    return {
        "status": "ok",
        "user_id": str(user.id),
        "old_role": old_role,
        "new_role": new_role,
        "message": f"User role changed from {old_role} to {new_role}."
    }


from fastapi import Depends

@router.get("/audit-logs", response_model=list[AuditLogResponse])
async def get_audit_logs(
    current_user: AdminUser,
    db: DBSession,
    filters: AuditLogFilter = Depends(),
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0),
):
    """FR-ADMIN-02 — Query system-wide audit log with optional filters."""
    query = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset)

    if filters.user_id:
        query = query.where(AuditLog.user_id == filters.user_id)
    if filters.action:
        query = query.where(AuditLog.action.ilike(f"%{filters.action}%"))
    if filters.date_from:
        query = query.where(AuditLog.timestamp >= filters.date_from)
    if filters.date_to:
        query = query.where(AuditLog.timestamp <= filters.date_to)

    result = await db.execute(query)
    return result.scalars().all()
