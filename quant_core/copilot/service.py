"""Copilot orchestration — index, retrieve, answer."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from quant_core.copilot import indexer as indexer_mod
from quant_core.copilot.indexer import load_index, rebuild_index as _rebuild


def _index_path(override: Path | None = None) -> Path:
    return override or indexer_mod.INDEX_PATH
from quant_core.copilot.llm import generate_answer, provider_name, sources_payload
from quant_core.copilot.models import CopilotAnswer
from quant_core.copilot.retriever import retrieve


def copilot_status(index_path: Path | None = None) -> dict[str, Any]:
    path = _index_path(index_path)
    chunks, meta = load_index(path)
    return {
        "provider": provider_name(),
        "indexed": path.exists(),
        "chunk_count": len(chunks),
        "built_at": meta.get("built_at"),
        "index_path": str(path),
    }


def rebuild_index(index_path: Path | None = None) -> dict[str, Any]:
    path = _index_path(index_path)
    result = _rebuild(path)
    return {**result, "provider": provider_name()}


def ask(
    question: str,
    *,
    top_k: int = 5,
    index_path: Path | None = None,
    auto_index: bool = True,
) -> CopilotAnswer:
    path = _index_path(index_path)
    chunks, _ = load_index(path)
    if not chunks and auto_index:
        rebuild_index(path)
        chunks, _ = load_index(path)
    hits = retrieve(question, chunks, top_k=top_k)
    answer_text, used_provider = generate_answer(question, hits)
    trace_id = str(uuid.uuid4())
    return CopilotAnswer(
        answer=answer_text,
        sources=sources_payload(hits),
        provider=used_provider,
        trace_id=trace_id,
        chunks_used=len(hits),
    )
