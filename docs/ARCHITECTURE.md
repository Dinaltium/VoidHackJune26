# Architecture

## Components

```
agent ──OpenAI API──► Defender proxy (FastAPI) ──► Upstream LLM (Groq)
                          │  inspection engine
                          │   ├─ deterministic rules   (tool/egress/secret)
                          │   ├─ injection scan         (heuristic + Prompt Guard 2)
                          │   ├─ PII redaction          (regex / Presidio)
                          │   ├─ cost guard             (per-session budget)
                          │   └─ safeguard judge        (gpt-oss-safeguard-20b)
                          ├─ signed receipts ──► SQLite
                          └─ events ──SSE──► Next.js dashboard
```

| Module | Responsibility |
|--------|----------------|
| `app/main.py` | FastAPI app: `/v1/chat/completions`, `/events` (SSE), dashboard API |
| `app/engine.py` | Orchestrates inbound + outbound inspection; mutates payload/completion |
| `app/detect/rules.py` | Tool allow/deny, egress allowlist, secret-in-args — deterministic |
| `app/detect/injection.py` | Heuristic injection score (+ optional Prompt Guard 2) |
| `app/detect/pii.py` | PII / secret redaction (regex; Presidio optional) |
| `app/detect/cost.py` | Token estimate + per-session budget |
| `app/detect/judge.py` | Selective gpt-oss-safeguard reasoning on flagged actions |
| `app/groq_client.py` | Async upstream client + guard-model calls (best-effort) |
| `app/policy.py` | YAML policy model; drives rules *and* the safeguard reasoner |
| `app/receipts.py` | HMAC-SHA256 signing + verification |
| `app/store.py` | SQLite (SQLAlchemy 2.0): receipts, events, usage |
| `app/events.py` | In-process pub/sub for SSE |
| `app/demo.py` | Deterministic attack scenarios for the dashboard |
| `app/mission.py` | Server-side autonomous agent runner (governed vs ungoverned) for Mission Control |
| `dashboard/` | Next.js 16 + Tailwind 4 live control-plane UI |
| `agent/` | Demo victim agent + poisoned document |

## Request lifecycle

1. **Inbound** — estimate tokens + check session budget (block if over); scan
   `tool`/`user` message content for injection (heuristic + Prompt Guard 2);
   redact PII/secrets from messages before they leave to the provider.
2. **Forward** — send the sanitized request to the upstream LLM.
3. **Outbound** — for each `tool_call` the model emits, enforce the tool
   allowlist, egress allowlist, and secret rules. Violations are **stripped**
   from the completion; if everything is stripped, a safe refusal replaces it.
   The selective safeguard judge adds auditable reasoning.
4. **Finalize** — build a signed receipt, persist it, emit a dashboard event,
   return the (possibly modified) completion.

## Enforcement model

The agent executes whatever tool calls the **model** emits. By removing a
disallowed `tool_call` from the model's response before it reaches the agent,
the defender prevents the action rather than merely warning about it. Default
posture is **fail-closed**.

## Degradation

Every model-backed layer (Prompt Guard 2, gpt-oss-safeguard) is best-effort:
on a missing key, network error, or unparseable response it returns `None` and
the deterministic + heuristic layers carry the decision. The proxy never
hard-fails because a guard model was unreachable.
