"""Append/read event logs for inference requests and results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

EVENT_DIR = Path("artifacts/events")
REQUEST_LOG = EVENT_DIR / "inference_requests.jsonl"
RESULT_LOG = EVENT_DIR / "inference_results.jsonl"


def append_event(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload) + "\n")


def read_events(path: Path, limit: int = 200) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return rows[-limit:]


def dashboard_snapshot() -> dict[str, Any]:
    requests = read_events(REQUEST_LOG, limit=1000)
    results = read_events(RESULT_LOG, limit=1000)
    req_map = {r["trace_id"]: r for r in requests if "trace_id" in r}
    matched = [r for r in results if r.get("trace_id") in req_map]
    avg_latency = 0.0
    if matched:
        deltas = []
        for row in matched:
            try:
                deltas.append(float(row.get("processed_ms", 0.0)))
            except Exception:
                continue
        avg_latency = sum(deltas) / len(deltas) if deltas else 0.0
    return {
        "request_count": len(requests),
        "result_count": len(results),
        "matched_count": len(matched),
        "avg_processed_ms": round(avg_latency, 2),
        "recent_requests": requests[-20:],
        "recent_results": results[-20:],
    }
