"""Funding Radar — cross-venue perpetual funding arbitrage scanner."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from quant_core.data import fetch_funding_rates_demo, resolve_price_feed
from quant_core.theme import inject_theme, render_footer, render_header

st.set_page_config(page_title="Funding Radar | Crypto Quant Nexus", layout="wide", page_icon="📡")
inject_theme()
render_header("Funding Radar", "Cross-exchange funding rate intelligence · arb scoring · carry analytics")

with st.sidebar:
    refresh = st.button("Refresh funding snapshot", type="primary")
    lookback_h = st.slider("History (hours)", 8, 168, 48, 8)
    min_edge_bps = st.slider("Min arb edge (bps)", 1, 50, 8)

funding = fetch_funding_rates_demo()
if refresh:
    st.toast("Funding data refreshed")

best = funding.loc[funding["funding_rate_pct"].idxmax()]
worst = funding.loc[funding["funding_rate_pct"].idxmin()]
edge_bps = (best["funding_rate_pct"] - worst["funding_rate_pct"]) * 100

c1, c2, c3, c4 = st.columns(4)
c1.metric("Top venue rate", f"{best['funding_rate_pct']:.4f}%", best["exchange"])
c2.metric("Bottom venue rate", f"{worst['funding_rate_pct']:.4f}%", worst["exchange"])
c3.metric("Arb edge", f"{edge_bps:.1f} bps")
c4.metric("Opportunity", "ACTIVE" if edge_bps >= min_edge_bps else "WATCH")

col1, col2 = st.columns([1.2, 1])
with col1:
    fig = px.bar(
        funding,
        x="exchange",
        y="funding_rate_pct",
        color="funding_rate_pct",
        color_continuous_scale="RdYlGn",
        title="Current Funding Rates by Venue",
    )
    fig.update_layout(template="plotly_dark", height=380, coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Ranked opportunities")
    funding["rank"] = range(1, len(funding) + 1)
    st.dataframe(
        funding[["rank", "exchange", "funding_rate_pct", "annualized_pct", "source"]],
        use_container_width=True,
        hide_index=True,
    )

hours = np.arange(lookback_h)
rng = np.random.default_rng(2026)
history = []
for ex in funding["exchange"]:
    base = funding.loc[funding["exchange"] == ex, "funding_rate_pct"].iloc[0]
    series = base + np.cumsum(rng.normal(0, 0.003, len(hours)))
    for h, v in zip(hours, series):
        history.append({"hour": h, "exchange": ex, "rate_pct": v})

hist_df = pd.DataFrame(history)
line = px.line(hist_df, x="hour", y="rate_pct", color="exchange", title="Funding Rate History (research)")
line.update_layout(template="plotly_dark", height=360)
st.plotly_chart(line, use_container_width=True)

price_df, label = resolve_price_feed("BTC/USDT", use_live=True)
spread_est = funding["funding_rate_pct"].max() - funding["funding_rate_pct"].min()
st.caption(f"Spot context: {label} · Est. 8h carry spread capture: **{spread_est*100:.2f} bps** (research estimate)")

if edge_bps >= min_edge_bps:
    st.success(
        f"**Arb signal:** Long funding on {worst['exchange']}, short on {best['exchange']} "
        f"— edge {edge_bps:.1f} bps (educational model only)."
    )
else:
    st.warning("Edge below threshold — monitor next funding window.")

render_footer()
