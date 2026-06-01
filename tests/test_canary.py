"""Canary policy engine tests."""

from quant_core.canary import apply_canary_update, evaluate_canary_policy


def test_canary_promote_when_win_rate_high():
    verdict = evaluate_canary_policy(avg_divergence=0.1, shadow_win_rate=0.6, samples=40)
    assert verdict["action"] == "promote_shadow"


def test_canary_rollback_when_divergence_high():
    verdict = evaluate_canary_policy(avg_divergence=0.8, shadow_win_rate=0.7, samples=40)
    assert verdict["action"] == "rollback_shadow"


def test_apply_canary_update_returns_state(tmp_path):
    out = apply_canary_update(
        avg_divergence=0.2,
        shadow_win_rate=0.55,
        samples=50,
        path=tmp_path / "state.json",
    )
    assert "state" in out
    assert out["state"]["samples"] == 50
