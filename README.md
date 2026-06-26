# Agent Firewall (working title)

> The operating layer that guards what AI agents actually **do**.

**VoidHack June 2026** — Theme: *The Operating Layer of the Internet*.

## Problem

Prompt injection is unsolved (OWASP LLM01:2025). Today's guardrails read **text**
and approve the words — then the agent emails your secrets in the next call.
Nobody guards the **action**.

## Idea

A transparent, OpenAI-compatible proxy that sits between an AI agent and the
LLM/world and enforces **action-level** policy:

- Default-deny **tool allowlist**
- **Egress** domain allowlist
- **Injection** detection on tool-returned / retrieved content
- In-flight **PII / secret** redaction
- **Cost / rate** guards
- Signed **decision receipts** + live dashboard

Integration cost: change one `base_url`.

> Guardrails check what the model *says*. We check what the agent *does*.

## Status

🚧 Day 1 — brainstorm + design locked, build starting. Architecture and demo
storyboard defined; implementation in progress during the hackathon period.

## Planned stack

- **Proxy:** Python / FastAPI (OpenAI-compatible endpoint)
- **Detection:** Llama Prompt Guard 2 (86M) · Microsoft Presidio · deterministic rules
- **Judge (selective):** Llama 3.3 70B / Claude Haiku 4.5
- **Dashboard:** live event stream + audit log
- **Store:** SQLite / Postgres

## License

MIT (see [LICENSE](LICENSE)) — to be added.
