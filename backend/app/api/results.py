"""
results.py — Results and dashboard data router.
FR-DASH-02: GET /batches/{id}/results  — Full dashboard payload
FR-DASH-02: GET /batches/{id}/heatmap  — N×N similarity matrix
FR-DASH-04: GET /submissions/{id}      — Per-student detail
             GET /submissions/{id}/pairs — Similarity pairs for a student
"""
import uuid
from sqlalchemy import func as sqlfunc

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.core.dependencies import DBSession, InstructorUser
from app.db.models import AIDetectionResult, Batch, RiskScore, SimilarityResult, Submission
from app.db.schemas import (
    BatchResponse, BatchResultsResponse, HeatmapResponse, SimilarityPairResponse,
    StudentRiskRow, SubmissionDetailResponse,
)
from app.engine.marking_calculator import calculate_marks
from app.api.batches import _get_owned_batch

router = APIRouter()


@router.get("/batches/{batch_id}/results", response_model=BatchResultsResponse)
async def get_batch_results(batch_id: uuid.UUID, current_user: InstructorUser, db: DBSession):
    """FR-DASH-02/03 — Return full results: risk ranking + heatmap data."""
    from sqlalchemy.orm import selectinload

    # Single query to get batch + submissions + risk scores
    query = (
        select(Batch)
        .where(Batch.id == batch_id)
        .options(
            selectinload(Batch.submissions).selectinload(Submission.risk_score)
        )
    )
    result = await db.execute(query)
    batch = result.scalar_one_or_none()
    
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")
    if current_user.role != "admin" and batch.instructor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")
    
    if batch.status != "done":
        raise HTTPException(status_code=400, detail=f"Batch is not complete (status: {batch.status}).")

    # Build risk ranking directly from eager-loaded submissions
    ranking = []
    for sub in sorted(batch.submissions, key=lambda x: (x.risk_score.weighted_score if x.risk_score else 0), reverse=True):
        if not sub.risk_score:
            continue
            
        marks_obtained = None
        marks_breakdown = None
        if batch.total_marks and batch.marking_config:
            marks_obtained, marks_breakdown = calculate_marks(
                total_marks=batch.total_marks,
                marking_config=batch.marking_config,
                ai_prob=sub.risk_score.ai_prob,
                text_sim_max=sub.risk_score.text_sim_max,
                code_sim_max=sub.risk_score.code_sim_max,
                weighted_score=sub.risk_score.weighted_score,
            )
            
        ranking.append(StudentRiskRow(
            submission_id=sub.id,
            student_id=sub.student_id,
            student_name=sub.student_name,
            risk_level=sub.risk_score.risk_level,
            weighted_score=sub.risk_score.weighted_score,
            ai_prob=sub.risk_score.ai_prob,
            text_sim_max=sub.risk_score.text_sim_max,
            code_sim_max=sub.risk_score.code_sim_max,
            marks_obtained=marks_obtained,
            marks_breakdown=marks_breakdown,
        ))

    heatmap = await _build_heatmap_from_loaded(batch.submissions, batch_id, db)

    batch_resp = BatchResponse(
        id=batch.id,
        name=batch.name,
        course_code=batch.course_code,
        status=batch.status,
        progress=batch.progress,
        uploaded_at=batch.uploaded_at,
        completed_at=batch.completed_at,
        submission_count=len(batch.submissions),
        total_marks=batch.total_marks,
        marking_config=batch.marking_config,
    )
    return BatchResultsResponse(batch=batch_resp, risk_ranking=ranking, heatmap=heatmap)


@router.get("/batches/{batch_id}/heatmap", response_model=HeatmapResponse)
async def get_heatmap(batch_id: uuid.UUID, current_user: InstructorUser, db: DBSession):
    """FR-DASH-02 — Return N×N text similarity matrix for D3.js rendering."""
    batch = await _get_owned_batch(batch_id, current_user, db)
    if batch.status != "done":
        raise HTTPException(status_code=400, detail="Batch processing not complete.")

    return await _build_heatmap(batch_id, db)


@router.get("/submissions/{submission_id}", response_model=SubmissionDetailResponse)
async def get_submission_detail(submission_id: uuid.UUID, current_user: InstructorUser, db: DBSession):
    """FR-DASH-04 — Per-student detail: risk breakdown, AI scores, similarity pairs."""
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(Submission)
        .where(Submission.id == submission_id)
        .options(
            selectinload(Submission.ai_result),
            selectinload(Submission.risk_score)
        )
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")

    # Verify ownership through batch
    batch = await _get_owned_batch(submission.batch_id, current_user, db)

    # Calculate marks on the fly if config is available
    if batch.total_marks and batch.marking_config and submission.risk_score:
        submission.marks_obtained, submission.marks_breakdown = calculate_marks(
            total_marks=batch.total_marks,
            marking_config=batch.marking_config,
            ai_prob=submission.risk_score.ai_prob,
            text_sim_max=submission.risk_score.text_sim_max,
            code_sim_max=submission.risk_score.code_sim_max,
            weighted_score=submission.risk_score.weighted_score,
        )

    return submission


@router.get("/submissions/{submission_id}/pdf")
async def get_submission_pdf(submission_id: uuid.UUID, current_user: InstructorUser, db: DBSession):
    """Return the original PDF file of the submission."""
    from fastapi.responses import FileResponse
    from pathlib import Path
    
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")

    await _get_owned_batch(submission.batch_id, current_user, db)

    path = Path(submission.file_path)
    if not path.exists():
        backend_dir = Path(__file__).resolve().parent.parent.parent
        alt_path = backend_dir / submission.file_path
        if alt_path.exists():
            path = alt_path
        else:
            root_path = backend_dir.parent / submission.file_path
            if root_path.exists():
                path = root_path
            else:
                raise HTTPException(status_code=404, detail=f"PDF file not found on disk: {submission.file_path}")
        
    filename = path.name if not path.name.endswith(".pdf") else path.name
    if not filename.endswith(".pdf"):
        filename += ".pdf"

    return FileResponse(
        path=path,
        media_type="application/pdf",
        filename=filename,
        content_disposition_type="inline"  # Allows viewing in browser natively
    )


@router.get("/submissions/{submission_id}/report/pdf")
async def get_submission_report_pdf(submission_id: uuid.UUID, current_user: InstructorUser, db: DBSession):
    """Generate and return the Enterprise Style Originality PDF report for this submission."""
    from app.reports import pdf_gen
    from app.db.models import Report

    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")

    batch = await _get_owned_batch(submission.batch_id, current_user, db)

    try:
        file_path = await pdf_gen.generate_submission_report(submission_id, db)
        # Record report
        try:
            report = Report(batch_id=batch.id, format="pdf", file_path=str(file_path), generated_by=current_user.id)
            db.add(report)
            await db.commit()
        except Exception:
            pass

        sid_str = submission.student_id or str(submission.id)[:8]
        return FileResponse(
            path=file_path,
            media_type="application/pdf",
            filename=f"originality_report_{sid_str}.pdf"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate originality report: {str(e)}")


@router.get("/submissions/{submission_id}/pairs", response_model=list[SimilarityPairResponse])
async def get_submission_pairs(submission_id: uuid.UUID, current_user: InstructorUser, db: DBSession):
    """Return all similarity pairs involving the given submission."""
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")

    await _get_owned_batch(submission.batch_id, current_user, db)

    pairs_result = await db.execute(
        select(SimilarityResult).where(
            (SimilarityResult.sub_a_id == submission_id) |
            (SimilarityResult.sub_b_id == submission_id)
        )
    )
    pairs = pairs_result.scalars().all()
    
    other_ids = {p.sub_b_id if p.sub_a_id == submission_id else p.sub_a_id for p in pairs}
    
    subs_map = {}
    if other_ids:
        subs_result = await db.execute(select(Submission).where(Submission.id.in_(other_ids)))
        subs_map = {s.id: s for s in subs_result.scalars().all()}
    
    response_list = []
    for pair in pairs:
        other_id = pair.sub_b_id if pair.sub_a_id == submission_id else pair.sub_a_id
        other_sub = subs_map.get(other_id)
        
        pair_dict = {
            "id": pair.id,
            "sub_a_id": pair.sub_a_id,
            "sub_b_id": pair.sub_b_id,
            "tfidf_score": pair.tfidf_score,
            "semantic_score": pair.semantic_score,
            "text_sim_fused": pair.text_sim_fused,
            "code_ast_score": pair.code_ast_score,
            "copy_direction": pair.copy_direction,
            "other_student_name": other_sub.student_name if other_sub else None,
            "other_student_id": other_sub.student_id if other_sub else None,
        }
        response_list.append(pair_dict)
        
    return response_list


# ── Private helpers ───────────────────────────────────────────────────────────

async def _build_risk_ranking(batch: Batch, db) -> list[StudentRiskRow]:
    """Query risk_scores joined with submissions, sorted descending by weighted_score."""
    rows = await db.execute(
        select(Submission, RiskScore)
        .join(RiskScore, RiskScore.submission_id == Submission.id)
        .where(Submission.batch_id == batch.id)
        .order_by(RiskScore.weighted_score.desc())
    )
    ranking = []
    for sub, rs in rows.all():
        # Calculate marks if config exists
        marks_obtained = None
        marks_breakdown = None
        if batch.total_marks and batch.marking_config:
            marks_obtained, marks_breakdown = calculate_marks(
                total_marks=batch.total_marks,
                marking_config=batch.marking_config,
                ai_prob=rs.ai_prob,
                text_sim_max=rs.text_sim_max,
                code_sim_max=rs.code_sim_max,
                weighted_score=rs.weighted_score,
            )
        
        ranking.append(StudentRiskRow(
            submission_id=sub.id,
            student_id=sub.student_id,
            student_name=sub.student_name,
            risk_level=rs.risk_level,
            weighted_score=rs.weighted_score,
            ai_prob=rs.ai_prob,
            text_sim_max=rs.text_sim_max,
            code_sim_max=rs.code_sim_max,
            marks_obtained=marks_obtained,
            marks_breakdown=marks_breakdown,
        ))
    return ranking


async def _build_heatmap(batch_id: uuid.UUID, db) -> HeatmapResponse:
    """Build N×N text similarity matrix keyed by student_id (or submission index)."""
    subs_result = await db.execute(
        select(Submission).where(Submission.batch_id == batch_id).order_by(Submission.created_at)
    )
    submissions = subs_result.scalars().all()

    # Use student_id if available, else fallback to short submission id
    labels = [
        s.student_id or str(s.id)[:8]
        for s in submissions
    ]
    n = len(labels)
    sub_ids = [s.id for s in submissions]
    id_to_idx = {sid: i for i, sid in enumerate(sub_ids)}

    # Initialize NxN matrix with zeros; diagonal is 1.0
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        matrix[i][i] = 1.0

    pairs_result = await db.execute(
        select(SimilarityResult).where(SimilarityResult.batch_id == batch_id)
    )
    for pair in pairs_result.scalars().all():
        i = id_to_idx.get(pair.sub_a_id)
        j = id_to_idx.get(pair.sub_b_id)
        if i is not None and j is not None:
            matrix[i][j] = pair.text_sim_fused
            matrix[j][i] = pair.text_sim_fused

    return HeatmapResponse(student_ids=labels, matrix=matrix)

async def _build_heatmap_from_loaded(submissions, batch_id: uuid.UUID, db) -> HeatmapResponse:
    """Build N×N text similarity matrix from pre-loaded submissions."""
    # Use student_id if available, else fallback to short submission id
    labels = [
        s.student_id or str(s.id)[:8]
        for s in submissions
    ]
    n = len(labels)
    sub_ids = [s.id for s in submissions]
    id_to_idx = {sid: i for i, sid in enumerate(sub_ids)}

    # Initialize NxN matrix with zeros; diagonal is 1.0
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        matrix[i][i] = 1.0

    pairs_result = await db.execute(
        select(SimilarityResult).where(SimilarityResult.batch_id == batch_id)
    )
    for pair in pairs_result.scalars().all():
        i = id_to_idx.get(pair.sub_a_id)
        j = id_to_idx.get(pair.sub_b_id)
        if i is not None and j is not None:
            matrix[i][j] = pair.text_sim_fused
            matrix[j][i] = pair.text_sim_fused

    return HeatmapResponse(student_ids=labels, matrix=matrix)
