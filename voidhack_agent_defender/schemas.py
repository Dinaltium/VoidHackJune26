from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Status(Enum):
    PASS = "pass"
    FLAG = "flag"
    BLOCK = "block"


@dataclass
class FunctionCall:
    name: str = ""
    arguments: str = ""


@dataclass
class ToolCall:
    id: str = ""
    type: str = "function"
    function: FunctionCall = field(default_factory=FunctionCall)

    def __init__(
        self,
        id: str = "",
        type: str = "function",
        function: FunctionCall | dict[str, Any] | None = None,
    ):
        self.id = id
        self.type = type
        if isinstance(function, FunctionCall):
            self.function = function
        elif isinstance(function, dict):
            self.function = FunctionCall(
                name=str(function.get("name") or ""),
                arguments=str(function.get("arguments") or ""),
            )
        else:
            self.function = FunctionCall()


@dataclass
class CheckResult:
    name: str
    status: Status = Status.PASS
    detail: str = ""
    latency_ms: float = 0.0
    meta: dict[str, Any] = field(default_factory=dict)
