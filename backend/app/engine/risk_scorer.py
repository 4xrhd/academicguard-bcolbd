"""
risk_scorer.py — Weighted risk score computation and classification.
FR-RISK-01: Whitepaper §4 Weight Profiles:
  Theory Only:  0.55 × AI prob + 0.45 × text_sim
  Code Present: 0.40 × AI prob + 0.35 × text_sim + 0.25 × code_sim
FR-RISK-02: LOW < 0.40 | MEDIUM 0.40–0.69 | HIGH ≥ 0.70
Thresholds and weights are read from config.py (no code change required to tune them).
"""
import uuid

from app.config import get_settings

settings = get_settings()


async def score_batch(batch_id: str, db) -> None:
    """Compute and persist risk scores for every submission in the batch."""
    from sqlalchemy import select, func
    from app.db.models import AIDetectionResult, RiskScore, SimilarityResult, Submission

    batch_uuid = uuid.UUID(batch_id)

    result = await db.execute(
        select(Submission).where(Submission.batch_id == batch_uuid)
    )
    submissions = result.scalars().all()
    sub_ids = [s.id for s in submissions]

    if not sub_ids:
        return

    # Bulk query: max text similarity per submission
    text_max_a = await db.execute(
        select(SimilarityResult.sub_a_id, func.max(SimilarityResult.text_sim_fused))
        .where(SimilarityResult.sub_a_id.in_(sub_ids))
        .group_by(SimilarityResult.sub_a_id)
    )
    text_max_b = await db.execute(
        select(SimilarityResult.sub_b_id, func.max(SimilarityResult.text_sim_fused))
        .where(SimilarityResult.sub_b_id.in_(sub_ids))
        .group_by(SimilarityResult.sub_b_id)
    )
    text_sim_map: dict[uuid.UUID, float] = {}
    for sid, val in text_max_a.all():
        text_sim_map[sid] = max(text_sim_map.get(sid, 0.0), float(val or 0.0))
    for sid, val in text_max_b.all():
        text_sim_map[sid] = max(text_sim_map.get(sid, 0.0), float(val or 0.0))

    # Bulk query: max code similarity per submission
    code_max_a = await db.execute(
        select(SimilarityResult.sub_a_id, func.max(SimilarityResult.code_ast_score))
        .where(SimilarityResult.sub_a_id.in_(sub_ids))
        .group_by(SimilarityResult.sub_a_id)
    )
    code_max_b = await db.execute(
        select(SimilarityResult.sub_b_id, func.max(SimilarityResult.code_ast_score))
        .where(SimilarityResult.sub_b_id.in_(sub_ids))
        .group_by(SimilarityResult.sub_b_id)
    )
    code_sim_map: dict[uuid.UUID, float] = {}
    for sid, val in code_max_a.all():
        code_sim_map[sid] = max(code_sim_map.get(sid, 0.0), float(val or 0.0))
    for sid, val in code_max_b.all():
        code_sim_map[sid] = max(code_sim_map.get(sid, 0.0), float(val or 0.0))

    # Bulk query: AI detection results
    ai_result = await db.execute(
        select(AIDetectionResult).where(AIDetectionResult.submission_id.in_(sub_ids))
    )
    ai_map = {r.submission_id: r.final_ai_prob for r in ai_result.scalars().all()}

    # Bulk query: existing risk scores for upsert
    existing_result = await db.execute(
        select(RiskScore).where(RiskScore.submission_id.in_(sub_ids))
    )
    existing_map = {r.submission_id: r for r in existing_result.scalars().all()}

    for sub in submissions:
        text_sim_max = text_sim_map.get(sub.id, 0.0)
        ai_prob = ai_map.get(sub.id, 0.0)

        # Determine weight profile and calculate weighted score
        weighted, final_code_sim_max, weight_profile = compute_risk_score(
            has_code=sub.has_code,
            text_sim_max=text_sim_max,
            code_sim_max=code_sim_map.get(sub.id, 0.0),
            ai_prob=ai_prob
        )

        risk_level = classify_risk(weighted)

        risk = existing_map.get(sub.id)
        if risk:
            risk.text_sim_max = text_sim_max
            risk.code_sim_max = final_code_sim_max
            risk.ai_prob = ai_prob
            risk.weighted_score = weighted
            risk.risk_level = risk_level
            risk.weight_profile = weight_profile
        else:
            risk = RiskScore(
                submission_id=sub.id,
                text_sim_max=text_sim_max,
                code_sim_max=final_code_sim_max,
                ai_prob=ai_prob,
                weighted_score=weighted,
                risk_level=risk_level,
                weight_profile=weight_profile,
            )
            db.add(risk)

    await db.flush()

def classify_risk(score: float) -> str:
    """FR-RISK-02 — Classify weighted score into LOW / MEDIUM / HIGH."""
    if score >= settings.RISK_HIGH_THRESHOLD:
        return "high"
    if score >= settings.RISK_MEDIUM_THRESHOLD:
        return "medium"
    return "low"

def compute_risk_score(has_code: bool, text_sim_max: float, code_sim_max: float, ai_prob: float) -> tuple[float, float | None, str]:
    """
    Computes the weighted risk score using the appropriate weight profile.
    
    Whitepaper §4 Weight Profiles:
      - Theory Only:  0.55 × AI Probability + 0.45 × Text Similarity
      - Code Present: 0.40 × AI Probability + 0.35 × Text Similarity + 0.25 × Code Similarity
    
    Returns: (weighted_score, final_code_sim_max, weight_profile)
    """
    if has_code:
        # Whitepaper Code-Present Profile: 0.40 AI + 0.35 Text + 0.25 Code
        weighted = (
            settings.WEIGHT_AI_PROB  * ai_prob +
            settings.WEIGHT_TEXT_SIM * text_sim_max +
            settings.WEIGHT_CODE_SIM * code_sim_max
        )
        return weighted, code_sim_max, "code_present"
    else:
        # Whitepaper Theory-Only Profile: 0.55 AI + 0.45 Text
        weighted = (
            0.55 * ai_prob +
            0.45 * text_sim_max
        )
        return weighted, None, "theory_only"
