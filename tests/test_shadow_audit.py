"""Shadow deployment and audit trail tests."""

from pathlib import Path

from quant_core.audit import append_decision_audit
from quant_core.shadow import route_with_shadow


def test_shadow_divergence_nonnegative():
    result = route_with_shadow(
        trace_id="t1",
        primary_fn=lambda: {"composite_score": 0.2},
        shadow_fn=lambda: {"composite_score": -0.1},
        canary_rate=1.0,
    )
    assert result.routed_to_shadow is True
    assert result.divergence >= 0


def test_append_decision_audit_creates_log():
    record = append_decision_audit(
        trace_id="trace-test",
        symbol="BTC/USDT",
        model_version="v1",
        dataset_version="d1",
        decision={"action": "OVERWEIGHT_LONG"},
        rationale={"flow": {"score": 0.4}},
    )
    assert "decision_hash" in record
    assert Path("artifacts/audit/decisions.jsonl").exists()
