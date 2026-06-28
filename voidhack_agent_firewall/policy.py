from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class SecretPattern:
    name: str
    regex: str

    def compiled(self) -> re.Pattern[str]:
        return re.compile(self.regex)


@dataclass
class ArgRule:
    name: str
    reason: str
    regex: str
    tools: list[str] = field(default_factory=lambda: ["*"])

    def compiled(self) -> re.Pattern[str]:
        return re.compile(self.regex)

    def applies_to(self, tool: str) -> bool:
        return "*" in self.tools or tool in self.tools


@dataclass
class Policy:
    version: int = 1
    description: str = ""
    tool_allowlist: list[str] = field(default_factory=list)
    tool_denylist: list[str] = field(default_factory=list)
    egress_allowlist: list[str] = field(default_factory=list)
    secret_patterns: list[SecretPattern] = field(default_factory=list)
    arg_rules: list[ArgRule] = field(default_factory=list)
    injection_phrases: list[str] = field(default_factory=list)
    injection_threshold: float = 0.80
    token_budget_per_session: int = 20000
    fail_closed: bool = True
    block_message: str = "[Agent Firewall] Action blocked by policy."

    def tool_allowed(self, name: str) -> bool:
        if name in self.tool_denylist:
            return False
        if not self.tool_allowlist:
            return True
        return name in self.tool_allowlist

    def host_allowed(self, host: str) -> bool:
        host = host.lower().strip()
        for allowed in self.egress_allowlist:
            allowed_host = allowed.lower().strip()
            if host == allowed_host or host.endswith("." + allowed_host):
                return True
        return False

    def compiled_secrets(self) -> list[tuple[str, re.Pattern[str]]]:
        return [(pattern.name, pattern.compiled()) for pattern in self.secret_patterns]

    def compiled_arg_rules(self) -> list[tuple[ArgRule, re.Pattern[str]]]:
        return [(rule, rule.compiled()) for rule in self.arg_rules]


def load_policy(path: str | Path) -> Policy:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return Policy(
        version=int(raw.get("version", 1)),
        description=str(raw.get("description", "")),
        tool_allowlist=list(raw.get("tool_allowlist") or []),
        tool_denylist=list(raw.get("tool_denylist") or []),
        egress_allowlist=list(raw.get("egress_allowlist") or []),
        secret_patterns=[
            SecretPattern(name=str(item["name"]), regex=str(item["regex"]))
            for item in raw.get("secret_patterns") or []
        ],
        arg_rules=[
            ArgRule(
                name=str(item["name"]),
                reason=str(item["reason"]),
                regex=str(item["regex"]),
                tools=list(item.get("tools") or ["*"]),
            )
            for item in raw.get("arg_rules") or []
        ],
        injection_phrases=list(raw.get("injection_phrases") or []),
        injection_threshold=float(raw.get("injection_threshold", 0.80)),
        token_budget_per_session=int(raw.get("token_budget_per_session", 20000)),
        fail_closed=bool(raw.get("fail_closed", True)),
        block_message=str(
            raw.get("block_message", "[Agent Firewall] Action blocked by policy.")
        ),
    )
