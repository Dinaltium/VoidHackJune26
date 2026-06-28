import os
import sys
from typing import Any, Dict
from openai import OpenAI

# Add proxy directory to sys.path to access validation rules
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "proxy"))

from app.policy import load_policy, Policy  # type: ignore
from app.detect.rules import check_tool_calls  # type: ignore
from app.detect import pii  # type: ignore
from app.schemas import Status, ToolCall  # type: ignore

class CompletionsWrapper:
    def __init__(self, original_completions: Any, policy: Policy):
        self._original = original_completions
        self._policy = policy

    def create(self, *args: Any, **kwargs: Any) -> Any:
        # 1. Inbound Inspection (Locally check input messages for PII/secrets)
        messages = kwargs.get("messages", [])
        for msg in messages:
            content = msg.get("content")
            if isinstance(content, str) and content:
                # Mask credentials or secrets in prompts locally
                redacted, pii_check = pii.scan_and_redact(content, self._policy, source=msg.get("role", "user"))
                if pii_check.status is Status.FLAG:
                    msg["content"] = redacted

        # 2. Call the actual upstream LLM
        response = self._original.create(*args, **kwargs)

        # 3. Outbound Inspection (Locally check response tool calls and arguments)
        choices = getattr(response, "choices", [])
        if not choices:
            return response

        message = choices[0].message
        raw_calls = getattr(message, "tool_calls", None) or []
        
        # Parse into our schema structure to run checks
        tool_calls = []
        for tc in raw_calls:
            tool_calls.append(ToolCall(
                id=tc.id,
                type=tc.type,
                function={"name": tc.function.name, "arguments": tc.function.arguments}
            ))

        firewall_meta: Dict[str, Any] = {
            "action": "allow",
            "reason": None,
            "rule_fired": None,
            "stripped_tool_calls": [],
            "blocked_calls": []
        }

        if tool_calls:
            findings, rules_check = check_tool_calls(tool_calls, self._policy)
            blocked_ids = {f.tool_call_id for f in findings if f.status is Status.BLOCK}

            if blocked_ids:
                # Strip blocked tool calls so agent framework never receives them
                kept = [tc for tc in raw_calls if tc.id not in blocked_ids]
                message.tool_calls = kept if kept else None
                
                # If everything was stripped and no text response remains, inject block message
                if not kept and not getattr(message, "content", None):
                    message.content = self._policy.block_message
                    choices[0].finish_reason = "content_filter"

                firewall_meta["action"] = "block"
                firewall_meta["stripped_tool_calls"] = sorted(blocked_ids)
                first_blocked = next(f for f in findings if f.status is Status.BLOCK)
                firewall_meta["rule_fired"] = "deterministic_rules"
                firewall_meta["reason"] = "; ".join(first_blocked.reasons)

                # Capture safe representation for logging
                by_id = {tc.id: tc for tc in raw_calls}
                for f in findings:
                    if f.status is Status.BLOCK:
                        tc_ref = by_id.get(f.tool_call_id)
                        raw_args = tc_ref.function.arguments if tc_ref else ""
                        safe_args, _ = pii.redact(raw_args or "", self._policy)
                        firewall_meta["blocked_calls"].append({
                            "name": f.tool_name,
                            "arguments": safe_args,
                            "reasons": f.reasons
                        })

        # Redact secrets from text output if any
        content = getattr(message, "content", None)
        if isinstance(content, str) and content:
            redacted, pii_check = pii.scan_and_redact(content, self._policy, source="completion")
            if pii_check.status is Status.FLAG:
                message.content = redacted
                firewall_meta["action"] = "redact"
                firewall_meta["reason"] = "secret/PII redacted from model output"

        # Inject firewall metadata into response object
        response.model_extra = getattr(response, "model_extra", {}) or {}
        response.model_extra["firewall"] = firewall_meta

        return response


class ChatWrapper:
    def __init__(self, original_chat: Any, policy: Policy):
        self._chat = original_chat
        self.completions = CompletionsWrapper(original_chat.completions, policy)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._chat, name)


class FirewallOpenAI:
    """Sleek drop-in client wrapper that adds policy controls to any OpenAI client in-process."""
    def __init__(
        self,
        client: OpenAI,
        policy_path: str
    ):
        self._client = client
        self._policy = load_policy(policy_path)
        self.chat = ChatWrapper(client.chat, self._policy)

    def __getattr__(self, name: str) -> Any:
        # Proxy attributes back to the original client
        return getattr(self._client, name)
