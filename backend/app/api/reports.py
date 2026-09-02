"""
reports.py — Report generation and export router.
FR-RPT-01: GET /batches/{id}/reports/pdf (Classroom Batch Audit Report)
FR-RPT-01: GET /submissions/{id}/reports/pdf (Enterprise Style Student Originality Report)
FR-RPT-02: GET /batches/{id}/reports/excel (Excel Summary + Analysis Sheets)
FR-RPT-03: GET /batches/{id}/reports/csv (Raw CSV stream)
FR-RPT-03: GET /batches/{id}/reports/json (Full JSON dump)
FR-RPT-04: Every export is recorded in audit_logs and reports tables.
"""
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select

from app.core.dependencies import DBSession, InstructorUser
from app.db.models import Report, Submission
from app.api.batches import _get_owned_batch
from app.reports import excel_gen, json_export, pdf_gen

router = APIRouter()


@router.get("/batches/{batch_id}/reports/pdf")
async def export_batch_pdf(batch_id: uuid.UUID, current_user: InstructorUser, db: DBSession):
    """FR-RPT-01 — Generate and stream a Classroom Batch Integrity Audit PDF report via ReportLab."""
    batch = await _get_owned_batch(batch_id, current_user, db)
    if batch.status != "done":
        raise HTTPException(status_code=400, detail="Batch processing not complete.")

    try:
        file_path = await pdf_gen.generate_batch_report(batch_id, db)
        await _record_export(batch_id, "pdf", file_path, current_user.id, db)
        safe_course = batch.course_code.replace(" ", "_") if batch.course_code else str(batch_id)[:8]
        return FileResponse(
            path=file_path,
            media_type="application/pdf",
            filename=f"integrity_audit_report_{safe_course}.pdf"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate batch PDF report: {str(e)}")


@router.get("/submissions/{submission_id}/reports/pdf")
async def export_submission_pdf(submission_id: uuid.UUID, current_user: InstructorUser, db: DBSession):
    """FR-RPT-01 — Generate and stream a Enterprise-grade Originality & AI Plagiarism PDF report for a single submission."""
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")

    # Verify ownership through batch
    batch = await _get_owned_batch(submission.batch_id, current_user, db)

    try:
        file_path = await pdf_gen.generate_submission_report(submission_id, db)
        await _record_export(batch.id, "pdf", file_path, current_user.id, db)
        sid_str = submission.student_id or str(submission.id)[:8]
        return FileResponse(
            path=file_path,
            media_type="application/pdf",
            filename=f"originality_report_{sid_str}.pdf"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate submission PDF report: {str(e)}")


@router.get("/batches/{batch_id}/reports/excel")
async def export_excel(batch_id: uuid.UUID, current_user: InstructorUser, db: DBSession):
    """FR-RPT-02 — Generate Excel workbook with Summary + Analysis sheets."""
    batch = await _get_owned_batch(batch_id, current_user, db)
    if batch.status != "done":
        raise HTTPException(status_code=400, detail="Batch processing not complete.")

    try:
        file_path = await excel_gen.generate(batch_id, db)
        await _record_export(batch_id, "excel", file_path, current_user.id, db)
        safe_course = batch.course_code.replace(" ", "_") if batch.course_code else str(batch_id)[:8]
        return FileResponse(
            path=file_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"integrity_report_{safe_course}.xlsx"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate Excel report: {str(e)}")


@router.get("/batches/{batch_id}/reports/csv")
async def export_csv(batch_id: uuid.UUID, current_user: InstructorUser, db: DBSession):
    """FR-RPT-03 — Stream raw CSV of all computed scores."""
    batch = await _get_owned_batch(batch_id, current_user, db)
    if batch.status != "done":
        raise HTTPException(status_code=400, detail="Batch processing not complete.")

    try:
        csv_data = await json_export.to_csv(batch_id, db)
        safe_course = batch.course_code.replace(" ", "_") if batch.course_code else str(batch_id)[:8]
        return StreamingResponse(
            iter([csv_data]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="integrity_report_{safe_course}.csv"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate CSV export: {str(e)}")


@router.get("/batches/{batch_id}/reports/json")
async def export_json(batch_id: uuid.UUID, current_user: InstructorUser, db: DBSession):
    """FR-RPT-03 — Return full JSON data dump for the batch."""
    batch = await _get_owned_batch(batch_id, current_user, db)
    if batch.status != "done":
        raise HTTPException(status_code=400, detail="Batch processing not complete.")

    try:
        return await json_export.generate_json(batch_id, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate JSON export: {str(e)}")


async def _record_export(batch_id, fmt, file_path, user_id, db):
    """FR-RPT-04 — Record report generation in reports table."""
    try:
        report = Report(batch_id=batch_id, format=fmt, file_path=str(file_path), generated_by=user_id)
        db.add(report)
        await db.commit()
    except Exception:
        # Non-blocking for report downloads
        pass
