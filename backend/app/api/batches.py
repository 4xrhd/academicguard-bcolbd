"""
batches.py — Batch upload and management router.
FR-UPLOAD-01: POST /batches/upload  — Upload 1–60 PDF files
FR-UPLOAD-04: GET  /batches/{id}/status — Polling endpoint
              GET  /batches         — List instructor batches
              GET  /batches/{id}    — Batch detail
              DELETE /batches/{id} — Delete batch
"""
import hashlib
import os
import uuid
from pathlib import Path
from typing import List, Optional, cast

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select, update
import json

from app.config import get_settings
from app.core.dependencies import DBSession, InstructorUser
from app.db.models import Batch, Submission, MarkingConfigTemplate
from app.db.schemas import BatchResponse, BatchStatusResponse, MarkingConfig
from app.engine import pdf_processor  # Analysis pipeline entry point

router = APIRouter()
settings = get_settings()

ALLOWED_MIME = {"application/pdf"}
PDF_MAGIC = b"%PDF"


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_batch(
    background_tasks: BackgroundTasks,
    current_user: InstructorUser,
    db: DBSession,
    batch_name: str = Form(...),
    course_code: str = Form(...),
    files: List[UploadFile] = File(...),
    config_id: Optional[uuid.UUID] = Form(None),
    marking_config_json: Optional[str] = Form(None),
):
    """FR-UPLOAD-01 — Accept 1–60 PDF files and enqueue async processing."""
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required.")
    if len(files) > settings.MAX_FILES_PER_BATCH:
        raise HTTPException(status_code=400, detail=f"Maximum {settings.MAX_FILES_PER_BATCH} files per batch.")

    # Create batch record
    batch = Batch(name=batch_name, course_code=course_code, instructor_id=current_user.id)
    
    # Handle marking configuration (FR-MARK-03)
    if marking_config_json:
        try:
            cfg_dict = json.loads(marking_config_json)
            # Use Pydantic model for validation
            validated_config = MarkingConfig.model_validate(cfg_dict)
            batch.total_marks = validated_config.total_marks
            batch.marking_config = validated_config.model_dump()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid marking_config_json format.")
    elif config_id:
        result = await db.execute(
            select(MarkingConfigTemplate)
            .where(MarkingConfigTemplate.id == config_id, MarkingConfigTemplate.user_id == current_user.id)
        )
        saved_cfg = result.scalar_one_or_none()
        if not saved_cfg:
            raise HTTPException(status_code=404, detail="Saved marking configuration not found.")
        batch.total_marks = saved_cfg.total_marks
        batch.marking_config = saved_cfg.config_data
    else:
        # Check for user's default config
        result = await db.execute(
            select(MarkingConfigTemplate)
            .where(MarkingConfigTemplate.user_id == current_user.id, MarkingConfigTemplate.is_default == True)
        )
        default_cfg = result.scalar_one_or_none()
        if default_cfg:
            batch.total_marks = default_cfg.total_marks
            batch.marking_config = default_cfg.config_data

    db.add(batch)
    await db.flush()  # Get batch.id before saving files

    upload_dir = Path(settings.UPLOAD_DIR) / str(batch.id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    rejected: list[str] = []
    saved_paths: list[tuple[str, str]] = []   # (original_name, saved_path)

    for file in files:
        if file.size and file.size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            rejected.append(file.filename or "unknown")
            continue
            
        content = await file.read()

        # Validated file size via pre-check above

        # Validate MIME type and PDF magic bytes (NFR-SEC-05)
        is_pdf = cast(bytes, content).startswith(PDF_MAGIC)
        if file.content_type not in ALLOWED_MIME or not is_pdf:
            rejected.append(file.filename or "unknown")
            continue

        # Store with SHA-256-hashed filename to prevent path traversal
        filename_hash = hashlib.sha256(cast(bytes, content)).hexdigest()
        dest = upload_dir / f"{filename_hash}.pdf"
        dest.write_bytes(cast(bytes, content))

        sub = Submission(
            batch_id=batch.id,
            file_path=str(dest),
            student_id=None,
            student_name=None,
        )
        db.add(sub)
        saved_paths.append((file.filename or "unknown", str(dest)))

    if not saved_paths:
        raise HTTPException(status_code=400, detail="No valid PDF files were accepted.")

    # Explicitly commit before starting background task to ensure visibility
    await db.commit()
    
    # Enqueue asynchronous processing pipeline
    background_tasks.add_task(pdf_processor.process_batch, str(batch.id))

    return {
        "batch_id": str(batch.id),
        "status": "pending",
        "accepted": len(saved_paths),
        "rejected": rejected,
    }


@router.get("", response_model=list[BatchResponse])
async def list_batches(current_user: InstructorUser, db: DBSession):
    """FR-DASH-01 — List all batches belonging to the logged-in instructor (admins see all)."""
    # Subquery: count submissions per batch in a single query (avoids N+1)
    count_subq = (
        select(
            Submission.batch_id,
            func.count(Submission.id).label("sub_count"),
        )
        .group_by(Submission.batch_id)
        .subquery()
    )

    query = (
        select(Batch, count_subq.c.sub_count)
        .outerjoin(count_subq, Batch.id == count_subq.c.batch_id)
        .order_by(Batch.uploaded_at.desc())
    )
    if current_user.role != "admin":
        query = query.where(Batch.instructor_id == current_user.id)

    result = await db.execute(query)

    response = []
    for batch, sub_count in result.all():
        data = BatchResponse.model_validate(batch)
        data.submission_count = sub_count or 0
        response.append(data)
    return response


@router.get("/{batch_id}", response_model=BatchResponse)
async def get_batch(batch_id: uuid.UUID, current_user: InstructorUser, db: DBSession):
    """Get batch detail. Instructors may only access their own batches (FR-AUTH-03)."""
    batch = await _get_owned_batch(batch_id, current_user, db)
    return batch


@router.get("/{batch_id}/status", response_model=BatchStatusResponse)
async def get_batch_status(batch_id: uuid.UUID, current_user: InstructorUser, db: DBSession):
    """FR-UPLOAD-04 — Polling endpoint; called every 3 seconds by the frontend."""
    batch = await _get_owned_batch(batch_id, current_user, db)
    return BatchStatusResponse(batch_id=batch.id, status=batch.status, progress=batch.progress)


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_batch(batch_id: uuid.UUID, current_user: InstructorUser, db: DBSession):
    """Delete batch and cascade-delete all related data (DB + Disk)."""
    import os
    from pathlib import Path
    
    batch = await _get_owned_batch(batch_id, current_user, db)
    
    # FR-UPLOAD-05: Clean up disk storage on batch deletion
    # Retrieve all file paths for this batch before deleting from DB
    subs_result = await db.execute(select(Submission.file_path).where(Submission.batch_id == batch_id))
    file_paths = subs_result.scalars().all()
    
    await db.delete(batch)
    await db.commit()

    for path_str in file_paths:
        if path_str:
            try:
                p = Path(path_str)
                if p.exists():
                    os.remove(p)
            except Exception as exc:
                print(f"[WARN] Failed to delete file {path_str}: {exc!r}")


@router.post("/{batch_id}/marking-config")
async def set_marking_config(
    batch_id: uuid.UUID,
    config: MarkingConfig,
    current_user: InstructorUser,
    db: DBSession,
):
    """FR-MARK-01 — Set marking configuration for batch."""
    batch = await _get_owned_batch(batch_id, current_user, db)
    batch.total_marks = config.total_marks
    batch.marking_config = config.model_dump()
    await db.commit()
    return {"status": "ok", "batch_id": str(batch.id)}


@router.get("/{batch_id}/marking-config")
async def get_marking_config(batch_id: uuid.UUID, current_user: InstructorUser, db: DBSession):
    """Get marking configuration for batch."""
    batch = await _get_owned_batch(batch_id, current_user, db)
    return {
        "total_marks": batch.total_marks,
        "marking_config": batch.marking_config,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_owned_batch(batch_id: uuid.UUID, user, db) -> Batch:
    result = await db.execute(select(Batch).where(Batch.id == batch_id))
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")
    # Admins may access any batch; instructors only their own
    if user.role != "admin" and batch.instructor_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied.")
    return batch
