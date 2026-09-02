"""
train_ai_detector.py — Train AI content detection model.
Run: python scripts/train_ai_detector.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pickle
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, roc_auc_score

def main():
    # Load features
    print("Loading features...")
    df = pd.read_csv("data/features.csv")
    
    FEATURES = ["perplexity", "burstiness", "stylometric"]
    X = df[FEATURES].values
    y = df["label"].values
    
    print(f"Dataset: {len(df)} samples")
    print(f"Class distribution: {sum(y)} AI, {len(y) - sum(y)} human")

    # Train / test split (stratified to preserve class balance)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    
    print(f"\nTraining set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples")

    # Pipeline: StandardScaler → LogisticRegression
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf",    LogisticRegression(C=1.0, max_iter=500, random_state=42)),
    ])

    # Cross-validation with adaptive fold count
    # For small datasets, use fewer folds
    n_folds = min(5, len(X_train) // 2)
    print(f"\nRunning {n_folds}-fold cross-validation...")
    
    if n_folds >= 2:
        cv_scores = cross_val_score(pipeline, X_train, y_train, cv=n_folds, scoring="roc_auc")
        print(f"CV ROC-AUC: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
    else:
        print("⚠ Dataset too small for cross-validation, skipping...")
        cv_scores = None

    # Final fit on full training set
    print("\nTraining final model...")
    pipeline.fit(X_train, y_train)

    # Evaluation on held-out test set
    print("\nEvaluating on test set...")
    y_pred  = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]
    
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=["human", "ai"]))
    print(f"Test ROC-AUC: {roc_auc_score(y_test, y_proba):.3f}")

    # Save model with disk versioning and backup preservation
    import shutil
    import json
    from datetime import datetime

    model_dir = Path("models")
    model_dir.mkdir(exist_ok=True)
    backups_dir = model_dir / "backups"
    backups_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    versioned_filename = f"ai_detector_v{timestamp}.pkl"
    versioned_path = model_dir / versioned_filename
    active_path = model_dir / "ai_detector.pkl"

    # Preserve old model if present
    if active_path.exists():
        backup_path = backups_dir / f"ai_detector_backup_{timestamp}.pkl"
        shutil.copy2(active_path, backup_path)
        print(f"✓ Preserved previous active model to {backup_path}")

    # Save versioned model file and update active model
    with open(versioned_path, "wb") as f:
        pickle.dump(pipeline, f)
    with open(active_path, "wb") as f:
        pickle.dump(pipeline, f)
    
    print(f"\n✓ Model saved to {versioned_path} and {active_path}")
    
    # Save model registry with historical preservation
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

    new_model_info = {
        "active": versioned_filename,
        "trained_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "samples": len(df),
        "roc_auc": float(roc_auc_score(y_test, y_proba)),
        "notes": "Trained via scripts/train_ai_detector.py"
    }

    registry["ai_detector"] = new_model_info
    registry["history"] = history

    with open(registry_path, "w") as f:
        json.dump(registry, f, indent=2)
    
    print("✓ Model registry updated with historical preservation")

if __name__ == "__main__":
    main()
