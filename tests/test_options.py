"""Black–Scholes and implied volatility round-trip tests."""

from quant_core.options import black_scholes_price, greeks, implied_volatility


def test_iv_round_trip():
    S, K, T, r, sigma = 100.0, 100.0, 0.5, 0.05, 0.35
    price = black_scholes_price(S, K, T, r, sigma, "call")
    iv = implied_volatility(price, S, K, T, r, "call")
    assert abs(iv - sigma) < 1e-3


def test_greeks_call_delta_range():
    g = greeks(100, 100, 0.5, 0.0, 0.3, "call")
    assert 0 < g["delta"] < 1
    assert g["gamma"] > 0
