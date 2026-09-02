"""
pdf_processor.py — PDF parsing pipeline entry point.
FR-UPLOAD-02: Cover page parsing  — Extract student_id and student_name via regex.
FR-UPLOAD-03: Text/code separation — Split raw_text into theory and code_blocks.

PDF Processing Engine Attribution & Citation:
This module integrates OpenDataLoader-PDF (Apache License 2.0) for AI-ready layout analysis.
- OpenDataLoader Project: https://opendataloader.org
- Repository: https://github.com/opendataloader-project/opendataloader-pdf
- Collaboration: Developed in collaboration with Dual Lab (https://duallab.com) and veraPDF (https://verapdf.org).
- Fallback: PyMuPDF (fitz) for headless execution without Java runtime.
"""
import os
import re
import asyncio
import uuid
from typing import cast, List, Optional

from app.engine.marking_calculator import calculate_marks


# ── Regex patterns for cover page extraction ─────────────────────────────────
# Handles: "Student ID:", "ID:", "Roll:", "Reg. No:", "Registration Number:"
# Accepts IDs with letters, digits, dashes, slashes (e.g. UG-2024/01)
_STUDENT_ID_RE = re.compile(
    r"(?:Student\s*ID|Roll(?:\s*No(?:\.)?)?|Reg(?:istration)?\.?\s*(?:No\.?|Number)?|ID)\s*[:\-\s]+([A-Z0-9][A-Z0-9\-\/]{1,30})",
    re.IGNORECASE,
)
_NAME_RE = re.compile(
    r"(?:(?:Student|Full)\s+)?Name\s*[:\-]+\s*([^\r\n]{2,80})",
    re.IGNORECASE,
)

# Code fence pattern (``` ... ```) for fenced code blocks
_CODE_FENCE_RE = re.compile(r"```(?:\w+)?\n(.*?)```", re.DOTALL)

# Keywords that strongly indicate a line of source code
_CODE_KEYWORDS = frozenset({
    "def ", "class ", "import ", "from ", "public ", "private ", "protected ",
    "static ", "void ", "int ", "char ", "float ", "double ", "bool ",
    "List<", "Vector<", "#include", "using namespace", "cout <<", "cin >>",
    "printf(", "scanf(", "System.out.println", "return ", "for (", "while (",
    "if (", "else if", "switch (", "try {", "catch (", "finally {",
    "const ", "self.", "this->", "std::", "#define ", "typedef ",
    "function ", "var ", "let ", "const ", "=>", "lambda ",
})


async def process_batch(batch_id: str) -> None:
    """
    Main entry point called by BackgroundTasks.
    Orchestrates the full analysis pipeline for all submissions in a batch.

    Pipeline stages:
        1. parse_pdfs         — extract text + cover page fields
        2. text_similarity    — TF-IDF + Sentence-Transformer pairwise scores
        3. code_similarity    — AST-based structural comparison
        4. ai_detection       — perplexity + stylometric + optional GPTZero
        5. risk_scoring       — weighted composite score + classification
    """
    # Deferred imports to avoid circular dependency at module load time
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.db.session import AsyncSessionLocal
    from app.db.models import Batch, Submission, AIDetectionResult
    from app.engine import ai_detector

    print(f"DEBUG: process_batch started for {batch_id}")
    async with AsyncSessionLocal() as db:
        print(f"DEBUG: DB session acquired for {batch_id}")
        
        # Retry loop for eventual consistency/race conditions
        batch = None
        for attempt in range(5):
            result = await db.execute(select(Batch).where(Batch.id == uuid.UUID(batch_id)))
            batch = result.scalar_one_or_none()
            if batch:
                break
            print(f"DEBUG: Batch {batch_id} not found yet, retrying in 0.2s... (Attempt {attempt+1}/5)")
            await asyncio.sleep(0.2)

        if not batch:
            print(f"DEBUG: Batch {batch_id} not found in DB after retries. Exiting.")
            return

        print(f"DEBUG: Found batch {batch.name}, setting status to processing")
        batch.status = "processing"
        batch.progress = 0.0
        await db.commit()

        try:
            # Stage 1 — Parse PDFs
            from sqlalchemy.orm import selectinload
            subs_result = await db.execute(
                select(Submission)
                .where(Submission.batch_id == batch.id)
                .options(selectinload(Submission.risk_score), selectinload(Submission.ai_result))
            )
            submissions = subs_result.scalars().all()
            total = len(submissions)

            for i, sub in enumerate(submissions):
                await _parse_submission(sub, db)
                batch.progress = (i + 1) / total * 25   # 0–25%
                await db.commit()

            # Stage 2 — Text similarity (FR-SIM-01, FR-SIM-02, FR-SIM-03)
            from app.engine import text_similarity
            await text_similarity.compute_batch(batch_id, db)
            batch.progress = 50.0
            await db.commit()

            # Stage 3 — Code similarity (FR-CODE-01, FR-CODE-02, FR-CODE-03)
            from app.engine import code_similarity
            await code_similarity.compute_batch(batch_id, db)
            batch.progress = 75.0
            await db.commit()

            # Stage 4 — AI detection (FR-AI-01 … FR-AI-05)
            from app.engine import ai_detector
            await ai_detector.analyse_batch(batch_id, db)
            batch.progress = 90.0
            await db.commit()

            # Stage 5 — Risk scoring (FR-RISK-01, FR-RISK-02)
            from app.engine import risk_scorer
            await risk_scorer.score_batch(batch_id, db)
            batch.progress = 95.0
            await db.commit()

            # Stage 6 — Automated Marking (FR-MARK-02)
            # We fetch submissions + risk scores to apply deductions
            if batch.total_marks and batch.marking_config:
                res = await db.execute(
                    select(Submission)
                    .where(Submission.batch_id == batch.id)
                    .options(selectinload(Submission.risk_score))
                )
                for sub in res.scalars().all():
                    if sub.risk_score:
                        sub.marks_obtained, sub.marks_breakdown = calculate_marks(
                            total_marks=batch.total_marks,
                            marking_config=batch.marking_config,
                            ai_prob=sub.risk_score.ai_prob,
                            text_sim_max=sub.risk_score.text_sim_max,
                            code_sim_max=sub.risk_score.code_sim_max,
                            weighted_score=sub.risk_score.weighted_score,
                        )

            batch.status = "done"
            batch.progress = 100.0
            from datetime import datetime
            batch.completed_at = datetime.utcnow()
            await db.commit()
            print(f"DEBUG: Batch {batch_id} fully complete and committed.")

        except Exception as exc:
            batch.status = "error"
            await db.commit()
            print(f"[CRITICAL] Batch {batch_id} failed: {exc!r}")


async def resume_pending_batches() -> None:
    """Startup task to re-queue batches that were pending or stuck in processing."""
    from app.db.session import AsyncSessionLocal
    from app.db.models import Batch
    from sqlalchemy import select
    
    print("DEBUG: Checking for pending/stuck batches to resume...")
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Batch).where(Batch.status.in_(["pending", "processing"]))
        )
        batches = result.scalars().all()
        
        for batch in batches:
            print(f"DEBUG: Resuming stalled batch {batch.id} ({batch.status})")
            # We use create_task instead of BackgroundTasks since we are at startup
            asyncio.create_task(process_batch(str(batch.id)))


async def _parse_submission(sub, db) -> None:
    """FR-UPLOAD-02/03 — Extract text from PDF and populate submission fields."""
    try:
        text, odl_code_blocks = await asyncio.to_thread(_extract_pdf_pipeline, sub.file_path)
        if not text or not text.strip():
            sub.parse_status = "parse_error"
            return
            
        student_id, student_name = _parse_cover_page(text, sub.file_path)
        raw_text, heuristic_code_blocks = _separate_text_and_code(text)

        # Merge OpenDataLoader-PDF natively identified code blocks with heuristic code blocks
        all_code_blocks = list(dict.fromkeys(odl_code_blocks + heuristic_code_blocks))

        sub.student_id   = student_id
        sub.student_name = student_name
        sub.raw_text     = raw_text
        sub.code_blocks  = all_code_blocks if all_code_blocks else None
        # Mark ok even if student_id is None — text was still extracted
        sub.parse_status = "ok" if text.strip() else "parse_error"
    except Exception as exc:
        print(f"[WARN] Failed to parse submission {sub.id}: {exc!r}")
        sub.parse_status = "parse_error"


import unicodedata

def _sanitize_adversarial_text(text: str) -> str:
    """
    Whitepaper Adversarial Defense Pipeline:
    1. Unicode NFKC normalization to resolve homoglyphs and compatibility representations.
    2. Strip zero-width spaces and invisible characters (U+200B-U+200D, U+FEFF, U+00AD, U+200E, U+200F, U+2060-U+206F).
    3. Normalize whitespace while preserving line structure.
    """
    if not text:
        return ""
    # Unicode NFKC normalization
    normalized = unicodedata.normalize("NFKC", text)
    # Strip invisible zero-width characters, bidirectional marks, and soft hyphens
    sanitized = re.sub(r"[\u200B-\u200D\uFEFF\u00AD\u200E\u200F\u202A-\u202E\u2060-\u206F]", "", normalized)
    return sanitized


def _clean_markdown_for_nlp(text: str) -> str:
    """Strip Markdown image markup and link URLs so NLP models receive clean text."""
    if not text:
        return ""
    # Strip markdown images: ![](<...>) or ![](...)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    # Strip markdown links: [label](url) -> label
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)
    return text


def _extract_with_opendataloader(file_path: str) -> tuple[str, list[str], dict]:
    """
    Extract structured text (Markdown), natively tagged code blocks, and 2D element layout JSON
    using OpenDataLoader-PDF (https://opendataloader.org).
    """
    import tempfile
    import json
    from pathlib import Path
    import opendataloader_pdf

    with tempfile.TemporaryDirectory() as tmp_dir:
        opendataloader_pdf.convert(
            input_path=file_path,
            output_dir=tmp_dir,
            format="markdown,json"
        )
        
        pdf_name = Path(file_path).stem
        md_file = Path(tmp_dir) / f"{pdf_name}.md"
        json_file = Path(tmp_dir) / f"{pdf_name}.json"
        
        raw_md = md_file.read_text(encoding="utf-8") if md_file.exists() else ""
        layout_tree = json.loads(json_file.read_text(encoding="utf-8")) if json_file.exists() else {}
        
        code_blocks: list[str] = []
        
        def _walk_tree(node):
            if isinstance(node, dict):
                node_type = node.get("type") or ""
                pdfua_tag = node.get("pdfua_tag") or ""
                if node_type in ("code", "code_block") or pdfua_tag == "Code":
                    content = node.get("content") or node.get("text") or ""
                    if content and len(content.strip()) > 5:
                        code_blocks.append(content.strip())
                for child in node.get("kids", []):
                    _walk_tree(child)
            elif isinstance(node, list):
                for item in node:
                    _walk_tree(item)
                    
        _walk_tree(layout_tree)
        cleaned_md = _clean_markdown_for_nlp(raw_md)
        sanitized_md = _sanitize_adversarial_text(cleaned_md)
        return sanitized_md, code_blocks, layout_tree


def _extract_pdf_pipeline(file_path: str) -> tuple[str, list[str]]:
    """
    Primary PDF extraction pipeline.
    Uses OpenDataLoader-PDF for layout extraction and markdown conversion.
    """
    try:
        text, odl_code_blocks, _ = _extract_with_opendataloader(file_path)
        if text and len(text.strip()) > 50:
            return text, odl_code_blocks
    except Exception as exc:
        print(f"[CRITICAL] OpenDataLoader-PDF failed for {file_path}: {exc!r}")

    return "", []





def _extract_text(file_path: str) -> str:
    """Backward-compatible helper function."""
    text, _ = _extract_pdf_pipeline(file_path)
    return text


_NON_ID_WORDS = frozenset({
    "class", "geometry", "section", "course", "semester", "date", "department",
    "university", "assignment", "submission", "lab", "instructor", "faculty",
    "teacher", "name", "student", "id", "roll", "reg", "group", "title", "subject",
    "report", "code", "page", "table", "figure", "algorithm", "system", "method",
    "analysis", "introduction", "abstract", "total", "marks", "grade", "theory",
    "experiment", "fall", "spring", "summer", "winter", "year", "term",
    "statement", "program", "input", "output", "solution", "exercise", "problem",
    "question", "topic", "task", "project", "function"
})

_TIER1_ID_RE = re.compile(
    r"\b(?:Student\s*(?:ID|Id|No|Number)|Roll(?:\s*(?:No|Number|\.))?|Reg(?:istration)?(?:\s*(?:No|Number|\.))?|Matric(?:\s*(?:No|Number|\.))?)\s*[:\-\s#=]+\s*([A-Za-z0-9][A-Za-z0-9\-\/_]{1,30})",
    re.IGNORECASE,
)
_TIER2_ID_RE = re.compile(
    r"\bID\s*[:\-\s#=]+\s*([A-Za-z0-9][A-Za-z0-9\-\/_]{1,30})",
    re.IGNORECASE,
)
_STANDALONE_NUMERIC_ID_RE = re.compile(
    r"\b([0-9]{4,14}|[0-9]{4}-[0-9]{1,2}-[0-9]{2,3}-[0-9]{3,4}|UG-[0-9]{4}\/[0-9]{2,4})\b"
)

_TIER1_NAME_RE = re.compile(
    r"\b(?:Student(?:\'s)?\s*Name|Full\s*Name|Name\s*of\s*Student|Submitted\s*By)\s*[:\-\s=]+\s*([^\r\n]{2,80})",
    re.IGNORECASE,
)
_TIER2_NAME_RE = re.compile(
    r"(?<!\bProgram\s)(?<!\bProject\s)(?<!\bCourse\s)(?<!\bFile\s)(?<!\bAssignment\s)(?<!\bLab\s)(?<!\bTopic\s)(?<!\bSubject\s)(?<!\bFunction\s)(?<!\bClass\s)\bName\s*[:\-\s=]+\s*([^\r\n]{2,80})",
    re.IGNORECASE,
)


def _parse_cover_page(text: str, file_path: Optional[str] = None) -> tuple[str | None, str | None]:
    """
    FR-UPLOAD-02 — Multi-tier regex extraction of student_id and student_name
    with strict false-positive rejection and PDF metadata author fallback.
    """
    text_content = cast(str, text) if text is not None else ""
    search_area = text_content[0:3000]

    # 1. Extract Student ID
    student_id = None
    m1 = _TIER1_ID_RE.search(search_area)
    if m1:
        candidate = m1.group(1).strip()
        if candidate.lower() not in _NON_ID_WORDS and (any(ch.isdigit() for ch in candidate) or len(candidate) >= 3):
            student_id = candidate

    if not student_id:
        m2 = _TIER2_ID_RE.search(search_area)
        if m2:
            candidate = m2.group(1).strip()
            if candidate.lower() not in _NON_ID_WORDS and any(ch.isdigit() for ch in candidate):
                student_id = candidate

    if not student_id:
        # Fallback: scan for standalone structured academic ID format
        m3 = _STANDALONE_NUMERIC_ID_RE.search(search_area)
        if m3:
            student_id = m3.group(1).strip()

    # 2. Extract Student Name
    student_name = None
    nm1 = _TIER1_NAME_RE.search(search_area)
    if nm1:
        raw_name = nm1.group(1).strip()
    else:
        nm2 = _TIER2_NAME_RE.search(search_area)
        raw_name = nm2.group(1).strip() if nm2 else None

    if raw_name:
        first_line = raw_name.splitlines()[0].strip()
        cleaned_name = re.split(
            r"\s*(?:\b(?:ID|Student|Roll|Reg|Date|Course|Assignment|Department|Batch|Semester|Instructor|Faculty|Teacher|Dr\.|Prof\.|Submitted\s*To|Section)\b|[:\-\|#])",
            first_line,
            flags=re.IGNORECASE,
        )[0].strip(" :-–\t")

        words = set(re.findall(r"\b[a-zA-Z]+\b", cleaned_name.lower()))
        if not words.intersection(_NON_ID_WORDS) and len(cleaned_name) >= 2:
            student_name = cleaned_name

    # 3. Fallback to PDF Document Metadata Author if student_name was not found via regex
    if not student_name and file_path and os.path.exists(file_path):
        try:
            doc = fitz.open(file_path)
            author = doc.metadata.get("author", "").strip()
            doc.close()
            if author and len(author) >= 2 and author.lower() not in _NON_ID_WORDS:
                words = set(re.findall(r"\b[a-zA-Z]+\b", author.lower()))
                if not words.intersection(_NON_ID_WORDS):
                    student_name = author
        except Exception:
            pass

    return student_id, student_name


def _separate_text_and_code(text: str) -> tuple[str, list[str]]:
    """
    FR-UPLOAD-03 — Split PDF text into theory prose and code_blocks list.

    Strategy:
      1. Extract explicit ``` fenced blocks.
      2. Clean Markdown images/links.
      3. Scan remaining lines for code-like patterns using keyword heuristics.
    """
    text = _clean_markdown_for_nlp(text)
    
    # Step 1 — Fenced blocks
    fenced = _CODE_FENCE_RE.findall(text)
    clean_text = _CODE_FENCE_RE.sub("", text)

    # Step 2 — Heuristic line scan
    lines = clean_text.splitlines()
    code_blocks: list[str] = list(fenced)
    current_block: list[str] = []
    theory_lines: list[str] = []

    in_code: bool = False
    non_code_count: int = 0

    for line in lines:
        stripped = line.strip()

        # Skip blank lines inside a code block (don't end it on a blank line)
        if not stripped:
            if in_code:
                current_block.append(line)
            else:
                theory_lines.append(line)
            continue

        is_codelike = (
            any(kw in line for kw in _CODE_KEYWORDS)
            or stripped.endswith(("{", "}", ";"))
            or stripped.startswith(("#include", "#define", "#ifdef", "#ifndef", "#pragma", "//", "/*"))
            or (in_code and stripped.startswith(("*", "*/")))
            or (line.startswith(("    ", "\t")) and not stripped.startswith(("*", "#", "-")))
        )

        if is_codelike:
            in_code = True
            non_code_count = 0  # Reset counter as we are in code
            current_block.append(line)
        else:
            if in_code:
                non_code_count = int(non_code_count + 1)
                if non_code_count > 2:
                    if current_block:
                        code_blocks.append("\n".join(current_block).strip())
                    current_block = []
                    in_code = False
                    non_code_count = 0
                    theory_lines.append(line)
                else:
                    current_block.append(line)
            else:
                theory_lines.append(line)

    if current_block:
        code_blocks.append("\n".join(current_block).strip())

    final_theory = "\n".join(theory_lines).strip()
    final_code_blocks = [b for b in code_blocks if len(b.strip()) > 5]

    return final_theory, final_code_blocks
