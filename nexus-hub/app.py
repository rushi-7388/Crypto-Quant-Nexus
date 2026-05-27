"""Crypto Quant Nexus 3.0 — unified product launcher & portfolio hub."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from quant_core.brand import AUTHOR, BRAND, GITHUB, GITHUB_REPO, PLATFORM_EDITION, TAGLINE, VERSION
from quant_core.deploy import resolve_api_docs_url
from quant_core.theme import inject_theme, render_footer

st.set_page_config(page_title=f"{BRAND} 3.0", layout="wide", page_icon="🚀")
inject_theme()

api_docs_url = resolve_api_docs_url()

st.markdown(f'<p class="nexus-header">{BRAND} · v{VERSION} · {PLATFORM_EDITION}</p>', unsafe_allow_html=True)
st.title("Quantitative Crypto Analytics Suite")
st.markdown(f"**{TAGLINE}**")
st.markdown(f"Built by [**{AUTHOR}**]({GITHUB}) · 2026 · [Repository]({GITHUB_REPO})")

plat1, plat2, plat3, plat4 = st.columns(4)
with plat1:
    st.link_button("Alpha Terminal", "http://localhost:8502", use_container_width=True, help="Run: streamlit run alpha-terminal/app.py")
with plat2:
    st.link_button("API docs (Swagger)", api_docs_url, use_container_width=True)
with plat3:
    st.link_button("CI pipeline", f"{GITHUB_REPO}/actions/workflows/ci.yml", use_container_width=True)
with plat4:
    st.link_button("Research docs", f"{GITHUB_REPO}/blob/main/docs/RESEARCH.md", use_container_width=True)

st.info(
    "**Flagship v3:** [Alpha Terminal](../alpha-terminal) fuses flow, regime, momentum & funding "
    "with purged walk-forward backtests and a 6-asset institutional universe."
)

PRODUCTS = [
    {
        "name": "Alpha Terminal",
        "folder": "alpha-terminal",
        "flagship": True,
        "desc": "Multi-signal fusion · universe rank · walk-forward backtest · data quality",
        "tech": "/v2/alpha/composite · /v2/research/backtest/flow",
    },
    {
        "name": "MM Pro",
        "folder": "mm-engine",
        "desc": "Avellaneda–Stoikov market making · LOB depth · inventory PnL",
        "tech": "LOB sim, spread optimization",
    },
    {
        "name": "Funding Radar",
        "folder": "funding-radar",
        "desc": "Cross-venue funding rates · arb edge scanner · carry history",
        "tech": "CCXT, multi-exchange",
    },
    {
        "name": "Flow Alpha",
        "folder": "flow-alpha",
        "desc": "Order flow imbalance · gradient boosting signals",
        "tech": "OFI, scikit-learn · `/v1/ml/flow/signal`",
    },
    {
        "name": "Vol Surface",
        "folder": "vol-surface",
        "desc": "IV surface 3D · smile/skew · Greeks chain",
        "tech": "Black–Scholes · `/v1/options/greeks`",
    },
    {
        "name": "Regime Nexus",
        "folder": "regime-nexus",
        "desc": "Bull/bear/panic regime ML · transition matrix",
        "tech": "K-Means · `/v1/ml/regime/current`",
    },
]

st.subheader("Products")
cols = st.columns(2)
for i, p in enumerate(PRODUCTS):
    with cols[i % 2]:
        prefix = "⭐ " if p.get("flagship") else ""
        st.markdown(f"### {prefix}{p['name']}")
        st.write(p["desc"])
        st.caption(p["tech"])
        st.code(f"streamlit run {p['folder']}/app.py", language="bash")

st.divider()
st.subheader("Quick start")
st.code(
    """pip install -r requirements.txt
make train                    # ML artifacts
streamlit run alpha-terminal/app.py   # flagship research UI
streamlit run nexus-hub/app.py        # this launcher
uvicorn api.main:app --port 8000      # REST + /v2/alpha/*""",
    language="bash",
)

st.subheader("Deploy live")
tab_streamlit, tab_render, tab_docker = st.tabs(["Streamlit Cloud", "Render (hub + API)", "Docker"])

with tab_streamlit:
    st.markdown(
        f"""
1. Push to [Crypto-Quant-Nexus]({GITHUB_REPO})
2. [share.streamlit.io](https://share.streamlit.io) → deploy `alpha-terminal/app.py` or `nexus-hub/app.py`
3. Set secret `API_DOCS_URL` to your FastAPI `/docs` URL
"""
    )

with tab_render:
    st.markdown(
        f"""
1. [Render Blueprint](https://dashboard.render.com) → [`render.yaml`]({GITHUB_REPO}/blob/main/render.yaml)
2. Hub + API services · [deploy guide]({GITHUB_REPO}/blob/main/docs/deploy-render.md)
"""
    )

with tab_docker:
    st.code("docker compose up --build", language="bash")

render_footer()
