# Blockchain Olympiad Bangladesh (BCOLBD) 2026 — Official Submission Guide & Manifest
## Artificial Intelligence Category (AInspire Track)

> **Team Name:** `AcademicGuard`  
> **Team ID:** `6a7f5c7d71ee7`  
> **Institution:** Department of Computer Science & Engineering (CSE), University of Information Technology and Sciences (UITS), Dhaka, Bangladesh  
> **Project Title:** AcademicGuard: A High-Throughput, Privacy-Preserving Machine Learning Architecture for Multi-Modal Academic Integrity and Code Forensics  
> **Target Track:** Artificial Intelligence (AI) Category  

---

## 1. Official Competition Calendar & Deadlines

| Phase | Milestone / Deliverable | Deadline | Status |
| :--- | :--- | :--- | :---: |
| **Phase 1** | **White Paper Submission (Preliminary Round)** | **Sunday, August 16, 2026** | **Completed** |
| **Phase 2** | Finalist Top 30 Teams Announcement | Monday, August 31, 2026 | — |
| **Phase 3** | **Final Submission (Whitepaper, Code Repo & Docs, Pitch Deck, Videos)** | **Wednesday, September 2, 2026** | **Ready** |
| **Phase 4** | Live Pitch Presentation & Technical Q&A Defense | September 2026 | Scheduled |

---

## 2. Official Deliverables Checklist & Naming Conventions

All submissions must follow the mandatory naming convention `<Team Name>_<Item Name>.<ext>`:

| # | Submission Item | Official File Name | Format | Size Limit | Notes |
| :-: | :--- | :--- | :---: | :---: | :--- |
| **1** | **Whitepaper** | `AcademicGuard_Whitepaper.pdf` | **PDF** | $\le 20\text{ MB}$ | Strictly budgeted to 10 pages; conforms to BCOLBD rubric. |
| **2** | **Technical Documentation & Code Repository** | `AcademicGuard_TD & CR.zip` | **ZIP** | — | **Mandatory for AI Category**. Contains complete source code, docs, and standalone reproducible inference demo. |
| **3** | **Pitch Deck (Presentation)** | `AcademicGuard_Pitch Deck.pdf` | **PDF** | $\le 20\text{ MB}$ | High-impact deck for 10-minute presentation. |
| **4** | **10-min Pitch Presentation Video** | `AcademicGuard_Presentation.mp4` | **MP4** | $\le 100\text{ MB}$ | Pitch presentation including 1-minute member role breakdown. |
| **5** | **10-min Prototype / Demo Video** | `AcademicGuard_Demo Video.mp4` | **MP4** | $\le 100\text{ MB}$ | Live screen demonstration of real-time multi-modal analysis. |
| **6** | **Demo Link** | `AcademicGuard_Demo Link.txt` | **TXT** | — | Web link to live hosted prototype and API swagger documentation. |
| *—* | *Poster Board* | *AcademicGuard_Poster Board.pdf* | *PDF* | *20 MB* | *Required only for Blockchain Category (Not AI Category).* |

---

## 3. Team Roster & Role Distribution

In accordance with BCOLBD AI track live presentation guidelines requiring a 1-minute introduction of each member's responsibilities:

| Member Name | Student ID & Academic Status | Contact Information | Core Responsibilities in Project |
| :--- | :--- | :--- | :--- |
| **Sumaia bintey Ismail**<br>*(Team Representative)* | **ID:** 1103<br>B.Sc. in CSE (4th Yr, 7th Sem)<br>Session: 2023–2027 | `sumaia_bintey1103@uits.edu.bd`<br>+880 1623-727260 | Lead Technical Writer, UI/UX Architect, Rubric Marking Engine & Benchmark Dataset Curation |
| **Kazi Md Azhar Uddin Abeer**<br>*(Core Team Member)* | **ID:** 1120<br>B.Sc. in CSE (4th Yr, 7th Sem)<br>Session: 2023–2027 | `azhar_uddin1120@uits.edu.bd`<br>+880 1760-211553 | Lead Backend Architect, Tree-Sitter AST & UniXcoder Code Forensics Engine, OpenDataLoader PDF Pipeline |
| **Ahmmed Abdali Khan**<br>*(Core Team Member)* | **ID:** 0432320005101118<br>B.Sc. in CSE (4th Yr, 7th Sem)<br>Session: 2023–2027 | `0432320005101118@uits.edu.bd`<br>+880 1571-503855 | AI Detection Lead (GPT-2 Perplexity & Burstiness), ESL Confidence Banding Algorithm, Database & DevOps |

---

## 4. Evaluation Scheme Alignment (Targeting 100/100)

### Preliminary Round: White Paper Evaluation (100 Points Total)
- **Criterion I: Vision & Problem Statement (30 Points):** Addresses the Academic Integrity Trilemma (Financial Cost vs ESL Equity vs Data Sovereignty) with localized Bangladesh higher education empirical context (student-to-faculty ratios $>40:1$, foreign currency SaaS drain).
- **Criterion II: Use Case & Existing Solutions (10 Points):** Detailed critique of Turnitin, Copyleaks, GPTZero, and Stanford MOSS. Includes 8-feature comparative matrix proving MOSS inadequacy for modern assignments.
- **Criterion III: Risks & Challenges (20 Points):** Technical mitigation of ESL false positives via **Algorithmic Confidence Threshold Banding** ($p \in [0.40, 0.75]$ quarantine) and defense against adversarial prompt injections.
- **Criterion IV: Architecture & Infrastructure (30 Points):** Multi-modal local pipeline (OpenDataLoader-PDF $\to$ TF-IDF/MiniLM $\to$ Tree-sitter/UniXcoder $\to$ GPT-2 PPL $\to$ Composite Scorer) running entirely CPU-bound on commodity campus servers.
- **Criterion V: Revenue & Distribution (10 Points):** Multi-tier freemium SaaS & on-premise air-gapped institutional licensing model with projected 3-year P&L.

### Final Round: Technical & Defense Evaluation (100% Total)
- **Technical Documentation & Code Repository (30% / 40 Points):**
  - *Technical Completeness & Documentation (20 pts):* Comprehensive system specification with mathematical formulations, database schemas, and pipeline blueprints.
  - *Code Quality & Inference Model (20 pts):* Clean, PEP 8 compliant, type-annotated code with a standalone 10-second zero-database inference verifier (`quick_inference_demo.py`).
- **Pitch Presentation (20% / 30 Points):** Professional 10-minute slide deck with clear value proposition and individual member contributions.
- **Technical Q&A Session (20%):** Rigorous defense covering algorithmic complexity ($O(N^2) \to O(N)$ via MinHash/FAISS), token log-likelihood math, and tree isomorphism kernels.
- **Demo Video (30 Points):** 10-minute high-definition walkthrough showing end-to-end ingestion of PDFs to rubric-deducted gradebook exports.

---

## 5. Directory Structure of `docs/BCOLBD-2026/`

```
docs/BCOLBD-2026/
├── BCOLBD_SUBMISSION_GUIDE.md               # This master document
├── AcademicGuard_Technical_Documentation.md  # Official comprehensive technical documentation (20/20 pts)
├── AcademicGuard_Whitepaper.pdf              # Compiled 10-page competition white paper
├── AcademicGuard_Whitepaper.docx             # Editable Word source file
├── AcademicGuard_Pitch_Deck_Outline.md       # Slide-by-slide 10-minute pitch deck outline
├── AcademicGuard_Demo_Video_Script.md        # 10-minute prototype video script & storyboard
└── AcademicGuard_Demo_Link.txt               # Text file containing live prototype URLs & credentials
```
