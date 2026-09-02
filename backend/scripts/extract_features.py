"""
extract_features.py — Extract AI detection features from dataset.
Run: python scripts/extract_features.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from app.engine.ai_detector import (
    compute_perplexity, compute_burstiness, compute_stylometric_score
)

def main():
    print("Loading dataset...")
    df = pd.read_csv("data/ai_detection_dataset.csv")
    print(f"Loaded {len(df)} samples")

    print("\nExtracting features (this may take a while)...")
    df["perplexity"]  = df["text"].apply(lambda x: compute_perplexity(x) or 0.0)
    df["burstiness"]  = df["text"].apply(lambda x: compute_burstiness(x) or 0.0)
    df["stylometric"] = df["text"].apply(lambda x: compute_stylometric_score(x) or 0.0)

    # Drop rows where feature extraction failed
    initial_count = len(df)
    df = df.dropna(subset=["stylometric"])
    final_count = len(df)
    
    if initial_count > final_count:
        print(f"Dropped {initial_count - final_count} samples due to extraction failures")

    output_path = "data/features.csv"
    df.to_csv(output_path, index=False)
    print(f"\n✓ Extracted features for {len(df)} samples")
    print(f"✓ Saved to {output_path}")

if __name__ == "__main__":
    main()
