"""
code_similarity.py — AST-based multi-language code similarity pipeline.
FR-CODE-01: Parse each code block with Tree-Sitter (C, C++, Java, Python); compare node sequences.
FR-CODE-02: Token normalization — rename all identifiers to canonical tokens via Alpha-Renaming.
FR-CODE-03: Store code_ast_score in similarity_results.code_ast_score.
"""
import difflib
import re
import asyncio
import uuid
from typing import List

import tree_sitter
import tree_sitter_python
import tree_sitter_c
import tree_sitter_cpp
import tree_sitter_java

LANGUAGES = {
    'python': tree_sitter.Language(tree_sitter_python.language()),
    'c': tree_sitter.Language(tree_sitter_c.language()),
    'cpp': tree_sitter.Language(tree_sitter_cpp.language()),
    'java': tree_sitter.Language(tree_sitter_java.language())
}

PARSERS = {name: tree_sitter.Parser(lang) for name, lang in LANGUAGES.items()}

async def compute_batch(batch_id: str, db) -> None:
    """
    For each existing similarity pair in the batch, compute code_ast_score
    from the code_blocks of both submissions and update the record.
    """
    from sqlalchemy import select
    from app.db.models import Submission, SimilarityResult

    sub_result = await db.execute(
        select(Submission).where(Submission.batch_id == uuid.UUID(batch_id))
    )
    submissions = sub_result.scalars().all()
    
    normalized_cache: dict[uuid.UUID, List[List[str]]] = {}
    for sub in submissions:
        normalized_cache[sub.id] = [
            normalize_code(block) for block in (sub.code_blocks or [])
            if block.strip()
        ]

    pairs_result = await db.execute(
        select(SimilarityResult).where(SimilarityResult.batch_id == uuid.UUID(batch_id))
    )
    for pair in pairs_result.scalars().all():
        tokens_a = normalized_cache.get(pair.sub_a_id, [])
        tokens_b = normalized_cache.get(pair.sub_b_id, [])
        
        if tokens_a and tokens_b:
            pair.code_ast_score = await asyncio.to_thread(
                _compute_similarity_from_tokens, tokens_a, tokens_b
            )


def _compute_similarity_from_tokens(tokens_list_a: List[List[str]], tokens_list_b: List[List[str]]) -> float:
    """Compare sets of pre-normalized tokens and return max similarity."""
    best = 0.0
    for ta in tokens_list_a:
        for tb in tokens_list_b:
            score = _sequence_similarity(ta, tb)
            if score > best:
                best = score
            if best >= 1.0:
                return 1.0
    return best


def compute_code_similarity(blocks_a: List[str], blocks_b: List[str]) -> float:
    """
    FR-CODE-01/02 — Compare code blocks from two submissions.
    Tries every combination of blocks from each submission and returns the
    highest pairwise similarity score (0.0–1.0).
    """
    if not blocks_a or not blocks_b:
        return 0.0

    best = 0.0
    for block_a in blocks_a:
        tokens_a = normalize_code(block_a)
        if not tokens_a:
            continue
        for block_b in blocks_b:
            tokens_b = normalize_code(block_b)
            if not tokens_b:
                continue
            score = _sequence_similarity(tokens_a, tokens_b)
            if score > best:
                best = score
            if best >= 1.0:
                return 1.0   # Short-circuit on perfect match
    return best


def normalize_code(source: str) -> List[str]:
    """
    FR-CODE-01/02 — Tokenize a code block into a normalized sequence using Tree-Sitter.
    Dynamically identifies the best grammar (C, C++, Java, Python) by parsing
    and selecting the AST with the fewest syntax errors, then performs Alpha-Renaming.
    """
    if not source or not source.strip():
        return []

    source_bytes = source.encode('utf8', errors='ignore')
    
    best_tree = None
    min_errors = float('inf')

    # Find the language grammar that parses with the fewest errors
    for name, parser in PARSERS.items():
        tree = parser.parse(source_bytes)
        errors = _count_errors(tree.root_node)
        if errors < min_errors:
            min_errors = errors
            best_tree = tree
            if errors == 0:
                break # Perfect parse
                
    if not best_tree:
        return []

    return _ast_tokens(best_tree.root_node)


# ── Private helpers ───────────────────────────────────────────────────────────

def _count_errors(node) -> int:
    """Recursively count ERROR and MISSING nodes in a Tree-Sitter AST."""
    errors = 1 if (node.type == 'ERROR' or node.is_missing) else 0
    for child in node.children:
        errors += _count_errors(child)
    return errors


def _ast_tokens(root_node) -> List[str]:
    """
    Deterministically walk a Tree-Sitter AST and produce a normalized token sequence.
    Performs Identifier Alpha-Renaming (var0, var1...) for Subtree Isomorphism Kernel.
    """
    identifier_map: dict[str, str] = {}
    counter = [0]
    tokens: List[str] = []

    def _visit(node, depth: int = 0):
        if depth > 1000: # safeguard
            return

        # Record named structural nodes or normalize identifiers
        if node.type == 'identifier':
            text = node.text.decode('utf8', errors='ignore')
            if text not in identifier_map:
                identifier_map[text] = f"var{counter[0]}"
                counter[0] += 1
            tokens.append(identifier_map[text])
        elif node.is_named:
            # We use node type to form the structural sequence
            tokens.append(node.type)
            
            # Extract simple literal values if possible
            if 'string' in node.type or 'integer' in node.type or 'number' in node.type:
                val = node.text.decode('utf8', errors='ignore')
                if len(val) < 50:
                    tokens.append(val)

        # Recursively visit children in source order
        for child in node.children:
            _visit(child, depth + 1)

    _visit(root_node, 0)
    return tokens


def _sequence_similarity(seq_a: List[str], seq_b: List[str]) -> float:
    """
    Compute similarity as difflib SequenceMatcher ratio.
    ratio() = 2 * matching_chars / total_chars ≈ Subtree Isomorphism proxy.
    """
    # Cap sequence length to avoid O(N^2) blowup
    MAX_LEN = 10000
    seq_a = seq_a[:MAX_LEN]
    seq_b = seq_b[:MAX_LEN]
    
    if not seq_a and not seq_b:
        return 1.0
    if not seq_a or not seq_b:
        return 0.0
    return difflib.SequenceMatcher(None, seq_a, seq_b).ratio()
