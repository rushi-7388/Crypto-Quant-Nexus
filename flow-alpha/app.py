"""Flow Alpha — order flow imbalance & short-horizon direction model."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from quant_core.data import resolve_price_feed
from quant_core.logging_config import configure_logging
from quant_core.ml.flow_model import (
    build_flow_features,
    horizon_bars_from_label,
    load_flow_artifact,
    predict_flow_signal,
    train_flow_model,
)
from quant_core.theme import inject_theme, render_footer, render_header

configure_logging(service_name="flow-alpha")
st.set_page_config(page_title="Flow Alpha | Crypto Quant Nexus", layout="wide", page_icon="⚡")
inject_theme()
render_header("Flow Alpha", "Order flow imbalance (OFI) · ML microstructure signals · liquidity pressure")

with st.sidebar:
    use_live = st.toggle("Live feed", True)
    horizon = st.selectbox("Prediction horizon", ["1 bar", "3 bars", "5 bars"])
    train_size = st.slider("Training window", 200, 600, 400, 50)
    use_saved = st.toggle("Use trained artifact", True)

df, feed_label = resolve_price_feed("BTC/USDT", use_live)
df = df.tail(train_size).copy()
horizon_bars = horizon_bars_from_label(horizon)

artifact = load_flow_artifact() if use_saved else None
if artifact is None or artifact.horizon_bars != horizon_bars:
    artifact = train_flow_model(df, horizon_bars=horizon_bars)

featured = build_flow_features(df)
featured["target"] = (featured["close"].shift(-horizon_bars) > featured["close"]).astype(int)
df = featured.dropna()
signal = predict_flow_signal(artifact, df)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Model accuracy", f"{artifact.accuracy * 100:.1f}%")
c2.metric("OFI (last)", f"{df['ofi'].iloc[-1]:,.0f}")
c3.metric("Confidence", f"{signal['confidence'] * 100:.1f}%")
c4.metric("Signal", signal["signal"])

col1, col2 = st.columns(2)
with col1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["timestamp"], y=df["close"], name="Price", line=dict(color="#94a3b8")))
    fig.add_trace(go.Bar(x=df["timestamp"], y=df["ofi"], name="OFI", yaxis="y2", marker_color="#63b3ed", opacity=0.5))
    fig.update_layout(template="plotly_dark", title="Price vs Order Flow Imbalance", height=400, yaxis2=dict(overlaying="y", side="right"))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    import numpy as np

    z = np.column_stack([df["ofi"].tail(40).values, df["pressure"].tail(40).values])
    st.plotly_chart(
        go.Figure(data=go.Heatmap(z=z, colorscale="Blues")).update_layout(
            template="plotly_dark", title="Liquidity Pressure Heatmap", height=400
        ),
        use_container_width=True,
    )

imp = pd.DataFrame(
    {"feature": list(artifact.features), "importance": artifact.model.feature_importances_}
).sort_values("importance", ascending=True)
fig_imp = go.Figure(go.Bar(x=imp["importance"], y=imp["feature"], orientation="h", marker_color="#8b5cf6"))
fig_imp.update_layout(template="plotly_dark", title="Feature Importance", height=280)
st.plotly_chart(fig_imp, use_container_width=True)

st.caption(
    f"Feed: {feed_label} · Horizon: {horizon} ({horizon_bars} bars) · "
    f"Artifact: {'loaded' if use_saved and load_flow_artifact() else 'session-trained'}"
)
st.dataframe(df[["timestamp", "close", "ofi", "pressure", "target"]].tail(20), use_container_width=True, hide_index=True)
render_footer()
