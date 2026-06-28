# voidhack-agent-firewall

Drop-in security guardrails for AI agents. Blocks unauthorized tool calls, data exfiltration, prompt injection, and secret leaks — **in-process, sub-millisecond, zero network**.

## Quick Start (npx)

```bash
# Scaffold a policy.yaml in your project
npx voidhack-agent-firewall init

# Validate your policy
npx voidhack-agent-firewall check

# Run the interactive demo
npx voidhack-agent-firewall demo
```

## Library Usage

### OpenAI SDK Wrapper

```js
import OpenAI from "openai";
import { FirewallOpenAI } from "voidhack-agent-firewall";

const raw = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

const client = new FirewallOpenAI(raw, {
  policyPath: "policy.yaml",
});

// Use exactly like the standard client
const res = await client.chat.completions.create({
  model: "gpt-4",
  messages: [{ role: "user", content: "Summarize the Q3 report" }],
  tools: myTools,
});

// Blocked tool calls are silently stripped before your agent sees them
console.log(res.firewall);
// { action: "block", reason: "tool 'send_email' is denied", ... }
```

### LangChain.js Callback Handler

```js
import { FirewallCallbackHandler } from "voidhack-agent-firewall/langchain";

const handler = new FirewallCallbackHandler({
  policyPath: "policy.yaml",
});

// Add to any LangChain agent executor
const executor = AgentExecutor.fromAgentAndTools({
  agent,
  tools,
  callbacks: [handler],
});

// Unauthorized tool calls throw PolicyViolationError immediately
```

### Standalone Rule Checks

```js
import { loadPolicy, checkToolCalls, scanAndRedact } from "voidhack-agent-firewall";

const policy = loadPolicy("policy.yaml");

// Check tool calls
const { findings, blocked } = checkToolCalls(
  [{ id: "1", function: { name: "send_email", arguments: '{"to":"x@evil.com"}' } }],
  policy
);

// Redact secrets/PII
const scan = scanAndRedact("API key: sk-abc123456789012345678", policy);
console.log(scan.redacted); // "API key: [REDACTED:openai_key]"
```

## What It Catches

| Threat | Example | Detection |
|--------|---------|-----------|
| Denied tools | `send_email`, `run_shell` | Tool denylist |
| Unknown tools | Any tool not on allowlist | Tool allowlist |
| Data exfiltration | `http_fetch("https://attacker.net/...")` | Egress allowlist |
| Secret leaks | API keys, AWS keys in tool args | Regex patterns |
| Path traversal | `../../etc/passwd` | Arg rules |
| Command injection | `--exec rm -rf /` | Arg rules |
| Shell substitution | `` `whoami` ``, `$(cat /etc/shadow)` | Arg rules |
| PII exposure | SSN, credit cards, emails | PII scanner |

## Policy Format

See `policy.yaml` for the full schema. Key sections:

```yaml
tool_allowlist: [read_doc, summarize]    # Only these tools allowed
tool_denylist:  [send_email, run_shell]  # Always blocked
egress_allowlist: [example.com]          # Only these hosts reachable
secret_patterns:                         # Block/redact these patterns
  - name: openai_key
    regex: 'sk-[A-Za-z0-9]{20,}'
arg_rules:                               # Block dangerous payloads
  - name: path_traversal
    reason: "path traversal in argument"
    regex: '\.\./|\.\.\\'
    tools: ["*"]
```
