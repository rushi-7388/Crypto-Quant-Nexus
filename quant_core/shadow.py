"""Shadow deployment router for canary scoring."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ShadowResult:
    trace_id: str
    primary: dict[str, Any]
    shadow: dict[str, Any]
    divergence: float
    routed_to_shadow: bool


def score_divergence(primary: dict[str, Any], shadow: dict[str, Any]) -> float:
    p = float(primary.get("composite_score", 0.0))
    s = float(shadow.get("composite_score", 0.0))
    return abs(p - s)


def route_with_shadow(
    *,
    trace_id: str,
    primary_fn: Callable[[], dict[str, Any]],
    shadow_fn: Callable[[], dict[str, Any]],
    canary_rate: float = 0.1,
) -> ShadowResult:
    primary = primary_fn()
    shadow = shadow_fn()
    routed = random.random() < max(0.0, min(1.0, canary_rate))
    div = score_divergence(primary, shadow)
    return ShadowResult(
        trace_id=trace_id,
        primary=primary,
        shadow=shadow,
        divergence=div,
        routed_to_shadow=routed,
    )
