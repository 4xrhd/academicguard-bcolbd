"""
test_pdf_visual.py — Generate visual demo PDFs for Enterprise originality report and batch report.
"""
import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from app.reports import pdf_gen


class MockBatch:
    def __init__(self):
        self.id = uuid.uuid4()
        self.name = "Advanced Natural Language Processing — Assignment 2"
        self.course_code = "CSE482"
        self.status = "done"
        self.uploaded_at = datetime.now(timezone.utc)
        self.completed_at = datetime.now(timezone.utc)
        self.total_marks = 100.0
        self.marking_config = {
            "ai_threshold": 0.5,
            "ai_deduction": 15.0,
            "text_sim_threshold": 0.4,
            "text_sim_deduction": 20.0,
            "code_sim_threshold": 0.5,
            "code_sim_deduction": 10.0,
        }
        self.instructor = MagicMock()
        self.instructor.full_name = "Dr. Katherine Johnson"
        self.submissions = []


class MockSubmission:
    def __init__(self, batch, student_id, name, text, code_blocks=None):
        self.id = uuid.uuid4()
        self.batch_id = batch.id
        self.batch = batch
        self.student_id = student_id
        self.student_name = name
        self.raw_text = text
        self.code_blocks = code_blocks or []
        self.created_at = datetime.now(timezone.utc)
        self.marks_obtained = None
        self.marks_breakdown = None

        self.risk_score = MagicMock()
        self.risk_score.weighted_score = 0.74
        self.risk_score.text_sim_max = 0.68
        self.risk_score.code_sim_max = 0.82 if code_blocks else None
        self.risk_score.ai_prob = 0.89
        self.risk_score.risk_level = "high"
        self.risk_score.weight_profile = "code_present" if code_blocks else "theory_only"

        self.ai_result = MagicMock()
        self.ai_result.perplexity_score = 9.8
        self.ai_result.burstiness_score = 3.1
        self.ai_result.stylometric_score = 0.82
        self.ai_result.final_ai_prob = 0.89
        self.ai_result.source = "fused"

    @property
    def has_code(self):
        return bool(self.code_blocks and len(self.code_blocks) > 0)


class MockPair:
    def __init__(self, sub_a_id, sub_b_id, fused, direction="a_to_b"):
        self.sub_a_id = sub_a_id
        self.sub_b_id = sub_b_id
        self.text_sim_fused = fused
        self.copy_direction = direction


async def run_visual_demo():
    batch = MockBatch()
    
    sample_text = (
        "Transformer models rely on the self-attention mechanism to capture global contextual dependencies across input sequences without sequential recurrence. "
        "The multi-head attention formulation projects queries, keys, and values into multiple representation subspaces, enabling the model to jointly attend to information from different positions. "
        "Position-wise feed-forward networks apply non-linear transformations independently at each position, consisting of two linear transformations with a ReLU or GELU activation in between. "
        "Layer normalization and residual connections are applied around each sub-layer to stabilize gradient flow during deep backpropagation training.\n\n"
        "In our empirical evaluation, we analyzed the token log-probability distributions produced by autoregressive language models. "
        "Perplexity measures the inverse geometric mean of the token probabilities, where lower values indicate that the language model finds the generated text predictable and characteristic of automated generative completion. "
        "Burstiness evaluates the sentence-level standard deviation of perplexity, as human writing exhibits high variance in sentence structure and complexity, whereas machine text maintains consistent statistical uniformity.\n\n"
        "We implemented the semantic similarity pipeline using sentence-transformers with the all-MiniLM-L6-v2 dense embedding model, combined with TF-IDF cosine similarity matrices. "
        "The resulting similarity matrix highlights direct copy-paste plagiarism as well as sophisticated paraphrase obfuscation across student submissions."
    )

    sample_code = [
        "def compute_attention(query, key, value, mask=None):\n"
        "    d_k = query.size(-1)\n"
        "    scores = torch.matmul(query, key.transpose(-2, -1)) / math.sqrt(d_k)\n"
        "    if mask is not None:\n"
        "        scores = scores.masked_fill(mask == 0, -1e9)\n"
        "    p_attn = F.softmax(scores, dim=-1)\n"
        "    return torch.matmul(p_attn, value), p_attn",
        
        "class MultiHeadedAttention(nn.Module):\n"
        "    def __init__(self, h, d_model, dropout=0.1):\n"
        "        super().__init__()\n"
        "        self.d_k = d_model // h\n"
        "        self.h = h\n"
        "        self.linears = nn.ModuleList([nn.Linear(d_model, d_model) for _ in range(4)])"
    ]

    sub = MockSubmission(batch, "300012001", "Marcus Vance", sample_text, sample_code)
    sub2 = MockSubmission(batch, "300012002", "Elena Rostova", "Peer text...", [])
    sub3 = MockSubmission(batch, "300012003", "David Chen", "Peer text 2...", [])
    batch.submissions = [sub, sub2, sub3]

    pair1 = MockPair(sub.id, sub2.id, 0.68, "a_to_b")
    pair2 = MockPair(sub.id, sub3.id, 0.44, "mutual")

    mock_db = AsyncMock()
    # Submission report mock returns
    mock_db_res1 = MagicMock()
    mock_db_res1.scalar_one_or_none.return_value = sub
    mock_db_res2 = MagicMock()
    mock_db_res2.scalars().all.return_value = [pair1, pair2]
    mock_db_res3 = MagicMock()
    mock_db_res3.scalars().all.return_value = [sub2, sub3]

    mock_db.execute.side_effect = [mock_db_res1, mock_db_res2, mock_db_res3]

    sub_pdf = await pdf_gen.generate_submission_report(sub.id, mock_db)
    print(f"Generated Enterprise originality report: {sub_pdf} (Size: {sub_pdf.stat().st_size} bytes)")

    # Batch report mock returns
    mock_db_batch = MagicMock()
    mock_db_batch.scalar_one_or_none.return_value = batch
    mock_db.execute.side_effect = None
    mock_db.execute.return_value = mock_db_batch

    batch_pdf = await pdf_gen.generate_batch_report(batch.id, mock_db)
    print(f"Generated Classroom Batch Audit Report: {batch_pdf} (Size: {batch_pdf.stat().st_size} bytes)")


if __name__ == "__main__":
    asyncio.run(run_visual_demo())
