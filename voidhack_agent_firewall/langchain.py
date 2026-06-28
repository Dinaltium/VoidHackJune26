import os
import sys
from typing import Any, Dict, List, Optional

# Add proxy directory to sys.path to access validation rules
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "proxy"))

from app.detect.rules import check_tool_calls  # type: ignore
from app.schemas import ToolCall, Status  # type: ignore
from app.policy import load_policy  # type: ignore

# Attempt to import LangChain's callback base class
try:
    from langchain_core.callbacks import BaseCallbackHandler
except ImportError:
    # Fallback mock if langchain is not installed in the current environment
    class BaseCallbackHandler: # type: ignore
        pass

class PolicyViolationError(ValueError):
    """Raised when an agent action violates security policies."""
    pass

class FirewallCallbackHandler(BaseCallbackHandler):
    """LangChain callback plugin that halts agent runs when tool calls or arguments violate security policy."""
    def __init__(self, policy_path: str):
        self.policy = load_policy(policy_path)

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: Any = None,
        parent_run_id: Any = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Any:
        """Intercepts tool execution right before it starts."""
        tool_name = serialized.get("name", "")
        
        # Check against denied tools
        if tool_name in self.policy.tool_denylist:
            raise PolicyViolationError(
                f"Security Block: Tool '{tool_name}' is restricted by security policy."
            )

        # Check against allowed tools & argument-level rules
        if self.policy.tool_allowlist and tool_name not in self.policy.tool_allowlist:
            raise PolicyViolationError(
                f"Security Block: Tool '{tool_name}' is not in the allowed tool list."
            )

        # Wrap in a ToolCall object to run argument checks
        # LangChain tools typically pass inputs as JSON string or keyword args
        tc = ToolCall(
            id=str(run_id or "lc-run"),
            type="function",
            function={"name": tool_name, "arguments": input_str}
        )

        findings, rules_check = check_tool_calls([tc], self.policy)
        blocked = [f for f in findings if f.status is Status.BLOCK]
        
        if blocked:
            reasons = "; ".join(blocked[0].reasons)
            raise PolicyViolationError(
                f"Security Block: Tool '{tool_name}' argument check failed. Reason: {reasons}"
            )
