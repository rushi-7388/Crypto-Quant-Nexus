"""Optional MLflow experiment tracking for training jobs."""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Generator

logger = logging.getLogger(__name__)


def mlflow_enabled() -> bool:
    return bool(os.getenv("MLFLOW_TRACKING_URI"))


@contextmanager
def mlflow_run(experiment_name: str, run_name: str) -> Generator[Any, None, None]:
    """Start an MLflow run when tracking URI is configured."""
    if not mlflow_enabled():
        yield None
        return

    try:
        import mlflow

        mlflow.set_experiment(experiment_name)
        with mlflow.start_run(run_name=run_name) as run:
            yield run
    except Exception as exc:
        logger.warning("mlflow_unavailable error=%s", exc)
        yield None


def log_sklearn_model(model: Any, artifact_path: str, registered_name: str | None = None) -> None:
    if not mlflow_enabled():
        return
    try:
        import mlflow.sklearn

        mlflow.sklearn.log_model(
            model,
            artifact_path=artifact_path,
            registered_model_name=registered_name,
        )
    except Exception as exc:
        logger.warning("mlflow_log_model_failed error=%s", exc)
