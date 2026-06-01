"""Consumer dashboard for event-driven inference + canary + audit health."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from quant_core.brand import BRAND, VERSION
from quant_core.copilot.ui_streamlit import render_copilot_panel
from quant_core.theme import inject_theme, render_footer, render_header

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

st.set_page_config(page_title=f"Ops Dashboard | {BRAND}", page_icon="📡", layout="wide")
inject_theme()
render_header("Ops Dashboard", "Kafka requests vs scored outputs · canary policy · audit integrity")

st.caption(f"API base: `{API_BASE}`")


def _get(path: str) -> dict:
    r = requests.get(f"{API_BASE}{path}", timeout=20)
    r.raise_for_status()
    return r.json()


def _post(path: str, payload: dict | None) -> dict:
    r = requests.post(f"{API_BASE}{path}", json=payload or {}, timeout=120)
    r.raise_for_status()
    return r.json()


try:
    dash = _get("/v2/events/dashboard")
    canary = _get("/v2/canary/status")
    audit = _get("/v2/audit/verify")
except Exception as exc:
    st.error(f"Cannot reach API: {exc}")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Requests", dash.get("request_count", 0))
c2.metric("Scored outputs", dash.get("result_count", 0))
c3.metric("Matched traces", dash.get("matched_count", 0))
c4.metric("Avg process ms", dash.get("avg_processed_ms", 0.0))

st.subheader("Canary status")
cc1, cc2, cc3 = st.columns(3)
cc1.metric("Active model", canary.get("active_model", "unknown"))
cc2.metric("Shadow win-rate", f"{canary.get('shadow_win_rate', 0.0):.2%}")
cc3.metric("Avg divergence", f"{canary.get('avg_divergence', 0.0):.4f}")
st.write(
    {
        "promoted": canary.get("promoted", False),
        "rolled_back": canary.get("rolled_back", False),
        "samples": canary.get("samples", 0),
    }
)

st.subheader("Audit integrity")
st.write({"ok": audit.get("ok", False), "records": audit.get("records", 0), "errors": audit.get("errors", [])})

col1, col2 = st.columns(2)
with col1:
    st.subheader("Recent inference requests")
    st.dataframe(pd.DataFrame(dash.get("recent_requests", [])), use_container_width=True, hide_index=True)
with col2:
    st.subheader("Recent scored outputs")
    st.dataframe(pd.DataFrame(dash.get("recent_results", [])), use_container_width=True, hide_index=True)

st.divider()
render_copilot_panel(_get, _post)

render_footer()
st.caption(f"{BRAND} v{VERSION} · Forward-Deployed Monitoring")
