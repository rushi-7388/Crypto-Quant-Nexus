"""Limit order book simulation for market-making research."""

from __future__ import annotations

import numpy as np
import pandas as pd


def simulate_lob(mid: float, levels: int = 12, tick: float = 0.5, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    bids, asks = [], []
    for i in range(1, levels + 1):
        bids.append({"side": "bid", "price": mid - i * tick, "size": rng.uniform(0.5, 8.0)})
        asks.append({"side": "ask", "price": mid + i * tick, "size": rng.uniform(0.5, 8.0)})
    return pd.DataFrame(bids + asks)


def avellaneda_stoikov_spread(
    mid: float,
    inventory: float,
    gamma: float,
    sigma: float,
    k: float = 1.5,
    T: float = 1.0,
) -> tuple[float, float]:
    """Reservation price skew + optimal half-spread (simplified AS model)."""
    reservation = mid - inventory * gamma * (sigma**2) * T
    half_spread = 0.5 * gamma * (sigma**2) * T + (1 / gamma) * np.log(1 + gamma / k)
    bid = reservation - half_spread
    ask = reservation + half_spread
    return float(bid), float(ask)


def order_flow_imbalance(bid_vol: float, ask_vol: float, prev_bid: float, prev_ask: float) -> float:
    """Cont-style OFI increment."""
    bid_contrib = bid_vol if bid_vol >= prev_bid else bid_vol - prev_bid
    ask_contrib = ask_vol if ask_vol >= prev_ask else ask_vol - prev_ask
    return bid_contrib - ask_contrib
