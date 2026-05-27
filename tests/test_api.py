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
