"""Inspection engine: the firewall's brain.

Wires the detection layers into the request lifecycle, mutates the request
(redaction) and the upstream completion (tool-call stripping) in place, and
emits signed receipts + dashboard events for every decision.
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime

from .config import Settings
from .detect import cost, injection, pii
from .detect.judge import judge_action
from .detect.rules import check_tool_calls
from .events import EventBus
from .groq_client import GroqClient
from .policy import Policy
from .receipts import sign
from .schemas import (
    Action,
    ChatCompletionRequest,
    CheckResult,
    Decision,
    Event,
    Receipt,
    Status,
    ToolCall,
)
from .store import Store, summarize_request


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


class Engine:
    def __init__(
        self,
        settings: Settings,
        policy: Policy,
        store: Store,
        client: GroqClient,
        bus: EventBus,
    ) -> None:
        self.settings = settings
        self.policy = policy
        self.store = store
        self.client = client
        self.bus = bus

    # ------------------------------------------------------------------ #
    # public entry point
    # ------------------------------------------------------------------ #
    async def handle(self, payload: dict, session_id: str) -> dict:
        """Full proxy flow. Returns the (possibly modified) completion dict."""
        # 1) inbound inspection (mutates payload for redaction)
        inbound = await self.inspect_inbound(payload, session_id)
        inbound_receipt = await self._finalize("inbound", payload, inbound, session_id)

        if inbound.action is Action.BLOCK:
            return self._refusal_completion(payload, inbound, inbound_receipt)

        # 2) forward to upstream provider
        completion = await self.client.chat_completion(payload)

        # 3) outbound inspection (mutates completion for tool-call stripping)
        outbound = await self.inspect_outbound(payload, completion)
        outbound_receipt = await self._finalize("outbound", payload, outbound, session_id)

        completion["firewall"] = {
            "action": outbound.action.value,
            "reason": outbound.reason,
            "rule_fired": outbound.rule_fired,
            "receipt_id": outbound_receipt.id,
            "stripped_tool_calls": outbound.stripped_tool_calls,
        }
        return completion

    # ------------------------------------------------------------------ #
    # inbound
    # ------------------------------------------------------------------ #
    async def inspect_inbound(self, payload: dict, session_id: str) -> Decision:
        decision = Decision()

        # cost guard
        used = self.store.add_usage(session_id, cost.estimate_tokens(payload))
        cost_check = cost.check_budget(used, self.policy)
        decision.checks.append(cost_check)
        if cost_check.status is Status.BLOCK:
            decision.action = Action.BLOCK
            decision.reason = cost_check.detail
            decision.rule_fired = "cost_guard"
            return decision

        messages = payload.get("messages", []) or []
        redactions = 0
        worst_injection: CheckResult | None = None

        for msg in messages:
            content = msg.get("content")
            role = msg.get("role")
            if not isinstance(content, str) or not content:
                continue

            # injection scan on untrusted surfaces (tool results + user input)
            if role in ("tool", "user"):
                groq_score = None
                if role == "tool":
                    groq_score = await self.client.prompt_guard_score(content)
                inj = injection.scan_text(content, self.policy, source=role, groq_score=groq_score)
                if inj.status is Status.FLAG and (
                    worst_injection is None or (inj.score or 0) > (worst_injection.score or 0)
                ):
                    worst_injection = inj

            # PII / secret redaction before content leaves to the provider
            redacted, pii_check = pii.scan_and_redact(content, self.policy, source=role or "msg")
            if pii_check.status is Status.FLAG:
                msg["content"] = redacted
                redactions += len(pii_check.meta.get("labels", []))
                decision.checks.append(pii_check)

        if worst_injection is not None:
            decision.checks.append(worst_injection)

        decision.redactions = redactions
        decision.modified = redactions > 0
        if redactions > 0:
            decision.action = Action.REDACT
            decision.reason = "PII/secrets redacted from request before forwarding"
        elif worst_injection is not None:
            decision.reason = "injection signal detected in inbound content"
        return decision

    # ------------------------------------------------------------------ #
    # outbound
    # ------------------------------------------------------------------ #
    async def inspect_outbound(self, payload: dict, completion: dict) -> Decision:
        decision = Decision()
        choices = completion.get("choices") or []
        if not choices:
            return decision
        message = choices[0].get("message") or {}

        # 1) tool-call enforcement
        raw_calls = message.get("tool_calls") or []
        tool_calls = [ToolCall.model_validate(tc) for tc in raw_calls]
        if tool_calls:
            findings, rules_check = check_tool_calls(tool_calls, self.policy)
            decision.checks.append(rules_check)
            blocked_ids = {f.tool_call_id for f in findings if f.status is Status.BLOCK}

            if blocked_ids:
                # strip the offending tool calls so the agent never executes them
                kept = [tc for tc in raw_calls if tc.get("id") not in blocked_ids]
                message["tool_calls"] = kept or None
                if not kept and not message.get("content"):
                    message["content"] = self.policy.block_message
                    choices[0]["finish_reason"] = "stop"
                decision.action = Action.BLOCK
                decision.stripped_tool_calls = sorted(blocked_ids)
                decision.modified = True
                first_blocked = next(f for f in findings if f.status is Status.BLOCK)
                decision.rule_fired = "deterministic_rules"
                decision.reason = "; ".join(first_blocked.reasons)

                # 2) selective safeguard judge — adds auditable reasoning
                judged, reasoning = await judge_action(
                    self.client, self.policy, _describe_calls(findings)
                )
                if judged is not None:
                    decision.checks.append(judged)
                if reasoning:
                    decision.reasoning = reasoning

        # 3) redact secrets/PII the model may have emitted in its text
        content = message.get("content")
        if isinstance(content, str) and content:
            redacted, pii_check = pii.scan_and_redact(content, self.policy, source="completion")
            if pii_check.status is Status.FLAG:
                message["content"] = redacted
                decision.checks.append(pii_check)
                decision.redactions += len(pii_check.meta.get("labels", []))
                decision.modified = True
                if decision.action is Action.ALLOW:
                    decision.action = Action.REDACT
                    decision.reason = "secret/PII redacted from model output"

        return decision

    # ------------------------------------------------------------------ #
    # finalize: receipt + event
    # ------------------------------------------------------------------ #
    async def _finalize(
        self, direction: str, payload: dict, decision: Decision, session_id: str
    ) -> Receipt:
        receipt = Receipt(
            id=_uid("rcpt"),
            ts=_now(),
            session_id=session_id,
            model=payload.get("model", ""),
            direction=direction,
            decision=decision,
            request_summary=summarize_request(payload),
        )
        sign(receipt, self.settings.hmac_secret)
        self.store.save_receipt(receipt)

        event = Event(
            id=_uid("evt"),
            ts=receipt.ts,
            session_id=session_id,
            action=decision.action,
            status=decision.worst_status(),
            title=_title(direction, decision),
            detail=decision.reason or decision.rule_fired or "",
            rule=decision.rule_fired,
            receipt_id=receipt.id,
            checks=decision.checks,
        )
        self.store.save_event(event)
        await self.bus.publish(event)
        return receipt

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _refusal_completion(self, payload: dict, decision: Decision, receipt: Receipt) -> dict:
        return {
            "id": _uid("fw"),
            "object": "chat.completion",
            "created": int(time.time()),
            "model": payload.get("model", ""),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": self.policy.block_message},
                    "finish_reason": "content_filter",
                }
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "firewall": {
                "action": decision.action.value,
                "reason": decision.reason,
                "rule_fired": decision.rule_fired,
                "receipt_id": receipt.id,
            },
        }


def _describe_calls(findings: list) -> str:
    parts = []
    for f in findings:
        if f.status is Status.BLOCK:
            parts.append(f"tool={f.tool_name} hosts={f.hosts} reasons={f.reasons}")
    return "\n".join(parts)


def _title(direction: str, decision: Decision) -> str:
    if decision.action is Action.BLOCK:
        if decision.rule_fired == "cost_guard":
            return "Token budget exceeded"
        if decision.stripped_tool_calls:
            return "Blocked tool call"
        return "Blocked by policy"
    if decision.action is Action.REDACT:
        return "PII / secret redacted"
    if decision.worst_status() is Status.FLAG:
        return "Injection flagged"
    return "Allowed"


def validate_request(payload: dict) -> ChatCompletionRequest:
    """Parse for validation side effects; raises on malformed input."""
    return ChatCompletionRequest.model_validate(payload)
