"""Nexus Hub API docs URL resolution."""

from quant_core.deploy import resolve_api_docs_url


def test_api_docs_url_default(monkeypatch):
    monkeypatch.delenv("API_DOCS_URL", raising=False)
    assert resolve_api_docs_url().endswith("/docs")


def test_api_docs_url_render_base(monkeypatch):
    monkeypatch.setenv("API_DOCS_URL", "https://cryptoquant-nexus-api.onrender.com")
    assert resolve_api_docs_url() == "https://cryptoquant-nexus-api.onrender.com/docs"
