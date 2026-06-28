from __future__ import annotations

import re

from .policy import Policy
from .schemas import CheckResult, Status

_PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("email", re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("credit_card", re.compile(r"\b(?:\d[ -]*?){13,16}\b")),
    (
        "phone",
        re.compile(r"\b(?:\+?\d{1,2}[ -]?)?\(?\d{3}\)?[ -]?\d{3}[ -]?\d{4}\b"),
    ),
    ("ipv4", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
]


def _mask(label: str) -> str:
    return f"[REDACTED:{label}]"


def redact(text: str, policy: Policy) -> tuple[str, list[str]]:
    if not text:
        return text, []

    labels: list[str] = []
    out = text

    for name, pattern in policy.compiled_secrets():
        if pattern.search(out):
            out = pattern.sub(_mask(name), out)
            labels.append(name)

    for name, pattern in _PII_PATTERNS:
        if pattern.search(out):
            out = pattern.sub(_mask(name), out)
            labels.append(name)

    return out, labels


def scan_and_redact(text: str, policy: Policy, source: str = "content") -> tuple[str, CheckResult]:
    redacted, labels = redact(text, policy)
    status = Status.FLAG if labels else Status.PASS
    detail = f"redacted in {source}: {', '.join(labels)}" if labels else f"no PII in {source}"
    return redacted, CheckResult(
        name="pii_redaction",
        status=status,
        detail=detail,
        meta={"labels": labels},
    )
