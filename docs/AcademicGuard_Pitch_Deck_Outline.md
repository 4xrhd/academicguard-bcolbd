# AcademicGuard — 10-Minute Pitch Deck Presentation Outline
## Blockchain Olympiad Bangladesh (BCOLBD 2026) — Artificial Intelligence Track

> **Deliverable Item:** Pitch Deck (Presentation) & Live Presentation  
> **Official File Name:** `AcademicGuard_Pitch Deck.pdf` (Presentation Slides) & `AcademicGuard_Presentation.mp4` (10-min Video)  
> **Presentation Duration:** Strictly 10 Minutes Maximum  
> **Language:** English  
> **Mandatory Requirement:** 1-minute introduction of each member's responsibilities  

---

## Slide Structure & Time Budget

```
+-----------------------------------------------------------------------------------------+
| Slide # | Topic & Focus Area                          | Allocated Time | Target Score  |
+---------+---------------------------------------------+----------------+---------------+
| Slide 1 | Title Page & Team Roster Introduction       | 1:00 min       | Mandatory req |
| Slide 2 | The Problem: The Academic Integrity Crisis  | 1:15 min       | 30 Pts        |
| Slide 3 | The Trilemma: Cost, ESL Bias & Privacy      | 1:15 min       | 30 Pts        |
| Slide 4 | Four Academic Use Cases & MOSS/Turnitin Gap | 1:00 min       | 10 Pts        |
| Slide 5 | AcademicGuard Multi-Modal Architecture      | 1:30 min       | 30 Pts        |
| Slide 6 | AI Authorship & ESL Confidence Banding      | 1:15 min       | 20 Pts        |
| Slide 7 | Compiler-Grade Code Forensics (Tree-Sitter) | 1:15 min       | 30 Pts        |
| Slide 8 | Automated Marking & Insight Analytics       | 0:45 min       | 20 Pts        |
| Slide 9 | Business Model, Commercialization & Roadmap | 0:45 min       | 10 Pts        |
| Slide 10| Conclusion, Impact & Q&A Invitation         | 0:45 min       | Summary       |
+---------+---------------------------------------------+----------------+---------------+
| Total   | 10 High-Impact Slides                       | 10:00 min      | 100 Points    |
+-----------------------------------------------------------------------------------------+
```

---

## Detailed Slide Content & Speaking Script

### Slide 1: Title & Team Responsibilities (Time: 0:00 - 1:00)
- **Visuals:** Project Logo, Team Name (`AcademicGuard`), Team ID (`6a7f5c7d71ee7`), Department of CSE, University of Information Technology and Sciences (UITS).
- **Mandatory 1-Minute Member Introductions:**
  1. **Sumaia bintey Ismail (Team Lead & Representative):** Oversees system design, front-end glassmorphic architecture, UI/UX accessibility, automated rubric marking logic, and benchmark dataset curation.
  2. **Kazi Md Azhar Uddin Abeer (Core Architect):** Engineered the backend pipeline, Tree-Sitter AST parser, UniXcoder neural code embedding pipeline, and OpenDataLoader-PDF layout analysis.
  3. **Ahmmed Abdali Khan (AI & Infrastructure Lead):** Designed the GPT-2 Perplexity & Burstiness AI detection engine, formulated Algorithmic Confidence Banding for ESL equity, and architected database/container deployment.

---

### Slide 2: The Problem — Academic Integrity Crisis in Bangladesh (Time: 1:00 - 2:15)
- **Core Message:** Frontier LLMs (ChatGPT, Claude, DeepSeek) and AI coding assistants (GitHub Copilot, Cursor) have democratized automated cheating.
- **Localized Empirical Context:**
  - High student-to-faculty ratios in Bangladesh ($>40:1$, reaching $60:1$ in public and private institutions).
  - Faculty grading overload ($200–300$ lab reports and term papers per semester).
  - Manual inspection is humanly impossible; superficial online checkers are easily evaded.

---

### Slide 3: The Trilemma — Why Existing Solutions Fail (Time: 2:15 - 3:30)
- **The Three Structural Failures:**
  1. **Exorbitant Cost:** Turnitin and Copyleaks charge $\$3–\$8$ per student/year in USD foreign currency, creating severe balance-of-payments strain for developing institutions.
  2. **Severe ESL Inequity:** Standard AI detectors exhibit up to $61\%$ false positive rates on non-native English (ESL) students due to restricted vocabulary and low stylistic burstiness.
  3. **Data Privacy & IP Leakage:** Uploading student theses and proprietary codebases to US-hosted cloud vendors violates institutional data sovereignty.

---

### Slide 4: Target Use Cases & Competitive Landscape (Time: 3:30 - 4:30)
- **Four Core Use Cases:**
  - Computer Science & Engineering Lab Code Verification.
  - Undergraduate & Postgraduate Thesis Defense.
  - Continuous LMS Integration (Moodle, Canvas).
  - Research Grant Governance.
- **Why Not Stanford MOSS?** MOSS has zero text/prose support, zero AI detection, uses unmaintained legacy Perl scripts, suffers an $O(N^2)$ scaling bottleneck, and is blind to semantic refactoring.

---

### Slide 5: Multi-Modal Local Architecture (Time: 4:30 - 6:00)
- **Technical Pipeline Diagram:**
  - **OpenDataLoader-PDF:** XY-Cut++ layout analysis splits documents into Theory vs. Code Blocks.
  - **Text Similarity:** Hybrid TF-IDF ($40\%$) + `all-MiniLM-L6-v2` dense vectors ($60\%$).
  - **Asynchronous Execution:** FastAPI background workers process batches concurrently without UI freeze.
  - **CPU-Only Efficiency:** Entire platform runs on commodity campus hardware without requiring GPUs.

---

### Slide 6: AI Authorship Detection & ESL Confidence Banding (Time: 6:00 - 7:15)
- **The Science:**
  - **Perplexity (PPL):** Auto-regressive log-likelihood via local GPT-2.
  - **Sentence Burstiness:** Measuring variance in sentence complexity ($\sigma / \mu$).
- **Algorithmic Confidence Threshold Banding (Our Innovation):**
  - $p < 0.40$: Human Zone (Zero penalty).
  - $0.40 \le p \le 0.75$: **ESL Quarantine Zone**. Strictly prohibits automated mark deductions; flags for visual sentence heatmap review.
  - $p > 0.75$: High-Confidence AI Zone (Eligible for rubric deduction).

---

### Slide 7: Compiler-Grade Code Forensics (Time: 7:15 - 8:30)
- **Beating Obfuscation:**
  - Variable renaming (`int total` $\to$ `int x`), loop interchange (`for` $\to$ `while`), and dead code insertion bypass token matchers.
  - **Tree-Sitter AST Normalization:** Canonicalizes variable tokens, mapping code to grammar trees.
  - **UniXcoder:** Neural code embeddings capture semantic equivalence across languages.

---

### Slide 8: Automated Rubric Marking & Glassmorphic Dashboard (Time: 8:30 - 9:15)
- **Faculty Time Savings:** 75% reduction in grading time.
- **Dynamic Risk Formula:**
  - Theory Profile: $0.55 \cdot \text{AI} + 0.45 \cdot \text{TextSim}$
  - Code Profile: $0.40 \cdot \text{AI} + 0.35 \cdot \text{TextSim} + 0.25 \cdot \text{CodeSim}$
- **Marking Templates:** Instant deduction application, gradebook export (PDF/Excel), and sentence-level heatmaps.

---

### Slide 9: Commercialization, Business Model & Roadmap (Time: 9:15 - 10:00)
- **Commercial Strategy:**
  - Tier 1: Open Community Edition for individual instructors (Local Docker).
  - Tier 2: Institutional Campus License ($80\%$ cheaper than Turnitin; paid in BDT).
- **Active Learning Loop:** Instructors submit override annotations, continuously retraining local models with zero downtime.

---

### Slide 10: Conclusion & Defense Q&A
- **Summary:** AcademicGuard is an equitable, high-throughput, sovereign academic integrity platform.
- **Call to Action:** *"Preserving Academic Truth through Localized Artificial Intelligence."*
- **Q&A Handover:** Open floor for jury technical defense.
