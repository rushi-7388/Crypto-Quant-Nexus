"""Signed audit chain verification tests."""

import json

from quant_core.audit import append_decision_audit, verify_audit_chain


def test_verify_audit_chain_ok(tmp_path, monkeypatch):
    path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("AUDIT_SIGNING_KEY", "test-key")
    # monkeypatch module path via direct call target
    from quant_core import audit as audit_mod

    original = audit_mod.AUDIT_LOG
    try:
        audit_mod.AUDIT_LOG = path
        append_decision_audit(
            trace_id="t1",
            symbol="BTC/USDT",
            model_version="v1",
            dataset_version="d1",
            decision={"r": "LONG"},
            rationale={"flow": {"score": 0.2}},
        )
        append_decision_audit(
            trace_id="t2",
            symbol="ETH/USDT",
            model_version="v1",
            dataset_version="d1",
            decision={"r": "SHORT"},
            rationale={"flow": {"score": -0.3}},
        )
        report = verify_audit_chain(path=path, secret="test-key")
        assert report["ok"] is True
        assert report["records"] == 2
    finally:
        audit_mod.AUDIT_LOG = original


def test_verify_audit_chain_detects_tamper(tmp_path, monkeypatch):
    path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("AUDIT_SIGNING_KEY", "test-key")
    from quant_core import audit as audit_mod

    original = audit_mod.AUDIT_LOG
    try:
        audit_mod.AUDIT_LOG = path
        append_decision_audit(
            trace_id="t1",
            symbol="BTC/USDT",
            model_version="v1",
            dataset_version="d1",
            decision={"r": "LONG"},
            rationale={"flow": {"score": 0.2}},
        )
        rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]
        rows[0]["decision"]["r"] = "HACKED"
        path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        report = verify_audit_chain(path=path, secret="test-key")
        assert report["ok"] is False
        assert len(report["errors"]) >= 1
    finally:
        audit_mod.AUDIT_LOG = original
