"""Decision audit trail with signed, tamper-evident hash chain."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUDIT_LOG = Path("artifacts/audit/decisions.jsonl")


def stable_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _sign(payload: dict[str, Any], secret: str) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()


def _last_hash(path: Path = AUDIT_LOG) -> str:
    if not path.exists():
        return "GENESIS"
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    if not lines:
        return "GENESIS"
    last = json.loads(lines[-1])
    return str(last.get("chain_hash", "GENESIS"))


def append_decision_audit(
    *,
    trace_id: str,
    symbol: str,
    model_version: str,
    dataset_version: str,
    decision: dict[str, Any],
    rationale: dict[str, Any],
) -> dict[str, Any]:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    secret = os.getenv("AUDIT_SIGNING_KEY", "dev-only-change-me")
    prev_hash = _last_hash(AUDIT_LOG)
    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "trace_id": trace_id,
        "symbol": symbol,
        "model_version": model_version,
        "dataset_version": dataset_version,
        "decision": decision,
        "rationale": rationale,
        "prev_chain_hash": prev_hash,
    }
    record["decision_hash"] = stable_hash(record)
    chain_payload = {"prev_chain_hash": prev_hash, "decision_hash": record["decision_hash"]}
    record["chain_hash"] = stable_hash(chain_payload)
    record["signature"] = _sign(record, secret)
    with AUDIT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    return record


def verify_audit_chain(path: Path = AUDIT_LOG, secret: str | None = None) -> dict[str, Any]:
    if not path.exists():
        return {"ok": True, "records": 0, "errors": []}
    sign_key = secret or os.getenv("AUDIT_SIGNING_KEY", "dev-only-change-me")
    errors: list[str] = []
    prev = "GENESIS"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    for idx, row in enumerate(rows):
        if row.get("prev_chain_hash") != prev:
            errors.append(f"row_{idx}:prev_chain_mismatch")
        expected_chain = stable_hash(
            {"prev_chain_hash": row.get("prev_chain_hash"), "decision_hash": row.get("decision_hash")}
        )
        if row.get("chain_hash") != expected_chain:
            errors.append(f"row_{idx}:chain_hash_invalid")
        expected_sig = _sign(
            {k: v for k, v in row.items() if k != "signature"},
            sign_key,
        )
        if row.get("signature") != expected_sig:
            errors.append(f"row_{idx}:signature_invalid")
        prev = str(row.get("chain_hash"))
    return {"ok": len(errors) == 0, "records": len(rows), "errors": errors}
