# AcademicGuard — PDF Data Extraction & Layout Analysis Guide

This guide details the document extraction pipeline implemented in `backend/app/engine/pdf_processor.py`, covering the integration of **OpenDataLoader-PDF**, **PyMuPDF (`fitz`)**, and the automated unit test suite.

---

## 1. Multi-Engine Architecture

AcademicGuard deploys a dual-engine architecture to achieve high layout fidelity and extraction reliability across diverse student PDF formats:

```
                      ┌──────────────────────────────────────┐
                      │      Incoming Student PDF Upload     │
                      └──────────────────┬───────────────────┘
                                         │
                                ┌────────▼────────┐
                                │ OpenDataLoader? │
                                └──┬────────────┬─┘
                       Yes (CLI/Lib)│            │ No / Fallback
                                   │            │
            ┌──────────────────────▼──────┐   ┌─▼───────────────────────────┐
            │   OpenDataLoader-PDF Engine │   │      PyMuPDF (fitz) Engine  │
            │  - XY-Cut++ Layout Analysis │   │  - Layout-aware block sort  │
            │  - Structured Markdown Text │   │  - Fast C-based extraction  │
            │  - 2D Spatial JSON Tree     │   │  - Regex code heuristic     │
            │  - Native Code Block Tags   │   │                             │
            └──────────────┬──────────────┘   └──────────────┬──────────────┘
                           │                                 │
                           └────────────────┬────────────────┘
                                            │
                               ┌────────────▼────────────┐
                               │ Extracted Submission:   │
                               │ - Student ID & Name     │
                               │ - Clean Theory Prose    │
                               │ - Isolated Code Blocks  │
                               └─────────────────────────┘
```

---

## 2. Core Extraction Engines

### 2.1 Primary: OpenDataLoader-PDF (`opendataloader-pdf`)
- **Benchmark-Leading Layout Analysis:** Ranks #1 with 0.907 overall accuracy across AI document parsing benchmarks.
- **XY-Cut++ Spatial Parsing:** Accurately separates multi-column text, data tables, headers, and callouts.
- **Structured Markdown & JSON Output:** Generates clean Markdown with native code fences (```) alongside bounding box coordinates.
- **CLI & Module Integration:** Invoked via `opendataloader-pdf <input.pdf> -o <out_dir> -f markdown json` or Python wrapper.

### 2.2 Fallback: PyMuPDF (`fitz`)
- High-speed C-based MuPDF rendering framework.
- Extracts page text blocks with physical layout coordinate sorting (`fitz.TEXT_PRESERVE_LIGATURES | fitz.TEXT_DEHYPHENATE`).
- Guarantees that analysis never fails even if OpenDataLoader encounters corrupted binary structures.

---

## 3. Student Identification & Cover Page Parsing

The ingestion pipeline scans the first 3,000 characters of the document using regex patterns:

- **Student ID:** Matches `Student ID:`, `Roll No:`, `Reg. No:`, `Registration Number:`, and alphanumeric ID structures (e.g., `UG-2024/01`, `0432320005101118`).
- **Student Name:** Matches `Name:`, `Student Name:`, `Full Name:`.

---

## 4. Theory Prose vs. Code Block Separation

To ensure accurate similarity scoring, documents are partitioned into theory prose and source code:
1. **Native Markdown Fences:** OpenDataLoader natively tags code blocks in Markdown output.
2. **Structural Keyword Lookahead:** For plain text feeds, the system scans for programming keywords (`def`, `class`, `import`, `#include`, `public`, `void`, `SELECT`) with a 3-line lookahead buffer.

---

## 5. Verification & Unit Testing

The extraction pipeline is tested via `backend/tests/test_opendataloader.py`:

```bash
# Run OpenDataLoader test suite
cd backend
python tests/test_opendataloader.py
```
