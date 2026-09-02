"""
text_similarity.py — NLP text similarity pipeline.
FR-SIM-01: TF-IDF cosine similarity via sklearn.
FR-SIM-02: Semantic similarity via all-MiniLM-L6-v2 Sentence-Transformers.
FR-SIM-03: Fused score = 0.4 × tfidf + 0.6 × semantic.
"""
import os
import asyncio
import uuid
from typing import List

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

from app.config import get_settings

settings = get_settings()

from typing import Any

# ── Model (loaded once at module level to avoid repeated warm-up) ─────────────
_MODEL: SentenceTransformer | None = None
_LEMMATIZER: Any = None
_STOPWORDS: set | None = None

def _get_model() -> SentenceTransformer:
    global _MODEL
    if _MODEL is None:
        print("Loading Sentence-Transformer model (this may take a minute)...")
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        print("✓ Sentence-Transformer model loaded")
    return _MODEL

def preload_models():
    """Eagerly load models and NLTK resources."""
    _get_model()
    _get_nltk_resources()

class DummyLemmatizer:
    def lemmatize(self, word: str) -> str:
        return word

def _get_nltk_resources():
    global _LEMMATIZER, _STOPWORDS
    if _LEMMATIZER is None or _STOPWORDS is None:
        try:
            _LEMMATIZER = WordNetLemmatizer()
            # Test if lemmatizer works
            _LEMMATIZER.lemmatize("testing")
            _STOPWORDS = set(stopwords.words('english'))
        except Exception:
            print("NLTK resources not fully available locally. Attempting download...")
            try:
                os.environ["NLTK_ALLOW_PROXIED_URLOPEN"] = "1"
                nltk.download('stopwords', quiet=True)
                nltk.download('wordnet', quiet=True)
                nltk.download('punkt', quiet=True)
                nltk.download('punkt_tab', quiet=True)
                _LEMMATIZER = WordNetLemmatizer()
                _STOPWORDS = set(stopwords.words('english'))
            except Exception as e:
                print(f"NLTK download failed or offline. Using robust fallback resources: {e}")
                _LEMMATIZER = DummyLemmatizer()
                _STOPWORDS = {
                    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", 
                    "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers", 
                    "herself", "it", "its", "itself", "they", "them", "their", "theirs", "themselves", 
                    "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are", 
                    "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does", 
                    "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as", "until", 
                    "while", "of", "at", "by", "for", "with", "about", "against", "between", "into", 
                    "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", 
                    "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here", 
                    "there", "when", "where", "why", "how", "all", "any", "both", "each", "few", "more", 
                    "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", 
                    "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now"
                }
    return _LEMMATIZER, _STOPWORDS


async def compute_batch(batch_id: str, db) -> None:
    """
    Compute pairwise text similarity for all submissions in the batch.
    Results stored in similarity_results table.
    Uses ProcessPoolExecutor for CPU-bound inference (NFR-SCAL).
    """
    from sqlalchemy import select, delete
    from app.db.models import Submission, SimilarityResult

    # Clear existing results for this batch to ensure idempotency
    await db.execute(
        delete(SimilarityResult).where(SimilarityResult.batch_id == uuid.UUID(batch_id))
    )

    result = await db.execute(
        select(Submission).where(
            Submission.batch_id == uuid.UUID(batch_id),
            Submission.raw_text.isnot(None),
        )
    )
    submissions = result.scalars().all()
    if len(submissions) < 2:
        return

    texts = [sub.raw_text or "" for sub in submissions]
    ids   = [sub.id for sub in submissions]

    # Compute TF-IDF similarity matrix (CPU-bound, run off event loop)
    tfidf_matrix = await asyncio.to_thread(_compute_tfidf, texts)

    # Compute semantic similarity matrix (CPU-bound, run off event loop)
    semantic_matrix = await asyncio.to_thread(_compute_semantic, texts)

    # Fuse scores and persist pairwise results
    n = len(submissions)
    for i in range(n):
        for j in range(i + 1, n):
            tfidf_score = 0.0
            if tfidf_matrix is not None:
                # Index into the matrix only after checking it's not None
                row = tfidf_matrix[i]
                tfidf_score = float(row[j])
            
            semantic_score = 0.0
            if semantic_matrix is not None:
                row_sem = semantic_matrix[i]
                semantic_score = float(row_sem[j])

            fused     = settings.TFIDF_WEIGHT * tfidf_score + settings.SEMANTIC_WEIGHT * semantic_score
            direction = _infer_copy_direction(submissions[i], submissions[j], tfidf_score, semantic_score)

            sim = SimilarityResult(
                batch_id=uuid.UUID(batch_id),
                sub_a_id=ids[i],
                sub_b_id=ids[j],
                tfidf_score=tfidf_score,
                semantic_score=semantic_score,
                text_sim_fused=fused,
                copy_direction=direction,
            )
            db.add(sim)


def _compute_tfidf(texts: List[str]) -> List[List[float]] | None:
    """
    FR-SIM-01 — TF-IDF vectorization + pairwise cosine similarity.
    Preprocessing: lowercase, stopword removal, lemmatization (NLTK).
    """
    try:
        preprocessed = [_preprocess(t) for t in texts]
        if not any(t.strip() for t in preprocessed):
            n = len(texts)
            return [[0.0] * n for _ in range(n)]
            
        vectorizer = TfidfVectorizer(
            max_features=10_000,
            ngram_range=(1, 2),  # Unigrams + bigrams
            min_df=1,
            sublinear_tf=True,
            stop_words='english'
        )
        tfidf_matrix = vectorizer.fit_transform(preprocessed)
        similarity = cosine_similarity(tfidf_matrix)
        return similarity.tolist()
    except Exception as e:
        print(f"Warning: TF-IDF computation failed: {e}")
        return None


def _compute_semantic(texts: List[str]) -> List[List[float]] | None:
    """
    FR-SIM-02 — Sentence-Transformer 384-dim embeddings + cosine similarity.
    Model: all-MiniLM-L6-v2 (pre-downloaded into Docker image at build time).
    """
    try:
        model = _get_model()
        embeddings = model.encode(texts, convert_to_tensor=True)
        similarity = cosine_similarity(embeddings.cpu().numpy())
        return similarity.tolist()
    except Exception as e:
        print(f"Warning: Semantic similarity computation failed: {e}")
        return None


def _preprocess(text: str) -> str:
    """Lowercase, remove stopwords, lemmatize using NLTK."""
    try:
        lemmatizer, stopwords_set = _get_nltk_resources()
        
        # Lowercase and tokenize
        text = text.lower()
        words = text.split()
        
        # Remove stopwords and lemmatize
        words = [
            lemmatizer.lemmatize(word) 
            for word in words 
            if word.isalnum() and word not in stopwords_set
        ]
        
        return ' '.join(words)
    except Exception as e:
        print(f"Warning: Preprocessing failed, using simple lowercase: {e}")
        return text.lower()


def _infer_copy_direction(sub_a, sub_b, tfidf: float, semantic: float) -> str:
    """
    FR-SIM-03 — Infer copy direction based on text length proxy.

    Logic:
    - If scores are low (< 0.3), direction is unknown.
    - Shorter submission is as original (Source); longer is Copier.
      (Rationale: a copier typically summarizes or adds padding).
    - If lengths are nearly identical (within 2%), we label as "mutual".
    """
    fused = settings.TFIDF_WEIGHT * tfidf + settings.SEMANTIC_WEIGHT * semantic
    if fused < 0.3:
        return "unknown"

    len_a = len(sub_a.raw_text or "")
    len_b = len(sub_b.raw_text or "")

    # Mutual if lengths are extremely close (within 2% and both fairly long)
    if abs(len_a - len_b) < (0.02 * max(len_a, len_b)):
        return "mutual"

    # Shorter text → likely the Source (Original)
    # If A is shorter, direction is a -> b
    return "a_to_b" if len_a < len_b else "b_to_a"


# ── Sub-Linear Scaling: MinHash Locality-Sensitive Hashing (LSH) ───────────────
# Whitepaper Section 4.5 & Equation 6: M = b * r = 128, b = 16 bands, r = 8 rows
_HASH_PRIME = 4294967311
_NUM_PERM = 128
_BANDS = 16
_ROWS = 8

# Deterministic random seed coefficients for reproducible MinHash permutations
np.random.seed(42)
_A_COEFFS = np.random.randint(1, _HASH_PRIME - 1, size=_NUM_PERM, dtype=np.int64)
_B_COEFFS = np.random.randint(0, _HASH_PRIME - 1, size=_NUM_PERM, dtype=np.int64)


import binascii

def compute_minhash_signature(text: str, k: int = 2) -> np.ndarray:
    """
    Whitepaper Section 4.5: Generate M=128 MinHash signature vector from k-shingles.
    """
    tokens = text.lower().split()
    if len(tokens) < k:
        shingles = [" ".join(tokens)] if tokens else [""]
    else:
        shingles = [" ".join(tokens[i:i+k]) for i in range(len(tokens) - k + 1)]

    # Hash shingles to 32-bit integers deterministically using crc32
    shingle_hashes = np.array([binascii.crc32(s.encode('utf-8')) for s in shingles], dtype=np.int64)
    if len(shingle_hashes) == 0:
        shingle_hashes = np.array([0], dtype=np.int64)

    # Compute min hash values across permutations: h_i(x) = (a * x + b) % p
    hash_matrix = (_A_COEFFS[:, None] * shingle_hashes[None, :] + _B_COEFFS[:, None]) % _HASH_PRIME
    signatures = np.min(hash_matrix, axis=1)
    return signatures


def minhash_lsh_filter(signatures: list[np.ndarray], b: int = 32, r: int = 4) -> set[tuple[int, int]]:
    """
    Whitepaper Equation 6: MinHash LSH Candidate Pairing.
    P_candidate = 1 - (1 - J(D_1, D_2)^r)^b
    Partitions M=128 signatures into bands. Default b=32 bands of r=4 rows.
    """
    buckets: dict[tuple[int, int], list[int]] = {}
    candidate_pairs: set[tuple[int, int]] = set()

    for doc_idx, sig in enumerate(signatures):
        for band_idx in range(b):
            start = band_idx * r
            end = start + r
            band_tuple = (band_idx, hash(tuple(sig[start:end])))
            if band_tuple in buckets:
                for other_idx in buckets[band_tuple]:
                    pair = (min(doc_idx, other_idx), max(doc_idx, other_idx))
                    candidate_pairs.add(pair)
                buckets[band_tuple].append(doc_idx)
            else:
                buckets[band_tuple] = [doc_idx]

    return candidate_pairs


