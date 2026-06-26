# Agent Firewall

> The operating layer that guards what AI agents actually **do**.
>
> *Guardrails check what the model says. We check what the agent does.*

**VoidHack June 2026** — Theme: *The Operating Layer of the Internet*.

A transparent, **OpenAI-compatible proxy** that sits between an AI agent and the
LLM/world and enforces **action-level** policy. Point your agent's `base_url` at
it — nothing else changes — and every tool call, egress destination, secret, and
token budget is checked before the agent can act.

## Why

Prompt injection is unsolved (OWASP LLM01:2025). Existing guardrails classify
*text* and approve the words — then the agent emails your secrets in the next
call. The firewall enforces at the layer where damage happens: **the action**.

It blocks by **stripping the disallowed `tool_call` out of the model's response
before the agent ever sees it** — prevention, not a warning. Default **fail-closed**.

## What it enforces

- **Tool allowlist** — default-deny; `send_email`, `run_shell`, … are blocked.
- **Egress allowlist** — URLs/email domains must be on the allowlist.
- **Injection scan** — heuristic + Meta **Prompt Guard 2** on tool results.
- **PII / secret redaction** — in-flight, both directions (regex; Presidio optional).
- **Cost guard** — per-session token budget.
- **Signed receipts** — every decision is HMAC-signed and auditable, streamed
  live to a control-plane dashboard.
- **Safeguard reasoner** — `gpt-oss-safeguard-20b` adds an auditable explanation
  on flagged actions (policy-following; reads `policies/policy.yaml`).

## Demo (before / after)

```bash
# BREACH — agent talks straight to the model; it emails data externally
python -m agent.run_attack --task email --direct

# SAFE — same task through the firewall; send_email is blocked, 0 exfiltration
python -m agent.run_attack --task email
```

The dashboard (`/`) shows decisions stream in live; **Run demo attack** replays a
spread of attacks through the real engine. See [docs/RUNBOOK.md](docs/RUNBOOK.md).

## Stack

| Layer | Tech |
|-------|------|
| Proxy | Python 3.12 · FastAPI 0.136 · Uvicorn · httpx · Pydantic 2 |
| Detection | deterministic rules · Prompt Guard 2 (Groq) · regex/Presidio PII |
| Reasoner | gpt-oss-safeguard-20b (Groq, selective) |
| Store | SQLite · SQLAlchemy 2.0 · HMAC-SHA256 receipts |
| Dashboard | Next.js 16 · Tailwind 4 · SSE live feed |
| Demo agent | OpenAI SDK · llama-3.3-70b-versatile |

All models run on the **Groq free tier** — zero cost, no card.

## Layout

```
proxy/        FastAPI firewall (app/ + tests/)
dashboard/    Next.js 16 control-plane UI
agent/        demo victim agent + poisoned document
policies/     policy.yaml
docs/         DESIGN · ARCHITECTURE · RUNBOOK
```

## Status

Working end-to-end. Backend: ruff + mypy + 34 pytest green. Dashboard: biome +
tsc + build + 2 Playwright e2e green. Verified live against Groq.

See [docs/DESIGN.md](docs/DESIGN.md) for the design + decision log and
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for components and data flow.

## License

MIT
