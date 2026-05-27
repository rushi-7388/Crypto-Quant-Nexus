"""Tests for OHLCV normalization and synthetic feeds."""

import pandas as pd

from quant_core.data import normalize_ohlcv, resolve_price_feed, synthetic_ohlcv


def test_synthetic_ohlcv_schema():
    df = synthetic_ohlcv(n=100, seed=7)
    assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert len(df) == 100
    assert (df["high"] >= df["close"]).all()
    assert (df["low"] <= df["close"]).all()


def test_normalize_renames_datetime():
    raw = pd.DataFrame(
        {
            "Datetime": pd.date_range("2026-01-01", periods=10, freq="min"),
            "Open": range(10),
            "High": range(10),
            "Low": range(10),
            "Close": range(10),
            "Volume": range(10),
        }
    )
    out = normalize_ohlcv(raw)
    assert "timestamp" in out.columns
    assert out["close"].notna().all()


def test_resolve_price_feed_offline():
    df, label = resolve_price_feed("BTC/USDT", use_live=False)
    assert len(df) > 50
    assert "Synthetic" in label
