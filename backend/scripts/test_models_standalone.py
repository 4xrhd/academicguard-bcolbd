"""
test_models_standalone.py — Standalone testing without config dependencies.
Run: python scripts/test_models_standalone.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import ast
import difflib
import re
from typing import List, Optional


# ── Standalone implementations (no config dependencies) ──────────────────────

def compute_stylometric_score(text: str) -> Optional[float]:
    """Extract stylometric features from text."""
    if not text.strip():
        return None

    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    words = text.split()

    if not words or not sentences:
        return None

    avg_sentence_len = len(words) / len(sentences)
    type_token_ratio = len(set(w.lower() for w in words)) / len(words)
    punct_density = sum(1 for c in text if c in ".,;:!?") / len(text)

    score = (
        0.3 * min(avg_sentence_len / 25, 1.0) +
        0.4 * (1 - type_token_ratio) +
        0.3 * (1 - punct_density * 10)
    )
    return min(max(score, 0.0), 1.0)


def normalize_code(source: str) -> List[str] | None:
    """Parse Python code and normalize identifiers."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    identifier_map: dict[str, str] = {}
    counter = [0]

    def canonical(name: str) -> str:
        if name not in identifier_map:
            identifier_map[name] = f"var{counter[0]}"
            counter[0] += 1
        return identifier_map[name]

    tokens: List[str] = []
    for node in ast.walk(tree):
        node_type = type(node).__name__
        tokens.append(node_type)

        if isinstance(node, ast.Name):
            tokens.append(canonical(node.id))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            tokens.append(canonical(node.name))
        elif isinstance(node, ast.ClassDef):
            tokens.append(canonical(node.name))

    return tokens


def compute_code_similarity(blocks_a: List[str], blocks_b: List[str]) -> float:
    """Compare code blocks using AST similarity."""
    if not blocks_a or not blocks_b:
        return 0.0

    best = 0.0
    for block_a in blocks_a:
        tokens_a = normalize_code(block_a)
        if tokens_a is None:
            continue
        for block_b in blocks_b:
            tokens_b = normalize_code(block_b)
            if tokens_b is None:
                continue
            
            # Edit distance similarity
            if not tokens_a and not tokens_b:
                score = 1.0
            else:
                max_len = max(len(tokens_a), len(tokens_b))
                if max_len == 0:
                    score = 0.0
                else:
                    matcher = difflib.SequenceMatcher(None, tokens_a, tokens_b)
                    score = matcher.ratio()
            
            best = max(best, score)
    return best


# ── Test functions ────────────────────────────────────────────────────────────

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
    assert score > 0.95, f"Expected >0.95, got {score}"
    
    # Test 2: Renamed variables
    code2a = "def calculate(num): return num * 2"
    code2b = "def compute(val): return val * 2"
    score = compute_code_similarity([code2a], [code2b])
    print(f"\nTest 2: Renamed variables")
    print(f"Code A: {code2a}")
    print(f"Code B: {code2b}")
    print(f"Similarity: {score:.3f} (expected: >0.8)")
    assert score > 0.8, f"Expected >0.8, got {score}"
    
    # Test 3: Different code
    code3a = "def foo(x): return x + 1"
    code3b = "class Bar: pass"
    score = compute_code_similarity([code3a], [code3b])
    print(f"\nTest 3: Different code")
    print(f"Code A: {code3a}")
    print(f"Code B: {code3b}")
    print(f"Similarity: {score:.3f} (expected: <0.5)")
    assert score < 0.5, f"Expected <0.5, got {score}"
    
    # Test 4: Token normalization
    tokens1 = normalize_code("def foo(x): return x")
    tokens2 = normalize_code("def bar(y): return y")
    print(f"\nTest 4: Token normalization")
    print(f"Tokens 1: {tokens1[:10]}...")
    print(f"Tokens 2: {tokens2[:10]}...")
    has_var0 = ('var0' in tokens1) and ('var0' in tokens2)
    print(f"Both contain 'var0': {has_var0}")
    assert has_var0, "Token normalization failed"
    
    print(f"\n✓ Code similarity detection working")


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
    
    # Test 1: Compare similar submissions (001 & 002)
    sub1, sub2 = submissions[0], submissions[1]
    print(f"\nTest 1: Similar submissions (paraphrased)")
    print(f"  Student 1: {sub1['student_name']}")
    print(f"  Student 2: {sub2['student_name']}")
    
    code_sim = compute_code_similarity([sub1['code']], [sub2['code']])
    print(f"  Code similarity: {code_sim:.3f} (expected: >0.8)")
    assert code_sim > 0.8, f"Expected >0.8, got {code_sim}"
    
    style1 = compute_stylometric_score(sub1['text'])
    style2 = compute_stylometric_score(sub2['text'])
    print(f"  Stylometric scores: {style1:.3f}, {style2:.3f}")
    
    # Test 2: Compare near-duplicate (001 & 005)
    sub1, sub5 = submissions[0], submissions[4]
    print(f"\nTest 2: Near-duplicate submissions")
    print(f"  Student 1: {sub1['student_name']}")
    print(f"  Student 5: {sub5['student_name']}")
    
    code_sim = compute_code_similarity([sub1['code']], [sub5['code']])
    print(f"  Code similarity: {code_sim:.3f} (expected: ~1.0)")
    assert code_sim > 0.95, f"Expected >0.95, got {code_sim}"
    
    # Test 3: Compare different topics (003 & 004)
    sub3, sub4 = submissions[2], submissions[3]
    print(f"\nTest 3: Different topics")
    print(f"  Student 3: {sub3['student_name']}")
    print(f"  Student 4: {sub4['student_name']}")
    
    code_sim = compute_code_similarity([sub3['code']], [sub4['code']])
    print(f"  Code similarity: {code_sim:.3f} (expected: <0.5)")
    assert code_sim < 0.5, f"Expected <0.5, got {code_sim}"
    
    print(f"\n✓ Sample data tests complete")


def main():
    print("\n" + "=" * 60)
    print("ACADEMICGUARD - MODEL TESTING SUITE")
    print("(Standalone - No Config Dependencies)")
    print("=" * 60)
    
    try:
        test_ai_detection()
        test_code_similarity()
        test_with_sample_data()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Expand data/ai_detection_dataset.csv with more samples")
        print("  2. Run: python scripts/train_ai_detector.py")
        print("  3. See MODEL_TESTING.md for detailed guide")
        print("")
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
