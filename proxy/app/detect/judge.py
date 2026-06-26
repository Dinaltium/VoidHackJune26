"""Selective reasoning judge backed by gpt-oss-safeguard-20b.

Only invoked on already-flagged actions (defense-in-depth, not the hot path).
Its job is to add an auditable *explanation* — and, when fail-closed is off, to
optionally rescue a false positive. The deterministic layers still decide blocks
on their own; the judge enriches the receipt with reasoning.
"""

from __future__ import annotations

import time

from ..groq_client import GroqClient
from ..policy import Policy
from ..schemas import CheckResult, Status


async def judge_action(
    client: GroqClient,
    policy: Policy,
    content: str,
) -> tuple[CheckResult | None, str | None]:
    """Return (CheckResult, reasoning) or (None, None) if the judge is unavailable."""
    t0 = time.perf_counter()
    verdict = await client.safeguard(policy.as_prompt_text(), content)
    if verdict is None:
        return None, None
    status = Status.BLOCK if verdict.block else Status.PASS
    result = CheckResult(
        name="safeguard_judge",
        status=status,
        detail=("policy violation confirmed" if verdict.block else "no violation found"),
        latency_ms=(time.perf_counter() - t0) * 1000,
        meta={"model": "gpt-oss-safeguard-20b"},
    )
    return result, verdict.reasoning
