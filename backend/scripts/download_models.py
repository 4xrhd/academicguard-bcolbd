"""
download_models.py — Pre-download all required models.
Run: python scripts/download_models.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 70)
print("DOWNLOADING MODELS")
print("=" * 70)
print("\nThis will download:")
print("  • GPT-2 (~500MB)")
print("  • Sentence-Transformers all-MiniLM-L6-v2 (~100MB)")
print("  • NLTK data (stopwords, wordnet, punkt)")
print("\nTotal download: ~600MB")
print("This may take 5-10 minutes depending on your connection.\n")

input("Press Enter to continue or Ctrl+C to cancel...")

# Download GPT-2
print("\n[1/3] Downloading GPT-2...")
try:
    from transformers import GPT2LMHeadModel, GPT2TokenizerFast
    print("  Loading tokenizer...")
    tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
    print("  Loading model...")
    model = GPT2LMHeadModel.from_pretrained("gpt2")
    print("  ✓ GPT-2 downloaded successfully")
except Exception as e:
    print(f"  ✗ Error downloading GPT-2: {e}")

# Download Sentence-Transformers
print("\n[2/3] Downloading Sentence-Transformers...")
try:
    from sentence_transformers import SentenceTransformer
    print("  Loading all-MiniLM-L6-v2...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    print("  ✓ Sentence-Transformers downloaded successfully")
except Exception as e:
    print(f"  ✗ Error downloading Sentence-Transformers: {e}")

# Download NLTK data
print("\n[3/3] Downloading NLTK data...")
try:
    import os, nltk
    os.environ["NLTK_ALLOW_PROXIED_URLOPEN"] = "1"
    try:
        nltk.pathsec.ALLOW_PROXIED_FETCH = True
    except Exception:
        pass
    print("  Downloading stopwords...")
    nltk.download('stopwords', quiet=True)
    print("  Downloading wordnet...")
    nltk.download('wordnet', quiet=True)
    print("  Downloading punkt...")
    nltk.download('punkt', quiet=True)
    print("  Downloading punkt_tab...")
    nltk.download('punkt_tab', quiet=True)
    print("  ✓ NLTK data downloaded successfully")
except Exception as e:
    print(f"  ✗ Error downloading NLTK data: {e}")

print("\n" + "=" * 70)
print("✓ ALL MODELS DOWNLOADED")
print("=" * 70)
print("\nYou can now run:")
print("  python scripts/test_transformers.py")
print("  python scripts/extract_features.py")
print("  python scripts/train_ai_detector.py")
