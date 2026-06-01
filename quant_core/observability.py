"""Lightweight observability primitives with trace propagation."""

from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from time import perf_counter

_TRACE_ID: ContextVar[str] = ContextVar("trace_id", default="")


@dataclass
class TraceContext:
    trace_id: str
    start_ts: float


def current_trace_id() -> str:
    trace_id = _TRACE_ID.get()
    if trace_id:
        return trace_id
    generated = str(uuid.uuid4())
    _TRACE_ID.set(generated)
    return generated


def start_trace(trace_id: str | None = None) -> TraceContext:
    tid = trace_id or str(uuid.uuid4())
    _TRACE_ID.set(tid)
    return TraceContext(trace_id=tid, start_ts=perf_counter())


def end_trace(ctx: TraceContext) -> float:
    return perf_counter() - ctx.start_ts


def log_with_trace(logger: logging.Logger, event: str, **fields: object) -> None:
    payload = {"trace_id": current_trace_id(), **fields}
    extras = " ".join(f'{k}="{v}"' for k, v in payload.items())
    logger.info("%s %s", event, extras)
