"""Deployment helpers — API docs URL resolution for hub and docs."""

from __future__ import annotations

import os

from quant_core.brand import DEFAULT_API_DOCS_URL


def resolve_api_docs_url() -> str:
    """Swagger UI URL — local default or Render base URL (appends /docs when missing)."""
    raw = os.getenv("API_DOCS_URL", DEFAULT_API_DOCS_URL).strip()
    if not raw:
        return DEFAULT_API_DOCS_URL
    raw = raw.rstrip("/")
    if raw.endswith("/docs"):
        return raw
    if raw.endswith("/redoc"):
        return raw.replace("/redoc", "/docs")
    return f"{raw}/docs"
