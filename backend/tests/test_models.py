"""
test_models.py — Unit tests for all detection models.
Run: pytest tests/test_models.py -v
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.engine.ai_detector import (
    compute_perplexity, compute_burstiness, compute_stylometric_score
)
from app.engine.text_similarity import _preprocess
from app.engine.code_similarity import normalize_code, compute_code_similarity


class TestAIDetector:
    """Test AI content detection features."""
    
    def test_stylometric_score_human_text(self):
        """Human text should have varied sentence structure."""
        text = "I love coding. It's fun! Sometimes it's hard though."
        score = compute_stylometric_score(text)
        assert score is not None
        assert 0.0 <= score <= 1.0
    
    def test_stylometric_score_ai_text(self):
        """AI text tends to have uniform structure."""
        text = """
        The implementation of algorithms requires careful consideration of complexity.
        Efficient solutions are crucial for optimizing performance metrics.
        Various approaches exist each with distinct characteristics and trade-offs.
        """
        score = compute_stylometric_score(text)
        assert score is not None
        assert 0.0 <= score <= 1.0
    
    def test_stylometric_score_empty(self):
        """Empty text should return None."""
        assert compute_stylometric_score("") is None
        assert compute_stylometric_score("   ") is None
    
    def test_perplexity_returns_float_when_gpt2_is_active(self):
        """Perplexity should return a valid float now that GPT-2 is fully loaded."""
        text = "This is a test sentence."
        result = compute_perplexity(text)
        # GPT-2 is active and returns a real perplexity value
        assert result is not None
        assert isinstance(result, float)
        assert result > 0.0
    
    def test_burstiness_returns_none_when_not_implemented(self):
        """Burstiness should return None until implemented."""
        text = "Sentence one. Sentence two. Sentence three."
        result = compute_burstiness(text)
        assert result is None


class TestTextSimilarity:
    """Test text similarity preprocessing."""
    
    def test_preprocess_lowercase(self):
        """Text should be lowercased."""
        result = _preprocess("HELLO WORLD")
        assert result == "hello world"
    
    def test_preprocess_preserves_content(self):
        """Basic preprocessing should preserve words."""
        text = "Binary search is efficient"
        result = _preprocess(text)
        assert "binary" in result
        assert "search" in result


class TestCodeSimilarity:
    """Test code similarity detection."""
    
    def test_normalize_code_simple(self):
        """Simple Python code should be normalized."""
        code = "def foo(x): return x + 1"
        tokens = normalize_code(code)
        assert tokens is not None
        assert "function_definition" in tokens
        assert "return_statement" in tokens
    
    def test_normalize_code_renames_identifiers(self):
        """Variable names should be normalized to var0, var1, etc."""
        code1 = "def foo(x): return x + 1"
        code2 = "def bar(y): return y + 1"
        
        tokens1 = normalize_code(code1)
        tokens2 = normalize_code(code2)
        
        # After normalization, both should have similar token sequences
        assert tokens1 is not None
        assert tokens2 is not None
        # Both should have var0 for the function name and parameter
        assert "var0" in tokens1
        assert "var0" in tokens2
    
    def test_normalize_code_invalid_syntax(self):
        """Invalid Python should fall back to fallback/regex tokenization."""
        code = "def foo(x: return x +"
        tokens = normalize_code(code)
        assert tokens is not None
        assert isinstance(tokens, list)
        assert len(tokens) > 0
    
    def test_compute_code_similarity_identical(self):
        """Identical code should have similarity close to 1.0."""
        code = "def foo(x): return x * 2"
        score = compute_code_similarity([code], [code])
        assert score > 0.9
    
    def test_compute_code_similarity_renamed_vars(self):
        """Code with renamed variables should still be similar."""
        code1 = "def calculate(num): return num * 2"
        code2 = "def compute(val): return val * 2"
        score = compute_code_similarity([code1], [code2])
        assert score > 0.8
    
    def test_compute_code_similarity_different(self):
        """Completely different code should have low similarity."""
        code1 = "def foo(x): return x + 1"
        code2 = "class Bar: pass"
        score = compute_code_similarity([code1], [code2])
        assert score < 0.5
    
    def test_compute_code_similarity_empty(self):
        """Empty code blocks should return 0.0."""
        assert compute_code_similarity([], []) == 0.0
        assert compute_code_similarity(["def foo(): pass"], []) == 0.0


class TestIntegration:
    """Integration tests with realistic data."""
    
    def test_full_pipeline_similar_submissions(self):
        """Test detection of similar submissions."""
        text1 = """
        Binary search is an efficient algorithm for finding items in sorted lists.
        It works by repeatedly dividing the search space in half.
        """
        
        text2 = """
        Binary search represents an efficient searching algorithm for sorted arrays.
        The methodology involves repeatedly dividing the search interval in half.
        """
        
        code1 = "def binary_search(arr, x): return x in arr"
        code2 = "def search(data, target): return target in data"
        
        # Both should have reasonable stylometric scores
        style1 = compute_stylometric_score(text1)
        style2 = compute_stylometric_score(text2)
        assert style1 is not None
        assert style2 is not None
        
        # Code should be similar after normalization
        code_sim = compute_code_similarity([code1], [code2])
        assert code_sim > 0.7


class TestRiskScoring:
    """Test dual weight profile logic."""
    
    def test_compute_risk_score_code_present(self):
        """When code is present, it should use the 35/35/30 split and return code_sim_max."""
        from app.engine.risk_scorer import compute_risk_score
        
        # 0.35 * 1.0 + 0.35 * 1.0 + 0.30 * 1.0 = 1.0
        weighted, final_code, profile = compute_risk_score(True, 1.0, 1.0, 1.0)
        assert abs(weighted - 1.0) < 1e-6
        assert final_code == 1.0
        assert profile == "code_present"
        
        # 0.35 * 0.5 + 0.35 * 0.5 + 0.30 * 0.5 = 0.5
        weighted, final_code, profile = compute_risk_score(True, 0.5, 0.5, 0.5)
        assert abs(weighted - 0.5) < 1e-6
        assert final_code == 0.5
    
    def test_compute_risk_score_text_only(self):
        """When code is not present, it should use the 50/50 split and return None for code_sim_max."""
        from app.engine.risk_scorer import compute_risk_score
        
        # 0.50 * 1.0 + 0.50 * 1.0 = 1.0
        weighted, final_code, profile = compute_risk_score(False, 1.0, 1.0, 1.0)
        assert abs(weighted - 1.0) < 1e-6
        assert final_code is None
        assert profile == "theory_only"
        
        # 0.55 * 0.8 (ai) + 0.45 * 0.4 (text) = 0.44 + 0.18 = 0.62
        weighted, final_code, profile = compute_risk_score(False, 0.4, 0.9, 0.8)
        assert abs(weighted - 0.62) < 1e-6
        assert final_code is None
    
    def test_classify_risk(self):
        """Test risk bucketing into low/medium/high."""
        from app.engine.risk_scorer import classify_risk
        
        assert classify_risk(0.1) == "low"
        assert classify_risk(0.39) == "low"
        assert classify_risk(0.40) == "medium"
        assert classify_risk(0.69) == "medium"
        assert classify_risk(0.70) == "high"
        assert classify_risk(0.99) == "high"


class TestESLConfidenceBandingAndMarking:
    """Test whitepaper confidence banding and ESL equity zero-deduction bypass."""

    def test_confidence_banding_thresholds(self):
        from app.engine.marking_calculator import get_confidence_band
        assert get_confidence_band(0.20) == "AUTHENTIC_HUMAN"
        assert get_confidence_band(0.39) == "AUTHENTIC_HUMAN"
        assert get_confidence_band(0.40) == "INCONCLUSIVE_HUMAN_REVIEW_REQUIRED"
        assert get_confidence_band(0.65) == "INCONCLUSIVE_HUMAN_REVIEW_REQUIRED"
        assert get_confidence_band(0.75) == "INCONCLUSIVE_HUMAN_REVIEW_REQUIRED"
        assert get_confidence_band(0.76) == "PROBABLE_SYNTHETIC_GENERATION"
        assert get_confidence_band(0.95) == "PROBABLE_SYNTHETIC_GENERATION"

    def test_esl_equity_zero_deduction(self):
        from app.engine.marking_calculator import calculate_marks
        config = {
            "ai_thresholds": [{"min_value": 0, "max_value": 100, "marks_deduct": 20}],
            "text_copy_thresholds": [],
            "code_ast_thresholds": [],
            "risk_score_thresholds": [],
            "enforce_esl_equity": True,
        }
        # Inconclusive band -> AI deduction must be strictly 0.0
        marks, breakdown = calculate_marks(100.0, config, ai_prob=0.55, text_sim_max=0.1, code_sim_max=None, weighted_score=0.3)
        assert breakdown["confidence_band"] == "INCONCLUSIVE_HUMAN_REVIEW_REQUIRED"
        assert breakdown["ai_deduction"] == 0.0
        assert marks == 100.0

        # Probable AI band (> 0.75) -> deduction applied
        marks, breakdown = calculate_marks(100.0, config, ai_prob=0.85, text_sim_max=0.1, code_sim_max=None, weighted_score=0.8)
        assert breakdown["confidence_band"] == "PROBABLE_SYNTHETIC_GENERATION"
        assert breakdown["ai_deduction"] == 20.0
        assert marks == 80.0


class TestMinHashLSH:
    """Test whitepaper MinHash LSH sub-linear candidate pairing."""

    def test_minhash_signature_and_matching(self):
        from app.engine.text_similarity import compute_minhash_signature, minhash_lsh_filter
        doc1 = "Distributed systems require consensus algorithms such as Paxos and Raft to ensure consistency."
        doc2 = "Distributed systems require consensus algorithms like Paxos and Raft for state consistency."
        doc3 = "Photosynthesis in green plants converts solar radiant energy into chemical glucose bonds."

        sig1 = compute_minhash_signature(doc1)
        sig2 = compute_minhash_signature(doc2)
        sig3 = compute_minhash_signature(doc3)

        assert len(sig1) == 128
        assert len(sig2) == 128

        candidates = minhash_lsh_filter([sig1, sig2, sig3])
        # doc1 and doc2 share high overlap and should be paired
        assert (0, 1) in candidates


class TestAdversarialSanitization:
    """Test Unicode NFKC and zero-width evasion stripping."""

    def test_zero_width_space_stripping(self):
        from app.engine.pdf_processor import _sanitize_adversarial_text
        evasive_text = "H\u200be\u200cl\u200dl\ufeffo W\u00ador\u200eld"
        cleaned = _sanitize_adversarial_text(evasive_text)
        assert cleaned == "Hello World"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

