"""LLM providers: mock (default), Ollama, OpenAI."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from quant_core.copilot.models import RetrievedChunk

SYSTEM_PROMPT = (
    "You are the Crypto Quant Nexus copilot. Answer using ONLY the provided context. "
    "Cite trace_id, symbol, or model_id when relevant. "
    "This is research infrastructure — not investment advice. "
    "If context is insufficient, say what is missing."
)


def provider_name() -> str:
    return os.getenv("COPILOT_LLM_PROVIDER", "mock").strip().lower()


def _format_context(chunks: list[RetrievedChunk]) -> str:
    blocks = []
    for i, hit in enumerate(chunks, start=1):
        meta = hit.chunk.metadata
        meta_str = ", ".join(f"{k}={v}" for k, v in meta.items() if v is not None)
        blocks.append(
            f"[{i}] source={hit.chunk.source_type} score={hit.score:.3f} {meta_str}\n"
            f"{hit.chunk.text[:1200]}"
        )
    return "\n\n".join(blocks)


def _mock_answer(question: str, chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return (
            "No indexed context found. Run POST /v2/copilot/index after generating "
            "audit events, inference logs, or backtests."
        )
    lines = [f"Question: {question}", "", "Summary from retrieved platform records:"]
    for hit in chunks:
        c = hit.chunk
        meta = c.metadata
        headline = meta.get("trace_id") or meta.get("model_id") or meta.get("symbol") or c.source_type
        snippet = c.text[:280].replace("\n", " ")
        lines.append(f"- [{c.source_type}] {headline} (relevance {hit.score:.2f}): {snippet}…")
    lines.append("")
    lines.append("Use cited trace_ids in /v2/audit/verify or Ops Dashboard for drill-down.")
    return "\n".join(lines)


def _ollama_answer(question: str, context: str) -> str:
    base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "llama3.2")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}",
            },
        ],
        "stream": False,
    }
    req = urllib.request.Request(
        f"{base}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body.get("message", {}).get("content", str(body))


def _openai_answer(question: str, context: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}",
            },
        ],
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body["choices"][0]["message"]["content"]


def generate_answer(question: str, chunks: list[RetrievedChunk]) -> tuple[str, str]:
    provider = provider_name()
    context = _format_context(chunks)
    if provider == "mock":
        return _mock_answer(question, chunks), provider
    try:
        if provider == "ollama":
            return _ollama_answer(question, context), provider
        if provider == "openai":
            return _openai_answer(question, context), provider
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, ValueError) as exc:
        fallback = _mock_answer(question, chunks)
        return f"{fallback}\n\n(LLM provider '{provider}' failed: {exc})", "mock"
    return _mock_answer(question, chunks), "mock"


def sources_payload(chunks: list[RetrievedChunk]) -> list[dict[str, Any]]:
    out = []
    for hit in chunks:
        out.append(
            {
                "chunk_id": hit.chunk.chunk_id,
                "source_type": hit.chunk.source_type,
                "score": round(hit.score, 4),
                "metadata": hit.chunk.metadata,
                "excerpt": hit.chunk.text[:400],
            }
        )
    return out
