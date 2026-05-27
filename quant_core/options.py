"""Black–Scholes and implied volatility utilities."""

from __future__ import annotations

import numpy as np
from scipy.stats import norm


def black_scholes_price(
    S: float, K: float, T: float, r: float, sigma: float, option_type: str = "call"
) -> float:
    if T <= 0 or sigma <= 0:
        intrinsic = max(S - K, 0) if option_type == "call" else max(K - S, 0)
        return float(intrinsic)
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if option_type == "call":
        return float(S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2))
    return float(K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1))


def implied_volatility(
    market_price: float,
    S: float,
    K: float,
    T: float,
    r: float = 0.0,
    option_type: str = "call",
    tol: float = 1e-6,
    max_iter: int = 80,
) -> float:
    sigma = 0.5
    for _ in range(max_iter):
        price = black_scholes_price(S, K, T, r, sigma, option_type)
        vega = S * norm.pdf(
            (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        ) * np.sqrt(T)
        if vega < 1e-12:
            break
        diff = price - market_price
        if abs(diff) < tol:
            return float(sigma)
        sigma -= diff / vega
        sigma = max(0.01, min(sigma, 5.0))
    return float(sigma)


def greeks(S: float, K: float, T: float, r: float, sigma: float, option_type: str = "call") -> dict:
    if T <= 0 or sigma <= 0:
        return {"delta": 0.0, "gamma": 0.0, "vega": 0.0, "theta": 0.0}
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    vega = S * norm.pdf(d1) * np.sqrt(T) / 100
    if option_type == "call":
        delta = norm.cdf(d1)
        theta = (
            -S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
            - r * K * np.exp(-r * T) * norm.cdf(d2)
        ) / 365
    else:
        delta = norm.cdf(d1) - 1
        theta = (
            -S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
            + r * K * np.exp(-r * T) * norm.cdf(-d2)
        ) / 365
    return {"delta": float(delta), "gamma": float(gamma), "vega": float(vega), "theta": float(theta)}
