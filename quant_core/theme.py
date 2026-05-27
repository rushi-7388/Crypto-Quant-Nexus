"""Unified Streamlit UI theme for all Nexus modules."""

from quant_core.brand import AUTHOR, BRAND, GITHUB, VERSION


def inject_theme() -> None:
    import streamlit as st

    st.markdown(
        f"""
        <style>
        .stApp {{
            background: linear-gradient(165deg, #030508 0%, #0a0f1a 45%, #0d1526 100%);
            color: #e8ecf4;
        }}
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #060a12, #0c1424);
            border-right: 1px solid rgba(99, 179, 237, 0.15);
        }}
        .nexus-header {{
            font-size: 0.85rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: #63b3ed;
            margin-bottom: 0.25rem;
        }}
        .nexus-footer {{
            font-size: 0.75rem;
            color: #64748b;
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid rgba(100, 116, 139, 0.3);
        }}
        div[data-testid="stMetricValue"] {{
            font-variant-numeric: tabular-nums;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(module_name: str, subtitle: str) -> None:
    import streamlit as st

    st.markdown(f'<p class="nexus-header">{BRAND} · v{VERSION}</p>', unsafe_allow_html=True)
    st.title(module_name)
    st.caption(subtitle)


def render_footer() -> None:
    import streamlit as st

    st.markdown(
        f'<p class="nexus-footer">© 2026 {AUTHOR} · '
        f'<a href="{GITHUB}" style="color:#63b3ed">{GITHUB}</a> · Research & education only</p>',
        unsafe_allow_html=True,
    )
