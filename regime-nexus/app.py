"""Regime Nexus — ML market regime detection & transition analytics."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.express as px
import streamlit as st

from quant_core.data import resolve_price_feed
from quant_core.logging_config import configure_logging
from quant_core.metrics import annualized_vol, sharpe_ratio
from quant_core.ml.regime_model import (
    detect_regimes,
    load_regime_artifact,
    train_regime_model,
    transition_matrix,
)
from quant_core.theme import inject_theme, render_footer, render_header

configure_logging(service_name="regime-nexus")
st.set_page_config(page_title="Regime Nexus | Crypto Quant Nexus", layout="wide", page_icon="🔮")
inject_theme()
render_header("Regime Nexus", "K-Means regime classification · volatility states · transition intelligence")

with st.sidebar:
    asset = st.selectbox("Asset", ["BTC/USDT", "ETH/USDT"])
    use_live = st.toggle("Live data", True)
    n_regimes = st.slider("Regimes", 3, 5, 4)
    use_saved = st.toggle("Use trained artifact", True)

df, feed_label = resolve_price_feed(asset, use_live)
df = df.tail(600).copy()

artifact = load_regime_artifact() if use_saved else None
if artifact is None or artifact.n_regimes != n_regimes:
    artifact, df = train_regime_model(df, n_regimes=n_regimes)
else:
    df = detect_regimes(artifact, df)

current = int(df["regime"].dropna().iloc[-1])
current_name = str(df["regime_name"].dropna().iloc[-1])
vol = annualized_vol(df["ret"].dropna())
sharpe = sharpe_ratio(df["ret"].dropna())
feat = df[["ret", "vol_20", "mom_10", "range_pct"]].dropna()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Current regime", current_name)
c2.metric("Ann. volatility", f"{vol * 100:.1f}%")
c3.metric("Sharpe", f"{sharpe:.2f}")
c4.metric("Samples", len(feat))

col1, col2 = st.columns(2)
with col1:
    plot_df = df.dropna(subset=["regime"])
    fig = px.scatter(
        plot_df,
        x="timestamp",
        y="close",
        color="regime_name",
        title="Price colored by detected regime",
    )
    fig.update_layout(template="plotly_dark", height=400)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    labels = plot_df["regime"].astype(int)
    cluster_fig = px.scatter(
        feat.reset_index(drop=True),
        x="vol_20",
        y="mom_10",
        color=labels.astype(str),
        title="Regime feature space",
        labels={"vol_20": "Volatility", "mom_10": "Momentum"},
    )
    cluster_fig.update_layout(template="plotly_dark", height=400)
    st.plotly_chart(cluster_fig, use_container_width=True)

st.subheader("Regime transition matrix")
st.dataframe(transition_matrix(plot_df).astype(int), use_container_width=True)

st.caption(f"Data: {feed_label} · Regimes: {n_regimes}")
st.dataframe(
    plot_df[["timestamp", "close", "vol_20", "mom_10", "regime_name"]].tail(25),
    use_container_width=True,
    hide_index=True,
)
render_footer()
