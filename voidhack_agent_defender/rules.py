from __future__ import annotations

import re
import time
import urllib.parse
from dataclasses import dataclass, field

from .policy import Policy
from .schemas import CheckResult, Status, ToolCall

_URL_RE = re.compile(r"(?:[a-z][a-z0-9+.\-]*:)?//[^\s\"'<>]+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@([A-Za-z0-9.\-]+\.[A-Za-z]{2,})")


@dataclass
class ToolFinding:
    tool_call_id: str
    tool_name: str
    status: Status
    reasons: list[str] = field(default_factory=list)
    hosts: list[str] = field(default_factory=list)
    secrets: list[str] = field(default_factory=list)
    arg_hits: list[str] = field(default_factory=list)


def _extract_hosts(arguments: str) -> list[str]:
    hosts: list[str] = []
    for url in _URL_RE.findall(arguments):
        netloc = urllib.parse.urlparse(url).netloc.lower()
        if netloc:
            hosts.append(netloc.split("@")[-1].split(":")[0])
    for match in _EMAIL_RE.finditer(arguments):
        hosts.append(match.group(1).lower())
    return hosts


def find_secrets(text: str, policy: Policy) -> list[str]:
    hits: list[str] = []
    for name, pattern in policy.compiled_secrets():
        if pattern.search(text or ""):
            hits.append(name)
    return hits


def check_arg_rules(tool: str, arguments: str, policy: Policy) -> list[str]:
    hits: list[str] = []
    for rule, pattern in policy.compiled_arg_rules():
        if rule.applies_to(tool) and pattern.search(arguments or ""):
            hits.append(rule.reason)
    return hits


def inspect_tool_call(tc: ToolCall, policy: Policy) -> ToolFinding:
    name = tc.function.name or "(unnamed)"
    args = tc.function.arguments or ""
    finding = ToolFinding(tool_call_id=tc.id, tool_name=name, status=Status.PASS)

    if not policy.tool_allowed(name):
        finding.status = Status.BLOCK
        verb = "denied" if name in policy.tool_denylist else "not on allowlist"
        finding.reasons.append(f"tool '{name}' is {verb}")

    hosts = _extract_hosts(args)
    finding.hosts = hosts
    bad_hosts = [host for host in hosts if not policy.host_allowed(host)]
    if bad_hosts:
        finding.status = Status.BLOCK
        finding.reasons.append(
            f"egress to non-allowlisted host(s): {', '.join(sorted(set(bad_hosts)))}"
        )

    secrets = find_secrets(args, policy)
    finding.secrets = secrets
    if secrets:
        finding.status = Status.BLOCK
        finding.reasons.append(f"secret(s) in tool args: {', '.join(secrets)}")

    arg_hits = check_arg_rules(name, args, policy)
    finding.arg_hits = arg_hits
    if arg_hits:
        finding.status = Status.BLOCK
        finding.reasons.extend(arg_hits)

    return finding


def check_tool_calls(
    tool_calls: list[ToolCall], policy: Policy
) -> tuple[list[ToolFinding], CheckResult]:
    started_at = time.perf_counter()
    findings = [inspect_tool_call(tool_call, policy) for tool_call in tool_calls]
    blocked = [finding for finding in findings if finding.status is Status.BLOCK]
    detail = (
        "; ".join(reason for finding in blocked for reason in finding.reasons)
        if blocked
        else f"{len(tool_calls)} tool call(s) within policy"
    )
    return findings, CheckResult(
        name="deterministic_rules",
        status=Status.BLOCK if blocked else Status.PASS,
        detail=detail,
        latency_ms=(time.perf_counter() - started_at) * 1000,
        meta={"blocked_tools": [finding.tool_name for finding in blocked]},
    )
