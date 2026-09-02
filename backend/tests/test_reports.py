"""
test_reports.py — Unit tests for Enterprise PDF, Excel, and JSON report generation.
"""
import uuid
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.reports import pdf_gen, excel_gen, json_export


class MockBatch:
    def __init__(self):
        self.id = uuid.uuid4()
        self.name = "CS101 Final Exam Analysis"
        self.course_code = "CS101"
        self.status = "done"
        self.uploaded_at = datetime.now(timezone.utc)
        self.completed_at = datetime.now(timezone.utc)
        self.total_marks = 100.0
        self.marking_config = {
            "ai_threshold": 0.5,
            "ai_deduction": 15.0,
            "text_sim_threshold": 0.4,
            "text_sim_deduction": 20.0,
            "code_sim_threshold": 0.5,
            "code_sim_deduction": 10.0,
        }
        self.instructor = MagicMock()
        self.instructor.full_name = "Prof. Alan Turing"
        self.submissions = []


class MockSubmission:
    def __init__(self, batch, student_id, name, text, code_blocks=None):
        self.id = uuid.uuid4()
        self.batch_id = batch.id
        self.batch = batch
        self.student_id = student_id
        self.student_name = name
        self.raw_text = text
        self.code_blocks = code_blocks or []
        self.created_at = datetime.now(timezone.utc)
        self.marks_obtained = None
        self.marks_breakdown = None

        self.risk_score = MagicMock()
        self.risk_score.weighted_score = 0.65
        self.risk_score.text_sim_max = 0.55
        self.risk_score.code_sim_max = 0.45 if code_blocks else None
        self.risk_score.ai_prob = 0.85
        self.risk_score.risk_level = "high"
        self.risk_score.weight_profile = "code_present" if code_blocks else "theory_only"

        self.ai_result = MagicMock()
        self.ai_result.perplexity_score = 12.4
        self.ai_result.burstiness_score = 4.2
        self.ai_result.stylometric_score = 0.78
        self.ai_result.final_ai_prob = 0.85
        self.ai_result.source = "local"

    @property
    def has_code(self):
        return bool(self.code_blocks and len(self.code_blocks) > 0)


@pytest.mark.asyncio
async def test_pdf_submission_report_generation(tmp_path):
    """Test generating a Enterprise-style single student originality report."""
    batch = MockBatch()
    sub = MockSubmission(
        batch=batch,
        student_id="STU1001",
        name="Alice Smith",
        text="This is an introductory essay on machine learning architectures. "
             "Neural networks optimize loss functions through backpropagation. "
             "Convolutional networks process spatial tensors efficiently.",
        code_blocks=["def forward(self, x):\n    return self.layer(x)"]
    )
    batch.submissions = [sub]

    mock_db = AsyncMock()
    # Mock submission query
    mock_db_result = MagicMock()
    mock_db_result.scalar_one_or_none.return_value = sub
    # Mock pairs query
    mock_pairs_result = MagicMock()
    mock_pairs_result.scalars().all.return_value = []
    
    mock_db.execute.side_effect = [mock_db_result, mock_pairs_result]

    with patch("app.reports.pdf_gen.settings.EXPORT_DIR", str(tmp_path)):
        output_path = await pdf_gen.generate_submission_report(sub.id, mock_db)

        assert output_path.exists()
        assert output_path.stat().st_size > 0
        
        # Verify valid PDF header
        with open(output_path, "rb") as f:
            header = f.read(5)
            assert header == b"%PDF-"


@pytest.mark.asyncio
async def test_pdf_batch_report_generation(tmp_path):
    """Test generating a classroom batch integrity audit report."""
    batch = MockBatch()
    sub1 = MockSubmission(batch, "STU1001", "Alice Smith", "Text 1")
    sub2 = MockSubmission(batch, "STU1002", "Bob Jones", "Text 2")
    batch.submissions = [sub1, sub2]

    mock_db = AsyncMock()
    mock_db_result = MagicMock()
    mock_db_result.scalar_one_or_none.return_value = batch
    mock_db.execute.return_value = mock_db_result

    with patch("app.reports.pdf_gen.settings.EXPORT_DIR", str(tmp_path)):
        output_path = await pdf_gen.generate_batch_report(batch.id, mock_db)

        assert output_path.exists()
        assert output_path.stat().st_size > 0
        with open(output_path, "rb") as f:
            assert f.read(5) == b"%PDF-"


@pytest.mark.asyncio
async def test_excel_batch_report_generation(tmp_path):
    """Test generating Excel summary and analysis sheets."""
    batch = MockBatch()
    sub = MockSubmission(batch, "STU1001", "Alice Smith", "Sample text")
    batch.submissions = [sub]

    mock_db = AsyncMock()
    mock_db_result = MagicMock()
    mock_db_result.scalar_one_or_none.return_value = batch
    mock_db.execute.return_value = mock_db_result

    with patch("app.reports.excel_gen.settings.EXPORT_DIR", str(tmp_path)):
        output_path = await excel_gen.generate(batch.id, mock_db)

        assert output_path.exists()
        assert output_path.stat().st_size > 0


@pytest.mark.asyncio
async def test_json_and_csv_export():
    """Test JSON and CSV exports."""
    batch = MockBatch()
    sub = MockSubmission(batch, "STU1001", "Alice Smith", "Sample text")
    batch.submissions = [sub]

    mock_db = AsyncMock()
    mock_db_result = MagicMock()
    mock_db_result.scalar_one_or_none.return_value = batch
    mock_pairs_result = MagicMock()
    mock_pairs_result.scalars().all.return_value = []
    mock_db.execute.side_effect = [mock_db_result, mock_pairs_result]

    json_data = await json_export.generate_json(batch.id, mock_db)
    assert json_data["batch"]["course_code"] == "CS101"
    assert len(json_data["submissions"]) == 1
    assert json_data["submissions"][0]["student_id"] == "STU1001"


@pytest.mark.asyncio
async def test_pdf_report_with_special_characters(tmp_path):
    """Test generating a PDF report containing XML-sensitive chars (<, >, &, \", ') and Unicode."""
    batch = MockBatch()
    sub = MockSubmission(
        batch=batch,
        student_id="STU<SPECIAL>&99",
        name="Elena Rostova & Co.",
        text="Algorithm comparison: if (x < 10 && y > 20) { return a & b; } "
             "Mathematical bounds: 0 < f(x) <= 1 & g(x) >= 0. "
             "Greek symbols & accents: α, β, γ, é, ü, ñ, ø.",
        code_blocks=["if (a < b && c > d) {\n    ptr = &var;\n}"]
    )
    batch.submissions = [sub]

    mock_db = AsyncMock()
    mock_db_result = MagicMock()
    mock_db_result.scalar_one_or_none.return_value = sub
    mock_pairs_result = MagicMock()
    mock_pairs_result.scalars().all.return_value = []
    mock_db.execute.side_effect = [mock_db_result, mock_pairs_result]

    with patch("app.reports.pdf_gen.settings.EXPORT_DIR", str(tmp_path)):
        output_path = await pdf_gen.generate_submission_report(sub.id, mock_db)

        assert output_path.exists()
        assert output_path.stat().st_size > 0
        with open(output_path, "rb") as f:
            assert f.read(5) == b"%PDF-"
