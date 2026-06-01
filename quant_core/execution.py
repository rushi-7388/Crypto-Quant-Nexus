"""Execution simulator with slippage, fees, and latency."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class ExecutionReport:
    side: Literal["buy", "sell"]
    quantity: float
    mid_price: float
    fill_price: float
    notional: float
    fee_paid: float
    slippage_cost: float
    latency_penalty: float
    total_cost: float


def simulate_execution(
    *,
    side: Literal["buy", "sell"],
    quantity: float,
    mid_price: float,
    spread_bps: float = 5.0,
    fee_bps: float = 2.0,
    slippage_bps_per_unit: float = 0.25,
    latency_ms: float = 25.0,
    latency_impact_bps_per_100ms: float = 0.5,
) -> ExecutionReport:
    notional = quantity * mid_price
    half_spread = spread_bps / 2 / 10_000
    slip = slippage_bps_per_unit * quantity / 10_000
    latency = (latency_ms / 100.0) * (latency_impact_bps_per_100ms / 10_000)
    impact = half_spread + slip + latency
    if side == "buy":
        fill = mid_price * (1 + impact)
    else:
        fill = mid_price * (1 - impact)
    fee_paid = notional * fee_bps / 10_000
    slippage_cost = notional * slip
    latency_penalty = notional * latency
    total_cost = fee_paid + slippage_cost + latency_penalty + notional * half_spread
    return ExecutionReport(
        side=side,
        quantity=quantity,
        mid_price=mid_price,
        fill_price=fill,
        notional=notional,
        fee_paid=fee_paid,
        slippage_cost=slippage_cost,
        latency_penalty=latency_penalty,
        total_cost=total_cost,
    )
