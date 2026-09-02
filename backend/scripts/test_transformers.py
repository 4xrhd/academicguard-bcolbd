"""
test_transformers.py — Test GPT-2 and Sentence-Transformers are working.
Run: python scripts/test_transformers.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
os.environ['DATABASE_URL'] = 'postgresql://dummy:dummy@localhost/dummy'
os.environ['JWT_SECRET_KEY'] = 'dummy_key_for_testing'

print("=" * 70)
print("TESTING GPT-2 AND SENTENCE-TRANSFORMERS")
print("=" * 70)

# Test 1: GPT-2 Perplexity
print("\n[1/4] Testing GPT-2 perplexity...")
try:
    from app.engine.ai_detector import compute_perplexity
    
    human_text = "I struggled with this problem but finally figured it out!"
    ai_text = "The implementation requires careful consideration of complexity factors."
    
    print(f"  Computing perplexity for human text...")
    human_perp = compute_perplexity(human_text)
    print(f"  Human text perplexity: {human_perp:.2f}" if human_perp else "  Failed")
    
    print(f"  Computing perplexity for AI text...")
    ai_perp = compute_perplexity(ai_text)
    print(f"  AI text perplexity: {ai_perp:.2f}" if ai_perp else "  Failed")
    
    if human_perp and ai_perp:
        print(f"  ✓ GPT-2 perplexity working")
    else:
        print(f"  ✗ GPT-2 perplexity failed")
except Exception as e:
    print(f"  ✗ Error: {e}")

# Test 2: Burstiness
print("\n[2/4] Testing burstiness calculation...")
try:
    from app.engine.ai_detector import compute_burstiness
    
    text = """
    This is sentence one. This is sentence two. This is sentence three.
    This is sentence four. This is sentence five. This is sentence six.
    """
    
    print(f"  Computing burstiness...")
    burstiness = compute_burstiness(text)
    print(f"  Burstiness score: {burstiness:.2f}" if burstiness else "  Failed (need 3+ sentences)")
    
    if burstiness is not None:
        print(f"  ✓ Burstiness calculation working")
    else:
        print(f"  ⚠ Burstiness returned None (may need longer text)")
except Exception as e:
    print(f"  ✗ Error: {e}")

# Test 3: TF-IDF Similarity
print("\n[3/4] Testing TF-IDF similarity...")
try:
    from app.engine.text_similarity import _compute_tfidf
    
    texts = [
        "Binary search is an efficient algorithm for finding items.",
        "Binary search represents an efficient searching algorithm.",
        "Bubble sort is a simple sorting algorithm."
    ]
    
    print(f"  Computing TF-IDF similarity matrix...")
    matrix = _compute_tfidf(texts)
    
    if matrix:
        print(f"  Similarity matrix shape: {len(matrix)}x{len(matrix[0])}")
        print(f"  Text 1 vs Text 2: {matrix[0][1]:.3f}")
        print(f"  Text 1 vs Text 3: {matrix[0][2]:.3f}")
        print(f"  ✓ TF-IDF similarity working")
    else:
        print(f"  ✗ TF-IDF failed")
except Exception as e:
    print(f"  ✗ Error: {e}")

# Test 4: Sentence-Transformers Semantic Similarity
print("\n[4/4] Testing Sentence-Transformers semantic similarity...")
try:
    from app.engine.text_similarity import _compute_semantic
    
    texts = [
        "Binary search is an efficient algorithm for finding items.",
        "Binary search represents an efficient searching algorithm.",
        "Bubble sort is a simple sorting algorithm."
    ]
    
    print(f"  Computing semantic similarity matrix...")
    matrix = _compute_semantic(texts)
    
    if matrix:
        print(f"  Similarity matrix shape: {len(matrix)}x{len(matrix[0])}")
        print(f"  Text 1 vs Text 2: {matrix[0][1]:.3f}")
        print(f"  Text 1 vs Text 3: {matrix[0][2]:.3f}")
        print(f"  ✓ Sentence-Transformers working")
    else:
        print(f"  ✗ Semantic similarity failed")
except Exception as e:
    print(f"  ✗ Error: {e}")

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print("""
If all tests passed:
  ✓ GPT-2 is loaded and working
  ✓ Sentence-Transformers is loaded and working
  ✓ TF-IDF vectorization is working
  ✓ All NLP features are enabled

Next steps:
  1. Run full test suite: python scripts/test_models_standalone.py
  2. Extract features: python scripts/extract_features.py
  3. Train model: python scripts/train_ai_detector.py

Note: First run will download models (~500MB for GPT-2, ~100MB for Sentence-Transformers)
This may take a few minutes depending on your internet connection.
""")
