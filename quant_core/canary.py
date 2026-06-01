"""Canary policy engine for auto promote/rollback decisions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CANARY_STATE_PATH = Path("artifacts/canary/state.json")


@dataclass
class CanaryThresholds:
    max_divergence: float = 0.30
    min_win_rate: float = 0.52
    min_samples: int = 25


def _default_state() -> dict[str, Any]:
    return {
        "active_model": "primary_v1",
        "shadow_model": "shadow_vNext",
        "promoted": False,
        "rolled_back": False,
        "samples": 0,
        "avg_divergence": 0.0,
        "shadow_win_rate": 0.0,
        "history": [],
    }


def load_canary_state(path: Path = CANARY_STATE_PATH) -> dict[str, Any]:
    if not path.exists():
        return _default_state()
    return json.loads(path.read_text(encoding="utf-8"))


def save_canary_state(state: dict[str, Any], path: Path = CANARY_STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def evaluate_canary_policy(
    *,
    avg_divergence: float,
    shadow_win_rate: float,
    samples: int,
    thresholds: CanaryThresholds | None = None,
) -> dict[str, Any]:
    t = thresholds or CanaryThresholds()
    if samples < t.min_samples:
        return {"action": "hold", "reason": "insufficient_samples"}
    if avg_divergence > t.max_divergence:
        return {"action": "rollback_shadow", "reason": "divergence_too_high"}
    if shadow_win_rate >= t.min_win_rate:
        return {"action": "promote_shadow", "reason": "shadow_outperforms_primary"}
    return {"action": "hold", "reason": "no_policy_trigger"}


def apply_canary_update(
    *,
    avg_divergence: float,
    shadow_win_rate: float,
    samples: int,
    thresholds: CanaryThresholds | None = None,
    path: Path = CANARY_STATE_PATH,
) -> dict[str, Any]:
    state = load_canary_state(path)
    verdict = evaluate_canary_policy(
        avg_divergence=avg_divergence,
        shadow_win_rate=shadow_win_rate,
        samples=samples,
        thresholds=thresholds,
    )
    state["samples"] = samples
    state["avg_divergence"] = avg_divergence
    state["shadow_win_rate"] = shadow_win_rate
    state["promoted"] = verdict["action"] == "promote_shadow"
    state["rolled_back"] = verdict["action"] == "rollback_shadow"
    state["history"].append(
        {
            "samples": samples,
            "avg_divergence": avg_divergence,
            "shadow_win_rate": shadow_win_rate,
            "action": verdict["action"],
            "reason": verdict["reason"],
        }
    )
    if state["promoted"]:
        state["active_model"] = state.get("shadow_model", "shadow_vNext")
    save_canary_state(state, path)
    return {"state": state, "verdict": verdict}
