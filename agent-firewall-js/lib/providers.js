import { FirewallOpenAI } from "./client.js";
import { loadPolicy } from "./policy.js";
import { checkToolCalls } from "./rules.js";
import { scanAndRedact } from "./pii.js";

export const OPENAI_COMPATIBLE_BASE_URLS = {
  openai: "https://api.openai.com/v1",
  groq: "https://api.groq.com/openai/v1",
  nvidia: "https://integrate.api.nvidia.com/v1",
  mistral: "https://api.mistral.ai/v1",
  together: "https://api.together.xyz/v1",
  fireworks: "https://api.fireworks.ai/inference/v1",
  perplexity: "https://api.perplexity.ai",
  deepseek: "https://api.deepseek.com",
  openrouter: "https://openrouter.ai/api/v1",
  local: "http://localhost:8000/v1",
};

export function openAICompatibleOptions(provider, opts = {}) {
  const baseURL = opts.baseURL || OPENAI_COMPATIBLE_BASE_URLS[provider];
  if (!baseURL) {
    throw new Error(`Unknown OpenAI-compatible provider: ${provider}`);
  }
  return {
    ...opts,
    baseURL,
  };
}

export async function createFirewallOpenAICompatible(provider, opts = {}) {
  const { default: OpenAI } = await import("openai");
  const { policyPath, ...clientOpts } = opts;
  const raw = new OpenAI(openAICompatibleOptions(provider, clientOpts));
  return new FirewallOpenAI(raw, { policyPath: policyPath || "policy.yaml" });
}

function stringifyArgs(args) {
  if (typeof args === "string") return args;
  if (args == null) return "{}";
  try {
    return JSON.stringify(args);
  } catch {
    return String(args);
  }
}

function read(obj, path) {
  let cur = obj;
  for (const key of path) {
    if (cur == null) return undefined;
    cur = cur[key];
  }
  return cur;
}

function makeFirewallMeta() {
  return {
    action: "allow",
    reason: null,
    rule_fired: null,
    stripped_tool_calls: [],
    blocked_calls: [],
  };
}

function enforceToolCalls(nativeCalls, policy, removeBlocked) {
  const meta = makeFirewallMeta();
  if (nativeCalls.length === 0) return meta;

  const mapped = nativeCalls.map((call) => ({
    id: call.id,
    function: {
      name: call.name,
      arguments: stringifyArgs(call.arguments),
    },
  }));

  const { findings } = checkToolCalls(mapped, policy);
  const blockedIds = new Set(
    findings.filter((f) => f.status === "block").map((f) => f.toolCallId)
  );

  if (blockedIds.size === 0) return meta;

  removeBlocked(blockedIds);
  const firstBlocked = findings.find((f) => f.status === "block");
  meta.action = "block";
  meta.stripped_tool_calls = [...blockedIds].sort();
  meta.rule_fired = "deterministic_rules";
  meta.reason = firstBlocked?.reasons?.join("; ") || "tool call blocked";
  meta.blocked_calls = findings
    .filter((f) => f.status === "block")
    .map((f) => ({
      name: f.toolName,
      reasons: f.reasons,
    }));
  return meta;
}

function redactAnthropicMessages(body, policy) {
  if (!Array.isArray(body?.messages)) return;
  for (const msg of body.messages) {
    if (typeof msg.content === "string" && msg.content) {
      const scan = scanAndRedact(msg.content, policy, msg.role || "user");
      if (scan.status === "flag") msg.content = scan.redacted;
    }
    if (Array.isArray(msg.content)) {
      for (const part of msg.content) {
        if (part?.type === "text" && typeof part.text === "string") {
          const scan = scanAndRedact(part.text, policy, msg.role || "user");
          if (scan.status === "flag") part.text = scan.redacted;
        }
      }
    }
  }
}

export class FirewallAnthropic {
  constructor(client, opts) {
    if (!opts?.policyPath) {
      throw new Error("FirewallAnthropic requires opts.policyPath");
    }
    this._client = client;
    this._policy = loadPolicy(opts.policyPath);
    this.messages = {
      create: async (body, requestOpts) => {
        redactAnthropicMessages(body, this._policy);
        const response = await this._client.messages.create(body, requestOpts);
        const content = response.content || [];
        const calls = content
          .filter((part) => part?.type === "tool_use")
          .map((part) => ({
            id: part.id,
            name: part.name,
            arguments: part.input,
          }));

        response.firewall = enforceToolCalls(calls, this._policy, (blockedIds) => {
          response.content = content.filter(
            (part) => part?.type !== "tool_use" || !blockedIds.has(part.id)
          );
          if (response.content.length === 0) {
            response.content = [{ type: "text", text: this._policy.block_message }];
          }
        });
        return response;
      },
    };
  }

  get models() {
    return this._client.models;
  }
}

export class FirewallGeminiModel {
  constructor(model, policy) {
    this._model = model;
    this._policy = policy;
  }

  async generateContent(request, requestOpts) {
    const response = await this._model.generateContent(request, requestOpts);
    const candidates = read(response, ["response", "candidates"]) || response.candidates || [];
    const calls = [];
    for (const [candidateIndex, candidate] of candidates.entries()) {
      const parts = candidate?.content?.parts || [];
      for (const [partIndex, part] of parts.entries()) {
        const fn = part?.functionCall || part?.function_call;
        if (fn) {
          calls.push({
            id: `gemini-${candidateIndex}-${partIndex}`,
            candidateIndex,
            partIndex,
            name: fn.name,
            arguments: fn.args || fn.arguments || {},
          });
        }
      }
    }

    response.firewall = enforceToolCalls(calls, this._policy, (blockedIds) => {
      const blockedCalls = calls
        .filter((call) => blockedIds.has(call.id))
        .sort((a, b) => b.partIndex - a.partIndex);
      for (const call of blockedCalls) {
        const parts = candidates[call.candidateIndex]?.content?.parts || [];
        parts.splice(call.partIndex, 1);
      }
      for (const candidate of candidates) {
        const parts = candidate?.content?.parts;
        if (Array.isArray(parts) && parts.length === 0) {
          parts.push({ text: this._policy.block_message });
        }
      }
    });
    return response;
  }

  startChat(params = {}) {
    const chat = this._model.startChat(params);
    return new FirewallGeminiChat(chat, this._policy);
  }
}

class FirewallGeminiChat {
  constructor(chat, policy) {
    this._chat = chat;
    this._policy = policy;
  }

  async sendMessage(message, requestOpts) {
    const response = await this._chat.sendMessage(message, requestOpts);
    return new FirewallGeminiModel(
      { generateContent: async () => response },
      this._policy
    ).generateContent({}, requestOpts);
  }
}

export class FirewallGoogleGenerativeAI {
  constructor(client, opts) {
    if (!opts?.policyPath) {
      throw new Error("FirewallGoogleGenerativeAI requires opts.policyPath");
    }
    this._client = client;
    this._policy = loadPolicy(opts.policyPath);
  }

  getGenerativeModel(params, requestOpts) {
    const model = this._client.getGenerativeModel(params, requestOpts);
    return new FirewallGeminiModel(model, this._policy);
  }
}
