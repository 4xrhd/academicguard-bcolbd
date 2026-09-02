from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import InstructorUser, DBSession
from app.db.models import MarkingConfigTemplate
from app.db.schemas import (
    MarkingConfigTemplateCreate,
    MarkingConfigTemplateUpdate,
    MarkingConfigTemplateResponse,
)

router = APIRouter(prefix="/marking", tags=["Marking Configurations"])

@router.post("/configs", response_model=MarkingConfigTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_marking_config(
    config_in: MarkingConfigTemplateCreate,
    current_user: InstructorUser,
    db: DBSession,
):
    """Save a new marking configuration template (FR-MARK-03)."""
    # If is_default is true, unset other defaults for this user
    if config_in.is_default:
        await db.execute(
            update(MarkingConfigTemplate)
            .where(MarkingConfigTemplate.user_id == current_user.id)
            .values(is_default=False)
        )

    new_config = MarkingConfigTemplate(
        **config_in.model_dump(),
        user_id=current_user.id
    )
    db.add(new_config)
    await db.commit()
    await db.refresh(new_config)
    return new_config

@router.get("/configs", response_model=List[MarkingConfigTemplateResponse])
async def list_marking_configs(
    current_user: InstructorUser,
    db: DBSession,
):
    """List all saved marking configurations for the current instructor."""
    result = await db.execute(
        select(MarkingConfigTemplate)
        .where(MarkingConfigTemplate.user_id == current_user.id)
        .order_by(MarkingConfigTemplate.is_default.desc(), MarkingConfigTemplate.created_at.desc())
    )
    return result.scalars().all()

@router.get("/configs/{config_id}", response_model=MarkingConfigTemplateResponse)
async def get_marking_config(
    config_id: uuid.UUID,
    current_user: InstructorUser,
    db: DBSession,
):
    """Get a specific marking configuration."""
    result = await db.execute(
        select(MarkingConfigTemplate)
        .where(
            MarkingConfigTemplate.id == config_id,
            MarkingConfigTemplate.user_id == current_user.id
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return config

@router.patch("/configs/{config_id}", response_model=MarkingConfigTemplateResponse)
async def update_marking_config(
    config_id: uuid.UUID,
    config_in: MarkingConfigTemplateUpdate,
    current_user: InstructorUser,
    db: DBSession,
):
    """Update a saved marking configuration."""
    # Check existence
    result = await db.execute(
        select(MarkingConfigTemplate)
        .where(
            MarkingConfigTemplate.id == config_id,
            MarkingConfigTemplate.user_id == current_user.id
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    # If setting as default, unset others
    if config_in.is_default:
        await db.execute(
            update(MarkingConfigTemplate)
            .where(MarkingConfigTemplate.user_id == current_user.id)
            .values(is_default=False)
        )

    # Update fields
    update_data = config_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(config, key, value)

    await db.commit()
    await db.refresh(config)
    return config

@router.delete("/configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_marking_config(
    config_id: uuid.UUID,
    current_user: InstructorUser,
    db: DBSession,
):
    """Delete a marking configuration."""
    result = await db.execute(
        delete(MarkingConfigTemplate)
        .where(
            MarkingConfigTemplate.id == config_id,
            MarkingConfigTemplate.user_id == current_user.id
        )
    )
    if getattr(result, "rowcount", 0) == 0:
        raise HTTPException(status_code=404, detail="Configuration not found")
    await db.commit()
    return None
