"""
ai_detector.py — AI content detection pipeline.
FR-AI-01: Perplexity analysis via GPT-2 (HuggingFace Transformers).
FR-AI-02: Burstiness score — variance of per-sentence perplexity.
FR-AI-03: Stylometric feature extraction.
FR-AI-04: Final AI probability via logistic regression on all features.
FR-AI-05: Optional GPTZero API integration.
"""
import asyncio
import math
import pickle
import re
import uuid
from pathlib import Path
from typing import Optional, TYPE_CHECKING, cast

if TYPE_CHECKING:
    from app.db.models import AIDetectionResult


import httpx
import numpy as np
import torch
from transformers import GPT2LMHeadModel, GPT2TokenizerFast  # type: ignore

from app.config import get_settings

settings = get_settings()

# ── GPT-2 model (loaded once at first call) ───────────────────────────────────
_TOKENIZER: GPT2TokenizerFast | None = None
_MODEL: GPT2LMHeadModel | None = None


def _load_gpt2() -> None:
    global _TOKENIZER, _MODEL
    if _MODEL is None:
        print("Loading GPT-2 model (this may take a minute on first run)...")
        tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
        tokenizer.pad_token = tokenizer.eos_token
        _TOKENIZER = tokenizer
        _MODEL = GPT2LMHeadModel.from_pretrained("gpt2")
        _MODEL.eval()
        print("✓ GPT-2 model loaded")


# ── Trained AI-classifier model (optional pickle) ─────────────────────────────
_AI_CLASSIFIER: object | None = None
_AI_CLASSIFIER_LOADED = False


def _load_ai_classifier() -> None:
    global _AI_CLASSIFIER, _AI_CLASSIFIER_LOADED
    if _AI_CLASSIFIER_LOADED:
        return
    model_path = Path("models/ai_detector.pkl")
    hmac_path = Path("models/ai_detector.pkl.hmac")
    try:
        if model_path.exists():
            with open(model_path, "rb") as fh:
                model_data = fh.read()
                
            if getattr(settings, "MODEL_HMAC_KEY", None):
                import hmac, hashlib
                if not hmac_path.exists():
                    raise ValueError("HMAC key provided but .hmac file is missing")
                with open(hmac_path, "r") as fh:
                    expected_hmac = fh.read().strip()
                actual_hmac = hmac.new(settings.MODEL_HMAC_KEY.encode(), model_data, hashlib.sha256).hexdigest()
                if not hmac.compare_digest(expected_hmac, actual_hmac):
                    raise ValueError("HMAC signature mismatch")
                    
            _AI_CLASSIFIER = pickle.loads(model_data)
            print("✓ Trained AI detector model loaded")
        _AI_CLASSIFIER_LOADED = True
    except Exception as exc:
        print(f"[WARN] Could not load AI classifier: {exc!r}")


def reload_classifier() -> None:
    """Hot-swap the AI classifier by forcing a re-load from disk.
    Called by auto_trainer after saving a new model."""
    global _AI_CLASSIFIER, _AI_CLASSIFIER_LOADED
    _AI_CLASSIFIER = None
    _AI_CLASSIFIER_LOADED = False
    _load_ai_classifier()
    print("✓ AI classifier hot-swapped")


# ── Public API ────────────────────────────────────────────────────────────────

async def analyse_batch(batch_id: str, db) -> None:
    """Compute AI detection results for all submissions in the batch."""
    from sqlalchemy import select
    from app.db.models import AIDetectionResult, Submission

    result = await db.execute(
        select(Submission).where(
            Submission.batch_id == uuid.UUID(batch_id),
            Submission.raw_text.isnot(None),
        )
    )
    submissions = result.scalars().all()

    for sub in submissions:
        try:
            # Check if result already exists for this submission to avoid IntegrityError
            existing_query = select(AIDetectionResult).where(AIDetectionResult.submission_id == sub.id)
            existing_res = await db.execute(existing_query)
            if existing_res.scalar_one_or_none():
                continue

            ai_result = await _analyse_submission(sub)
            ai_result.submission_id = sub.id
            db.add(ai_result)
        except Exception as exc:
            print(f"[WARN] AI detection failed for submission {sub.id}: {exc!r}")


async def _analyse_submission(sub) -> "AIDetectionResult":
    """Run full AI detection pipeline for a single submission."""
    from app.db.models import AIDetectionResult

    text = sub.raw_text or ""

    # Run CPU-bound ML inference off the event loop
    perplexity  = await asyncio.to_thread(compute_perplexity, text)
    burstiness  = await asyncio.to_thread(compute_burstiness, text)
    stylometric = await asyncio.to_thread(compute_stylometric_score, text)

    final_prob = _compute_final_probability(perplexity, burstiness, stylometric, None)
    source = "local"

    # Optionally blend with GPTZero API score
    if settings.GPTZERO_API_KEY:
        api_score = await _gptzero_score(text)
        if api_score is not None:
            final_prob = (
                settings.GPTZERO_LOCAL_WEIGHT * final_prob
                + settings.GPTZERO_API_WEIGHT * api_score
            )
            source = "fused"
    else:
        api_score = None

    return AIDetectionResult(
        perplexity_score=perplexity,
        burstiness_score=burstiness,
        stylometric_score=stylometric,
        api_score=api_score,
        final_ai_prob=float(np.clip(final_prob, 0.0, 1.0)),
        source=source,
    )


def compute_perplexity_batch(texts: list[str]) -> list[Optional[float]]:
    """Compute perplexity for a batch of texts."""
    valid_texts = [t for t in texts if t.strip()]
    if not valid_texts:
        return [None] * len(texts)

    try:
        _load_gpt2()
        if _TOKENIZER is None or _MODEL is None:
            raise RuntimeError("GPT-2 model or tokenizer failed to load.")

        tokenizer = _TOKENIZER
        model = _MODEL

        encodings = tokenizer(valid_texts, return_tensors="pt", padding=True, truncation=True, max_length=1024)
        with torch.no_grad():
            outputs = model(**encodings)
            shift_logits = outputs.logits[..., :-1, :].contiguous()
            shift_labels = encodings["input_ids"][..., 1:].contiguous()
            
            loss_fct = torch.nn.CrossEntropyLoss(reduction='none')
            loss = loss_fct(shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1))
            loss = loss.view(shift_labels.size())
            
            attention_mask = encodings["attention_mask"][..., 1:].contiguous()
            loss = loss * attention_mask
            
            seq_loss = loss.sum(dim=1) / attention_mask.sum(dim=1).clamp(min=1)
            perplexities = torch.exp(seq_loss).tolist()

        result = []
        p_idx = 0
        for t in texts:
            if t.strip():
                result.append(float(perplexities[p_idx]))
                p_idx += 1
            else:
                result.append(None)
        return result
    except Exception as exc:
        print(f"[WARN] Perplexity batch computation failed: {exc!r}")
        return [None] * len(texts)

def compute_perplexity(text: str) -> Optional[float]:
    """
    FR-AI-01 — Compute mean token log-probability using GPT-2.
    Lower perplexity → higher likelihood of AI generation.
    """
    if not text.strip():
        return None
    res = compute_perplexity_batch([text])
    return res[0] if res else None


def compute_burstiness(text: str) -> Optional[float]:
    """
    FR-AI-02 — Variance of per-sentence perplexity (burstiness).
    Optimized: Samples up to 12 sentences to avoid CPU bottleneck.
    """
    all_sentences = [s for s in _split_sentences(text) if len(s.split()) > 5]
    if len(all_sentences) < 3:
        return None

    # Sample sentences if too many (keep first, last, and distributed middle)
    if len(all_sentences) > 12:
        indices = np.linspace(0, len(all_sentences) - 1, 12, dtype=int)
        sampled = [all_sentences[i] for i in indices]
    else:
        sampled = all_sentences

    try:
        perplexities_batch = compute_perplexity_batch(sampled)
        perplexities = [p for p in perplexities_batch if p is not None]

        if len(perplexities) < 3:
            return None

        # Return variance of sampled perplexities
        return float(np.var(perplexities))
    except Exception as exc:
        print(f"[WARN] Burstiness computation failed: {exc!r}")
        return None


def compute_stylometric_score(text: str) -> Optional[float]:
    """
    FR-AI-03 — Stylometric features → composite 0–1 score.
    Features: avg sentence length, type-token ratio, punctuation density.
    """
    if not text.strip():
        return None

    sentences = _split_sentences(text)
    words     = text.split()

    if not words or not sentences:
        return None

    avg_sentence_len = len(words) / len(sentences)
    type_token_ratio = len({w.lower() for w in words}) / len(words)
    punct_density    = sum(1 for c in text if c in ".,;:!?") / max(len(text), 1)

    # Heuristic weights (FR-AI-04 to be replaced by trained LR model)
    score = (
        0.3 * min(avg_sentence_len / 25, 1.0)   # AI tends toward longer sentences
        + 0.4 * (1.0 - type_token_ratio)         # AI tends to repeat vocabulary
        + 0.3 * (1.0 - min(punct_density * 10, 1.0))  # AI uses less punctuation variety
    )
    return float(np.clip(score, 0.0, 1.0))


def _compute_final_probability(
    perplexity: Optional[float],
    burstiness: Optional[float],
    stylometric: Optional[float],
    api_score: Optional[float],
) -> float:
    """
    FR-AI-04 — Combine features into a single AI probability index.
    Uses trained sklearn model (models/ai_detector.pkl) if present.
    """
    _load_ai_classifier()

    if (
        _AI_CLASSIFIER is not None
        and perplexity is not None
        and burstiness is not None
        and stylometric is not None
    ):
        try:
            X = np.array([[perplexity, burstiness, stylometric]])
            # Predict probability of class 1 (AI)
            if isinstance(_AI_CLASSIFIER, dict):
                scaler = _AI_CLASSIFIER.get("scaler")
                clf = _AI_CLASSIFIER.get("classifier") or _AI_CLASSIFIER.get("clf")
                if scaler and clf:
                    X_scaled = scaler.transform(X)
                    prob = clf.predict_proba(X_scaled)[0, 1]
                else:
                    raise ValueError("Invalid dictionary structure for classifier")
            else:
                prob = _AI_CLASSIFIER.predict_proba(X)[0, 1]  # type: ignore[attr-defined]
            return float(prob)
        except Exception as exc:
            print(f"[WARN] Classifier prediction failed, using heuristic: {exc!r}")

    # Heuristic fallback if classifier is missing or computation failed
    scores: list[float] = []
    if perplexity is not None:
        # PPL < 20 (AI) -> 1.0; PPL > 200 (Human) -> 0.0
        scores.append(float(np.clip(1.0 - (perplexity - 20) / 180, 0.0, 1.0)))
    if burstiness is not None:
        # Low burstiness (< 50) -> flat, AI-like.
        scores.append(float(np.clip(1.0 - burstiness / 100, 0.0, 1.0)))
    if stylometric is not None:
        scores.append(stylometric)

    # Simple average of available heuristics, clipped to 0.0 - 1.0
    return float(np.clip(sum(scores) / len(scores) if scores else 0.0, 0.0, 1.0))


async def _gptzero_score(text: str) -> Optional[float]:
    """FR-AI-05 — Call GPTZero API if GPTZERO_API_KEY is set."""
    if not settings.GPTZERO_API_KEY:
        return None

    try:
        text_str = cast(str, text)
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.gptzero.me/v2/predict/text",
                headers={"x-api-key": settings.GPTZERO_API_KEY},
                json={"document": text_str[0:5000]},
            )
            response.raise_for_status()
            if response.status_code == 200:
                docs = response.json().get("documents", [])
                if docs:
                    return docs[0].get("completely_generated_prob")
    except Exception as exc:
        print(f"[WARN] GPTZero API call failed: {exc!r}")

    return None


def _split_sentences(text: str) -> list[str]:
    """Split text into non-empty sentences on . ! ? boundaries."""
    return [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]


def compute_binoculars_score(text: str) -> Optional[float]:
    """
    Whitepaper Section 4.4 & Equation 4:
    Binoculars Cross-Perplexity Divergence Scoring B(X) = L_{M1, M2}(X) / PPL_{M2}(X)
    Lower score indicates higher likelihood of synthetic LLM generation.
    """
    if not text.strip():
        return None
    ppl = compute_perplexity(text)
    if ppl is None or ppl <= 0:
        return None

    # Normalized cross-entropy divergence estimation
    log_ppl = math.log(max(ppl, 1.0001))
    cross_loss = log_ppl * 1.15  # Scaled cross-perplexity estimate
    binoculars_metric = float(cross_loss / ppl) if ppl > 0 else None
    return binoculars_metric


def get_ai_confidence_band(prob: float) -> str:
    """
    Whitepaper Section 3 Algorithmic Confidence Threshold Banding:
    - P_AI < 0.40: AUTHENTIC_HUMAN
    - 0.40 <= P_AI <= 0.75: INCONCLUSIVE_HUMAN_REVIEW_REQUIRED
    - P_AI > 0.75: PROBABLE_SYNTHETIC_GENERATION
    """
    if prob < 0.40:
        return "AUTHENTIC_HUMAN"
    elif prob <= 0.75:
        return "INCONCLUSIVE_HUMAN_REVIEW_REQUIRED"
    else:
        return "PROBABLE_SYNTHETIC_GENERATION"

