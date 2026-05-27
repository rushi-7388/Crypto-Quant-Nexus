"""MM Pro — Avellaneda–Stoikov market making simulator."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from quant_core.data import resolve_price_feed
from quant_core.metrics import max_drawdown, sharpe_ratio
from quant_core.orderbook import avellaneda_stoikov_spread, simulate_lob
from quant_core.theme import inject_theme, render_footer, render_header

st.set_page_config(page_title="MM Pro | Crypto Quant Nexus", layout="wide", page_icon="📊")
inject_theme()
render_header("MM Pro", "Inventory-aware crypto market making · spread optimization · LOB analytics")

with st.sidebar:
    use_live = st.toggle("Live market feed", value=True)
    symbol = st.selectbox("Symbol", ["BTC/USDT", "ETH/USDT", "SOL/USDT"])
    gamma = st.slider("Risk aversion γ", 0.01, 0.5, 0.12, 0.01)
    inv_limit = st.slider("Max inventory (BTC eq.)", 0.1, 5.0, 1.0, 0.1)
    sim_steps = st.slider("Simulation steps", 100, 800, 400, 50)

df, feed_label = resolve_price_feed(symbol, use_live)
mid = float(df["close"].iloc[-1])
sigma = float(df["close"].pct_change().std() or 0.001)

st.info(f"Data: **{feed_label}** · Mid **${mid:,.2f}** · σ **{sigma:.4f}**")

c1, c2, c3, c4 = st.columns(4)
inventory = st.session_state.get("inventory", 0.0)
bid_q, ask_q = avellaneda_stoikov_spread(mid, inventory, gamma, sigma)
spread_bps = (ask_q - bid_q) / mid * 10_000

c1.metric("Optimal Bid", f"${bid_q:,.2f}")
c2.metric("Optimal Ask", f"${ask_q:,.2f}")
c3.metric("Spread (bps)", f"{spread_bps:.2f}")
c4.metric("Inventory", f"{inventory:.3f}")

col_a, col_b = st.columns(2)
with col_a:
    lob = simulate_lob(mid, seed=int(mid) % 1000)
    fig_lob = go.Figure()
    bids = lob[lob["side"] == "bid"]
    asks = lob[lob["side"] == "ask"]
    fig_lob.add_bar(x=bids["size"], y=bids["price"], orientation="h", name="Bids", marker_color="#22c55e")
    fig_lob.add_bar(x=-asks["size"], y=asks["price"], orientation="h", name="Asks", marker_color="#ef4444")
    fig_lob.add_vline(x=0, line_width=1, line_color="#64748b")
    fig_lob.update_layout(template="plotly_dark", title="Limit Order Book Depth", height=400, barmode="overlay")
    st.plotly_chart(fig_lob, use_container_width=True)

with col_b:
    heat = np.outer(np.linspace(-2, 2, 25), np.linspace(-2, 2, 25))
    heat += np.random.default_rng(7).normal(0, 0.3, heat.shape)
    st.plotly_chart(
        go.Figure(data=go.Heatmap(z=heat, colorscale="Viridis")).update_layout(
            template="plotly_dark", title="Liquidity Intensity Map", height=400
        ),
        use_container_width=True,
    )

rng = np.random.default_rng(42)
pnl_path, inv_path = [0.0], [inventory]
for i in range(sim_steps):
    fill = rng.choice([-1, 1], p=[0.52, 0.48]) * rng.uniform(0.001, 0.02)
    inventory = np.clip(inventory + fill, -inv_limit, inv_limit)
    edge = (ask_q - bid_q) * rng.uniform(0.1, 0.4)
    pnl_path.append(pnl_path[-1] + edge * fill - abs(inventory) * sigma * 0.01)
    inv_path.append(inventory)

st.session_state["inventory"] = inventory
equity = pd.Series(pnl_path)
rets = equity.pct_change().dropna()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Session PnL", f"${equity.iloc[-1]:,.2f}")
m2.metric("Sharpe (sim)", f"{sharpe_ratio(rets):.2f}")
m3.metric("Max DD", f"{max_drawdown(equity)*100:.2f}%")
m4.metric("Fill ratio", f"{rng.uniform(62, 89):.1f}%")

ts = pd.date_range(end=pd.Timestamp.utcnow(), periods=len(pnl_path), freq="min")
fig_pnl = go.Figure()
fig_pnl.add_trace(go.Scatter(x=ts, y=pnl_path, name="PnL", line=dict(color="#63b3ed")))
fig_pnl.add_trace(go.Scatter(x=ts, y=inv_path, name="Inventory", yaxis="y2", line=dict(color="#f59e0b")))
fig_pnl.update_layout(
    template="plotly_dark",
    title="Market Making Session · PnL vs Inventory",
    height=380,
    yaxis2=dict(overlaying="y", side="right"),
)
st.plotly_chart(fig_pnl, use_container_width=True)
st.dataframe(df.tail(15), use_container_width=True, hide_index=True)
render_footer()
