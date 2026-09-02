"""
training.py — Model training API.
Trigger retraining, view training history, activate/rollback models.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from sqlalchemy import select, update

from app.core.dependencies import AdminUser, DBSession, InstructorUser
from app.db.models import TrainingRun
from app.db.schemas import TrainingRunResponse, TrainingStatsResponse

router = APIRouter()


@router.post("/training/start", response_model=TrainingRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_training(
    current_user: AdminUser,
    db: DBSession,
    background_tasks: BackgroundTasks,
):
    """Trigger model retraining as a background task."""
    # Check if training is already running
    running_result = await db.execute(
        select(TrainingRun).where(TrainingRun.status.in_(["pending", "running"]))
    )
    if running_result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="A training run is already in progress. Wait for it to complete.",
        )

    # Check data readiness
    from app.engine.auto_trainer import get_annotation_stats
    stats = await get_annotation_stats()
    if not stats["ready_to_train"]:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough annotated data. Need at least {stats['min_samples_required']} "
                   f"total samples with {stats['min_per_class_required']} per class. "
                   f"Currently have: {stats['binary_distribution']}",
        )

    # Create training run record
    run = TrainingRun(
        user_id=current_user.id,
        status="pending",
    )
    db.add(run)
    await db.flush()

    # Explicitly commit before starting background task to ensure visibility
    await db.commit()

    # Start training in background
    from app.engine.auto_trainer import run_training
    background_tasks.add_task(run_training, str(run.id))

    return run


@router.get("/training/status", response_model=TrainingRunResponse | None)
async def training_status(current_user: InstructorUser, db: DBSession):
    """Get the most recent training run status."""
    result = await db.execute(
        select(TrainingRun).order_by(TrainingRun.started_at.desc()).limit(1)
    )
    run = result.scalar_one_or_none()
    if not run:
        return None
    return run


async def _sync_registry_to_db(db: DBSession, current_user_id: Optional[uuid.UUID] = None):
    """Sync deployed models from model_registry.json into training_runs DB table if missing."""
    import json
    from pathlib import Path
    from datetime import datetime, timezone
    from app.db.models import TrainingRun, User

    registry_path = Path("models/model_registry.json")
    if not registry_path.exists():
        registry_path = Path(__file__).resolve().parent.parent.parent / "models" / "model_registry.json"
        if not registry_path.exists():
            return

    try:
        data = json.loads(registry_path.read_text())
        ai_data = data.get("ai_detector", {})
        active_filename = ai_data.get("active")
        if not active_filename:
            return

        model_path = f"models/{active_filename}"
        
        # Check if DB has this model_path
        res = await db.execute(select(TrainingRun).where(TrainingRun.model_path == model_path))
        existing = res.scalar_one_or_none()

        if not existing:
            # Determine user_id for TrainingRun
            uid = current_user_id
            if not uid:
                user_res = await db.execute(select(User.id).limit(1))
                uid = user_res.scalar_one_or_none()
            if not uid:
                return

            # Deactivate current active runs
            await db.execute(update(TrainingRun).values(is_active=False))
            
            trained_at_str = ai_data.get("trained_on") or ai_data.get("trained_at", "2026-08-26T10:41:27")
            try:
                dt = datetime.fromisoformat(str(trained_at_str).replace("Z", ""))
            except Exception:
                try:
                    dt = datetime.strptime(str(trained_at_str), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                except Exception:
                    dt = datetime.now(timezone.utc)

            run = TrainingRun(
                user_id=uid,
                status="completed",
                samples_count=int(ai_data.get("samples", 70)),
                accuracy=float(ai_data.get("accuracy", 0.72)),
                roc_auc=float(ai_data.get("roc_auc", 0.752)),
                f1_score=float(ai_data.get("f1_score", 0.68)),
                precision_score=float(ai_data.get("precision", 0.74)),
                recall_score=float(ai_data.get("recall", 0.63)),
                model_path=model_path,
                is_active=True,
                training_config={"source": "Auto-sync from model registry", "notes": ai_data.get("notes", "")},
                started_at=dt,
                completed_at=dt
            )
            db.add(run)
            await db.commit()
    except Exception as e:
        print(f"[WARN] Failed to auto-sync model_registry.json to DB: {e}")
        await db.rollback()


@router.get("/training/history", response_model=list[TrainingRunResponse])
async def training_history(current_user: InstructorUser, db: DBSession):
    """List all past training runs with metrics."""
    await _sync_registry_to_db(db, current_user.id)
    result = await db.execute(
        select(TrainingRun).order_by(TrainingRun.started_at.desc()).limit(50)
    )
    return result.scalars().all()


@router.get("/training/data-summary", response_model=TrainingStatsResponse)
async def data_summary(current_user: InstructorUser, db: DBSession):
    """Return annotation statistics and training readiness."""
    from app.engine.auto_trainer import get_annotation_stats
    stats = await get_annotation_stats()
    return TrainingStatsResponse(**stats)


@router.post("/training/{run_id}/activate", response_model=TrainingRunResponse)
async def activate_model(
    run_id: uuid.UUID,
    current_user: AdminUser,
    db: DBSession,
):
    """Activate a specific trained model version."""
    result = await db.execute(
        select(TrainingRun).where(
            TrainingRun.id == run_id,
            TrainingRun.status == "completed",
        )
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Completed training run not found.")

    if not run.model_path:
        raise HTTPException(status_code=400, detail="This training run has no saved model.")

    import shutil
    from pathlib import Path

    model_path = Path(run.model_path)
    if not model_path.exists():
        raise HTTPException(status_code=404, detail="Model file not found on disk.")

    # Copy to active model path
    active_path = Path("models/ai_detector.pkl")
    shutil.copy2(model_path, active_path)

    # Deactivate all, activate this one
    await db.execute(
        update(TrainingRun).where(TrainingRun.is_active == True).values(is_active=False)  # noqa: E712
    )
    run.is_active = True

    # Hot-swap the classifier
    from app.engine.ai_detector import reload_classifier
    reload_classifier()

    await db.flush()
    return run


@router.post("/training/{run_id}/rollback", response_model=TrainingRunResponse)
async def rollback_model(
    run_id: uuid.UUID,
    current_user: AdminUser,
    db: DBSession,
):
    """Rollback to a previous model version (alias for activate)."""
    return await activate_model(run_id, current_user, db)
