# AcademicGuard — 10-Minute Prototype & Demo Video Storyboard
## Blockchain Olympiad Bangladesh (BCOLBD 2026) — Artificial Intelligence Track

> **Deliverable Item:** Prototype / Demo Video  
> **Official File Name:** `AcademicGuard_Demo Video.mp4`  
> **Video Duration:** Maximum 10:00 Minutes  
> **Target Criteria:** Demo Video Evaluation (30 Points: Functionality 15 pts, Presentation Quality 15 pts)  
> **Resolution:** 1080p Full HD (1920x1080, 60fps)  
> **Format:** MP4 (H.264 / AAC, File Size $< 100\text{ MB}$)  

---

## Scene Breakdown & Demonstration Plan

```
+-----------------------------------------------------------------------------------------------+
| Scene # | Video Segment                              | Duration | Screen Capture Subject     |
+---------+--------------------------------------------+----------+----------------------------+
| Scene 1 | Introduction & System Architecture Intro   | 0:00–1:00| Splash Screen & Dashboard  |
| Scene 2 | Batch PDF Ingestion & OpenDataLoader Parsing| 1:00–2:30| Upload Flow & Parser Logs  |
| Scene 3 | Real-Time Async Pipeline & Status Polling  | 2:30–3:45| Pipeline Progress Indicators|
| Scene 4 | Dynamic Risk Scoring & Insight Engine      | 3:45–5:00| Batch Results Table        |
| Scene 5 | AI Authorship Heatmap & ESL Banding Demo   | 5:00–6:30| Sentence Perplexity Viewer |
| Scene 6 | Code Forensics & AST Clone Comparison      | 6:30–7:45| Side-by-Side Code Diff     |
| Scene 7 | Automated Marking & Template Deductions    | 7:45–8:45| Rubric Calculator & Marks  |
| Scene 8 | Active Learning Retraining & Model Registry| 8:45–9:30| Annotations & Auto-Trainer |
| Scene 9 | Standalone Reproducibility CLI Demo & Wrap | 9:30–10:0| `quick_inference_demo.py`  |
+---------+--------------------------------------------+----------+----------------------------+
```

---

## Script & Voiceover Guide

### Scene 1: Introduction & Architecture Overview (0:00 – 1:00)
- **Visual:** Open browser at `http://localhost:8080`. Display sleek dark-mode glassmorphic dashboard.
- **Narrator Voiceover:**
  > *"Welcome to the official prototype demonstration of AcademicGuard for Blockchain Olympiad Bangladesh 2026. AcademicGuard is an on-premise, privacy-preserving academic integrity and automated grading platform powered by local machine learning. Here on the instructor dashboard, faculty members gain an immediate, high-level overview of class submission health, average risk scores, and integrity distribution."*

### Scene 2: Batch PDF Ingestion & Layout Parsing (1:00 – 2:30)
- **Visual:** Navigate to `/pages/upload.html`. Drag and drop a batch of 5 student lab submission PDFs. Show cover page extraction in action.
- **Narrator Voiceover:**
  > *"AcademicGuard handles realistic classroom workflows with multi-file batch uploads. Using OpenDataLoader-PDF, our pipeline conducts XY-Cut++ 2D spatial layout analysis to intelligently isolate cover page metadata—extracting student IDs and names—while cleanly separating theory text from embedded source code blocks."*

### Scene 3: Asynchronous Pipeline Execution (2:30 – 3:45)
- **Visual:** Show active batch processing progress bar transitioning from 0% to 100% across the 6 pipeline stages: Ingestion $\to$ Text Similarity $\to$ Code Forensics $\to$ AI Detection $\to$ Dynamic Risk Scoring $\to$ Automated Marking.
- **Narrator Voiceover:**
  > *"Unlike legacy tools that block or timeout on large files, AcademicGuard delegates processing to asynchronous FastAPI background workers. Clients poll status non-blockingly while CPU-optimized transformer inference runs locally on the host machine with zero cloud API latency."*

### Scene 4: Dynamic Risk Scoring & Batch Overview (3:45 – 5:00)
- **Visual:** Navigate to `/pages/results.html`. Filter by Risk Level (High, Medium, Low). Show `TEXT_ONLY` vs `CODE_PRESENT` weight profile badges.
- **Narrator Voiceover:**
  > *"Once complete, the Insight Engine renders a prioritized submission list. Notice the adaptive weight profiles: for pure theory essays, the system evaluates AI detection and text similarity. For programming labs, it dynamically incorporates AST code clone metrics into the composite risk score."*

### Scene 5: AI Authorship Detection & ESL Confidence Banding (5:00 – 6:30)
- **Visual:** Open a student submission detail page. Show the **Sentence-Level Perplexity Heatmap**. Click an amber-highlighted sentence showing low perplexity but quarantined due to ESL banding.
- **Narrator Voiceover:**
  > *"Here is AcademicGuard's AI detection engine. By evaluating GPT-2 token log-likelihood and sentence burstiness variance, sentences are color-coded in real-time. Notice our key equity breakthrough: Algorithmic Confidence Threshold Banding. Submissions in the 0.40 to 0.75 confidence interval are automatically quarantined without automated deductions, safeguarding non-native English students from false accusations."*

### Scene 6: Compiler-Grade Code Forensics (6:30 – 7:45)
- **Visual:** Switch to the Code Similarity tab. Show side-by-side AST diff viewer between two students whose variable names are completely different (`total` vs `result`, `i` vs `idx`), yet flagged with 92% similarity.
- **Narrator Voiceover:**
  > *"In programming assignments, students routinely evade superficial token matchers like Stanford MOSS by renaming variables. AcademicGuard uses Tree-Sitter compiler parsing to normalize identifiers and compares structural syntax trees and UniXcoder embeddings, exposing logical clones regardless of surface obfuscation."*

### Scene 7: Automated Rubric Marking & Deductions (7:45 – 8:45)
- **Visual:** Demonstrate the Rubric Marking panel. Adjust threshold sliders, apply a pre-saved "CS101 Lab Template", and show final marks dynamically recalculate from 100 down to 72 with itemized deduction breakdowns. Export audit-ready PDF/Excel report.
- **Narrator Voiceover:**
  > *"Faculty grading time is cut by up to 75%. Configurable rubric templates automatically apply standardized penalties for confirmed plagiarism while preserving human override control. Audit-ready PDF and Excel reports are exported with a single click."*

### Scene 8: Human-in-the-Loop Active Learning (8:45 – 9:30)
- **Visual:** Navigate to `/pages/training.html`. Show the annotation queue. Submit an instructor verification label. Show the auto-trainer update `model_registry.json` and hot-swap the active classifier in memory.
- **Narrator Voiceover:**
  > *"AcademicGuard is a self-improving platform. Instructor feedback feeds directly into an active learning loop. When threshold annotations are reached, the system retrains the scikit-learn classifier, logs performance metrics, and hot-swaps the model with zero server downtime."*

### Scene 9: Reproducibility CLI Demo & Wrap-Up (9:30 – 10:00)
- **Visual:** Open terminal. Run `python3 quick_inference_demo.py`. Show instant output of AI perplexity, AST code clone detection, and risk scoring in 3 seconds.
- **Narrator Voiceover:**
  > *"For competition jury verification, our inference pipeline is 100% reproducible with a single zero-dependency CLI script. AcademicGuard delivers data sovereignty, academic equity, and high throughput to higher education in Bangladesh. Thank you."*
