"""Copilot data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CopilotChunk:
    chunk_id: str
    source_type: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievedChunk:
    chunk: CopilotChunk
    score: float


@dataclass
class CopilotAnswer:
    answer: str
    sources: list[dict[str, Any]]
    provider: str
    trace_id: str
    chunks_used: int
