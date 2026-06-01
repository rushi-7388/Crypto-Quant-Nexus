"""FastAPI smoke tests."""

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_flow_signal_endpoint():
    r = client.get("/v1/ml/flow/signal", params={"use_live": False})
    assert r.status_code == 200
    data = r.json()
    assert data["signal"] in {"BULLISH", "BEARISH", "NEUTRAL"}


def test_regime_endpoint():
    r = client.get("/v1/ml/regime/current", params={"use_live": False})
    assert r.status_code == 200
    assert "current_regime" in r.json()


def test_v2_alpha_composite():
    r = client.get("/v2/alpha/composite", params={"use_live": False})
    assert r.status_code == 200
    body = r.json()
    assert "composite_score" in body


def test_v2_universe():
    r = client.get("/v2/universe")
    assert r.status_code == 200
    assert r.json()["count"] >= 6


def test_v2_feature_parity():
    r = client.get("/v2/features/parity", params={"symbol": "BTC/USDT"})
    assert r.status_code == 200
    assert "max_drift" in r.json()


def test_v2_execution_simulator():
    payload = {"side": "buy", "quantity": 1.5, "mid_price": 100000}
    r = client.post("/v2/execution/simulate", json=payload)
    assert r.status_code == 200
    assert r.json()["total_cost"] >= 0


def test_v2_portfolio_optimizer():
    r = client.get("/v2/portfolio/optimize", params={"use_live": False})
    assert r.status_code == 200
    body = r.json()
    assert "weights" in body or "error" in body


def test_v2_canary_status():
    r = client.get("/v2/canary/status")
    assert r.status_code == 200
    assert "active_model" in r.json()


def test_v2_canary_evaluate():
    r = client.post(
        "/v2/canary/evaluate",
        json={"avg_divergence": 0.2, "shadow_win_rate": 0.56, "samples": 50},
    )
    assert r.status_code == 200
    assert "verdict" in r.json()


def test_v2_audit_verify():
    r = client.get("/v2/audit/verify")
    assert r.status_code == 200
    assert "ok" in r.json()


def test_v2_events_dashboard():
    r = client.get("/v2/events/dashboard")
    assert r.status_code == 200
    body = r.json()
    assert "request_count" in body
    assert "result_count" in body


def test_v2_copilot_status():
    r = client.get("/v2/copilot/status")
    assert r.status_code == 200
    assert "provider" in r.json()


def test_v2_copilot_ask_mock():
    r = client.post(
        "/v2/copilot/ask",
        json={"question": "Summarize platform governance logs", "top_k": 3},
    )
    assert r.status_code == 200
    body = r.json()
    assert "answer" in body
    assert body.get("provider") == "mock"
