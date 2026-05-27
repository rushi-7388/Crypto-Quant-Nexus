"""Train all ML models (used by Makefile and nightly CI)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    scripts = [
        ROOT / "mlops" / "training" / "train_flow_alpha.py",
        ROOT / "mlops" / "training" / "train_regime_nexus.py",
    ]
    for script in scripts:
        result = subprocess.run([sys.executable, str(script), "--no-live"], check=False)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
