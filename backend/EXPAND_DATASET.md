# Expanding the AcademicGuard Training Dataset

This document explains how to load internet datasets (from Kaggle, Hugging Face, HC3, DAIGT), add custom training data, extract features, and retrain the AcademicGuard detection model.

---

## 1. Fast Track: Google Colab Retraining with Internet Datasets
The fastest and most powerful way to train on thousands of real-world human vs AI academic essays is via our Google Colab notebook:
- **Notebook**: [`../notebooks/AcademicGuard_Model_Retraining.ipynb`](../notebooks/AcademicGuard_Model_Retraining.ipynb)
- **Comprehensive Guide**: [`../docs/MODEL_RETRAINING_GUIDELINES.md`](../docs/MODEL_RETRAINING_GUIDELINES.md)

### Supported Internet Datasets in Colab:
- **Kaggle DAIGT V2 (`drc311/daigt-v2-train-dataset`)**: 40,000+ essays from the Kaggle LLM Detection Competition.
- **HC3 (`Hello-SimpleAI/HC3`)**: 24,000+ academic Q&As across Computer Science, Medicine, Finance, and Law.
- **GPT-Wiki-Intro (`aadityaubhat/GPT-wiki-intro`)**: 150,000+ Wikipedia vs GPT-3 generated articles.
- **Kaggle API CLI**: Direct download of any Kaggle dataset via `kaggle datasets download -d <dataset-id>`.
- **Public URL / GitHub**: Direct streaming of raw CSV files.

---

## 2. Dataset Format Requirements
Save your custom training dataset to `backend/data/ai_detection_dataset.csv` with the following columns:

```csv
text,label
"Students' genuine lab report text...",0
"LLM-generated synthetic academic text...",1
```

- **`0`**: Human / Authentic student writing (or peer-to-peer plagiarized human text)
- **`1`**: AI-generated text (ChatGPT, Claude, Gemini, GPT-4, LLaMA, etc.)

---

## 3. Local CLI Retraining Workflow
From the `backend/` directory:

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Extract features (Perplexity, Burstiness, Stylometrics)
python scripts/extract_features.py

# 3. Train classifier & update model registry
python scripts/train_ai_detector.py

# 4. Evaluate across benchmarks
python scripts/evaluate_models.py
```

