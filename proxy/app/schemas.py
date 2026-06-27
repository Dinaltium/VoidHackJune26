"""Pydantic models: OpenAI-compatible wire types + firewall decision types.

The OpenAI request/response models are intentionally lenient (`extra="allow"`)
so the proxy is a faithful pass-through for fields it does not care about.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# --------------------------------------------------------------------------- #
# OpenAI-compatible wire types (lenient pass-through)
# --------------------------------------------------------------------------- #


class FunctionCall(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str = ""
    arguments: str = ""  # JSON-encoded string, per OpenAI spec


class ToolCall(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str = ""
    type: str = "function"
    function: FunctionCall = Field(default_factory=FunctionCall)


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="allow")
    role: str
    content: str | None = None
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[ToolCall] | None = None


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    model: str
    messages: list[ChatMessage] = Field(default_factory=list)
    tools: list[dict[str, Any]] | None = None
    tool_choice: Any | None = None
    stream: bool = False
    temperature: float | None = None


# --------------------------------------------------------------------------- #
# Firewall decision types
# --------------------------------------------------------------------------- #


class Action(StrEnum):
    ALLOW = "allow"
    REDACT = "redact"
    BLOCK = "block"


class Status(StrEnum):
    PASS = "pass"
    FLAG = "flag"
    BLOCK = "block"


class CheckResult(BaseModel):
    """Outcome of one inspection stage."""

    name: str
    status: Status = Status.PASS
    detail: str = ""
    score: float | None = None
    latency_ms: float = 0.0
    meta: dict[str, Any] = Field(default_factory=dict)


class Decision(BaseModel):
    """Aggregate verdict for a single proxied call."""

    action: Action = Action.ALLOW
    reason: str = ""
    checks: list[CheckResult] = Field(default_factory=list)
    rule_fired: str | None = None
    redactions: int = 0
    stripped_tool_calls: list[str] = Field(default_factory=list)
    blocked_calls: list[dict[str, Any]] = Field(default_factory=list)  # {name, arguments, reasons}
    reasoning: str | None = None  # gpt-oss-safeguard chain-of-thought, when used
    modified: bool = False

    def worst_status(self) -> Status:
        if any(c.status is Status.BLOCK for c in self.checks):
            return Status.BLOCK
        if any(c.status is Status.FLAG for c in self.checks):
            return Status.FLAG
        return Status.PASS


class Receipt(BaseModel):
    """Tamper-evident audit record. `signature` covers `payload_hash`."""

    id: str
    ts: str
    session_id: str
    model: str
    direction: str  # "inbound" | "outbound"
    decision: Decision
    request_summary: dict[str, Any] = Field(default_factory=dict)
    payload_hash: str = ""
    signature: str = ""


class Event(BaseModel):
    """Lightweight projection streamed to the dashboard over SSE."""

    id: str
    ts: str
    session_id: str
    action: Action
    status: Status
    title: str
    detail: str = ""
    rule: str | None = None
    receipt_id: str | None = None
    checks: list[CheckResult] = Field(default_factory=list)
