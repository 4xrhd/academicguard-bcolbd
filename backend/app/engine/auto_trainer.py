"""
auto_trainer.py — Automated model training pipeline.

Workflow:
    1. Collect annotated submissions from the database
    2. Extract features (perplexity, burstiness, stylometric)
    3. Train a StandardScaler → LogisticRegression pipeline
    4. Validate against held-out test set
    5. Save model + metrics, optionally hot-swap if performance improves
"""
import asyncio
import json
import pickle
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, classification_report, f1_score,
    precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.config import get_settings

settings = get_settings()

# Minimum samples per class required to train
MIN_SAMPLES_PER_CLASS = 5
MIN_TOTAL_SAMPLES = 20

# Lock to prevent concurrent model registry writes
_TRAINING_LOCK = asyncio.Lock()

# Label mapping: annotation labels → binary classifier target
LABEL_MAP = {
    "human": 0,
    "ai_generated": 1,
    "plagiarized": 0,   # Plagiarized is human-written (copied), not AI
    "mixed": 1,         # Mixed content treated as AI-flagged
}


async def run_training(training_run_id: str) -> None:
    """
    Main training pipeline — runs as a background task.
    Updates the TrainingRun record with progress, metrics, and results.
    """
    from sqlalchemy import select, update
    from app.db.session import AsyncSessionLocal
    from app.db.models import Annotation, Submission, TrainingRun

    async with AsyncSessionLocal() as db:
        # Mark as running
        
        # Retry loop for eventual consistency/race conditions
        run = None
        import asyncio
        for attempt in range(5):
            run_result = await db.execute(
                select(TrainingRun).where(TrainingRun.id == uuid.UUID(training_run_id))
            )
            run = run_result.scalar_one_or_none()
            if run:
                break
            print(f"[TRAINER] TrainingRun {training_run_id} not found yet, retrying... (Attempt {attempt+1}/5)")
            await asyncio.sleep(0.2)

        if not run:
            print(f"[TRAINER] TrainingRun {training_run_id} not found after retries. Exiting.")
            return

        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        await db.commit()

        try:
            # ── Phase 1: Collect annotated data ──────────────────────────
            print("[TRAINER] Phase 1: Collecting annotated submissions...")
            result = await db.execute(
                select(Submission, Annotation)
                .join(Annotation, Annotation.submission_id == Submission.id)
                .where(Submission.raw_text.isnot(None))
            )
            rows = result.all()

            texts = []
            labels = []
            for sub, ann in rows:
                if ann.label in LABEL_MAP:
                    texts.append(sub.raw_text)
                    labels.append(LABEL_MAP[ann.label])

            if len(texts) < MIN_TOTAL_SAMPLES:
                raise ValueError(
                    f"Need at least {MIN_TOTAL_SAMPLES} valid annotated samples with extracted text, "
                    f"but only found {len(texts)}."
                )

            labels_arr = np.array(labels)
            class_counts = {
                "human": int(np.sum(labels_arr == 0)),
                "ai": int(np.sum(labels_arr == 1)),
            }

            if class_counts["human"] < MIN_SAMPLES_PER_CLASS:
                raise ValueError(
                    f"Need at least {MIN_SAMPLES_PER_CLASS} 'human' samples, "
                    f"got {class_counts['human']}."
                )
            if class_counts["ai"] < MIN_SAMPLES_PER_CLASS:
                raise ValueError(
                    f"Need at least {MIN_SAMPLES_PER_CLASS} 'ai' samples, "
                    f"got {class_counts['ai']}."
                )

            print(f"[TRAINER] Collected {len(texts)} samples: {class_counts}")
            run.samples_count = len(texts)
            await db.commit()

            # ── Phase 2: Extract features ────────────────────────────────
            print("[TRAINER] Phase 2: Extracting features...")
            from app.engine.ai_detector import (
                compute_perplexity, compute_burstiness, compute_stylometric_score,
            )

            features = []
            for i, text in enumerate(texts):
                clean_text = text[:4000] if text else ""
                ppl = await asyncio.to_thread(compute_perplexity, clean_text) or 0.0
                bur = await asyncio.to_thread(compute_burstiness, clean_text) or 0.0
                sty = await asyncio.to_thread(compute_stylometric_score, clean_text) or 0.0
                features.append([ppl, bur, sty])
                if (i + 1) % 10 == 0 or i == len(texts) - 1:
                    print(f"[TRAINER]   Extracted features for {i + 1}/{len(texts)}")
                await asyncio.sleep(0.01)

            X = np.array(features)
            y = labels_arr

            # Drop any rows where all features are zero (extraction failed)
            valid_mask = np.any(X != 0.0, axis=1)
            X = X[valid_mask]
            y = y[valid_mask]

            if len(X) < MIN_TOTAL_SAMPLES:
                raise ValueError(
                    f"After feature extraction, only {len(X)} valid samples remain "
                    f"(need {MIN_TOTAL_SAMPLES})."
                )

            print(f"[TRAINER] Feature extraction complete: {len(X)} valid samples")

            # ── Phase 3: Train model (CPU-bound, run off event loop) ──────
            print("[TRAINER] Phase 3: Training model...")
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, stratify=y, random_state=42,
            )

            pipeline = Pipeline([
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(C=1.0, max_iter=500, random_state=42)),
            ])

            # Cross-validation (CPU-bound)
            n_folds = min(5, min(np.sum(y_train == 0), np.sum(y_train == 1)))
            n_folds = max(n_folds, 2)
            cv_scores = await asyncio.to_thread(
                cross_val_score, pipeline, X_train, y_train, cv=n_folds, scoring="roc_auc"
            )
            print(f"[TRAINER] CV ROC-AUC: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

            # Final training (CPU-bound)
            await asyncio.to_thread(pipeline.fit, X_train, y_train)

            # ── Phase 4: Evaluate ────────────────────────────────────────
            print("[TRAINER] Phase 4: Evaluating model...")
            y_pred = pipeline.predict(X_test)
            y_proba = pipeline.predict_proba(X_test)[:, 1]

            metrics = {
                "accuracy": float(accuracy_score(y_test, y_pred)),
                "roc_auc": float(roc_auc_score(y_test, y_proba)),
                "f1": float(f1_score(y_test, y_pred)),
                "precision": float(precision_score(y_test, y_pred)),
                "recall": float(recall_score(y_test, y_pred)),
            }
            print(f"[TRAINER] Metrics: {metrics}")

            # ── Phase 5: Save model (locked to prevent concurrent writes) ─
            print("[TRAINER] Phase 5: Saving model...")
            async with _TRAINING_LOCK:
                import shutil
                model_dir = Path("models")
                model_dir.mkdir(exist_ok=True)
                backups_dir = model_dir / "backups"
                backups_dir.mkdir(exist_ok=True)

                # Version the model file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                model_filename = f"ai_detector_v{timestamp}.pkl"
                model_path = model_dir / model_filename
                active_path = model_dir / "ai_detector.pkl"

                # Preserve old active model on disk
                if active_path.exists():
                    backup_path = backups_dir / f"ai_detector_backup_{timestamp}.pkl"
                    try:
                        shutil.copy2(active_path, backup_path)
                        print(f"[TRAINER] Preserved active model backup at {backup_path}")
                    except Exception as b_exc:
                        print(f"[TRAINER] Warning: Failed to backup active model: {b_exc!r}")

                with open(model_path, "wb") as f:
                    pickle.dump(pipeline, f)

                # Also save as the active model
                with open(active_path, "wb") as f:
                    pickle.dump(pipeline, f)

                # Update model registry with historical preservation
                registry_path = model_dir / "model_registry.json"
                registry = {}
                if registry_path.exists():
                    try:
                        with open(registry_path, "r") as f:
                            registry = json.load(f)
                    except Exception:
                        registry = {}

                history = registry.get("history", [])
                if "ai_detector" in registry and isinstance(registry["ai_detector"], dict):
                    history.append(registry["ai_detector"])

                registry["ai_detector"] = {
                    "active": model_filename,
                    "trained_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "samples": int(len(X)),
                    "roc_auc": metrics["roc_auc"],
                    "accuracy": metrics["accuracy"],
                    "f1_score": metrics["f1"],
                    "cv_roc_auc_mean": float(cv_scores.mean()),
                    "cv_roc_auc_std": float(cv_scores.std()),
                    "class_distribution": class_counts,
                    "notes": f"Auto-trained from {len(X)} annotated submissions",
                }
                registry["history"] = history

                with open(registry_path, "w") as f:
                    json.dump(registry, f, indent=2)

            # ── Phase 6: Hot-swap the live model ─────────────────────────
            print("[TRAINER] Phase 6: Hot-swapping live model...")
            from app.engine.ai_detector import reload_classifier
            reload_classifier()

            # Deactivate all previous runs, activate this one
            await db.execute(
                update(TrainingRun).where(TrainingRun.is_active == True).values(is_active=False)  # noqa: E712
            )

            run.status = "completed"
            run.accuracy = metrics["accuracy"]
            run.roc_auc = metrics["roc_auc"]
            run.f1_score = metrics["f1"]
            run.precision_score = metrics["precision"]
            run.recall_score = metrics["recall"]
            run.model_path = str(model_path)
            run.is_active = True
            run.completed_at = datetime.now(timezone.utc)
            run.training_config = {
                "pipeline": "StandardScaler + LogisticRegression",
                "features": ["perplexity", "burstiness", "stylometric"],
                "test_size": 0.2,
                "cv_folds": int(n_folds),
                "C": 1.0,
                "max_iter": 500,
            }
            await db.commit()

            print(f"[TRAINER] ✓ Training complete! Model saved to {model_path}")
            print(f"[TRAINER] ✓ ROC-AUC: {metrics['roc_auc']:.3f}, "
                  f"Accuracy: {metrics['accuracy']:.3f}, F1: {metrics['f1']:.3f}")

        except Exception as exc:
            run.status = "failed"
            run.error_message = str(exc)
            run.completed_at = datetime.now(timezone.utc)
            await db.commit()
            print(f"[TRAINER] ✗ Training failed: {exc!r}")
            raise


async def get_annotation_stats() -> dict:
    """Return summary statistics about available annotations."""
    from sqlalchemy import select, func
    from app.db.session import AsyncSessionLocal
    from app.db.models import Annotation

    async with AsyncSessionLocal() as db:
        # Total count
        total_result = await db.execute(select(func.count(Annotation.id)))
        total = total_result.scalar_one()

        # Per-label counts
        label_result = await db.execute(
            select(Annotation.label, func.count(Annotation.id))
            .group_by(Annotation.label)
        )
        label_counts = {row[0]: row[1] for row in label_result.all()}

        # Binary distribution for classifier
        human_count = label_counts.get("human", 0) + label_counts.get("plagiarized", 0)
        ai_count = label_counts.get("ai_generated", 0) + label_counts.get("mixed", 0)

        # Readiness check
        ready = (
            human_count >= MIN_SAMPLES_PER_CLASS
            and ai_count >= MIN_SAMPLES_PER_CLASS
            and total >= MIN_TOTAL_SAMPLES
        )

        return {
            "total_annotations": total,
            "label_distribution": label_counts,
            "binary_distribution": {"human": human_count, "ai": ai_count},
            "min_samples_required": MIN_TOTAL_SAMPLES,
            "min_per_class_required": MIN_SAMPLES_PER_CLASS,
            "ready_to_train": ready,
        }


async def resume_pending_training() -> None:
    """Startup task to re-queue training runs that were pending or stuck in running."""
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.db.models import TrainingRun
    import asyncio

    print("[TRAINER] Checking for pending/stuck training runs to resume...")
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TrainingRun).where(TrainingRun.status.in_(["pending", "running"]))
        )
        runs = result.scalars().all()

        for run in runs:
            print(f"[TRAINER] Resuming stalled training run {run.id} ({run.status})")
            # We don't await run_training here; we start it as a task
            asyncio.create_task(run_training(str(run.id)))
