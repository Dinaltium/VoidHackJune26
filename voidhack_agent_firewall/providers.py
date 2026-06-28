import json
from typing import Any, Callable

from . import pii
from .client import FirewallOpenAI
from .policy import Policy, load_policy
from .rules import check_tool_calls
from .schemas import Status, ToolCall

OPENAI_COMPATIBLE_BASE_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "groq": "https://api.groq.com/openai/v1",
    "nvidia": "https://integrate.api.nvidia.com/v1",
    "mistral": "https://api.mistral.ai/v1",
    "together": "https://api.together.xyz/v1",
    "fireworks": "https://api.fireworks.ai/inference/v1",
    "perplexity": "https://api.perplexity.ai",
    "deepseek": "https://api.deepseek.com",
    "openrouter": "https://openrouter.ai/api/v1",
    "local": "http://localhost:8000/v1",
}


def create_openai_compatible_firewall(
    provider: str,
    *,
    api_key: str | None = None,
    policy_path: str,
    base_url: str | None = None,
    **client_kwargs: Any,
) -> FirewallOpenAI:
    """Create a guarded OpenAI-compatible client for Groq/NVIDIA/Mistral/Together/etc."""
    resolved_base_url = base_url or OPENAI_COMPATIBLE_BASE_URLS.get(provider)
    if not resolved_base_url:
        raise ValueError(f"Unknown OpenAI-compatible provider: {provider}")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ImportError(
            "create_openai_compatible_firewall requires the OpenAI SDK. "
            "Install with `pip install voidhack-agent-firewall[openai]`."
        ) from exc
    raw = OpenAI(api_key=api_key, base_url=resolved_base_url, **client_kwargs)
    return FirewallOpenAI(raw, policy_path=policy_path)


def _stringify_args(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value if value is not None else {})
    except TypeError:
        return str(value)


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _set(obj: Any, name: str, value: Any) -> None:
    if isinstance(obj, dict):
        obj[name] = value
    else:
        setattr(obj, name, value)


def _firewall_meta() -> dict[str, Any]:
    return {
        "action": "allow",
        "reason": None,
        "rule_fired": None,
        "stripped_tool_calls": [],
        "blocked_calls": [],
    }


def _enforce_tool_calls(
    calls: list[dict[str, Any]],
    policy: Policy,
    remove_blocked: Callable[[set[str]], None],
) -> dict[str, Any]:
    meta = _firewall_meta()
    if not calls:
        return meta

    tool_calls = [
        ToolCall(
            id=call["id"],
            type="function",
            function={"name": call["name"], "arguments": _stringify_args(call.get("arguments"))},
        )
        for call in calls
    ]
    findings, _ = check_tool_calls(tool_calls, policy)
    blocked_ids = {f.tool_call_id for f in findings if f.status is Status.BLOCK}
    if not blocked_ids:
        return meta

    remove_blocked(blocked_ids)
    first_blocked = next(f for f in findings if f.status is Status.BLOCK)
    meta["action"] = "block"
    meta["stripped_tool_calls"] = sorted(blocked_ids)
    meta["rule_fired"] = "deterministic_rules"
    meta["reason"] = "; ".join(first_blocked.reasons)
    meta["blocked_calls"] = [
        {"name": f.tool_name, "reasons": f.reasons}
        for f in findings
        if f.status is Status.BLOCK
    ]
    return meta


def _redact_anthropic_messages(body: dict[str, Any], policy: Policy) -> None:
    for msg in body.get("messages", []) or []:
        content = msg.get("content")
        role = msg.get("role", "user")
        if isinstance(content, str) and content:
            redacted, check = pii.scan_and_redact(content, policy, source=role)
            if check.status is Status.FLAG:
                msg["content"] = redacted
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text = part.get("text")
                    if isinstance(text, str) and text:
                        redacted, check = pii.scan_and_redact(text, policy, source=role)
                        if check.status is Status.FLAG:
                            part["text"] = redacted


class _AnthropicMessagesWrapper:
    def __init__(self, messages: Any, policy: Policy):
        self._messages = messages
        self._policy = policy

    def create(self, *args: Any, **kwargs: Any) -> Any:
        body = kwargs if kwargs else (args[0] if args and isinstance(args[0], dict) else {})
        _redact_anthropic_messages(body, self._policy)
        response = self._messages.create(*args, **kwargs)
        content = _get(response, "content", []) or []
        calls = [
            {"id": _get(part, "id"), "name": _get(part, "name"), "arguments": _get(part, "input")}
            for part in content
            if _get(part, "type") == "tool_use"
        ]

        def remove(blocked_ids: set[str]) -> None:
            kept = [
                part
                for part in content
                if _get(part, "type") != "tool_use" or _get(part, "id") not in blocked_ids
            ]
            if not kept:
                kept = [{"type": "text", "text": self._policy.block_message}]
            _set(response, "content", kept)

        _set(response, "firewall", _enforce_tool_calls(calls, self._policy, remove))
        return response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._messages, name)


class FirewallAnthropic:
    """Drop-in wrapper for Anthropic Claude clients using native tool_use blocks."""

    def __init__(self, client: Any, policy_path: str):
        self._client = client
        self._policy = load_policy(policy_path)
        self.messages = _AnthropicMessagesWrapper(client.messages, self._policy)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)


class FirewallGeminiModel:
    """Wrapper for Gemini model objects that strips blocked function_call parts."""

    def __init__(self, model: Any, policy: Policy):
        self._model = model
        self._policy = policy

    def generate_content(self, *args: Any, **kwargs: Any) -> Any:
        response = self._model.generate_content(*args, **kwargs)
        candidates = _get(response, "candidates", []) or []
        calls: list[dict[str, Any]] = []
        for candidate_index, candidate in enumerate(candidates):
            content = _get(candidate, "content")
            parts = _get(content, "parts", []) if content is not None else []
            for part_index, part in enumerate(parts):
                fn = _get(part, "function_call") or _get(part, "functionCall")
                if fn is not None:
                    calls.append(
                        {
                            "id": f"gemini-{candidate_index}-{part_index}",
                            "candidate_index": candidate_index,
                            "part_index": part_index,
                            "name": _get(fn, "name"),
                            "arguments": _get(fn, "args") or _get(fn, "arguments") or {},
                        }
                    )

        def remove(blocked_ids: set[str]) -> None:
            for call in sorted(calls, key=lambda c: c["part_index"], reverse=True):
                if call["id"] not in blocked_ids:
                    continue
                candidate = candidates[call["candidate_index"]]
                parts = _get(_get(candidate, "content"), "parts", [])
                if isinstance(parts, list):
                    parts.pop(call["part_index"])
                    if not parts:
                        parts.append({"text": self._policy.block_message})

        _set(response, "firewall", _enforce_tool_calls(calls, self._policy, remove))
        return response

    def start_chat(self, *args: Any, **kwargs: Any) -> Any:
        chat = self._model.start_chat(*args, **kwargs)
        return FirewallGeminiChat(chat, self._policy)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._model, name)


class FirewallGeminiChat:
    def __init__(self, chat: Any, policy: Policy):
        self._chat = chat
        self._policy = policy

    def send_message(self, *args: Any, **kwargs: Any) -> Any:
        response = self._chat.send_message(*args, **kwargs)
        return FirewallGeminiModel(
            type("_OneShotGeminiModel", (), {"generate_content": lambda *_a, **_k: response})(),
            self._policy,
        ).generate_content()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._chat, name)


class FirewallGoogleGenerativeAI:
    """Drop-in wrapper for google-generativeai clients."""

    def __init__(self, client: Any, policy_path: str):
        self._client = client
        self._policy = load_policy(policy_path)

    def GenerativeModel(self, *args: Any, **kwargs: Any) -> FirewallGeminiModel:
        return FirewallGeminiModel(self._client.GenerativeModel(*args, **kwargs), self._policy)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)
