"""Structured logging for quant_core and services."""

from __future__ import annotations

import logging
import os
import sys
from typing import Any


def configure_logging(service_name: str = "crypto-quant-nexus", level: str | None = None) -> None:
    """Configure JSON-friendly structured logging once per process."""
    log_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    root = logging.getLogger()
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt='{"time":"%(asctime)s","level":"%(levelname)s","service":"'
            + service_name
            + '","logger":"%(name)s","message":"%(message)s"}',
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    root.addHandler(handler)
    root.setLevel(log_level)


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    """Emit a single-line structured event."""
    extras = " ".join(f'{k}="{v}"' for k, v in fields.items())
    logger.info("%s %s", event, extras)
