#!/bin/bash
# setup_models.sh — Automated model testing setup
# Run: chmod +x scripts/setup_models.sh && ./scripts/setup_models.sh

set -e  # Exit on error

echo "=========================================="
echo "AcademicGuard - Model Setup"
echo "=========================================="

# Check if we're in the backend directory
if [ ! -f "requirements.txt" ]; then
    echo "Error: Must run from backend/ directory"
    echo "Usage: cd backend && bash scripts/setup_models.sh"
    exit 1
fi

# Create directories
echo ""
echo "Creating directories..."
mkdir -p models data tests scripts

# Create test data
echo ""
echo "Creating test data..."
python scripts/create_test_data.py

# Run manual tests
echo ""
echo "Running manual tests..."
python scripts/test_models_manual.py

# Run unit tests if pytest is available
echo ""
echo "Running unit tests..."
if command -v pytest &> /dev/null; then
    pytest tests/test_models.py -v
else
    echo "⚠ pytest not found, skipping unit tests"
    echo "Install with: pip install pytest pytest-asyncio"
fi

echo ""
echo "=========================================="
echo "✓ Model setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Review test results above"
echo "  2. Expand data/ai_detection_dataset.csv with more samples"
echo "  3. Run: python scripts/train_ai_detector.py"
echo "  4. See MODEL_TESTING.md for detailed guide"
echo ""
