"""
marking_calculator.py — Calculate marks based on detection scores and thresholds.
"""
from typing import Any, Optional


def calculate_marks(
    total_marks: float,
    marking_config: dict,
    ai_prob: Optional[float],
    text_sim_max: Optional[float],
    code_sim_max: Optional[float],
    weighted_score: Optional[float],
) -> tuple[float, dict]:
    """
    Calculate marks obtained and breakdown of deductions.
    
    Args:
        total_marks: Total marks for assignment
        marking_config: Config with thresholds for each feature
        ai_prob: AI detection probability (0-1)
        text_sim_max: Max text similarity (0-1)
        code_sim_max: Max code similarity (0-1)
        weighted_score: Overall risk score (0-1)
    
    Returns:
        (marks_obtained, marks_breakdown)
    """
    if not marking_config:
        return total_marks, {}
    
    marks_breakdown: dict[str, Any] = {
        "ai_deduction": 0.0,
        "text_copy_deduction": 0.0,
        "code_ast_deduction": 0.0,
        "risk_score_deduction": 0.0,
    }
    
    # Convert probabilities to percentages for threshold matching
    ai_percent = (ai_prob or 0.0) * 100
    text_percent = (text_sim_max or 0.0) * 100
    code_percent = (code_sim_max or 0.0) * 100
    risk_percent = (weighted_score or 0.0) * 100
    
    # Algorithmic Confidence Threshold Banding (Whitepaper Section 3 & 4.8)
    confidence_band = get_confidence_band(ai_prob)
    marks_breakdown["confidence_band"] = confidence_band

    # Calculate deductions for each feature
    # ESL Equity Enforcement: Inconclusive band (0.40 <= P_AI <= 0.75) requires human review and has 0.0 automated deduction
    if confidence_band == "INCONCLUSIVE_HUMAN_REVIEW_REQUIRED" and marking_config.get("enforce_esl_equity", True):
        marks_breakdown["ai_deduction"] = 0.0
    else:
        marks_breakdown["ai_deduction"] = _get_deduction(
            ai_percent, marking_config.get("ai_thresholds", [])
        )

    marks_breakdown["text_copy_deduction"] = _get_deduction(
        text_percent, marking_config.get("text_copy_thresholds", [])
    )
    marks_breakdown["code_ast_deduction"] = _get_deduction(
        code_percent, marking_config.get("code_ast_thresholds", [])
    )
    marks_breakdown["risk_score_deduction"] = _get_deduction(
        risk_percent, marking_config.get("risk_score_thresholds", [])
    )
    
    # Calculate total deduction
    total_deduction = (
        marks_breakdown["ai_deduction"]
        + marks_breakdown["text_copy_deduction"]
        + marks_breakdown["code_ast_deduction"]
        + marks_breakdown["risk_score_deduction"]
    )
    marks_breakdown["total_deductions"] = total_deduction
    marks_obtained = max(0.0, total_marks - total_deduction)
    
    return marks_obtained, marks_breakdown


def get_confidence_band(ai_prob: Optional[float]) -> str:
    """
    Algorithmic Confidence Threshold Banding (Whitepaper Section 3 & Section 4.8):
    - P_AI < 0.40: AUTHENTIC_HUMAN
    - 0.40 <= P_AI <= 0.75: INCONCLUSIVE_HUMAN_REVIEW_REQUIRED (Zero automated deduction)
    - P_AI > 0.75: PROBABLE_SYNTHETIC_GENERATION
    """
    if ai_prob is None:
        return "AUTHENTIC_HUMAN"
    if ai_prob < 0.40:
        return "AUTHENTIC_HUMAN"
    elif ai_prob <= 0.75:
        return "INCONCLUSIVE_HUMAN_REVIEW_REQUIRED"
    else:
        return "PROBABLE_SYNTHETIC_GENERATION"


def _get_deduction(value: float, thresholds: list[dict]) -> float:
    """Find matching threshold and return deduction."""
    for threshold in thresholds:
        if threshold["min_value"] <= value <= threshold["max_value"]:
            return threshold["marks_deduct"]
    return 0.0
