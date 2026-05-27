"""Alpha Terminal — unified quant research command center (flagship v3)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from quant_core.brand import BRAND, VERSION
from quant_core.data import resolve_price_feed
from quant_core.logging_config import configure_logging
from quant_core.platform.catalog import ASSET_UNIVERSE, cache_ohlcv, list_universe
from quant_core.platform.quality import ohlcv_quality_report
from quant_core.research.alpha_fusion import composite_alpha, fuse_multi_asset
from quant_core.research.flow_backtest import run_flow_alpha_backtest
from quant_core.theme import inject_theme, render_footer, render_header

configure_logging(service_name="alpha-terminal")

st.set_page_config(
    page_title=f"Alpha Terminal | {BRAND}",
    layout="wide",
    page_icon="🌐",
)
inject_theme()
render_header(
    "Alpha Terminal",
    "Multi-signal fusion · walk-forward backtests · universe ranking · data quality",
)

with st.sidebar:
    symbol = st.selectbox("Primary asset", list_universe())
    use_live = st.toggle("Live market data", True)
    window = st.slider("Lookback bars", 300, 800, 500, 50)
    run_cache = st.button("Cache OHLCV to parquet")

if run_cache:
    path = cache_ohlcv(symbol, use_live=use_live)
    st.sidebar.success(f"Cached → {path}")

df, feed = resolve_price_feed(symbol, use_live)
df = df.tail(window).copy()
quality = ohlcv_quality_report(df)

tab_alpha, tab_bt, tab_uni, tab_dq = st.tabs(
    ["Composite Alpha", "Walk-Forward Backtest", "Universe Rank", "Data Quality"]
)

with tab_alpha:
    with st.spinner("Fusing flow · regime · momentum · funding…"):
        alpha = composite_alpha(symbol, use_live=use_live, window=window)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Composite score", f"{alpha['composite_score']:+.3f}", help="-1 bearish … +1 bullish")
    c2.metric("Conviction", f"{alpha['conviction']:.1%}")
    c3.metric("Action", alpha["recommendation"])
    c4.metric("Flow signal", alpha["components"]["flow"]["signal"])

    comp = alpha["components"]
    fig = go.Figure(
        go.Bar(
            x=list(comp.keys()),
            y=[comp[k]["score"] for k in comp],
            marker_color=["#63b3ed", "#8b5cf6", "#34d399", "#fbbf24"],
        )
    )
    fig.update_layout(
        template="plotly_dark",
        title="Signal component scores",
        yaxis_range=[-1, 1],
        height=320,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.json(alpha)
    st.caption(f"Feed: {feed} · {ASSET_UNIVERSE.get(symbol, {}).get('sector', 'crypto')}")

with tab_bt:
    st.caption("Purged walk-forward ML backtest (Lopez de Prado style gap) — research only.")
    if st.button("Run Flow Alpha backtest", type="primary"):
        with st.spinner("Walk-forward folds…"):
            bt = run_flow_alpha_backtest(df, symbol=symbol)
        m = bt.metrics
        cols = st.columns(5)
        cols[0].metric("Sharpe", f"{m['sharpe']:.2f}")
        cols[1].metric("Sortino", f"{m['sortino']:.2f}")
        cols[2].metric("Max DD", f"{m['max_drawdown']:.1%}")
        cols[3].metric("Hit rate", f"{m['hit_rate']:.1%}")
        cols[4].metric("Calmar", f"{m['calmar']:.2f}")
        if len(bt.equity_curve) > 0:
            eq_fig = go.Figure()
            eq_fig.add_trace(
                go.Scatter(y=bt.equity_curve.values, name="Strategy", line=dict(color="#63b3ed"))
            )
            eq_fig.update_layout(template="plotly_dark", title="OOS equity curve", height=360)
            st.plotly_chart(eq_fig, use_container_width=True)
        st.dataframe(pd.DataFrame(bt.folds), use_container_width=True, hide_index=True)

with tab_uni:
    st.caption("Cross-sectional rank — composite alpha across institutional universe.")
    top_n = st.slider("Top N", 3, 6, 5)
    if st.button("Rank universe"):
        with st.spinner("Scoring assets…"):
            ranked = fuse_multi_asset(use_live=use_live, top_n=top_n)
        st.dataframe(ranked, use_container_width=True, hide_index=True)
        if not ranked.empty:
            rfig = go.Figure(
                go.Bar(
                    x=ranked["symbol"],
                    y=ranked["composite_score"],
                    marker_color=ranked["composite_score"],
                    marker_colorscale="RdYlGn",
                )
            )
            rfig.update_layout(template="plotly_dark", title="Alpha rank", height=300)
            st.plotly_chart(rfig, use_container_width=True)

with tab_dq:
    c1, c2 = st.columns(2)
    c1.metric("Quality score", f"{quality['score']:.0%}")
    c2.metric("Passed", "Yes" if quality["passed"] else "No")
    st.write("Issues:", quality["issues"] or "None")
    st.metric("Rows validated", quality["rows"])

st.caption(f"{BRAND} v{VERSION} · Alpha Terminal · Not financial advice")
render_footer()
