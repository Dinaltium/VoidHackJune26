"""Per-session token cost guard.

A cheap char-based estimator (≈4 chars/token) avoids a tiktoken dependency.
Usage accumulates in the store; exceeding the policy budget blocks the turn.
"""

from __future__ import annotations

import time

from ..policy import Policy
from ..schemas import CheckResult, Status


def estimate_tokens(payload: dict) -> int:
    """Rough token estimate over all message content + tool schemas."""
    chars = 0
    for m in payload.get("messages", []) or []:
        content = m.get("content")
        if isinstance(content, str):
            chars += len(content)
        for tc in m.get("tool_calls", []) or []:
            chars += len(((tc.get("function") or {}).get("arguments")) or "")
    for t in payload.get("tools", []) or []:
        chars += len(str(t))
    return max(1, chars // 4)


def check_budget(session_total: int, policy: Policy) -> CheckResult:
    t0 = time.perf_counter()
    over = session_total > policy.token_budget_per_session
    status = Status.BLOCK if over else Status.PASS
    detail = (
        f"session token budget exceeded: {session_total}/{policy.token_budget_per_session}"
        if over
        else f"tokens {session_total}/{policy.token_budget_per_session}"
    )
    return CheckResult(
        name="cost_guard",
        status=status,
        detail=detail,
        latency_ms=(time.perf_counter() - t0) * 1000,
        meta={"session_total": session_total, "budget": policy.token_budget_per_session},
    )
