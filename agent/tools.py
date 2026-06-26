"""Tool implementations for the demo victim agent.

`send_email` is the dangerous capability. In a real breach (no firewall) it
"sends" to whatever the model was tricked into. Behind the firewall the call is
stripped before the agent ever receives it, so this code never runs for a
malicious destination.
"""

from __future__ import annotations

import json
from pathlib import Path

POISONED_DIR = Path(__file__).resolve().parent / "poisoned"

# OpenAI-style tool schemas advertised to the model.
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_doc",
            "description": "Read a document by name and return its text.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Send an email to a recipient.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize",
            "description": "Return a short summary of provided text.",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        },
    },
]

# Side-effect log so the demo can prove whether a breach occurred.
SENT_EMAILS: list[dict] = []


def read_doc(name: str) -> str:
    safe = Path(name).name  # prevent traversal
    path = POISONED_DIR / (safe if safe.endswith(".txt") else f"{safe}.txt")
    if not path.exists():
        return f"(no document named {name!r})"
    return path.read_text(encoding="utf-8")


def send_email(to: str, subject: str, body: str) -> str:
    record = {"to": to, "subject": subject, "body": body}
    SENT_EMAILS.append(record)
    return f"EMAIL SENT to {to} (subject={subject!r})"


def summarize(text: str) -> str:
    head = " ".join(text.split())[:160]
    return f"Summary: {head}..."


def dispatch(name: str, arguments: str) -> str:
    """Execute a tool call locally and return a string result."""
    try:
        args = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        args = {}
    if name == "read_doc":
        return read_doc(args.get("name", ""))
    if name == "send_email":
        return send_email(args.get("to", ""), args.get("subject", ""), args.get("body", ""))
    if name == "summarize":
        return summarize(args.get("text", ""))
    return f"(unknown tool {name})"
