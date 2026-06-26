# Agent Firewall — Design & Decision Log

> VoidHack June 2026 · Theme: *The Operating Layer of the Internet*

## 1. Understanding summary

- **What:** A transparent, OpenAI-compatible proxy that sits between an AI agent
  and the LLM/world and enforces **action-level** policy — default-deny tool
  allowlist, egress allowlist, prompt-injection detection on tool results,
  in-flight PII/secret redaction, and per-session cost guards. Every decision
  emits a signed, tamper-evident receipt and a live dashboard event.
- **Why:** Prompt injection is an unsolved problem (OWASP LLM01:2025). Existing
  guardrails classify *text* and approve the words — then the agent emails the
  secret in the next call. The firewall enforces at the layer where damage
  actually happens: the action.
- **Who:** Developers and startups shipping AI agents; platform/security teams
  who must govern what agents are allowed to do. Adoption cost = change one
  `base_url`.
- **One-liner:** *Guardrails check what the model says. We check what the agent does.*

## 2. Non-functional posture

- **Performance:** deterministic checks are sub-millisecond; model-backed layers
  are optional and off the hot path. Local-only path adds negligible latency.
- **Scale:** demo-scale (single node, SQLite). Designed to swap Postgres + an
  external bus without touching the pipeline.
- **Security:** it *is* a security product — **fail-closed** by default, signed
  receipts, default-deny tooling.
- **Reliability:** every model-backed layer degrades gracefully; the proxy never
  hard-fails because a guard model was unreachable.

## 3. Non-goals

- Not an inference-only guardrail (we go past text to the action).
- Not an AI gateway (routing/caching is commodity — explicitly avoided).
- Not an enterprise governance suite; not multi-tenant production scale.

## 4. Decision log

| # | Decision | Alternatives considered | Why |
|---|----------|------------------------|-----|
| D1 | Build at the **action/egress layer**, not the prompt layer | Inference guardrail (classify prompts only) | Guardrails approve text while the agent still acts; the gap is the action. The whole wedge. |
| D2 | **OpenAI-compatible proxy** as the integration surface | SDK middleware; MCP proxy | One `base_url` change = universal, language-agnostic, best demo. MCP proxy kept as future work. |
| D3 | Enforce by **stripping the model's `tool_call`** before the agent sees it | Post-hoc alerting; trusting the client | The agent executes what the model emits; removing the call is real prevention, not a warning. |
| D4 | **Deterministic-first** detection (allowlist, egress, regex) | Model-only detection | Always-on, offline, never flaky — holds the demo even if every model API is down. |
| D5 | **Prompt Guard 2 (86M)** for injection, **gpt-oss-safeguard-20b** as selective reasoner | Generic LLM-as-judge; Llama Guard 4 | Purpose-built classifier on the hot path; policy-following reasoner adds auditable explanations. Llama Guard 4 was deprecated on Groq (Feb 2026). |
| D6 | **All free models** via Groq free tier; local fallbacks | Paid APIs | Zero cost. Hot path is local so rate limits never bite. |
| D7 | **Signed receipts (HMAC-SHA256)** | Plain logs | Tamper-evident audit trail — the compliance/usefulness story. |
| D8 | **Egress HTTP guard = stretch**, not MVP | In-MVP | 3.5-day budget; deterministic allowlist on tool args covers the demo. |
| D9 | Victim model = **llama-3.3-70b-versatile** | llama-4-scout | Scout emitted malformed tool calls + resisted the bait; 70B gives clean, reliable function-calling for the live demo. |
| D10 | **Python 3.12** in a conda env `firewall` | 3.10 (system) / 3.13 | 3.12 is the wheel-stable sweet spot; isolates from the system 3.10. |

## 5. Final design

See [ARCHITECTURE.md](ARCHITECTURE.md) for components and data flow. The request
lifecycle:

```
agent → POST /v1/chat/completions → firewall
  inbound:  cost guard · injection scan (tool/user) · PII redaction
  → forward sanitized request → upstream LLM
  outbound: tool allowlist · egress allowlist · secret scan
            → strip violating tool_calls · selective safeguard judge
  → sign receipt · emit SSE event → return (modified) completion → agent
```

Enforcement is fail-closed: a disallowed tool, an out-of-policy destination, a
secret in tool arguments, or a blown token budget all result in a block, and the
agent receives a safe refusal instead of the dangerous action.
