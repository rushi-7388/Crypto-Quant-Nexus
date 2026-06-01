"""Shared Streamlit panel for Quant Copilot."""

from __future__ import annotations

from typing import Any, Callable

import streamlit as st


def render_copilot_panel(
    api_get: Callable[[str], dict[str, Any]],
    api_post: Callable[[str, dict[str, Any] | None], dict[str, Any]],
) -> None:
    st.subheader("Quant Copilot (RAG)")
    st.caption("Retrieval over audit chain, inference events, model cards, and backtest logs.")

    try:
        status = api_get("/v2/copilot/status")
    except Exception as exc:
        st.warning(f"Copilot status unavailable: {exc}")
        status = {}

    c1, c2, c3 = st.columns(3)
    c1.metric("Indexed chunks", status.get("chunk_count", 0))
    c2.metric("LLM provider", status.get("provider", "mock"))
    c3.metric("Index built", "yes" if status.get("indexed") else "no")

    if st.button("Rebuild copilot index", type="secondary"):
        with st.spinner("Indexing audit, events, model cards, backtests…"):
            try:
                out = api_post("/v2/copilot/index", {})
                st.success(f"Indexed {out.get('chunk_count', 0)} chunks.")
            except Exception as exc:
                st.error(str(exc))

    question = st.text_area(
        "Ask about decisions, backtests, or model governance",
        placeholder="e.g. What is the latest BTC backtest Sharpe? Is the audit chain intact?",
        height=100,
    )
    top_k = st.slider("Retrieval top-k", min_value=1, max_value=10, value=5)

    if st.button("Ask copilot", type="primary", disabled=not question.strip()):
        with st.spinner("Retrieving context…"):
            try:
                resp = api_post("/v2/copilot/ask", {"question": question.strip(), "top_k": top_k})
            except Exception as exc:
                st.error(str(exc))
                return
        st.markdown("**Answer**")
        st.write(resp.get("answer", ""))
        st.caption(f"trace_id: `{resp.get('trace_id')}` · provider: `{resp.get('provider')}`")
        sources = resp.get("sources", [])
        if sources:
            with st.expander("Sources", expanded=True):
                for src in sources:
                    st.markdown(
                        f"**{src.get('source_type')}** · score `{src.get('score')}` · "
                        f"`{src.get('metadata', {})}`"
                    )
                    st.code(src.get("excerpt", ""), language="text")
