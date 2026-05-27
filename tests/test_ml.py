"""ML pipeline training and inference."""

from quant_core.data import synthetic_ohlcv
from quant_core.ml.flow_model import (
    build_flow_features,
    horizon_bars_from_label,
    load_flow_artifact,
    predict_flow_signal,
    save_flow_artifact,
    train_flow_model,
)
from quant_core.ml.regime_model import (
    detect_regimes,
    load_regime_artifact,
    save_regime_artifact,
    train_regime_model,
)


def test_horizon_mapping():
    assert horizon_bars_from_label("5 bars") == 5


def test_flow_model_train_and_predict(tmp_path):
    df = synthetic_ohlcv(n=400, seed=11)
    artifact = train_flow_model(df, horizon_bars=3)
    assert 0 <= artifact.accuracy <= 1
    featured = build_flow_features(df)
    signal = predict_flow_signal(artifact, featured)
    assert signal["signal"] in {"BULLISH", "BEARISH", "NEUTRAL"}


def test_flow_artifact_round_trip(tmp_path):
    df = synthetic_ohlcv(n=350, seed=3)
    artifact = train_flow_model(df)
    save_flow_artifact(artifact, tmp_path)
    loaded = load_flow_artifact(tmp_path)
    assert loaded is not None
    assert loaded.horizon_bars == artifact.horizon_bars


def test_regime_model_train_and_detect(tmp_path):
    df = synthetic_ohlcv(n=500, seed=21)
    artifact, labeled = train_regime_model(df, n_regimes=4)
    assert "regime_name" in labeled.columns
    save_regime_artifact(artifact, tmp_path)
    loaded = load_regime_artifact(tmp_path)
    assert loaded is not None
    redetected = detect_regimes(loaded, df.tail(200))
    assert redetected["regime"].notna().any()
