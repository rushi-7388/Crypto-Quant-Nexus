"""Build and persist copilot chunk index."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quant_core.copilot.models import CopilotChunk
from quant_core.copilot.sources import collect_all_documents

INDEX_DIR = Path("artifacts/copilot")
INDEX_PATH = INDEX_DIR / "index.json"
CHUNK_CHARS = 900
CHUNK_OVERLAP = 120

_TOKEN_RE = re.compile(r"[a-z0-9_./-]+", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _chunk_text(text: str, base_id: str, source_type: str, metadata: dict[str, Any]) -> list[CopilotChunk]:
    text = " ".join(text.split())
    if len(text) <= CHUNK_CHARS:
        return [
            CopilotChunk(
                chunk_id=f"{base_id}:0",
                source_type=source_type,
                text=text,
                metadata=dict(metadata),
            )
        ]
    chunks: list[CopilotChunk] = []
    start = 0
    idx = 0
    while start < len(text):
        end = min(len(text), start + CHUNK_CHARS)
        piece = text[start:end]
        chunks.append(
            CopilotChunk(
                chunk_id=f"{base_id}:{idx}",
                source_type=source_type,
                text=piece,
                metadata=dict(metadata),
            )
        )
        if end >= len(text):
            break
        start = max(0, end - CHUNK_OVERLAP)
        idx += 1
    return chunks


def build_chunks() -> list[CopilotChunk]:
    all_chunks: list[CopilotChunk] = []
    for doc_idx, (source_type, text, metadata) in enumerate(collect_all_documents()):
        if not text.strip():
            continue
        base_id = f"{source_type}-{doc_idx}"
        all_chunks.extend(_chunk_text(text, base_id, source_type, metadata))
    return all_chunks


def save_index(chunks: list[CopilotChunk], path: Path = INDEX_PATH) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "chunk_count": len(chunks),
        "chunks": [
            {
                "chunk_id": c.chunk_id,
                "source_type": c.source_type,
                "text": c.text,
                "metadata": c.metadata,
            }
            for c in chunks
        ],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {"built_at": payload["built_at"], "chunk_count": len(chunks), "path": str(path)}


def load_index(path: Path = INDEX_PATH) -> tuple[list[CopilotChunk], dict[str, Any]]:
    if not path.exists():
        return [], {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    chunks = [
        CopilotChunk(
            chunk_id=row["chunk_id"],
            source_type=row["source_type"],
            text=row["text"],
            metadata=row.get("metadata", {}),
        )
        for row in payload.get("chunks", [])
    ]
    meta = {"built_at": payload.get("built_at"), "chunk_count": len(chunks), "path": str(path)}
    return chunks, meta


def rebuild_index(path: Path = INDEX_PATH) -> dict[str, Any]:
    chunks = build_chunks()
    return save_index(chunks, path=path)
