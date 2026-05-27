"""Data platform — universe and quality."""

from quant_core.data import synthetic_ohlcv
from quant_core.platform.catalog import list_universe
from quant_core.platform.quality import ohlcv_quality_report


def test_universe_has_major_assets():
    symbols = list_universe()
    assert "BTC/USDT" in symbols
    assert "ETH/USDT" in symbols


def test_quality_passes_clean_synthetic():
    df = synthetic_ohlcv(200, seed=3)
    report = ohlcv_quality_report(df)
    assert report["score"] > 0.5
    assert report["rows"] == 200
