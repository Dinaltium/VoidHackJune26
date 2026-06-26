"""Prompt-injection detection.

Two tiers:
  • Heuristic (local, always-on): phrase + structural signals. Deterministic,
    offline, the basis for tests.
  • Prompt Guard 2 (Groq, optional): Meta's 86M classifier, used to raise the
    score when a key is present. Never the sole gate — fail-closed on its errors.
"""

from __future__ import annotations

import re
import time

from ..policy import Policy
from ..schemas import CheckResult, Status

# structural signals beyond literal phrases
_IMPERATIVE_TO_MODEL = re.compile(
    r"\b(ignore|disregard|forget|override)\b.{0,30}\b(previous|prior|above|earlier|all)\b",
    re.IGNORECASE,
)
_ROLE_CONFUSION = re.compile(
    r"\b(you are now|act as|pretend to be|new system prompt)\b", re.IGNORECASE
)
_EXFIL = re.compile(
    r"\b(exfiltrat|send|email|forward|post|upload|leak)\b.{0,40}"
    r"\b(key|secret|token|credential|password|api)\b",
    re.IGNORECASE,
)


def heuristic_score(text: str, policy: Policy) -> tuple[float, list[str]]:
    """Return (score 0..1, matched signal names) for a piece of text."""
    if not text:
        return 0.0, []
    lowered = text.lower()
    signals: list[str] = []
    score = 0.0

    for phrase in policy.injection_phrases:
        if phrase.lower() in lowered:
            signals.append(f"phrase:{phrase}")
            score = max(score, 0.85)

    if _IMPERATIVE_TO_MODEL.search(text):
        signals.append("imperative_override")
        score = max(score, 0.9)
    if _ROLE_CONFUSION.search(text):
        signals.append("role_confusion")
        score = max(score, 0.8)
    if _EXFIL.search(text):
        signals.append("exfiltration_intent")
        score = max(score, 0.92)

    return score, signals


def scan_text(
    text: str,
    policy: Policy,
    *,
    source: str = "content",
    groq_score: float | None = None,
) -> CheckResult:
    """Combine heuristic and (optional) Prompt Guard 2 score into one verdict."""
    t0 = time.perf_counter()
    score, signals = heuristic_score(text, policy)
    if groq_score is not None:
        score = max(score, groq_score)
        signals.append(f"prompt_guard_2:{groq_score:.2f}")

    status = Status.FLAG if score >= policy.injection_threshold else Status.PASS
    detail = (
        f"injection signals in {source}: {', '.join(signals)}"
        if signals
        else f"no injection signal in {source}"
    )
    return CheckResult(
        name="injection_scan",
        status=status,
        detail=detail,
        score=round(score, 3),
        latency_ms=(time.perf_counter() - t0) * 1000,
        meta={"source": source, "signals": signals},
    )
