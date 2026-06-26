"""Async client for the upstream OpenAI-compatible provider (Groq).

Three responsibilities:
  • forward chat completions (the proxy's main job)
  • Prompt Guard 2 score (best-effort augmentation of the heuristic)
  • gpt-oss-safeguard verdict + reasoning (selective, on flagged actions)

Every model-backed helper is best-effort: on missing key, network error, or an
unparseable response it returns ``None`` and the caller relies on the
deterministic / heuristic layers. The proxy never hard-fails because a guard
model was unreachable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

from .config import Settings


@dataclass
class SafeguardVerdict:
    block: bool
    reasoning: str


class GroqClient:
    def __init__(self, settings: Settings) -> None:
        self._s = settings
        self._client = httpx.AsyncClient(
            base_url=settings.groq_base_url,
            timeout=settings.upstream_timeout_s,
            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    @property
    def enabled(self) -> bool:
        return self._s.groq_enabled

    # ------------------------------------------------------------------ #
    # main forward path
    # ------------------------------------------------------------------ #
    async def chat_completion(self, payload: dict) -> dict:
        """Forward a (sanitized) chat-completion request and return the JSON body."""
        resp = await self._client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------ #
    # Prompt Guard 2 (optional augmentation)
    # ------------------------------------------------------------------ #
    async def prompt_guard_score(self, text: str) -> float | None:
        if not self.enabled or not self._s.enable_groq_promptguard or not text.strip():
            return None
        try:
            resp = await self._client.post(
                "/chat/completions",
                json={
                    "model": self._s.promptguard_model,
                    "messages": [{"role": "user", "content": text[:4000]}],
                    "temperature": 0,
                },
            )
            resp.raise_for_status()
            body = resp.json()
            content = body["choices"][0]["message"]["content"]
            return _parse_guard_score(content)
        except (httpx.HTTPError, KeyError, IndexError, ValueError):
            return None

    # ------------------------------------------------------------------ #
    # gpt-oss-safeguard (policy-following reasoner)
    # ------------------------------------------------------------------ #
    async def safeguard(self, policy_text: str, content: str) -> SafeguardVerdict | None:
        if not self.enabled or not self._s.enable_safeguard_judge:
            return None
        system = (
            f"{policy_text}\n\n"
            "You are a safety classifier. Decide whether the CONTENT below "
            "violates the policy. Respond with a single line `VERDICT: ALLOW` or "
            "`VERDICT: BLOCK`, then a short `REASON:` explaining why."
        )
        try:
            resp = await self._client.post(
                "/chat/completions",
                json={
                    "model": self._s.safeguard_model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": f"CONTENT:\n{content[:6000]}"},
                    ],
                    "temperature": 0,
                },
            )
            resp.raise_for_status()
            body = resp.json()
            text = body["choices"][0]["message"]["content"]
            return _parse_safeguard(text)
        except (httpx.HTTPError, KeyError, IndexError, ValueError):
            return None


_SCORE_RE = re.compile(r"\b(?:score|probability|p)\s*[:=]\s*([01](?:\.\d+)?)", re.IGNORECASE)


def _parse_guard_score(content: str) -> float | None:
    """Map a Prompt Guard style response to a 0..1 score, best-effort."""
    if not content:
        return None
    m = _SCORE_RE.search(content)
    if m:
        return max(0.0, min(1.0, float(m.group(1))))
    lowered = content.lower()
    if any(k in lowered for k in ("injection", "jailbreak", "malicious", "unsafe", "label_1")):
        return 0.95
    if any(k in lowered for k in ("benign", "safe", "label_0")):
        return 0.0
    try:  # a bare float?
        return max(0.0, min(1.0, float(content.strip())))
    except ValueError:
        return None


def _parse_safeguard(text: str) -> SafeguardVerdict:
    lowered = text.lower()
    block = "verdict: block" in lowered or re.search(r"\bblock\b", lowered) is not None
    reason = text.strip()
    m = re.search(r"reason\s*[:\-]\s*(.+)", text, re.IGNORECASE | re.DOTALL)
    if m:
        reason = m.group(1).strip()
    return SafeguardVerdict(block=block, reasoning=reason[:800])
