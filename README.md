# AcademicGuard — Code Repository & Technical Documentation
## Blockchain Olympiad Bangladesh (BCOLBD 2026) — Artificial Intelligence Track (AInspire)

> **Official Deliverable:** Technical Documentation & Code Repository  
> **Package Name:** `AcademicGuard_TD & CR.zip`  
> **Team Name:** `AcademicGuard` | **Team ID:** `6a7f5c7d71ee7`  
> **Institution:** Department of Computer Science & Engineering, University of Information Technology and Sciences (UITS), Dhaka, Bangladesh  
> **Evaluation Weightage:** 30% / 40 Points (Technical Completeness 20 pts + Code Quality & Inference Model 20 pts)  

---

## 🚀 10-Second Reproducibility Quickstart (For BCOLBD Judges)

To immediately verify the AI models, AST code clone detection, ESL confidence banding, and dynamic risk scoring with **zero database setup and zero configuration**, execute:

```bash
python3 quick_inference_demo.py
```

This runs our standalone inference verification test suite across all 4 machine learning pipelines in under 3 seconds.

---

## 📋 Table of Contents

1. [Project Overview](#-project-overview)
2. [Directory Structure](#-directory-structure)
3. [System Architecture & AI Models](#-system-architecture--ai-models)
4. [Local Full-Stack Deployment Guide](#-local-full-stack-deployment-guide)
5. [API Documentation & Health Endpoints](#-api-documentation--health-endpoints)
6. [Team Roster & Contributions](#-team-roster--contributions)

---

## 🎯 Project Overview

**AcademicGuard** is an on-premise, privacy-preserving academic integrity and automated grading platform engineered for higher education institutions in Bangladesh. It solves the **Academic Integrity Trilemma** (exorbitant foreign currency SaaS fees, severe non-native English/ESL false positive bias, and institutional data sovereignty risks) using local machine learning pipelines on commodity CPU hardware.

### Key Innovations:
- **OpenDataLoader-PDF Layout Parsing:** Employs XY-Cut++ 2D spatial analysis to extract metadata and separate theory text from source code.
- **Hybrid Semantic Text Similarity:** Combines lexical TF-IDF ($40\%$) with `sentence-transformers/all-MiniLM-L6-v2` dense embeddings ($60\%$).
- **Compiler-Grade Code Forensics:** Tree-Sitter AST parsing canonicalizes variable identifiers, defeating semantic obfuscation alongside `UniXcoder` neural code representations.
- **Research-Validated AI Detection:** Auto-regressive token log-likelihood (**GPT-2 Perplexity**), sentence-level variance (**Burstiness**), and vocabulary entropy (**Stylometry**).
- **Algorithmic Confidence Threshold Banding:** A protective quarantine zone ($p \in [0.40, 0.75]$) prohibiting automated penalties on ambiguous or ESL student essays.
- **Dynamic Risk Scoring & Automated Rubric Marking:** Content-aware scoring (`TEXT_ONLY` vs `CODE_PRESENT`) driving automated grade deductions.
- **Continuous Active Learning:** Human-in-the-loop retraining engine that updates local classifiers with versioned tracking in `model_registry.json`.

---

## 📂 Directory Structure

```
AcademicGuard_TD_CR/
├── README.md                      # This official submission README
├── TECHNICAL_DOCUMENTATION.md     # Comprehensive 20-point technical documentation
├── quick_inference_demo.py        # Standalone 1-command reproducible AI inference runner
├── docker-compose.yml             # Production Docker Compose orchestration
├── docker-compose.prod.yml        # Multi-stage production compose configuration
├── Dockerfile.all                 # All-in-one container definition
├── run-local.sh                   # Automated local developer launcher
├── setup.sh                       # Environment setup script
├── supervisord.conf               # Supervisor multi-process manager
├── .env.example                   # Sanitized environment template
├── pyrightconfig.json             # Static type checking configuration
├── backend/                       # Python 3.11+ FastAPI backend
│   ├── app/
│   │   ├── api/                   # REST routers (auth, batches, results, reports, admin, etc.)
│   │   ├── core/                  # Security, JWT auth, rate limiting, audit logger
│   │   ├── db/                    # SQLAlchemy models & PostgreSQL migrations
│   │   ├── engine/                # NLP, AST code forensics, AI detector & marking engine
│   │   └── reports/               # Audit-ready PDF, Excel, and JSON report generators
│   ├── models/                    # Model registry and active detector pickle
│   ├── scripts/                   # Model downloaders, trainers & standalone test scripts
│   ├── tests/                     # Pytest automated test suite
│   ├── requirements.txt           # Python dependencies (pinned bcrypt for passlib)
│   └── Dockerfile                 # Backend container definition
├── frontend/                      # Static Vanilla HTML5/CSS3/JS Single Page Application
│   ├── pages/                     # Dashboard, upload, results, submission, annotate, admin
│   ├── js/                        # Modular Vanilla JS (Insight Engine, Heatmaps, Diff Viewer)
│   ├── css/                       # Custom modern glassmorphic design system
│   └── assets/                    # Icons and static resources
├── nginx/                         # Nginx reverse proxy configuration
└── synthetic_dataset/             # Benchmark evaluation datasets
```

---

## 🏗️ System Architecture & AI Models

```
Document Upload (PDF)
        │
        ▼
[ OpenDataLoader-PDF Layout Analysis ]
        ├── Theory Prose ───────► [ TF-IDF + all-MiniLM-L6-v2 Semantic Similarity ]
        │                                        │
        ├── Embedded Code ──────► [ Tree-Sitter AST Normalization + UniXcoder ]
        │                                        │
        └── Statistical Signal ─► [ GPT-2 Perplexity + Burstiness Variance ]
                                                 │
                                                 ▼
                                  [ ESL Confidence Banding Quarantine ]
                                                 │
                                                 ▼
                                  [ Dynamic Composite Risk Scorer ]
                                                 │
                                                 ▼
                                  [ Rubric-Based Mark Deductions ]
```

---

## 💻 Local Full-Stack Deployment Guide

### Option A: Complete Multi-Container Stack (Recommended)
```bash
./setup.sh && docker compose up -d --build
```
- **Web Interface:** `http://localhost:8080`
- **Interactive OpenAPI Documentation:** `http://localhost:8000/api/docs`

### Option B: Local Developer Execution (Without Docker)
```bash
# 1. Start Backend
cd backend
source venv/bin/activate
pip install -r requirements.txt
python scripts/download_models.py
uvicorn app.main:app --reload --port 8000

# 2. Start Frontend
python -m http.server 8080 --directory frontend
```

---

## 👥 Team Roster & Responsibilities

| Member Name | Student ID & Academic Status | Contact | Responsibilities |
| :--- | :--- | :--- | :--- |
| **Sumaia bintey Ismail**<br>*(Team Representative)* | **ID:** 1103<br>B.Sc. in CSE (4th Yr, 7th Sem)<br>Session: 2023–2027 | `sumaia_bintey1103@uits.edu.bd` | System specification, Glassmorphic UI/UX architecture, Automated Rubric Marking Engine & Benchmark Datasets |
| **Kazi Md Azhar Uddin Abeer**<br>*(Core Team Member)* | **ID:** 1120<br>B.Sc. in CSE (4th Yr, 7th Sem)<br>Session: 2023–2027 | `azhar_uddin1120@uits.edu.bd` | Backend architecture, Tree-Sitter AST Parsing, UniXcoder Neural Code Forensics, OpenDataLoader PDF Pipeline |
| **Ahmmed Abdali Khan**<br>*(Core Team Member)* | **ID:** 0432320005101118<br>B.Sc. in CSE (4th Yr, 7th Sem)<br>Session: 2023–2027 | `0432320005101118@uits.edu.bd` | AI Authorship Detection (GPT-2 Perplexity & Burstiness), ESL Confidence Banding Algorithm, Database & DevOps |
