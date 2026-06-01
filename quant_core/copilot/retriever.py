"""Lexical retrieval over copilot chunks (TF-IDF style, no extra deps)."""

from __future__ import annotations

import math
from collections import Counter

from quant_core.copilot.indexer import tokenize
from quant_core.copilot.models import CopilotChunk, RetrievedChunk


def _doc_freq(chunks: list[CopilotChunk]) -> Counter[str]:
    df: Counter[str] = Counter()
    for chunk in chunks:
        for term in set(tokenize(chunk.text)):
            df[term] += 1
    return df


def _tfidf_vector(terms: Counter[str], df: Counter[str], n_docs: int) -> dict[str, float]:
    vec: dict[str, float] = {}
    for term, tf in terms.items():
        idf = math.log((1 + n_docs) / (1 + df.get(term, 0))) + 1.0
        vec[term] = (1 + math.log(tf)) * idf
    return vec


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a.get(k, 0.0) * b.get(k, 0.0) for k in set(a) | set(b))
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def retrieve(
    question: str,
    chunks: list[CopilotChunk],
    *,
    top_k: int = 5,
) -> list[RetrievedChunk]:
    if not chunks:
        return []
    df = _doc_freq(chunks)
    n_docs = max(len(chunks), 1)
    q_vec = _tfidf_vector(Counter(tokenize(question)), df, n_docs)
    scored: list[RetrievedChunk] = []
    for chunk in chunks:
        t_vec = _tfidf_vector(Counter(tokenize(chunk.text)), df, n_docs)
        score = _cosine(q_vec, t_vec)
        if score > 0:
            scored.append(RetrievedChunk(chunk=chunk, score=score))
    scored.sort(key=lambda r: r.score, reverse=True)
    return scored[:top_k]
