# Quick Start - Model Testing

Get started testing AcademicGuard models in 2 minutes.

## One-Command Setup

```bash
cd backend
python scripts/test_models_standalone.py
```

That's it! This will:
- ✓ Test AI detection (Neural Perplexity + Stylometry)
- ✓ Test text similarity (Semantic Embeddings + TF-IDF)
- ✓ Test code similarity (AST-based normalization)
- ✓ Verify all research-validated functionality

## What Gets Tested

### 1. AI Detection
- Sentence length analysis
- Lexical diversity (type-token ratio)
- Punctuation patterns
- Distinguishes human vs AI writing styles

### 2. Code Similarity
- Python AST parsing
- Variable/function name normalization
- Structural comparison
- Detects copied code even with renamed variables

### 3. Sample Data
- 5 realistic student submissions
- Known similarity patterns
- Tests edge cases (identical, paraphrased, different)

## Test Results

```
✓ AI detection features working
✓ Code similarity detection working
✓ Sample data tests complete
✓ ALL TESTS PASSED
```

## Next Steps

### For Development
```bash
# Run with verbose output
python scripts/test_models_standalone.py

# Create more test data
python scripts/create_test_data.py
```

### For Production Training
```bash
# 1. Expand training dataset
# Edit: data/ai_detection_dataset.csv (add 1000+ samples)

# 2. Extract features
python scripts/extract_features.py

# 3. Train model
python scripts/train_ai_detector.py
```

### For Full System Testing
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run unit tests
pytest tests/test_models.py -v
```

## Files Created

```
backend/
├── data/
│   ├── ai_detection_dataset.csv     # 10 sample texts (5 human, 5 AI)
│   └── test_submissions.json        # 5 realistic submissions
├── scripts/
│   ├── test_models_standalone.py    # ← Main test script
│   ├── create_test_data.py          # Generate test data
│   ├── extract_features.py          # Feature extraction
│   └── train_ai_detector.py         # Model training
└── tests/
    └── test_models.py               # Unit tests
```

## Troubleshooting

### "No such file or directory"
Make sure you're in the `backend/` directory:
```bash
cd backend
python scripts/test_models_standalone.py
```

### "Module not found"
The standalone script has no dependencies beyond Python stdlib. If you see this error, check your Python version:
```bash
python --version  # Should be 3.11+
```

### Tests fail
Check the error message. Common issues:
- Syntax errors in test data
- Missing data files (run `create_test_data.py`)
- Python version < 3.11

## See Also

- `../RESEARCH_METHODOLOGY.md` - Technical methodology & mathematical foundations
- `MODEL_TESTING.md` - Complete testing guide
- `TRANSFORMERS_ENABLED.md` - Neural model configuration guide
- `../README.md` - System setup
