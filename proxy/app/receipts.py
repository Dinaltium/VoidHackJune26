"""Tamper-evident decision receipts.

A receipt's `payload_hash` is the SHA-256 of a canonical JSON view of the
security-relevant fields; `signature` is an HMAC-SHA256 of that hash under the
server secret. Anyone with the secret can recompute and detect tampering.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from .schemas import Receipt


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_hash(receipt: Receipt) -> str:
    """Hash the immutable, security-relevant projection of a receipt."""
    payload = {
        "id": receipt.id,
        "ts": receipt.ts,
        "session_id": receipt.session_id,
        "model": receipt.model,
        "direction": receipt.direction,
        "decision": receipt.decision.model_dump(mode="json"),
        "request_summary": receipt.request_summary,
    }
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def sign(receipt: Receipt, secret: str) -> Receipt:
    receipt.payload_hash = compute_hash(receipt)
    receipt.signature = hmac.new(
        secret.encode("utf-8"), receipt.payload_hash.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return receipt


def verify(receipt: Receipt, secret: str) -> bool:
    """True iff the receipt's hash matches its contents AND the signature is valid."""
    expected_hash = compute_hash(receipt)
    if not hmac.compare_digest(expected_hash, receipt.payload_hash or ""):
        return False
    expected_sig = hmac.new(
        secret.encode("utf-8"), receipt.payload_hash.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_sig, receipt.signature or "")
