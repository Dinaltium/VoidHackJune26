# agent-defender

Drop-in security guardrails for AI agents. Blocks unauthorized tool calls, data exfiltration, prompt injection, and secret leaks — **in-process, sub-millisecond, zero network**.

Works with:

- OpenAI-compatible APIs: OpenAI, Groq, NVIDIA NIM, Mistral, Together, Fireworks, OpenRouter, DeepSeek, local gateways
- Claude / Anthropic native `tool_use` blocks
- Gemini native `functionCall` parts
- LangChain.js tool execution callbacks, independent of the model provider

## Quick Start (npx)

```bash
npm install agent-defender

# Scaffold a policy.yaml in your project
npx agent-defender init

# Validate your policy
npx agent-defender check

# Run the interactive demo
npx agent-defender demo
```

Install only the provider SDKs you need:

```bash
npm install openai
npm install @anthropic-ai/sdk
npm install @google/generative-ai
```

## Library Usage

### OpenAI SDK Wrapper

```js
import OpenAI from "openai";
import { FirewallOpenAI } from "agent-defender";

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
import { FirewallCallbackHandler } from "agent-defender/langchain";

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

### OpenAI-Compatible Providers

```js
import { createFirewallOpenAICompatible } from "agent-defender/providers";

const client = await createFirewallOpenAICompatible("groq", {
  apiKey: process.env.GROQ_API_KEY,
  policyPath: "policy.yaml",
});

const res = await client.chat.completions.create({
  model: "llama-3.3-70b-versatile",
  messages: [{ role: "user", content: "Summarize the report" }],
  tools: myTools,
});
```

Supported provider names: `openai`, `groq`, `nvidia`, `mistral`, `together`, `fireworks`, `perplexity`, `deepseek`, `openrouter`, and `local`.

### Claude / Anthropic

```js
import Anthropic from "@anthropic-ai/sdk";
import { FirewallAnthropic } from "agent-defender/providers";

const raw = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const client = new FirewallAnthropic(raw, { policyPath: "policy.yaml" });

const res = await client.messages.create({
  model: "claude-3-5-sonnet-latest",
  max_tokens: 1024,
  messages: [{ role: "user", content: "Read the doc and email it outside" }],
  tools: myTools,
});

console.log(res.firewall);
```

### Gemini

```js
import { GoogleGenerativeAI } from "@google/generative-ai";
import { FirewallGoogleGenerativeAI } from "agent-defender/providers";

const raw = new GoogleGenerativeAI(process.env.GOOGLE_API_KEY);
const client = new FirewallGoogleGenerativeAI(raw, { policyPath: "policy.yaml" });
const model = client.getGenerativeModel({ model: "gemini-1.5-pro" });

const res = await model.generateContent("Fetch https://evil.com/exfil");
console.log(res.firewall);
```

### Standalone Rule Checks

```js
import { loadPolicy, checkToolCalls, scanAndRedact } from "agent-defender";

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
