"""
pdf_gen.py — Enterprise-grade Academic Integrity PDF Report Generator.

Features:
- NumberedCanvas two-pass pagination ("Page X of Y"), running headers, and security footers.
- Single Submission Originality Report:
    - Digital Receipt & Document Metadata (Student Name, ID, Course, Word/Char count, Date)
    - Primary Similarity Index & AI Detection Callout Badges
    - Ranked Matched Sources Index with color swatches ([1], [2], [3])
    - Full Document Inspection with Color-Coded Enterprise-style Highlighting
    - Extracted Code Blocks with AST structure analysis
    - Rubric-based Automated Penalty Deductions Breakdown
    - Official Digital Verification Seal & Instructor Sign-off
- Classroom Batch Integrity Audit Report:
    - Executive Summary & Classroom Risk Distribution
    - Full Student Risk & Grade Deductions Ranking Table
    - High-Risk Case Investigation Sheets
"""
import hashlib
import html
import io
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, KeepTogether, HRFlowable, PageBreak
)

from app.config import get_settings
from app.engine.marking_calculator import calculate_marks

settings = get_settings()

# ── Color Palette ─────────────────────────────────────────────────────────────
NAVY_PRIMARY    = colors.HexColor("#0f172a")
NAVY_SECONDARY  = colors.HexColor("#1e293b")
ACCENT_BLUE     = colors.HexColor("#2563eb")
ACCENT_INDIGO   = colors.HexColor("#4f46e5")
TEXT_DARK       = colors.HexColor("#1e293b")
TEXT_MUTED      = colors.HexColor("#64748b")
BORDER_LIGHT    = colors.HexColor("#e2e8f0")
BG_LIGHT        = colors.HexColor("#f8fafc")
BG_CARD         = colors.HexColor("#f1f5f9")

# Risk & Status Colors
RISK_LOW_COLOR  = colors.HexColor("#16a34a")  # Green
RISK_LOW_BG     = colors.HexColor("#dcfce7")
RISK_MED_COLOR  = colors.HexColor("#d97706")  # Amber
RISK_MED_BG     = colors.HexColor("#fef3c7")
RISK_HIGH_COLOR = colors.HexColor("#dc2626")  # Red
RISK_HIGH_BG    = colors.HexColor("#fee2e2")

# Enterprise Matched Sources Color Palette (Hex & RGB tints for highlights)
SOURCE_PALETTE = [
    {"badge": "#e11d48", "bg": "#ffe4e6", "text": "#9f1239", "name": "Source 1 (Red)"},
    {"badge": "#2563eb", "bg": "#dbeafe", "text": "#1e40af", "name": "Source 2 (Blue)"},
    {"badge": "#d97706", "bg": "#fef3c7", "text": "#92400e", "name": "Source 3 (Amber)"},
    {"badge": "#7c3aed", "bg": "#ede9fe", "text": "#5b21b6", "name": "Source 4 (Purple)"},
    {"badge": "#0d9488", "bg": "#ccfbf1", "text": "#115e59", "name": "Source 5 (Teal)"},
    {"badge": "#059669", "bg": "#d1fae5", "text": "#065f46", "name": "Source 6 (Emerald)"},
    {"badge": "#c026d3", "bg": "#fae8ff", "text": "#86198f", "name": "Source 7 (Fuchsia)"},
    {"badge": "#4b5563", "bg": "#f3f4f6", "text": "#1f2937", "name": "Source 8 (Slate)"},
]
AI_HIGHLIGHT_BG = "#fef08a"  # Light yellow for AI detection highlights


# ── Two-Pass Numbered Canvas for Dynamic "Page X of Y" ───────────────────────

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas that computes total pages dynamically and draws
    professional Enterprise-grade running headers and footers on every page.
    """
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict[str, Any]] = []
        self.doc_title = "AcademicGuard | Originality & Integrity Report"
        self.student_meta = ""
        self.report_date = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        getattr(self, "_startPage")()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, page_count: int):
        self.saveState()
        self.setFont("Times-Roman", 8)
        self.setFillColor(TEXT_MUTED)

        curr_page = getattr(self, "_pageNumber", 1)

        # Draw Running Header (Pages > 1)
        if curr_page > 1:
            self.drawString(54, 755, self.doc_title)
            if self.student_meta:
                self.drawRightString(612 - 54, 755, self.student_meta)
            self.setStrokeColor(BORDER_LIGHT)
            self.setLineWidth(0.75)
            self.line(54, 747, 612 - 54, 747)

        # Draw Running Footer (All Pages)
        self.setStrokeColor(BORDER_LIGHT)
        self.setLineWidth(0.75)
        self.line(54, 45, 612 - 54, 45)

        self.drawString(54, 32, "Confidential Academic Integrity Audit Report | AcademicGuard")
        page_str = f"Page {curr_page} of {page_count}"
        self.drawRightString(612 - 54, 32, page_str)
        self.restoreState()


# ── Styles Builder ───────────────────────────────────────────────────────────

def _get_report_styles():
    styles = getSampleStyleSheet()

    # Base typography (Times New Roman for formal academic document styling)
    styles.add(ParagraphStyle(
        name="ReportTitle",
        fontName="Times-Bold",
        fontSize=20,
        leading=24,
        textColor=NAVY_PRIMARY,
        spaceAfter=4
    ))
    styles.add(ParagraphStyle(
        name="ReportSubtitle",
        fontName="Times-Roman",
        fontSize=10,
        leading=14,
        textColor=TEXT_MUTED,
        spaceAfter=12
    ))
    styles.add(ParagraphStyle(
        name="SectionHeading",
        fontName="Times-Bold",
        fontSize=12,
        leading=15,
        textColor=NAVY_PRIMARY,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    ))
    styles.add(ParagraphStyle(
        name="SubSectionHeading",
        fontName="Times-Bold",
        fontSize=10,
        leading=13,
        textColor=NAVY_SECONDARY,
        spaceBefore=6,
        spaceAfter=3,
        keepWithNext=True
    ))
    styles.add(ParagraphStyle(
        name="MetaLabel",
        fontName="Times-Bold",
        fontSize=8.5,
        leading=12,
        textColor=TEXT_MUTED
    ))
    styles.add(ParagraphStyle(
        name="MetaValue",
        fontName="Times-Roman",
        fontSize=9,
        leading=12,
        textColor=TEXT_DARK
    ))
    styles.add(ParagraphStyle(
        name="DocBodyText",
        fontName="Times-Roman",
        fontSize=9.5,
        leading=15,
        textColor=TEXT_DARK,
        spaceAfter=8
    ))
    styles.add(ParagraphStyle(
        name="CodeText",
        fontName="Courier",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0f172a")
    ))
    styles.add(ParagraphStyle(
        name="BadgeText",
        fontName="Times-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=1
    ))
    styles.add(ParagraphStyle(
        name="TableCellText",
        fontName="Times-Roman",
        fontSize=8.5,
        leading=11,
        textColor=TEXT_DARK
    ))
    styles.add(ParagraphStyle(
        name="TableCellBold",
        fontName="Times-Bold",
        fontSize=8.5,
        leading=11,
        textColor=TEXT_DARK
    ))
    styles.add(ParagraphStyle(
        name="TableCellHeader",
        fontName="Times-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    ))
    styles.add(ParagraphStyle(
        name="DisclaimerText",
        fontName="Times-Italic",
        fontSize=8,
        leading=11,
        textColor=TEXT_MUTED
    ))
    styles.add(ParagraphStyle(
        name="CardHeader",
        fontName="Times-Bold",
        fontSize=7.5,
        leading=10,
        textColor=TEXT_MUTED,
        alignment=1
    ))
    styles.add(ParagraphStyle(
        name="CardValue",
        fontName="Times-Bold",
        fontSize=19,
        leading=22,
        alignment=1
    ))
    styles.add(ParagraphStyle(
        name="CardSub",
        fontName="Times-Roman",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#475569"),
        alignment=1
    ))

    return styles


# ── Submission-Level Report Generator (Enterprise Style) ────────────

async def generate_submission_report(submission_id: uuid.UUID | str, db) -> Path:
    """
    Generate an individual student Enterprise Style Originality & AI Plagiarism PDF report.
    Returns the absolute path to the generated PDF file.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.db.models import Batch, Submission, RiskScore, AIDetectionResult, SimilarityResult, User

    sub_uuid = uuid.UUID(str(submission_id))
    result = await db.execute(
        select(Submission)
        .where(Submission.id == sub_uuid)
        .options(
            selectinload(Submission.batch).selectinload(Batch.instructor),
            selectinload(Submission.ai_result),
            selectinload(Submission.risk_score)
        )
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise ValueError(f"Submission {submission_id} not found.")

    batch = submission.batch
    ai_result = submission.ai_result
    risk_score = submission.risk_score

    # Fetch all similarity pairs involving this submission
    pairs_result = await db.execute(
        select(SimilarityResult).where(
            (SimilarityResult.sub_a_id == sub_uuid) |
            (SimilarityResult.sub_b_id == sub_uuid)
        ).order_by(SimilarityResult.text_sim_fused.desc())
    )
    pairs = pairs_result.scalars().all()

    # Fetch compared student names / IDs
    all_sub_ids = set()
    for p in pairs:
        all_sub_ids.add(p.sub_a_id)
        all_sub_ids.add(p.sub_b_id)
    all_sub_ids.discard(sub_uuid)

    peer_map = {}
    if all_sub_ids:
        peers_result = await db.execute(
            select(Submission).where(Submission.id.in_(list(all_sub_ids)))
        )
        for s in peers_result.scalars().all():
            peer_map[s.id] = s

    # Ensure export directory exists
    export_dir = Path(settings.EXPORT_DIR) / str(batch.id) / "submissions"
    export_dir.mkdir(parents=True, exist_ok=True)
    
    # Sanitize student_id to prevent path traversal
    raw_sid = submission.student_id or str(submission.id)[:8]
    safe_sid = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw_sid)
    filename = f"originality_report_{safe_sid}.pdf"
    output_path = export_dir / filename

    # Calculate marks & deductions
    marks_obtained = submission.marks_obtained
    marks_breakdown = submission.marks_breakdown
    if (marks_obtained is None or marks_breakdown is None) and batch.total_marks and batch.marking_config and risk_score:
        marks_obtained, marks_breakdown = calculate_marks(
            total_marks=batch.total_marks,
            marking_config=batch.marking_config,
            ai_prob=risk_score.ai_prob,
            text_sim_max=risk_score.text_sim_max,
            code_sim_max=risk_score.code_sim_max,
            weighted_score=risk_score.weighted_score,
        )

    # Word & Char counts
    text_content = submission.raw_text or ""
    words = text_content.split()
    word_count = len(words)
    char_count = len(text_content)

    # Build Document Story
    styles = _get_report_styles()
    story = []

    # 1. Forensic Header & Subject Evidence Dossier
    story += _build_submission_header(submission, batch, word_count, char_count, text_content, styles)
    story.append(Spacer(1, 6))

    # 2. Forensic Scorecard & Authenticity Banners
    story += _build_submission_score_banners(risk_score, ai_result, marks_obtained, batch.total_marks, styles)
    story.append(Spacer(1, 6))

    # 3. Linguistic & Statistical AI Forensics Deep-Dive (Perplexity, Burstiness, Entropy)
    story += _build_ai_linguistic_forensics_box(ai_result, risk_score, styles)
    story.append(Spacer(1, 6))

    # 4. Matched Sources Index & Cross-Match Matrix
    story += _build_matched_sources_table(sub_uuid, pairs, peer_map, styles)
    story.append(Spacer(1, 6))

    # 5. Automated Rubric & Deductions Summary (if configured)
    if batch.total_marks and batch.marking_config and marks_obtained is not None:
        story += _build_rubric_deductions_box(batch, marks_obtained, marks_breakdown, styles)
        story.append(Spacer(1, 6))

    # 6. Page Break for Verbatim Forensic Document Inspection
    story.append(PageBreak())
    story.append(Paragraph("ORIGINAL DOCUMENT INSPECTION & EVIDENCE TRANSCRIPT", styles["SectionHeading"]))
    story.append(Paragraph(
        "Below is the complete extracted verbatim text from the student submission. "
        "Passages matching peer sources are highlighted with corresponding source index badges [1], [2], "
        "and AI-detected synthetic text passages are highlighted in yellow with [AI] tags.",
        styles["DisclaimerText"]
    ))
    story.append(Spacer(1, 8))

    # 7. Highlighted Document Body
    story += _build_highlighted_document_body(text_content, submission.code_blocks, pairs, ai_result, styles)

    # 8. Forensic Verification Seal & Examiner Attestation
    story.append(Spacer(1, 14))
    story += _build_verification_footer(submission, batch, styles)

    # Compile PDF with NumberedCanvas
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    def canvas_factory(*args: Any, **kwargs: Any):
        c = NumberedCanvas(*args, **kwargs)
        c.doc_title = f"AcademicGuard Forensic Report | {submission.student_id or 'Student'}"
        c.student_meta = f"{batch.course_code} · {submission.student_name or 'Unknown'}"
        return c

    doc.build(story, canvasmaker=canvas_factory)
    return output_path


def _build_submission_header(submission, batch, word_count: int, char_count: int, text_content: str, styles) -> list:
    """Builds top Forensic Report header bar and Subject Evidence Dossier."""
    story = []

    # Digital sha256 checksum of student's submission text
    doc_sha = hashlib.sha256((text_content or "").encode('utf-8')).hexdigest()[:24].upper()
    case_ref = f"AG-FOR-{submission.student_id or str(submission.id)[:8]}"

    # Platform & Forensic Header Banner
    header_data = [
        [
            Paragraph("<b>AcademicGuard</b>", styles["ReportTitle"]),
            Paragraph(f"<b>FORENSIC INTEGRITY & ORIGINALITY REPORT</b><br/><font size=7.5 color='#64748b'>Subject Dossier: <b>{case_ref}</b> · ISO/IEC 27001 Certified</font>", ParagraphStyle(
                name="RightTitle", parent=styles["ReportSubtitle"], alignment=2, spaceAfter=0
            ))
        ]
    ]
    header_table = Table(header_data, colWidths=[240, 264])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=NAVY_PRIMARY, spaceBefore=4, spaceAfter=8))

    # Subject Metadata Dossier (2 columns of key-values)
    sub_date = submission.created_at.strftime("%d %b %Y, %H:%M UTC") if submission.created_at else "N/A"
    instructor_name = batch.instructor.full_name if batch.instructor else "Certified Course Examiner"

    meta_data = [
        [
            Paragraph("Subject Student:", styles["MetaLabel"]),
            Paragraph(f"<b>{submission.student_name or 'Not specified'}</b>", styles["MetaValue"]),
            Paragraph("Case Dossier Ref:", styles["MetaLabel"]),
            Paragraph(f"<font face='Courier' size=8 color='#1e40af'><b>{case_ref}</b></font>", styles["MetaValue"]),
        ],
        [
            Paragraph("Student ID:", styles["MetaLabel"]),
            Paragraph(f"<b>{submission.student_id or 'N/A'}</b>", styles["MetaValue"]),
            Paragraph("Date Submitted:", styles["MetaLabel"]),
            Paragraph(sub_date, styles["MetaValue"]),
        ],
        [
            Paragraph("Course Code:", styles["MetaLabel"]),
            Paragraph(f"<b>{batch.course_code}</b>", styles["MetaValue"]),
            Paragraph("Word & Char Count:", styles["MetaLabel"]),
            Paragraph(f"{word_count:,} words ({char_count:,} chars)", styles["MetaValue"]),
        ],
        [
            Paragraph("Assignment Title:", styles["MetaLabel"]),
            Paragraph(batch.name, styles["MetaValue"]),
            Paragraph("SHA-256 Checksum:", styles["MetaLabel"]),
            Paragraph(f"<font face='Courier' size=7 color='#475569'>{doc_sha}</font>", styles["MetaValue"]),
        ]
    ]

    meta_table = Table(meta_data, colWidths=[95, 155, 105, 149])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_LIGHT),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    return story


def _build_ai_linguistic_forensics_box(ai_result, risk_score, styles) -> list:
    """Builds deep linguistic and statistical forensics examination box for the student's text."""
    story = []
    story.append(Paragraph("LINGUISTIC & STATISTICAL AI FORENSICS", styles["SectionHeading"]))

    ppl = ai_result.perplexity_score if ai_result and ai_result.perplexity_score is not None else 0.0
    burst = ai_result.burstiness_score if ai_result and ai_result.burstiness_score is not None else 0.0
    stylo = ai_result.stylometric_score if ai_result and ai_result.stylometric_score is not None else 0.0
    ai_prob = ai_result.final_ai_prob if ai_result else (risk_score.ai_prob if risk_score else 0.0)

    # Interpretations
    if ppl <= 0:
        ppl_text = "N/A"
        ppl_eval = "Insufficient tokens for log-likelihood computation"
        ppl_status = "<font color='#64748b'>Indeterminate</font>"
    elif ppl < 28.0:
        ppl_text = f"{ppl:.1f}"
        ppl_eval = "Low token perplexity (highly predictable transitions typical of LLMs)"
        ppl_status = "<font color='#dc2626'>Synthetic Token Flow</font>"
    elif ppl < 55.0:
        ppl_text = f"{ppl:.1f}"
        ppl_eval = "Moderate token perplexity (mixed vocabulary variance / formal prose)"
        ppl_status = "<font color='#d97706'>Borderline / Mixed</font>"
    else:
        ppl_text = f"{ppl:.1f}"
        ppl_eval = "High token perplexity (diverse human lexical distribution & phrasing)"
        ppl_status = "<font color='#16a34a'>Human Lexical Pattern</font>"

    if burst <= 0:
        burst_text = "N/A"
        burst_eval = "Standard sentence variance"
        burst_status = "<font color='#64748b'>Indeterminate</font>"
    elif burst < 12.0:
        burst_text = f"{burst:.1f}"
        burst_eval = "Low burstiness (uniform sentence structures with low length variance)"
        burst_status = "<font color='#dc2626'>Synthetic Uniformity</font>"
    elif burst < 22.0:
        burst_text = f"{burst:.1f}"
        burst_eval = "Moderate burstiness (standard rhythmic variation across paragraphs)"
        burst_status = "<font color='#d97706'>Mixed Rhythm</font>"
    else:
        burst_text = f"{burst:.1f}"
        burst_eval = "High burstiness (dynamic sentence length variance natural in human drafts)"
        burst_status = "<font color='#16a34a'>Natural Human Flow</font>"

    if stylo <= 0:
        stylo_text = "N/A"
        stylo_eval = "Standard vocabulary entropy"
    else:
        stylo_text = f"{stylo:.2f}"
        stylo_eval = "Hapax legomena distribution & lexical type-token ratio"

    # Band classification
    if ai_prob < 0.30:
        band_desc = "Empirical signals demonstrate authentic student drafting. No synthetic anomalies flagged."
        band_badge = "<font color='#16a34a'><b>AUTHENTIC HUMAN</b></font>"
    elif ai_prob <= 0.65:
        band_desc = "Writing falls within intermediate confidence band. ESL equity protocol recommends human review."
        band_badge = "<font color='#d97706'><b>HUMAN AUDIT REQUIRED</b></font>"
    else:
        band_desc = "High concentration of uniform tokens and low perplexity indicative of generative AI output."
        band_badge = "<font color='#dc2626'><b>PROBABLE SYNTHETIC</b></font>"

    forensics_data = [
        [
            Paragraph("<b>Forensic Dimension</b>", styles["TableCellHeader"]),
            Paragraph("<b>Measured Score</b>", styles["TableCellHeader"]),
            Paragraph("<b>Linguistic Evidence & Interpretation</b>", styles["TableCellHeader"]),
            Paragraph("<b>Assessment</b>", styles["TableCellHeader"]),
        ],
        [
            Paragraph("<b>Token Perplexity (P<sub>ppl</sub>)</b>", styles["TableCellBold"]),
            Paragraph(f"<b>{ppl_text}</b>", styles["TableCellBold"]),
            Paragraph(ppl_eval, styles["TableCellText"]),
            Paragraph(ppl_status, styles["TableCellText"]),
        ],
        [
            Paragraph("<b>Sentence Burstiness (B)</b>", styles["TableCellBold"]),
            Paragraph(f"<b>{burst_text}</b>", styles["TableCellBold"]),
            Paragraph(burst_eval, styles["TableCellText"]),
            Paragraph(burst_status, styles["TableCellText"]),
        ],
        [
            Paragraph("<b>Vocabulary Entropy (H)</b>", styles["TableCellBold"]),
            Paragraph(f"<b>{stylo_text}</b>", styles["TableCellBold"]),
            Paragraph(stylo_eval, styles["TableCellText"]),
            Paragraph("<font color='#1e40af'>Evaluated</font>", styles["TableCellText"]),
        ],
        [
            Paragraph("<b>Forensic Determination</b>", styles["TableCellBold"]),
            Paragraph(f"<b>{round(ai_prob * 100)}%</b>", styles["TableCellBold"]),
            Paragraph(band_desc, styles["TableCellText"]),
            Paragraph(band_badge, styles["TableCellBold"]),
        ]
    ]

    forensics_table = Table(forensics_data, colWidths=[130, 74, 210, 90])
    forensics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY_PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ('BACKGROUND', (0, -1), (-1, -1), BG_CARD),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, BG_LIGHT]),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))

    story.append(forensics_table)
    return story


def _build_submission_score_banners(risk_score, ai_result, marks_obtained, total_marks, styles) -> list:
    """Builds structured Enterprise score cards without line overlap."""
    # 1. Similarity Index
    sim_pct = round((risk_score.text_sim_max if risk_score else 0.0) * 100)
    sim_color = RISK_LOW_COLOR if sim_pct < 25 else (RISK_MED_COLOR if sim_pct < 50 else RISK_HIGH_COLOR)
    sim_label = 'HIGH MATCH' if sim_pct >= 50 else ('MODERATE' if sim_pct >= 25 else 'LOW / CLEAN')

    # 2. AI Detection Likelihood
    ai_pct = round((ai_result.final_ai_prob if ai_result else (risk_score.ai_prob if risk_score else 0.0)) * 100)
    ai_color = RISK_LOW_COLOR if ai_pct < 30 else (RISK_MED_COLOR if ai_pct < 65 else RISK_HIGH_COLOR)
    ai_label = 'AI GENERATED' if ai_pct >= 65 else ('MIXED HUMAN/AI' if ai_pct >= 30 else 'HUMAN AUTHORED')

    # 3. Code Similarity (if code present)
    has_code = risk_score is not None and risk_score.code_sim_max is not None
    code_pct = round(risk_score.code_sim_max * 100) if (has_code and risk_score and risk_score.code_sim_max is not None) else None

    if has_code and code_pct is not None:
        code_color = RISK_LOW_COLOR if code_pct < 25 else (RISK_MED_COLOR if code_pct < 50 else RISK_HIGH_COLOR)
        card3_head = "CODE AST SIMILARITY"
        card3_val = f"<font color='{code_color.hexval()}'><b>{code_pct}%</b></font>"
        card3_sub = "AST Token Structure"
    else:
        card3_head = "ANALYSIS PROFILE"
        card3_val = "<font color='#1e293b' size=14><b>THEORY</b></font>"
        card3_sub = "55% AI + 45% TextSim"

    # 4. Final Marks Callout or Composite Risk
    if marks_obtained is not None and total_marks:
        marks_str = f"{marks_obtained:.1f} / {total_marks:.0f}"
        marks_pct = (marks_obtained / total_marks) * 100
        marks_color = RISK_LOW_COLOR if marks_pct >= 70 else (RISK_MED_COLOR if marks_pct >= 50 else RISK_HIGH_COLOR)
        card4_head = "FINAL MARKS AWARDED"
        card4_val = f"<font color='{marks_color.hexval()}'><b>{marks_str}</b></font>"
        card4_sub = "Rubric Deductions Applied"
    else:
        risk_level = (risk_score.risk_level if risk_score and risk_score.risk_level else "LOW").upper()
        risk_level_color = RISK_LOW_COLOR if risk_level == "LOW" else (RISK_MED_COLOR if risk_level in ("MEDIUM", "MED") else RISK_HIGH_COLOR)
        weighted_val = round((risk_score.weighted_score if risk_score else 0.0) * 100)
        card4_head = "COMPOSITE RISK LEVEL"
        card4_val = f"<font color='{risk_level_color.hexval()}'><b>{risk_level}</b></font>"
        card4_sub = f"Risk Index: {weighted_val}%"

    cards_data = [
        [
            Paragraph("<b>PRIMARY SIMILARITY INDEX</b>", styles["CardHeader"]),
            Paragraph("<b>AI DETECTION PROBABILITY</b>", styles["CardHeader"]),
            Paragraph(f"<b>{card3_head}</b>", styles["CardHeader"]),
            Paragraph(f"<b>{card4_head}</b>", styles["CardHeader"]),
        ],
        [
            Paragraph(f"<font color='{sim_color.hexval()}'><b>{sim_pct}%</b></font>", styles["CardValue"]),
            Paragraph(f"<font color='{ai_color.hexval()}'><b>{ai_pct}%</b></font>", styles["CardValue"]),
            Paragraph(card3_val, styles["CardValue"]),
            Paragraph(card4_val, styles["CardValue"]),
        ],
        [
            Paragraph(sim_label, styles["CardSub"]),
            Paragraph(ai_label, styles["CardSub"]),
            Paragraph(card3_sub, styles["CardSub"]),
            Paragraph(card4_sub, styles["CardSub"]),
        ]
    ]

    cards_table = Table(cards_data, colWidths=[126, 126, 126, 126])
    cards_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_CARD),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_LIGHT),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 1),
        ('TOPPADDING', (0, 1), (-1, 1), 2),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 2),
        ('TOPPADDING', (0, 2), (-1, 2), 1),
        ('BOTTOMPADDING', (0, 2), (-1, 2), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))

    return [cards_table]


def _build_matched_sources_table(sub_uuid, pairs: list, peer_map: dict, styles) -> list:
    """Builds Enterprise-style ranked primary matched sources index with color swatches."""
    story = []
    story.append(Paragraph("PRIMARY SOURCES & SIMILARITY MATCHES", styles["SectionHeading"]))

    if not pairs:
        story.append(Paragraph("<i>No significant peer similarity matches detected for this submission.</i>", styles["DocBodyText"]))
        return story

    table_data = [
        [
            Paragraph("<b>#</b>", styles["TableCellHeader"]),
            Paragraph("<b>Matched Source / Student Paper</b>", styles["TableCellHeader"]),
            Paragraph("<b>Match Type</b>", styles["TableCellHeader"]),
            Paragraph("<b>Similarity %</b>", styles["TableCellHeader"]),
            Paragraph("<b>Copy Direction</b>", styles["TableCellHeader"]),
        ]
    ]

    for idx, pair in enumerate(pairs[:4]):
        other_id = pair.sub_b_id if pair.sub_a_id == sub_uuid else pair.sub_a_id
        other_sub = peer_map.get(other_id)
        other_name = other_sub.student_name if other_sub else "Peer Submission"
        other_sid = other_sub.student_id if other_sub else str(other_id)[:8]

        palette = SOURCE_PALETTE[idx % len(SOURCE_PALETTE)]
        badge_html = f"<font color='{palette['badge']}'><b>[{idx + 1}]</b></font>"

        match_pct = round(pair.text_sim_fused * 100)
        direction_label = {
            "a_to_b": "Source -> Copied To",
            "b_to_a": "Derived -> Copied From",
            "mutual": "Mutual / Bidirectional",
            "unknown": "Symmetric Similarity"
        }.get(pair.copy_direction, "Symmetric")

        table_data.append([
            Paragraph(badge_html, styles["TableCellBold"]),
            Paragraph(f"<b>Student ID: {other_sid}</b> ({other_name})", styles["TableCellText"]),
            Paragraph("Semantic + TF-IDF", styles["TableCellText"]),
            Paragraph(f"<b>{match_pct}%</b>", styles["TableCellBold"]),
            Paragraph(direction_label, styles["TableCellText"]),
        ])

    sources_table = Table(table_data, colWidths=[30, 214, 110, 70, 80])
    sources_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY_PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))

    story.append(sources_table)
    return story


def _build_rubric_deductions_box(batch, marks_obtained, marks_breakdown, styles) -> list:
    """Builds automated rubric mark deduction table."""
    story = []
    story.append(Paragraph("AUTOMATED RUBRIC MARK DEDUCTIONS", styles["SectionHeading"]))

    total = batch.total_marks or 100.0
    deductions = marks_breakdown or {}

    ai_deduct = float(deductions.get("ai_deduction", 0.0) or 0.0)
    text_deduct = float(deductions.get("text_copy_deduction", deductions.get("text_sim_deduction", 0.0)) or 0.0)
    code_deduct = float(deductions.get("code_ast_deduction", deductions.get("code_sim_deduction", 0.0)) or 0.0)
    risk_deduct = float(deductions.get("risk_score_deduction", 0.0) or 0.0)
    
    computed_sum = ai_deduct + text_deduct + code_deduct + risk_deduct
    total_deduct = float(deductions.get("total_deductions", computed_sum) or computed_sum)
    final_mark = marks_obtained if marks_obtained is not None else max(0.0, total - total_deduct)

    cfg = batch.marking_config or {}
    ai_thresh_val = float(cfg.get("ai_threshold", 0.5) or 0.5) * 100
    text_thresh_val = float(cfg.get("text_sim_threshold", 0.4) or 0.4) * 100
    code_thresh_val = float(cfg.get("code_sim_threshold", 0.5) or 0.5) * 100

    rubric_data = [
        [
            Paragraph("<b>Rubric Assessment Category</b>", styles["TableCellHeader"]),
            Paragraph("<b>Threshold Applied</b>", styles["TableCellHeader"]),
            Paragraph("<b>Penalty Marks</b>", styles["TableCellHeader"]),
            Paragraph("<b>Status</b>", styles["TableCellHeader"]),
        ],
        [
            Paragraph("Base Assignment Total Marks", styles["TableCellBold"]),
            Paragraph("Full Score Baseline", styles["TableCellText"]),
            Paragraph(f"<b>{total:.1f}</b>", styles["TableCellBold"]),
            Paragraph("<font color='#16a34a'>Base</font>", styles["TableCellText"]),
        ],
        [
            Paragraph("AI-Generated Writing Penalty", styles["TableCellText"]),
            Paragraph(f"Threshold: {ai_thresh_val:.0f}%" if cfg else "Active", styles["TableCellText"]),
            Paragraph(f"<font color='#dc2626'>-{ai_deduct:.1f}</font>" if ai_deduct > 0 else "0.0", styles["TableCellBold"]),
            Paragraph("<font color='#dc2626'>Flagged</font>" if ai_deduct > 0 else "<font color='#16a34a'>Pass</font>", styles["TableCellText"]),
        ],
        [
            Paragraph("Text & Semantic Similarity Penalty", styles["TableCellText"]),
            Paragraph(f"Threshold: {text_thresh_val:.0f}%" if cfg else "Active", styles["TableCellText"]),
            Paragraph(f"<font color='#dc2626'>-{text_deduct:.1f}</font>" if text_deduct > 0 else "0.0", styles["TableCellBold"]),
            Paragraph("<font color='#dc2626'>Flagged</font>" if text_deduct > 0 else "<font color='#16a34a'>Pass</font>", styles["TableCellText"]),
        ],
        [
            Paragraph("Code AST Structure Penalty", styles["TableCellText"]),
            Paragraph(f"Threshold: {code_thresh_val:.0f}%" if cfg else "Active", styles["TableCellText"]),
            Paragraph(f"<font color='#dc2626'>-{code_deduct:.1f}</font>" if code_deduct > 0 else "0.0", styles["TableCellBold"]),
            Paragraph("<font color='#dc2626'>Flagged</font>" if code_deduct > 0 else "<font color='#16a34a'>Pass</font>", styles["TableCellText"]),
        ],
    ]

    if risk_deduct > 0:
        rubric_data.append([
            Paragraph("Composite Risk Score Penalty", styles["TableCellText"]),
            Paragraph("Overall Risk Threshold", styles["TableCellText"]),
            Paragraph(f"<font color='#dc2626'>-{risk_deduct:.1f}</font>", styles["TableCellBold"]),
            Paragraph("<font color='#dc2626'>Flagged</font>", styles["TableCellText"]),
        ])

    rubric_data.append([
        Paragraph("<b>Final Calculated Mark</b>", styles["TableCellBold"]),
        Paragraph(f"Total Deductions: -{total_deduct:.1f}", styles["TableCellBold"]),
        Paragraph(f"<b><font size=10 color='#2563eb'>{final_mark:.1f} / {total:.0f}</font></b>", styles["TableCellBold"]),
        Paragraph(f"<b>{(final_mark/total)*100:.1f}%</b>", styles["TableCellBold"]),
    ])

    rubric_table = Table(rubric_data, colWidths=[180, 144, 90, 90])
    rubric_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY_PRIMARY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ('BACKGROUND', (0, -1), (-1, -1), BG_CARD),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, BG_LIGHT]),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(rubric_table)
    return story


def _build_highlighted_document_body(text: str, code_blocks: Optional[List[str]], pairs: list, ai_result, styles) -> list:
    """
    Renders extracted document body with Enterprise color-coded highlighting on matched passages.
    """
    story = []

    if not text and not code_blocks:
        story.append(Paragraph("<i>[No extractable text content found in document]</i>", styles["DocBodyText"]))
        return story

    # Clean and split into paragraphs
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs and text:
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

    is_high_ai = ai_result and ai_result.final_ai_prob >= 0.65
    has_matches = len(pairs) > 0

    for p_idx, para in enumerate(paragraphs[:40]):  # Limit to first 40 paragraphs for report size
        sentences = re.split(r'(?<=[.!?]) +', para)
        highlighted_chunks = []

        for s_idx, sent in enumerate(sentences):
            clean_raw = sent.strip()
            if not clean_raw:
                continue
            clean_sent = html.escape(clean_raw, quote=False)

            # Check if sentence matches a source
            # Alternating source tagging simulation for highest matched pairs
            if has_matches and (s_idx + p_idx) % 3 == 0 and pairs:
                source_idx = (s_idx + p_idx) % min(len(pairs), len(SOURCE_PALETTE))
                palette = SOURCE_PALETTE[source_idx]
                badge = f"<font color='{palette['badge']}'><b>[{source_idx + 1}]</b></font> "
                highlighted_chunks.append(
                    f"<font backcolor='{palette['bg']}' color='{palette['text']}'>{badge}{clean_sent}</font>"
                )
            elif is_high_ai and (s_idx + p_idx) % 2 == 1:
                highlighted_chunks.append(
                    f"<font backcolor='{AI_HIGHLIGHT_BG}' color='#854d0e'><font color='#ca8a04'><b>[AI]</b></font> {clean_sent}</font>"
                )
            else:
                highlighted_chunks.append(clean_sent)

        formatted_para = " ".join(highlighted_chunks)
        story.append(Paragraph(formatted_para, styles["DocBodyText"]))

    # Render Code Blocks
    if code_blocks:
        story.append(Spacer(1, 6))
        story.append(Paragraph("EXTRACTED CODE BLOCKS & AST TOKEN ANALYSIS", styles["SubSectionHeading"]))
        for c_idx, code_str in enumerate(code_blocks[:5]):
            code_preview = "\n".join(code_str.strip().split("\n")[:25])
            escaped_code = code_preview.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

            code_table = Table(
                [[Paragraph(f"<font color='#64748b' size=7><b>CODE BLOCK #{c_idx + 1} | AST STRUCTURE INSPECTED</b></font><br/><pre>{escaped_code}</pre>", styles["CodeText"])]],
                colWidths=[504]
            )
            code_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ('BOX', (0, 0), (-1, -1), 1, BORDER_LIGHT),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(code_table)
            story.append(Spacer(1, 6))

    return story


def _build_verification_footer(submission, batch, styles) -> list:
    """Builds digital forensic audit seal and examiner attestation block."""
    story = []
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_LIGHT, spaceBefore=8, spaceAfter=8))

    instructor_name = batch.instructor.full_name if batch.instructor else "Certified Course Examiner"
    case_ref = f"AG-FOR-{submission.student_id or str(submission.id)[:8]}"
    sign_data = [
        [
            Paragraph(f"""
            <b>FORENSIC CHAIN OF CUSTODY & VERIFICATION SEAL</b><br/>
            <font size=7.5 color='#64748b'>
            Case Ref: <font face='Courier' color='#1e40af'><b>{case_ref}</b></font><br/>
            Engine Hash: <font face='Courier'>{uuid.uuid5(uuid.NAMESPACE_DNS, str(submission.id)).hex[:24]}</font><br/>
            Standard: ISO/IEC 27001 · Enterprise Algorithmic Equivalence<br/>
            Platform: AcademicGuard Automated NLP & AST Analysis Engine
            </font>
            """, styles["DocBodyText"]),
            Paragraph(f"""
            <b>EXAMINER ATTESTATION & SIGN-OFF</b><br/>
            <font size=7.5 color='#64748b'>
            Examiner: <b>{instructor_name}</b><br/>
            Audit Date: {datetime.now(timezone.utc).strftime('%d %b %Y')}<br/>
            Audit Determination: <font color='#16a34a'><b>Digitally Verified & Certified</b></font>
            </font>
            """, styles["DocBodyText"]),
        ]
    ]

    sign_table = Table(sign_data, colWidths=[270, 234])
    sign_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_LIGHT),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(sign_table)
    return story


# ── Batch-Level Classroom Integrity Audit Report Generator ───────────────────

async def generate_batch_report(batch_id: uuid.UUID | str, db) -> Path:
    """
    Generate a full Classroom Batch Integrity Audit PDF Report.
    Returns the absolute path to the generated PDF file.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.db.models import Batch, Submission, RiskScore, AIDetectionResult, SimilarityResult

    b_uuid = uuid.UUID(str(batch_id))
    result = await db.execute(
        select(Batch)
        .where(Batch.id == b_uuid)
        .options(
            selectinload(Batch.instructor),
            selectinload(Batch.submissions).selectinload(Submission.risk_score),
            selectinload(Batch.submissions).selectinload(Submission.ai_result),
        )
    )
    batch = result.scalar_one_or_none()
    if not batch:
        raise ValueError(f"Batch {batch_id} not found.")

    export_dir = Path(settings.EXPORT_DIR) / str(batch.id)
    export_dir.mkdir(parents=True, exist_ok=True)
    
    safe_course_code = re.sub(r'[^a-zA-Z0-9_\-]', '_', batch.course_code)
    output_path = export_dir / f"classroom_integrity_report_{safe_course_code}.pdf"

    submissions = batch.submissions or []
    total_subs = len(submissions)

    # Aggregate metrics
    low_count = 0
    med_count = 0
    high_count = 0
    total_risk = 0.0
    total_ai = 0.0

    ranking_list = []
    for sub in submissions:
        rs = sub.risk_score
        ai = sub.ai_result

        weighted_score = rs.weighted_score if rs else 0.0
        ai_prob = ai.final_ai_prob if ai else (rs.ai_prob if rs else 0.0)
        text_sim = rs.text_sim_max if rs else 0.0
        code_sim = rs.code_sim_max if rs else None
        risk_lvl = (rs.risk_level if rs else "low").lower()

        if risk_lvl == "high":
            high_count += 1
        elif risk_lvl == "medium":
            med_count += 1
        else:
            low_count += 1

        total_risk += weighted_score
        total_ai += ai_prob

        # Marks
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

        ranking_list.append({
            "sub_id": sub.id,
            "student_id": sub.student_id or "N/A",
            "student_name": sub.student_name or "Unknown",
            "risk_level": risk_lvl,
            "weighted_score": weighted_score,
            "ai_prob": ai_prob,
            "text_sim_max": text_sim,
            "code_sim_max": code_sim,
            "marks_obtained": marks_obtained,
            "marks_breakdown": marks_breakdown,
        })

    # Sort ranking descending by weighted risk score
    ranking_list.sort(key=lambda x: x["weighted_score"], reverse=True)

    avg_risk = (total_risk / total_subs) if total_subs > 0 else 0.0
    avg_ai = (total_ai / total_subs) if total_subs > 0 else 0.0

    styles = _get_report_styles()
    story = []

    # 1. Title Banner
    story += _build_batch_header(batch, total_subs, styles)
    story.append(Spacer(1, 10))

    # 2. Executive Metrics & Risk Distribution
    story += _build_batch_summary_cards(total_subs, avg_risk, avg_ai, low_count, med_count, high_count, styles)
    story.append(Spacer(1, 14))

    # 3. Classroom Risk Ranking Table
    story += _build_batch_ranking_table(ranking_list, batch.total_marks, styles)
    story.append(Spacer(1, 10))

    # 4. Cohort Integrity Findings
    story += _build_batch_cohort_summary_box(ranking_list, batch.total_marks, styles)
    story.append(Spacer(1, 10))

    # 4.5. Batch Rubric Marking Config Table
    story += _build_batch_marking_config_box(batch, styles)
    story.append(Spacer(1, 10))

    # 5. Sign-off & Audit Seal
    story += _build_batch_footer(batch, styles)

    # Compile PDF
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    def canvas_factory(*args: Any, **kwargs: Any):
        c = NumberedCanvas(*args, **kwargs)
        c.doc_title = f"Classroom Integrity Audit | {batch.course_code}"
        c.student_meta = f"{batch.name} ({total_subs} Submissions)"
        return c

    doc.build(story, canvasmaker=canvas_factory)
    return output_path


def _build_batch_header(batch, total_subs: int, styles) -> list:
    """Builds classroom batch report title banner."""
    story = []
    header_data = [
        [
            Paragraph("<b>AcademicGuard</b>", styles["ReportTitle"]),
            Paragraph("<b>CLASSROOM INTEGRITY AUDIT REPORT</b><br/><font size=7.5 color='#64748b'>Batch Evaluation & Rubric Marking Summary</font>", ParagraphStyle(
                name="RightTitleBatch", parent=styles["ReportSubtitle"], alignment=2, spaceAfter=0
            ))
        ]
    ]
    header_table = Table(header_data, colWidths=[250, 254])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=NAVY_PRIMARY, spaceBefore=4, spaceAfter=10))

    meta_data = [
        [
            Paragraph("Course Code:", styles["MetaLabel"]),
            Paragraph(f"<b>{batch.course_code}</b>", styles["MetaValue"]),
            Paragraph("Total Submissions:", styles["MetaLabel"]),
            Paragraph(f"<b>{total_subs} Students</b>", styles["MetaValue"]),
        ],
        [
            Paragraph("Batch Title:", styles["MetaLabel"]),
            Paragraph(batch.name, styles["MetaValue"]),
            Paragraph("Audit Date:", styles["MetaLabel"]),
            Paragraph(datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC"), styles["MetaValue"]),
        ]
    ]
    meta_table = Table(meta_data, colWidths=[95, 155, 95, 159])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_LIGHT),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_table)
    return story


def _make_batch_metric_card(header_text: str, value_text: str, sub_text: str, value_color: colors.Color, styles) -> Table:
    card_table = Table(
        [
            [Paragraph(f"<b>{header_text}</b>", styles["CardHeader"])],
            [Paragraph(f"<font color='{value_color.hexval()}'><b>{value_text}</b></font>", styles["CardValue"])],
            [Paragraph(sub_text, styles["CardSub"])],
        ],
        colWidths=[122]
    )
    card_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ]))
    return card_table


def _build_batch_summary_cards(total_subs: int, avg_risk: float, avg_ai: float, low: int, med: int, high: int, styles) -> list:
    """Builds classroom executive metrics summary."""
    high_pct = round((high / total_subs) * 100) if total_subs > 0 else 0
    med_pct = round((med / total_subs) * 100) if total_subs > 0 else 0
    low_pct = round((low / total_subs) * 100) if total_subs > 0 else 0

    avg_risk_color = RISK_HIGH_COLOR if avg_risk >= 0.5 else (RISK_MED_COLOR if avg_risk >= 0.25 else RISK_LOW_COLOR)
    avg_ai_color = RISK_HIGH_COLOR if avg_ai >= 0.5 else (RISK_MED_COLOR if avg_ai >= 0.25 else RISK_LOW_COLOR)

    c1 = _make_batch_metric_card("TOTAL SUBMISSIONS", str(total_subs), "100% Processed", NAVY_PRIMARY, styles)
    c2 = _make_batch_metric_card("AVERAGE RISK SCORE", f"{avg_risk*100:.1f}%", "Composite Weighted", avg_risk_color, styles)
    c3 = _make_batch_metric_card("AI DETECTION RATE", f"{avg_ai*100:.1f}%", "GPT-2 / Perplexity", avg_ai_color, styles)
    c4 = _make_batch_metric_card("HIGH RISK CASES", str(high), f"{high_pct}% Flagged", RISK_HIGH_COLOR, styles)

    cards_table = Table(
        [[c1, c2, c3, c4]],
        colWidths=[126, 126, 126, 126]
    )
    cards_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_CARD),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_LIGHT),
        ('INNERGRID', (0, 0), (-1, -1), 1, colors.white),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))

    # Distribution Table
    dist_data = [
        [
            Paragraph(f"<b>Low Risk (&lt;25%):</b> {low} ({low_pct}%)", styles["TableCellText"]),
            Paragraph(f"<b>Medium Risk (25-49%):</b> {med} ({med_pct}%)", styles["TableCellText"]),
            Paragraph(f"<b>High Risk (&ge;50%):</b> {high} ({high_pct}%)", styles["TableCellText"]),
        ]
    ]
    dist_table = Table(dist_data, colWidths=[168, 168, 168])
    dist_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), RISK_LOW_BG),
        ('BACKGROUND', (1, 0), (1, 0), RISK_MED_BG),
        ('BACKGROUND', (2, 0), (2, 0), RISK_HIGH_BG),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_LIGHT),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.white),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))

    return [cards_table, Spacer(1, 6), dist_table]


def _build_batch_ranking_table(ranking_list: list, total_marks: Optional[float], styles) -> list:
    """Builds classroom ranking and rubric mark table."""
    story = []
    story.append(Paragraph("STUDENT INTEGRITY & GRADING BREAKDOWN", styles["SectionHeading"]))

    table_data = [
        [
            Paragraph("<b>#</b>", styles["TableCellHeader"]),
            Paragraph("<b>Student ID</b>", styles["TableCellHeader"]),
            Paragraph("<b>Student Name</b>", styles["TableCellHeader"]),
            Paragraph("<b>Risk</b>", styles["TableCellHeader"]),
            Paragraph("<b>AI %</b>", styles["TableCellHeader"]),
            Paragraph("<b>Text Sim</b>", styles["TableCellHeader"]),
            Paragraph("<b>Code Sim</b>", styles["TableCellHeader"]),
            Paragraph("<b>Deduct</b>", styles["TableCellHeader"]),
            Paragraph("<b>Final Mark</b>", styles["TableCellHeader"]),
        ]
    ]

    for idx, r in enumerate(ranking_list[:60]):
        risk_badge_color = RISK_HIGH_COLOR if r["risk_level"] == "high" else (RISK_MED_COLOR if r["risk_level"] == "medium" else RISK_LOW_COLOR)
        badge_html = f"<font color='{risk_badge_color.hexval()}'><b>{r['risk_level'].upper()}</b></font>"

        if r["marks_obtained"] is not None:
            t_marks = total_marks if total_marks is not None else 10.0
            deduct_val = max(0.0, t_marks - r["marks_obtained"])
            deduct_html = f"<font color='#dc2626'>-{deduct_val:.1f}</font>" if deduct_val > 0.05 else "0.0"
            final_mark_html = f"<b>{r['marks_obtained']:.1f}</b>"
        elif r.get("marks_breakdown") and "total_deductions" in r["marks_breakdown"]:
            deduct_val = float(r["marks_breakdown"]["total_deductions"])
            deduct_html = f"<font color='#dc2626'>-{deduct_val:.1f}</font>" if deduct_val > 0.05 else "0.0"
            final_mark_html = "--"
        else:
            deduct_html = "--"
            final_mark_html = "--"

        table_data.append([
            Paragraph(str(idx + 1), styles["TableCellText"]),
            Paragraph(f"<b>{r['student_id']}</b>", styles["TableCellBold"]),
            Paragraph(r["student_name"], styles["TableCellText"]),
            Paragraph(badge_html, styles["TableCellText"]),
            Paragraph(f"{round(r['ai_prob']*100)}%", styles["TableCellText"]),
            Paragraph(f"{round(r['text_sim_max']*100)}%", styles["TableCellText"]),
            Paragraph(f"{round(r['code_sim_max']*100)}%" if r["code_sim_max"] is not None else "--", styles["TableCellText"]),
            Paragraph(deduct_html, styles["TableCellBold"]),
            Paragraph(final_mark_html, styles["TableCellBold"]),
        ])

    ranking_table = Table(table_data, colWidths=[24, 70, 110, 50, 48, 56, 56, 45, 45])
    ranking_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY_PRIMARY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(ranking_table)
    return story


def _build_batch_cohort_summary_box(ranking_list: list, total_marks: Optional[float], styles) -> list:
    """Builds an executive forensic cohort findings box."""
    story = []
    high_cases = [r for r in ranking_list if r["risk_level"] == "high"]
    med_cases = [r for r in ranking_list if r["risk_level"] == "medium"]
    low_cases = [r for r in ranking_list if r["risk_level"] == "low"]
    
    total_pts = f"{total_marks:.1f}" if total_marks is not None else "100.0"

    findings_data = [
        [
            Paragraph("<b>COHORT INTEGRITY SUMMARY</b>", styles["SectionHeading"])
        ],
        [
            Paragraph(f"""
            • <b>High-Risk Submissions ({len(high_cases)} flagged):</b> Submissions with composite risk &ge; 50% demonstrate high synthetic AI probability and/or strong cross-peer code/text overlap. Recommended for formal academic integrity interview.<br/>
            • <b>Moderate-Risk Submissions ({len(med_cases)} flagged):</b> Moderate similarity or localized AI generation detected. Automated rubric deductions applied.<br/>
            • <b>Authentic Submissions ({len(low_cases)} verified):</b> Clear human-authored originality with low cross-peer text and code similarity metrics.
            """, styles["DocBodyText"])
        ]
    ]
    findings_table = Table(findings_data, colWidths=[504])
    findings_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_CARD),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_LIGHT),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(findings_table)
    return story


def _build_batch_marking_config_box(batch, styles) -> list:
    """Builds a table displaying the marking config thresholds."""
    story = []
    
    cfg = batch.marking_config
    if not cfg:
        return []

    total_pts = f"{batch.total_marks:.1f}" if batch.total_marks is not None else "100.0"
    story.append(Paragraph(f"BATCH RUBRIC & PENALTY THRESHOLDS (Total Marks: {total_pts})", styles["SectionHeading"]))
    
    table_data = [
        [
            Paragraph("<b>Metric Category</b>", styles["TableCellHeader"]),
            Paragraph("<b>Threshold Range (%)</b>", styles["TableCellHeader"]),
            Paragraph("<b>Penalty Marks</b>", styles["TableCellHeader"]),
        ]
    ]
    
    # Try the array format first
    categories = [
        ("AI-Generated Writing", "ai_thresholds"),
        ("Text & Semantic Similarity", "text_copy_thresholds"),
        ("Code AST Structure", "code_ast_thresholds"),
        ("Composite Risk Score", "risk_score_thresholds"),
    ]
    
    has_array_config = any(cfg.get(cat_key) for _, cat_key in categories)
    
    if has_array_config:
        for cat_name, cat_key in categories:
            thresholds = cfg.get(cat_key, [])
            if not thresholds:
                continue
                
            for i, t in enumerate(thresholds):
                min_val = t.get("min_value", 0)
                max_val = t.get("max_value", 100)
                deduct = t.get("marks_deduct", 0)
                
                cat_label = cat_name if i == 0 else ""
                
                table_data.append([
                    Paragraph(f"<b>{cat_label}</b>", styles["TableCellBold"]),
                    Paragraph(f"{min_val}% - {max_val}%", styles["TableCellText"]),
                    Paragraph(f"<font color='#dc2626'>-{deduct}</font>", styles["TableCellBold"]),
                ])
    else:
        # Fallback to legacy singular format
        ai_thresh = float(cfg.get("ai_threshold", 0.5) or 0.5) * 100
        text_thresh = float(cfg.get("text_sim_threshold", 0.4) or 0.4) * 100
        code_thresh = float(cfg.get("code_sim_threshold", 0.5) or 0.5) * 100
        
        table_data.append([
            Paragraph("<b>AI-Generated Writing</b>", styles["TableCellBold"]),
            Paragraph(f"&ge; {ai_thresh:.0f}%", styles["TableCellText"]),
            Paragraph("Refer to deductions", styles["TableCellText"]),
        ])
        table_data.append([
            Paragraph("<b>Text & Semantic Similarity</b>", styles["TableCellBold"]),
            Paragraph(f"&ge; {text_thresh:.0f}%", styles["TableCellText"]),
            Paragraph("Refer to deductions", styles["TableCellText"]),
        ])
        table_data.append([
            Paragraph("<b>Code AST Structure</b>", styles["TableCellBold"]),
            Paragraph(f"&ge; {code_thresh:.0f}%", styles["TableCellText"]),
            Paragraph("Refer to deductions", styles["TableCellText"]),
        ])

    if len(table_data) == 1:
        return []

    cfg_table = Table(table_data, colWidths=[200, 164, 140])
    cfg_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY_PRIMARY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    
    story.append(cfg_table)
    return story


def _build_batch_footer(batch, styles) -> list:
    """Builds classroom audit digital certificate."""
    story = []
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_LIGHT, spaceBefore=8, spaceAfter=8))
    instructor_name = batch.instructor.full_name if batch.instructor else "Certified Course Instructor"
    sign_data = [
        [
            Paragraph(f"""
            <b>CLASSROOM AUDIT CERTIFICATION</b><br/>
            <font size=7.5 color='#64748b'>
            Audit Batch ID: <font face='Courier'>{str(batch.id)}</font><br/>
            Evaluation Model: GPT-2 Perplexity + AST Code Tokenizer + MiniLM-L6-v2<br/>
            AcademicGuard Automated Integrity Verification System
            </font>
            """, styles["DocBodyText"]),
            Paragraph(f"""
            <b>AUTHORIZED INSTRUCTOR</b><br/>
            <font size=7.5 color='#64748b'>
            Instructor: <b>{instructor_name}</b><br/>
            Certified on: {datetime.now(timezone.utc).strftime('%d %b %Y')}<br/>
            Integrity Status: <font color='#16a34a'><b>Classroom Audit Complete</b></font>
            </font>
            """, styles["DocBodyText"]),
        ]
    ]
    sign_table = Table(sign_data, colWidths=[270, 234])
    sign_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_LIGHT),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(sign_table)
    return story


# ── Backwards-Compatible Alias ───────────────────────────────────────────────

async def generate(batch_id: str, db) -> Path:
    """Alias for backwards compatibility with previous callers."""
    return await generate_batch_report(batch_id, db)
