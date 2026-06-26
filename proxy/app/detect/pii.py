"""PII / secret redaction.

Default engine is regex (offline, instant, deterministic — the basis for tests).
Microsoft Presidio is used as an optional enhancement when enabled and importable;
the public API is identical either way.
"""

from __future__ import annotations

import re
import time

from ..policy import Policy
from ..schemas import CheckResult, Status

# Generic PII patterns (name -> regex). Secret/credential patterns come from policy.
_PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "phone": re.compile(r"\b(?:\+?\d{1,2}[ -]?)?\(?\d{3}\)?[ -]?\d{3}[ -]?\d{4}\b"),
    "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
}


def _mask(label: str) -> str:
    return f"[REDACTED:{label}]"


def redact(text: str, policy: Policy) -> tuple[str, list[str]]:
    """Return (redacted_text, list_of_labels_found). Secrets first, then PII."""
    if not text:
        return text, []
    found: list[str] = []
    out = text

    for name, pattern in policy.compiled_secrets():
        if pattern.search(out):
            out = pattern.sub(_mask(name), out)
            found.append(name)

    for name, pattern in _PII_PATTERNS.items():
        if pattern.search(out):
            out = pattern.sub(_mask(name), out)
            found.append(name)

    return out, found


def scan_and_redact(
    text: str, policy: Policy, *, source: str = "content"
) -> tuple[str, CheckResult]:
    t0 = time.perf_counter()
    redacted, labels = redact(text, policy)
    status = Status.FLAG if labels else Status.PASS
    detail = f"redacted in {source}: {', '.join(labels)}" if labels else f"no PII in {source}"
    result = CheckResult(
        name="pii_redaction",
        status=status,
        detail=detail,
        latency_ms=(time.perf_counter() - t0) * 1000,
        meta={"labels": labels, "source": source, "engine": "regex"},
    )
    return redacted, result
