"""Feature store contracts and parity tests."""

from quant_core.feature_store import load_contracts, parity_report


def test_load_contracts():
    contracts = load_contracts()
    names = [c.name for c in contracts]
    assert "composite_score" in names
    assert len(contracts) >= 5


def test_parity_report_shape():
    report = parity_report("BTC/USDT")
    assert "online" in report
    assert "offline" in report
    assert "max_drift" in report
