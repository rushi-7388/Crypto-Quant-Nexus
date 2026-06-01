"""Collect raw documents from platform artifacts and APIs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from quant_core import audit as audit_mod
from quant_core import events_store as events_mod
from quant_core.ml.model_card import flow_alpha_model_card, regime_nexus_model_card
from quant_core.research import backtest_store as backtest_mod


def _read_jsonl(path: Path, limit: int = 500) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows[-limit:]


def _flatten(obj: Any, prefix: str = "") -> str:
    if isinstance(obj, dict):
        parts = []
        for key, val in obj.items():
            parts.append(_flatten(val, f"{prefix}{key}."))
        return " ".join(parts)
    if isinstance(obj, list):
        return " ".join(_flatten(v, prefix) for v in obj[:50])
    return f"{prefix}{obj}" if prefix else str(obj)


def _record_to_text(record: dict[str, Any]) -> str:
    return _flatten(record).strip()


def iter_audit_documents(limit: int = 500) -> Iterator[tuple[str, str, dict[str, Any]]]:
    for row in _read_jsonl(audit_mod.AUDIT_LOG, limit=limit):
        meta = {
            "trace_id": row.get("trace_id"),
            "symbol": row.get("symbol"),
            "model_version": row.get("model_version"),
            "decision_hash": row.get("decision_hash"),
            "timestamp_utc": row.get("timestamp_utc"),
        }
        yield ("audit", _record_to_text(row), meta)


def iter_event_documents(limit: int = 500) -> Iterator[tuple[str, str, dict[str, Any]]]:
    for path in (events_mod.REQUEST_LOG, events_mod.RESULT_LOG):
        label = path.stem
        for row in events_mod.read_events(path, limit=limit):
            meta = {
                "log": label,
                "trace_id": row.get("trace_id"),
                "symbol": row.get("symbol"),
                "timestamp_utc": row.get("timestamp_utc") or row.get("ts"),
            }
            yield ("event", _record_to_text(row), meta)


def iter_model_card_documents() -> Iterator[tuple[str, str, dict[str, Any]]]:
    import json as _json
    from pathlib import Path as _Path

    flow_meta, regime_meta = {}, {}
    flow_path = _Path("artifacts/models/flow_alpha/metadata.json")
    regime_path = _Path("artifacts/models/regime_nexus/metadata.json")
    if flow_path.exists():
        flow_meta = _json.loads(flow_path.read_text(encoding="utf-8"))
    if regime_path.exists():
        regime_meta = _json.loads(regime_path.read_text(encoding="utf-8"))
    for name, card in (
        ("flow_alpha", flow_alpha_model_card(flow_meta)),
        ("regime_nexus", regime_nexus_model_card(regime_meta)),
    ):
        meta = {"model_id": card.get("model_id"), "model_name": name}
        yield ("model_card", _record_to_text(card), meta)


def iter_backtest_documents(limit: int = 200) -> Iterator[tuple[str, str, dict[str, Any]]]:
    for row in backtest_mod.read_backtest_snapshots(limit=limit):
        meta = {
            "symbol": row.get("symbol"),
            "feed": row.get("feed"),
            "timestamp_utc": row.get("timestamp_utc"),
            "source": row.get("source"),
        }
        yield ("backtest", _record_to_text(row), meta)


def iter_research_json_files() -> Iterator[tuple[str, str, dict[str, Any]]]:
    research_dir = backtest_mod.RESEARCH_DIR
    if not research_dir.exists():
        return
    for path in sorted(research_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        meta = {"file": path.name, "symbol": payload.get("symbol")}
        yield ("backtest", _record_to_text(payload), meta)


def collect_all_documents(
    *,
    include_audit: bool = True,
    include_events: bool = True,
    include_model_cards: bool = True,
    include_backtests: bool = True,
) -> list[tuple[str, str, dict[str, Any]]]:
    docs: list[tuple[str, str, dict[str, Any]]] = []
    if include_audit:
        docs.extend(iter_audit_documents())
    if include_events:
        docs.extend(iter_event_documents())
    if include_model_cards:
        docs.extend(iter_model_card_documents())
    if include_backtests:
        docs.extend(iter_backtest_documents())
        docs.extend(iter_research_json_files())
    return docs
