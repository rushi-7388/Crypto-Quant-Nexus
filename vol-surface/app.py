"""Vol Surface — implied volatility surface & Greeks analytics."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from quant_core.data import resolve_price_feed
from quant_core.options import black_scholes_price, greeks, implied_volatility
from quant_core.theme import inject_theme, render_footer, render_header

st.set_page_config(page_title="Vol Surface | Crypto Quant Nexus", layout="wide", page_icon="🌐")
inject_theme()
render_header("Vol Surface", "Crypto options IV surface · smile/skew · Greeks dashboard")

with st.sidebar:
    spot_override = st.number_input("Spot override (0 = live)", 0.0, 200_000.0, 0.0, 1000.0)
    r = st.slider("Risk-free rate %", 0.0, 8.0, 4.0, 0.25) / 100
    skew = st.slider("Skew intensity", 0.0, 1.5, 0.6, 0.05)

df, feed_label = resolve_price_feed("BTC/USDT", True)
S = spot_override if spot_override > 0 else float(df["close"].iloc[-1])
st.caption(f"Underlying: **${S:,.2f}** · {feed_label}")

maturities = [7, 14, 30, 60, 90]
strikes = np.linspace(S * 0.85, S * 1.15, 15)
records, iv_grid = [], np.zeros((len(maturities), len(strikes)))

for i, T_days in enumerate(maturities):
    T = T_days / 365
    for j, K in enumerate(strikes):
        moneyness = K / S
        base_iv = 0.55 + skew * (moneyness - 1) ** 2 * 8 - 0.08 * np.log(T_days + 1)
        base_iv = max(0.15, min(base_iv, 1.2))
        price = black_scholes_price(S, K, T, r, base_iv, "call")
        noise = np.random.default_rng(int(K)).uniform(0.98, 1.02)
        iv = implied_volatility(price * noise, S, K, T, r, "call")
        iv_grid[i, j] = iv
        g = greeks(S, K, T, r, iv, "call")
        records.append(
            {
                "expiry_days": T_days,
                "strike": K,
                "moneyness": moneyness,
                "iv": iv,
                "price": price,
                **g,
            }
        )

chain = pd.DataFrame(records)
atm = chain.loc[(chain["strike"] - S).abs().idxmin()]

c1, c2, c3, c4 = st.columns(4)
c1.metric("ATM IV (30d)", f"{chain[chain['expiry_days']==30]['iv'].median()*100:.1f}%")
c2.metric("Delta", f"{atm['delta']:.3f}")
c3.metric("Gamma", f"{atm['gamma']:.5f}")
c4.metric("Vega", f"{atm['vega']:.3f}")

col1, col2 = st.columns(2)
with col1:
    surface = go.Figure(data=[go.Surface(x=strikes, y=maturities, z=iv_grid, colorscale="Viridis")])
    surface.update_layout(template="plotly_dark", title="Implied Volatility Surface", height=420, scene=dict(zaxis_title="IV"))
    st.plotly_chart(surface, use_container_width=True)

with col2:
    smile = chain[chain["expiry_days"] == 30]
    fig_smile = go.Figure()
    fig_smile.add_trace(go.Scatter(x=smile["strike"], y=smile["iv"] * 100, mode="lines+markers", name="30d smile"))
    fig_smile.update_layout(template="plotly_dark", title="Volatility Smile (30d)", height=420)
    st.plotly_chart(fig_smile, use_container_width=True)

st.subheader("Options chain · Greeks")
st.dataframe(
    chain[chain["expiry_days"] == 30][["strike", "iv", "price", "delta", "gamma", "vega", "theta"]].round(4),
    use_container_width=True,
    hide_index=True,
)
render_footer()
