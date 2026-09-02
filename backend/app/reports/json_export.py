"""
json_export.py — CSV and JSON export generators.
FR-RPT-03: Raw data exports containing all computed scores, metadata, and mark deductions.
"""
import csv
import io
import uuid
from typing import Any

from app.config import get_settings
from app.engine.marking_calculator import calculate_marks

settings = get_settings()


async def generate_json(batch_id: uuid.UUID | str, db) -> dict[str, Any]:
    """
    FR-RPT-03 — Return full JSON data dump for the batch.
    Includes: batch metadata, all submissions with risk scores, AI results, similarity pairs, and marks.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.db.models import Batch, Submission, RiskScore, AIDetectionResult, SimilarityResult

    b_uuid = uuid.UUID(str(batch_id))
    result = await db.execute(
        select(Batch)
        .where(Batch.id == b_uuid)
        .options(
            selectinload(Batch.submissions).selectinload(Submission.risk_score),
            selectinload(Batch.submissions).selectinload(Submission.ai_result),
        )
    )
    batch = result.scalar_one_or_none()
    if not batch:
        raise ValueError(f"Batch {batch_id} not found.")

    pairs_result = await db.execute(
        select(SimilarityResult).where(SimilarityResult.batch_id == b_uuid)
    )
    pairs = pairs_result.scalars().all()

    submissions_data = []
    for sub in batch.submissions:
        rs = sub.risk_score
        ai = sub.ai_result

        marks_obtained = sub.marks_obtained
        marks_breakdown = sub.marks_breakdown
        if (marks_obtained is None or marks_breakdown is None) and batch.total_marks and batch.marking_config and rs:
            marks_obtained, marks_breakdown = calculate_marks(
                total_marks=batch.total_marks,
                marking_config=batch.marking_config,
                ai_prob=rs.ai_prob,
                text_sim_max=rs.text_sim_max,
                code_sim_max=rs.code_sim_max,
                weighted_score=rs.weighted_score,
            )

        submissions_data.append({
            "id": str(sub.id),
            "student_id": sub.student_id,
            "student_name": sub.student_name,
            "has_code": sub.has_code,
            "risk": {
                "level": rs.risk_level if rs else None,
                "weighted_score": rs.weighted_score if rs else None,
                "text_sim_max": rs.text_sim_max if rs else None,
                "code_sim_max": rs.code_sim_max if rs else None,
                "ai_prob": rs.ai_prob if rs else None,
                "weight_profile": rs.weight_profile if rs else None,
            } if rs else None,
            "ai_detection": {
                "perplexity": ai.perplexity_score if ai else None,
                "burstiness": ai.burstiness_score if ai else None,
                "stylometric": ai.stylometric_score if ai else None,
                "final_prob": ai.final_ai_prob if ai else None,
                "source": ai.source if ai else None,
            } if ai else None,
            "marking": {
                "marks_obtained": marks_obtained,
                "total_marks": batch.total_marks,
                "breakdown": marks_breakdown,
            } if batch.total_marks else None,
        })

    similarity_data = [
        {
            "sub_a_id": str(p.sub_a_id),
            "sub_b_id": str(p.sub_b_id),
            "tfidf_score": p.tfidf_score,
            "semantic_score": p.semantic_score,
            "text_sim_fused": p.text_sim_fused,
            "code_ast_score": p.code_ast_score,
            "copy_direction": p.copy_direction,
        }
        for p in pairs
    ]

    return {
        "batch": {
            "id": str(batch.id),
            "name": batch.name,
            "course_code": batch.course_code,
            "status": batch.status,
            "total_marks": batch.total_marks,
            "uploaded_at": batch.uploaded_at.isoformat() if batch.uploaded_at else None,
            "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
        },
        "submissions": submissions_data,
        "similarity_pairs": similarity_data,
    }


async def to_csv(batch_id: uuid.UUID | str, db) -> str:
    """
    FR-RPT-03 — Serialize batch results to CSV string.
    Columns: student_id, student_name, risk_level, weighted_score,
             text_sim_max, code_sim_max, ai_prob, marks_obtained, total_marks
    """
    json_data = await generate_json(batch_id, db)
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Student ID", "Student Name", "Risk Level", "Weighted Score (%)",
        "AI Probability (%)", "Max Text Similarity (%)", "Max Code Similarity (%)",
        "Marks Obtained", "Total Marks"
    ])

    total_marks = json_data.get("batch", {}).get("total_marks")
    for sub in json_data.get("submissions", []):
        risk = sub.get("risk") or {}
        ai = sub.get("ai_detection") or {}
        marking = sub.get("marking") or {}

        w_score = f"{risk.get('weighted_score', 0.0) * 100:.1f}" if risk.get("weighted_score") is not None else "N/A"
        ai_prob = f"{ai.get('final_prob', 0.0) * 100:.1f}" if ai.get("final_prob") is not None else "N/A"
        text_sim = f"{risk.get('text_sim_max', 0.0) * 100:.1f}" if risk.get("text_sim_max") is not None else "N/A"
        code_sim = f"{risk.get('code_sim_max', 0.0) * 100:.1f}" if risk.get("code_sim_max") is not None else "N/A"
        marks_obtained = f"{marking.get('marks_obtained'):.1f}" if marking.get("marks_obtained") is not None else "N/A"

        writer.writerow([
            sub.get("student_id") or "N/A",
            sub.get("student_name") or "Unknown",
            (risk.get("level") or "N/A").upper(),
            w_score,
            ai_prob,
            text_sim,
            code_sim,
            marks_obtained,
            total_marks if total_marks is not None else "N/A"
        ])

    return output.getvalue()
