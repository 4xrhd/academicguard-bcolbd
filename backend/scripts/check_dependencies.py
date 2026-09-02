"""
check_dependencies.py — Check if all required packages are installed.
Run: python scripts/check_dependencies.py
"""
import sys

print("=" * 70)
print("CHECKING DEPENDENCIES")
print("=" * 70)

dependencies = {
    'torch': 'PyTorch',
    'transformers': 'HuggingFace Transformers (GPT-2)',
    'sentence_transformers': 'Sentence-Transformers',
    'sklearn': 'scikit-learn (TF-IDF)',
    'nltk': 'NLTK (text preprocessing)',
    'numpy': 'NumPy',
    'httpx': 'HTTPX (API calls)',
}

missing = []
installed = []

for module, name in dependencies.items():
    try:
        __import__(module)
        installed.append(name)
        print(f"✓ {name}")
    except ImportError:
        missing.append(name)
        print(f"✗ {name} - NOT INSTALLED")

print("\n" + "=" * 70)
if missing:
    print(f"MISSING DEPENDENCIES: {len(missing)}")
    print("=" * 70)
    print("\nTo install missing dependencies:")
    print("  pip install -r requirements.txt")
    sys.exit(1)
else:
    print(f"✓ ALL DEPENDENCIES INSTALLED ({len(installed)}/{len(dependencies)})")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Download models: python scripts/download_models.py")
    print("  2. Test models: python scripts/test_transformers.py")
    print("  3. Extract features: python scripts/extract_features.py")
    sys.exit(0)
