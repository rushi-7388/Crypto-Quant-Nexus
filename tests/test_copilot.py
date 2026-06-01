"""Quant Copilot — indexing, retrieval, and API."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app
from quant_core.audit import append_decision_audit
from quant_core.copilot.indexer import rebuild_index
from quant_core.copilot.retriever import retrieve
from quant_core.copilot.service import ask
from quant_core.copilot.sources import collect_all_documents

client = TestClient(app)


@pytest.fixture
def copilot_artifacts(tmp_path, monkeypatch):
    audit = tmp_path / "audit.jsonl"
    events = tmp_path / "events"
    events.mkdir()
    research = tmp_path / "research"
    research.mkdir()
    index = tmp_path / "copilot" / "index.json"
    backtests = research / "backtests.jsonl"

    monkeypatch.setenv("AUDIT_SIGNING_KEY", "test-key")
    from quant_core import audit as audit_mod

    audit_mod.AUDIT_LOG = audit
    append_decision_audit(
        trace_id="trace-copilot-1",
        symbol="BTC/USDT",
        model_version="test_v1",
        dataset_version="demo",
        decision={"composite_score": 0.42},
        rationale={"note": "unit test decision"},
    )

    from quant_core import events_store as ev_mod

    ev_mod.EVENT_DIR = events
    ev_mod.REQUEST_LOG = events / "inference_requests.jsonl"
    ev_mod.RESULT_LOG = events / "inference_results.jsonl"
    ev_mod.append_event(
        ev_mod.REQUEST_LOG,
        {"trace_id": "trace-copilot-1", "symbol": "BTC/USDT", "timestamp_utc": "2026-01-01T00:00:00Z"},
    )

    from quant_core.research import backtest_store as bt_mod

    bt_mod.RESEARCH_DIR = research
    bt_mod.BACKTEST_LOG = backtests
    bt_mod.persist_backtest_snapshot(
        symbol="BTC/USDT",
        feed="demo",
        metrics={"sharpe": 1.2, "max_drawdown": -0.1},
        folds=[{"fold": 0, "sharpe": 1.0}],
        oos_points=100,
        source="test",
    )

    from quant_core.copilot import indexer as idx_mod

    idx_mod.INDEX_DIR = tmp_path / "copilot"
    idx_mod.INDEX_PATH = index

    yield index


def test_collect_documents_includes_audit_and_backtest(copilot_artifacts):
    docs = collect_all_documents()
    types = {d[0] for d in docs}
    assert "audit" in types
    assert "backtest" in types


def test_rebuild_and_retrieve_trace(copilot_artifacts):
    rebuild_index(copilot_artifacts)
    from quant_core.copilot.indexer import load_index

    chunks, meta = load_index(copilot_artifacts)
    assert meta["chunk_count"] > 0
    hits = retrieve("trace copilot BTC decision", chunks, top_k=5)
    assert hits
    assert any("trace-copilot-1" in str(h.chunk.metadata) + h.chunk.text for h in hits)


def test_ask_mock_provider(copilot_artifacts, monkeypatch):
    monkeypatch.setenv("COPILOT_LLM_PROVIDER", "mock")
    rebuild_index(copilot_artifacts)
    result = ask(
        "composite score BTC unit test decision",
        index_path=copilot_artifacts,
        auto_index=False,
    )
    assert result.answer
    assert result.provider == "mock"
    assert result.chunks_used >= 1


def test_copilot_api_endpoints(copilot_artifacts, monkeypatch):
    monkeypatch.setenv("COPILOT_LLM_PROVIDER", "mock")
    from quant_core.copilot import indexer as idx_mod

    monkeypatch.setattr(idx_mod, "INDEX_PATH", copilot_artifacts)
    client.post("/v2/copilot/index")

    r = client.get("/v2/copilot/status")
    assert r.status_code == 200
    assert r.json()["provider"] == "mock"

    r = client.post(
        "/v2/copilot/ask",
        json={"question": "composite score BTC unit test decision", "top_k": 3},
    )
    assert r.status_code == 200
    body = r.json()
    assert "answer" in body
    assert body["chunks_used"] >= 1
