# Model Testing Guide

This guide explains how to test all models in the AcademicGuard system.

## Quick Start

```bash
cd backend

# 1. Create test data
python scripts/create_test_data.py

# 2. Run manual tests (no dependencies on GPT-2/transformers)
python scripts/test_models_manual.py

# 3. Run unit tests
pytest tests/test_models.py -v
```

## Test Structure

### 1. AI Detection Tests
Tests the stylometric feature extraction that detects AI-generated content:
- Sentence length analysis
- Type-token ratio (lexical diversity)
- Punctuation density

**Current Status:** ✓ Working (basic features)
**TODO:** Implement GPT-2 perplexity and burstiness

### 2. Code Similarity Tests
Tests AST-based code comparison:
- Python code parsing
- Token normalization (variable renaming)
- Edit distance similarity

**Current Status:** ✓ Fully working
**TODO:** Add multi-language support (Tree-sitter)

### 3. Text Similarity Tests
Tests text preprocessing pipeline:
- Lowercase normalization
- Content preservation

**Current Status:** ✓ Basic preprocessing working
**TODO:** Implement TF-IDF and Sentence-Transformers

## Test Data

### AI Detection Dataset
Location: `data/ai_detection_dataset.csv`
- 10 samples (5 human, 5 AI-generated)
- Used for feature extraction testing
- Expand to 1000+ samples for production training

### Sample Submissions
Location: `data/test_submissions.json`
- 5 realistic student submissions
- Known similarity patterns:
  - Students 1 & 2: High similarity (paraphrased)
  - Students 1 & 5: Very high similarity (near-duplicate)
  - Students 3 & 4: Low similarity (different topics)

## Running Tests

### Manual Testing (Recommended for Development)
```bash
python scripts/test_models_manual.py
```
This runs all tests with detailed output and doesn't require heavy dependencies.

### Unit Tests (For CI/CD)
```bash
pytest tests/test_models.py -v
```

### Specific Test Classes
```bash
# Test only AI detection
pytest tests/test_models.py::TestAIDetector -v

# Test only code similarity
pytest tests/test_models.py::TestCodeSimilarity -v

# Test integration
pytest tests/test_models.py::TestIntegration -v
```

## Training Models

### AI Detector (Logistic Regression)

**Step 1:** Collect training data
- Minimum 500 samples per class (1000 total)
- Recommended: 3000+ samples
- Format: CSV with columns `text,label` (0=human, 1=AI)

**Step 2:** Extract features
```bash
python scripts/extract_features.py
```
This creates `data/features.csv` with perplexity, burstiness, and stylometric scores.

**Step 3:** Train model
```bash
python scripts/train_ai_detector.py
```
This creates:
- `models/ai_detector.pkl` - Trained model
- `models/model_registry.json` - Model metadata

**Step 4:** Evaluate
The training script outputs:
- Cross-validation ROC-AUC
- Test set classification report
- Confusion matrix

**Minimum acceptable metrics:**
- ROC-AUC ≥ 0.80
- Precision (AI class) ≥ 0.75
- Recall (AI class) ≥ 0.70

## Model Files

```
backend/
├── models/
│   ├── ai_detector.pkl              # Trained AI detector
│   ├── model_registry.json          # Model metadata
│   └── sentence_transformer_finetuned/  # (Optional) Fine-tuned embeddings
├── data/
│   ├── ai_detection_dataset.csv     # Training data
│   ├── features.csv                 # Extracted features
│   └── test_submissions.json        # Test data
├── scripts/
│   ├── create_test_data.py          # Generate test data
│   ├── extract_features.py          # Feature extraction
│   ├── train_ai_detector.py         # Train AI detector
│   └── test_models_manual.py        # Manual testing
└── tests/
    └── test_models.py               # Unit tests
```

## Current Implementation Status

### ✓ Implemented
- [x] Code similarity (Python AST)
- [x] Token normalization
- [x] Stylometric features
- [x] Text preprocessing
- [x] Test data generation
- [x] Unit tests

### ⚠ Partially Implemented (Commented Out)
- [ ] GPT-2 perplexity analysis
- [ ] Burstiness calculation
- [ ] TF-IDF similarity
- [ ] Sentence-Transformer embeddings

### 📋 TODO
- [ ] Multi-language code support (Tree-sitter)
- [ ] Fine-tune Sentence-Transformers
- [ ] GPTZero API integration
- [ ] Model versioning system
- [ ] Performance benchmarks

## Enabling Full Features

To enable GPT-2 and Sentence-Transformers (requires ~2GB RAM):

1. Uncomment imports in `app/engine/ai_detector.py`:
```python
import torch
import numpy as np
from transformers import GPT2LMHeadModel, GPT2TokenizerFast
```

2. Uncomment model loading:
```python
def _load_gpt2():
    global _TOKENIZER, _MODEL
    if _MODEL is None:
        _TOKENIZER = GPT2TokenizerFast.from_pretrained("gpt2")
        _MODEL = GPT2LMHeadModel.from_pretrained("gpt2")
        _MODEL.eval()
```

3. Uncomment implementations in `compute_perplexity()` and `compute_burstiness()`

4. Similarly for `app/engine/text_similarity.py`

## Troubleshooting

### "No module named 'app'"
```bash
# Make sure you're in the backend directory
cd backend
python scripts/test_models_manual.py
```

### "File not found: data/test_submissions.json"
```bash
python scripts/create_test_data.py
```

### "Model file not found"
This is expected - models are trained on-demand. The system works without trained models using fallback heuristics.

### Tests fail with import errors
```bash
# Install dependencies
pip install -r requirements.txt
```

## Next Steps

1. **Expand training data:** Collect 1000+ labeled samples
2. **Train production model:** Run `train_ai_detector.py` with full dataset
3. **Enable transformers:** Uncomment GPT-2 and Sentence-Transformers code
4. **Add multi-language support:** Implement Tree-sitter integration
5. **Benchmark performance:** Measure accuracy on held-out test set

## References

- See `guide-model.md` for complete training guide
- See `README.md` for system setup
- See `documentation/technical/SRS_AcademicGuard_v4.md` for requirements
