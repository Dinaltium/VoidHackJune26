"""SDK Integration Demo.

Demonstrates how to import and use the `agent_defender` SDK in two ways:
  1. Standalone client wrapper (FirewallOpenAI)
  2. LangChain Callback Handler (FirewallCallbackHandler)

Both run locally/in-process using policy.yaml without requiring the proxy server.
"""

import os
import sys
from openai import OpenAI

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from agent_defender import FirewallOpenAI, FirewallCallbackHandler
from agent_defender.langchain import PolicyViolationError

# Path to the active policy configuration
POLICY_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "policies", "policy.yaml")

def demo_openai_wrapper() -> None:
    print("\n--- Demo 1: Standalone OpenAI Client Wrapper ---")
    
    # Initialize standard OpenAI client (using a mock key / url since we block locally)
    raw_client = OpenAI(api_key="sk-mock-key")
    
    # Wrap it with our firewall locally
    client = FirewallOpenAI(
        client=raw_client,
        policy_path=POLICY_PATH
    )
    
    # Define a tool call that is disallowed by policy.yaml
    # E.g. transfer_funds
    print("Agent attempts to request a restricted tool ('transfer_funds')...")
    
    # In a real scenario, this would call the LLM and the LLM would return tool calls.
    # To demonstrate the in-process interception, let's trigger it.
    # We'll mock the completion response from the original client's chat.completions.create
    # to return a tool call, and watch the wrapper intercept and strip it locally.
    
    class MockFunction:
        def __init__(self, name: str, arguments: str):
            self.name = name
            self.arguments = arguments

    class MockToolCall:
        def __init__(self, tc_id: str, name: str, arguments: str):
            self.id = tc_id
            self.type = "function"
            self.function = MockFunction(name, arguments)

    class MockMessage:
        def __init__(self, content: str | None, tool_calls: list):
            self.content = content
            self.tool_calls = tool_calls
            self.role = "assistant"

    class MockChoice:
        def __init__(self, message: MockMessage):
            self.message = message
            self.finish_reason = "stop"
            self.index = 0

    class MockResponse:
        def __init__(self, choices: list):
            self.choices = choices
            self.model_extra = {}

    # Setup the mock completions create method
    def mock_create(*args: Any, **kwargs: Any) -> Any:
        return MockResponse([
            MockChoice(MockMessage(
                content=None,
                tool_calls=[MockToolCall("call-1", "transfer_funds", '{"amount": 5000, "to": "ops@attacker.net"}')]
            ))
        ])

    # Temporarily substitute original create for demonstration
    client.chat.completions._original.create = mock_create
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Please send money to ops@attacker.net"}]
    )
    
    print(f"Firewall decision: {response.model_extra.get('firewall', {}).get('action')}")
    print(f"Reason: {response.model_extra.get('firewall', {}).get('reason')}")
    print(f"Stripped Tool Calls: {response.model_extra.get('firewall', {}).get('stripped_tool_calls')}")
    print(f"Tool calls returned to agent: {getattr(response.choices[0].message, 'tool_calls', None)}")


def demo_langchain_callback() -> None:
    print("\n--- Demo 2: LangChain Callback Handler ---")
    
    # Initialize our callback handler with the policy
    handler = FirewallCallbackHandler(policy_path=POLICY_PATH)
    
    # Simulate a tool run lifecycle
    # We will trigger the on_tool_start callback with an allowed vs disallowed tool
    
    print("1. Simulating an allowed tool ('read_doc')...")
    try:
        handler.on_tool_start(
            serialized={"name": "read_doc"},
            input_str='{"path": "report.pdf"}'
        )
        print("  [OK] Allowed: read_doc passed policy checks.")
    except PolicyViolationError as exc:
        print(f"  [BLOCKED] {exc}")

    print("\n2. Simulating a restricted tool ('send_email')...")
    try:
        handler.on_tool_start(
            serialized={"name": "send_email"},
            input_str='{"to": "hacker@evil.com", "body": "stolen data"}'
        )
        print("  [OK] Allowed.")
    except PolicyViolationError as exc:
        print(f"  [BLOCKED] {exc}")


if __name__ == "__main__":
    from typing import Any
    demo_openai_wrapper()
    demo_langchain_callback()
