"""Deterministic, always-on rules. Zero network, sub-millisecond, never flaky.

This is the firewall's backbone: tool allow/deny, egress host allowlist, and
secret/credential leak detection inside tool-call arguments. If every model API
is down, these still hold the line.
"""

from __future__ import annotations

import json
import re
import time
import urllib.parse
from dataclasses import dataclass, field

from ..policy import Policy
from ..schemas import CheckResult, Status, ToolCall

# crude but effective host/URL extractor for tool arguments
_URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@([A-Za-z0-9.\-]+\.[A-Za-z]{2,})")


@dataclass
class ToolFinding:
    tool_call_id: str
    tool_name: str
    status: Status
    reasons: list[str] = field(default_factory=list)
    hosts: list[str] = field(default_factory=list)
    secrets: list[str] = field(default_factory=list)


def _extract_hosts(arguments: str) -> list[str]:
    hosts: list[str] = []
    for url in _URL_RE.findall(arguments):
        netloc = urllib.parse.urlparse(url).netloc.lower()
        if netloc:
            hosts.append(netloc.split("@")[-1].split(":")[0])
    for m in _EMAIL_RE.finditer(arguments):
        hosts.append(m.group(1).lower())  # email domain counts as egress target
    return hosts


def find_secrets(text: str, policy: Policy) -> list[str]:
    hits: list[str] = []
    for name, pattern in policy.compiled_secrets():
        if pattern.search(text or ""):
            hits.append(name)
    return hits


def inspect_tool_call(tc: ToolCall, policy: Policy) -> ToolFinding:
    """Evaluate one model-emitted tool call against the deterministic policy."""
    name = tc.function.name or "(unnamed)"
    args = tc.function.arguments or ""
    finding = ToolFinding(tool_call_id=tc.id, tool_name=name, status=Status.PASS)

    # 1) tool allow/deny
    if not policy.tool_allowed(name):
        finding.status = Status.BLOCK
        verb = "denied" if name in policy.tool_denylist else "not on allowlist"
        finding.reasons.append(f"tool '{name}' is {verb}")

    # 2) egress allowlist
    hosts = _extract_hosts(args)
    finding.hosts = hosts
    bad_hosts = [h for h in hosts if not policy.host_allowed(h)]
    if bad_hosts:
        finding.status = Status.BLOCK
        bad = ", ".join(sorted(set(bad_hosts)))
        finding.reasons.append(f"egress to non-allowlisted host(s): {bad}")

    # 3) secret leak in args
    secrets = find_secrets(args, policy)
    finding.secrets = secrets
    if secrets:
        finding.status = Status.BLOCK
        finding.reasons.append(f"secret(s) in tool args: {', '.join(secrets)}")

    return finding


def check_tool_calls(
    tool_calls: list[ToolCall], policy: Policy
) -> tuple[list[ToolFinding], CheckResult]:
    """Inspect every tool call; return findings + a rollup CheckResult."""
    t0 = time.perf_counter()
    findings = [inspect_tool_call(tc, policy) for tc in tool_calls]
    blocked = [f for f in findings if f.status is Status.BLOCK]
    status = Status.BLOCK if blocked else Status.PASS
    if blocked:
        detail = "; ".join(r for f in blocked for r in f.reasons)
    else:
        detail = f"{len(tool_calls)} tool call(s) within policy"
    result = CheckResult(
        name="deterministic_rules",
        status=status,
        detail=detail,
        latency_ms=(time.perf_counter() - t0) * 1000,
        meta={"blocked_tools": [f.tool_name for f in blocked]},
    )
    return findings, result


def parse_arguments(arguments: str) -> dict:
    try:
        out = json.loads(arguments or "{}")
        return out if isinstance(out, dict) else {"_value": out}
    except (json.JSONDecodeError, TypeError):
        return {}
