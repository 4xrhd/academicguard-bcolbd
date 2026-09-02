"""
annotations.py — Annotation API for ground-truth labeling.
Instructors annotate submissions with labels (human, ai_generated, etc.)
to build training data for the AI detection model.
"""
import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func

from app.core.dependencies import DBSession, InstructorUser
from app.db.models import Annotation, Submission, Batch
from app.db.schemas import (
    AnnotationCreate, AnnotationUpdate, AnnotationResponse,
    AnnotationBulkCreate,
)

router = APIRouter()


@router.post(
    "/submissions/{submission_id}/annotate",
    response_model=AnnotationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def annotate_submission(
    submission_id: uuid.UUID,
    body: AnnotationCreate,
    current_user: InstructorUser,
    db: DBSession,
):
    """Create a ground-truth annotation for a submission."""
    # Verify submission exists and user owns the batch
    sub = await _get_owned_submission(submission_id, current_user, db)

    # Check for existing annotation
    existing = await db.execute(
        select(Annotation).where(Annotation.submission_id == submission_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Annotation already exists. Use PUT to update.",
        )

    annotation = Annotation(
        submission_id=submission_id,
        user_id=current_user.id,
        label=body.label,
        confidence=body.confidence,
        notes=body.notes,
    )
    db.add(annotation)
    await db.flush()
    return annotation


@router.put(
    "/submissions/{submission_id}/annotate",
    response_model=AnnotationResponse,
)
async def update_annotation(
    submission_id: uuid.UUID,
    body: AnnotationUpdate,
    current_user: InstructorUser,
    db: DBSession,
):
    """Update an existing annotation."""
    await _get_owned_submission(submission_id, current_user, db)

    result = await db.execute(
        select(Annotation).where(Annotation.submission_id == submission_id)
    )
    annotation = result.scalar_one_or_none()
    if not annotation:
        raise HTTPException(status_code=404, detail="No annotation found for this submission.")

    if body.label is not None:
        annotation.label = body.label
    if body.confidence is not None:
        annotation.confidence = body.confidence
    if body.notes is not None:
        annotation.notes = body.notes

    await db.flush()
    return annotation


@router.get(
    "/batches/{batch_id}/annotations",
    response_model=list[AnnotationResponse],
)
async def list_batch_annotations(
    batch_id: uuid.UUID,
    current_user: InstructorUser,
    db: DBSession,
):
    """List all annotations for a batch."""
    # Verify batch ownership
    batch_result = await db.execute(
        select(Batch).where(Batch.id == batch_id, Batch.instructor_id == current_user.id)
    )
    batch = batch_result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")

    result = await db.execute(
        select(Annotation)
        .join(Submission, Submission.id == Annotation.submission_id)
        .where(Submission.batch_id == batch_id)
        .order_by(Annotation.created_at)
    )
    return result.scalars().all()


@router.post(
    "/batches/{batch_id}/annotate-bulk",
    response_model=list[AnnotationResponse],
    status_code=status.HTTP_201_CREATED,
)
async def bulk_annotate(
    batch_id: uuid.UUID,
    body: AnnotationBulkCreate,
    current_user: InstructorUser,
    db: DBSession,
):
    """Bulk annotate multiple submissions in a batch."""
    # Verify batch ownership
    batch_result = await db.execute(
        select(Batch).where(Batch.id == batch_id, Batch.instructor_id == current_user.id)
    )
    batch = batch_result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")

    created = []
    for item in body.annotations:
        # Verify submission belongs to this batch
        sub_result = await db.execute(
            select(Submission).where(
                Submission.id == item.submission_id,
                Submission.batch_id == batch_id,
            )
        )
        sub = sub_result.scalar_one_or_none()
        if not sub:
            continue  # Skip invalid submission IDs

        # Upsert: update if exists, create if not
        existing_result = await db.execute(
            select(Annotation).where(Annotation.submission_id == item.submission_id)
        )
        existing = existing_result.scalar_one_or_none()

        if existing:
            existing.label = item.label
            existing.confidence = item.confidence
            existing.notes = item.notes
            created.append(existing)
        else:
            annotation = Annotation(
                submission_id=item.submission_id,
                user_id=current_user.id,
                label=item.label,
                confidence=item.confidence,
                notes=item.notes,
            )
            db.add(annotation)
            await db.flush()
            created.append(annotation)

    return created


@router.get("/annotations/stats")
async def annotation_stats(current_user: InstructorUser, db: DBSession):
    """Return annotation statistics and training readiness."""
    from app.engine.auto_trainer import get_annotation_stats
    return await get_annotation_stats()


@router.get("/annotations/export")
async def export_annotations(current_user: InstructorUser, db: DBSession):
    """Export annotations as a JSON list. Instructors see only their own; admins see all."""
    query = (
        select(Annotation, Submission.raw_text, Submission.student_id)
        .join(Submission, Submission.id == Annotation.submission_id)
        .join(Batch, Batch.id == Submission.batch_id)
        .order_by(Annotation.created_at)
    )
    if current_user.role != "admin":
        query = query.where(Batch.instructor_id == current_user.id)

    result = await db.execute(query)
    rows = result.all()

    export = []
    for ann, text, student_id in rows:
        export.append({
            "submission_id": str(ann.submission_id),
            "student_id": student_id,
            "label": ann.label,
            "confidence": ann.confidence,
            "notes": ann.notes,
            "text_preview": (text or "")[:200],
            "annotated_at": ann.created_at.isoformat(),
        })

    return {"count": len(export), "annotations": export}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_owned_submission(submission_id: uuid.UUID, current_user, db):
    """Verify that the submission exists and belongs to the user's batch."""
    result = await db.execute(
        select(Submission).where(Submission.id == submission_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found.")

    batch_result = await db.execute(
        select(Batch).where(Batch.id == sub.batch_id)
    )
    batch = batch_result.scalar_one_or_none()
    if not batch or (batch.instructor_id != current_user.id and current_user.role != "admin"):
        raise HTTPException(status_code=403, detail="Access denied.")

    return sub
