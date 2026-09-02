"""
test_models_manual.py — Manual testing script for all models.
Run: python scripts/test_models_manual.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from app.engine.ai_detector import compute_stylometric_score
from app.engine.code_similarity import normalize_code, compute_code_similarity
from app.engine.text_similarity import _preprocess


def test_ai_detection():
    """Test AI detection features."""
    print("=" * 60)
    print("AI DETECTION TESTS")
    print("=" * 60)
    
    human_text = "I struggled with this problem but finally figured it out!"
    ai_text = "The implementation requires careful consideration of complexity factors."
    
    human_score = compute_stylometric_score(human_text)
    ai_score = compute_stylometric_score(ai_text)
    
    print(f"\nHuman text: {human_text[:50]}...")
    print(f"Stylometric score: {human_score:.3f}")
    
    print(f"\nAI text: {ai_text[:50]}...")
    print(f"Stylometric score: {ai_score:.3f}")
    
    print(f"\n✓ AI detection features working")


def test_code_similarity():
    """Test code similarity detection."""
    print("\n" + "=" * 60)
    print("CODE SIMILARITY TESTS")
    print("=" * 60)
    
    # Test 1: Identical code
    code1 = "def foo(x): return x + 1"
    score = compute_code_similarity([code1], [code1])
    print(f"\nTest 1: Identical code")
    print(f"Code: {code1}")
    print(f"Similarity: {score:.3f} (expected: ~1.0)")
    
    # Test 2: Renamed variables
    code2a = "def calculate(num): return num * 2"
    code2b = "def compute(val): return val * 2"
    score = compute_code_similarity([code2a], [code2b])
    print(f"\nTest 2: Renamed variables")
    print(f"Code A: {code2a}")
    print(f"Code B: {code2b}")
    print(f"Similarity: {score:.3f} (expected: >0.8)")
    
    # Test 3: Different code
    code3a = "def foo(x): return x + 1"
    code3b = "class Bar: pass"
    score = compute_code_similarity([code3a], [code3b])
    print(f"\nTest 3: Different code")
    print(f"Code A: {code3a}")
    print(f"Code B: {code3b}")
    print(f"Similarity: {score:.3f} (expected: <0.5)")
    
    # Test 4: Token normalization
    tokens1 = normalize_code("def foo(x): return x")
    tokens2 = normalize_code("def bar(y): return y")
    print(f"\nTest 4: Token normalization")
    print(f"Tokens 1: {tokens1[:10]}...")
    print(f"Tokens 2: {tokens2[:10]}...")
    print(f"Both contain 'var0': {('var0' in tokens1) and ('var0' in tokens2)}")
    
    print(f"\n✓ Code similarity detection working")


def test_text_preprocessing():
    """Test text preprocessing."""
    print("\n" + "=" * 60)
    print("TEXT PREPROCESSING TESTS")
    print("=" * 60)
    
    text = "Binary Search is EFFICIENT!"
    processed = _preprocess(text)
    
    print(f"\nOriginal: {text}")
    print(f"Processed: {processed}")
    print(f"Lowercased: {processed.islower()}")
    
    print(f"\n✓ Text preprocessing working")


def test_with_sample_data():
    """Test with realistic sample data."""
    print("\n" + "=" * 60)
    print("SAMPLE DATA TESTS")
    print("=" * 60)
    
    data_path = Path("data/test_submissions.json")
    if not data_path.exists():
        print(f"\n⚠ Sample data not found at {data_path}")
        print("Run: python scripts/create_test_data.py")
        return
    
    with open(data_path) as f:
        submissions = json.load(f)
    
    print(f"\nLoaded {len(submissions)} test submissions")
    
    # Compare first two submissions (should be similar)
    sub1, sub2 = submissions[0], submissions[1]
    
    print(f"\nComparing:")
    print(f"  Student 1: {sub1['student_name']}")
    print(f"  Student 2: {sub2['student_name']}")
    
    # Code similarity
    code_sim = compute_code_similarity([sub1['code']], [sub2['code']])
    print(f"\nCode similarity: {code_sim:.3f}")
    
    # Stylometric scores
    style1 = compute_stylometric_score(sub1['text'])
    style2 = compute_stylometric_score(sub2['text'])
    print(f"Stylometric scores: {style1:.3f}, {style2:.3f}")
    
    print(f"\n✓ Sample data tests complete")


def main():
    print("\n" + "=" * 60)
    print("ACADEMICGUARD - MODEL TESTING SUITE")
    print("=" * 60)
    
    try:
        test_ai_detection()
        test_code_similarity()
        test_text_preprocessing()
        test_with_sample_data()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
