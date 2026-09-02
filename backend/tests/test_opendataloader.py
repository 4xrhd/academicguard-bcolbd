"""
test_opendataloader.py — Unit tests for OpenDataLoader-PDF parsing engine integration.
Run: pytest tests/test_opendataloader.py -v
"""
import os
import tempfile
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.engine.pdf_processor import (
    _extract_with_opendataloader,
    _extract_pdf_pipeline,
    _extract_text_pymupdf
)

# Search for a sample uploaded PDF for testing
TEST_PDF_PATH = None
uploads_dir = Path(__file__).parent.parent / "uploads"
if uploads_dir.exists():
    pdf_files = list(uploads_dir.rglob("*.pdf"))
    if pdf_files:
        TEST_PDF_PATH = str(pdf_files[0])


class TestOpenDataLoaderPDF:
    """Test suite for OpenDataLoader-PDF layout parsing and fallback mechanisms."""

    def test_extract_with_opendataloader_sample_pdf(self):
        """Verify OpenDataLoader-PDF extracts text and JSON structure from a sample PDF if present."""
        if not TEST_PDF_PATH or not os.path.exists(TEST_PDF_PATH):
            pytest.skip("No sample PDF available for testing")

        text, code_blocks, layout_tree = _extract_with_opendataloader(TEST_PDF_PATH)
        assert isinstance(text, str)
        assert isinstance(code_blocks, list)
        assert isinstance(layout_tree, dict)

    def test_extract_pdf_pipeline_fallback(self):
        """Verify fallback to PyMuPDF when given invalid file path."""
        text, code_blocks = _extract_pdf_pipeline("non_existent_file.pdf")
        assert text == ""
        assert code_blocks == []
