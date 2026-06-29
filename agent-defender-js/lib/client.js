/**
 * FirewallOpenAI — drop-in wrapper for the OpenAI Node.js SDK.
 *
 * Intercepts chat.completions.create(), runs the policy engine locally
 * in-process, and strips blocked tool calls before the agent ever sees them.
 *
 * Usage:
 *   import OpenAI from "openai";
 *   import { FirewallOpenAI } from "agent-defender";
 *
 *   const raw = new OpenAI({ apiKey: "..." });
 *   const client = new FirewallOpenAI(raw, { policyPath: "policy.yaml" });
 *
 *   // Use exactly like the standard client — blocked calls are stripped silently
 *   const res = await client.chat.completions.create({ model: "gpt-4", messages, tools });
 *   console.log(res.firewall); // { action, reason, stripped_tool_calls, ... }
 */

import { loadPolicy } from "./policy.js";
import { checkToolCalls } from "./rules.js";
import { scanAndRedact } from "./pii.js";

export class FirewallOpenAI {
  /**
   * @param {import("openai").default} client  — an already-constructed OpenAI client
   * @param {{ policyPath: string }} opts
   */
  constructor(client, opts) {
    if (!opts?.policyPath) {
      throw new Error("FirewallOpenAI requires opts.policyPath");
    }
    this._client = client;
    this._policy = loadPolicy(opts.policyPath);

    // Build the chat.completions proxy
    const self = this;
    this.chat = {
      completions: {
        /**
         * Drop-in replacement for client.chat.completions.create().
         * Runs inbound + outbound policy checks in-process.
         */
        async create(body, requestOpts) {
          // 1. Inbound: redact secrets/PII in user messages
          if (Array.isArray(body.messages)) {
            for (const msg of body.messages) {
              if (typeof msg.content === "string" && msg.content) {
                const scan = scanAndRedact(
                  msg.content,
                  self._policy,
                  msg.role || "user"
                );
                if (scan.status === "flag") {
                  msg.content = scan.redacted;
                }
              }
            }
          }

          // 2. Call the upstream LLM through the original client
          const response = await self._client.chat.completions.create(
            body,
            requestOpts
          );

          // 3. Outbound: inspect tool calls in the response
          const firewallMeta = {
            action: "allow",
            reason: null,
            rule_fired: null,
            stripped_tool_calls: [],
            blocked_calls: [],
          };

          const choice = response.choices?.[0];
          if (choice) {
            const rawCalls = choice.message?.tool_calls || [];

            if (rawCalls.length > 0) {
              const mapped = rawCalls.map((tc) => ({
                id: tc.id,
                function: {
                  name: tc.function.name,
                  arguments: tc.function.arguments,
                },
              }));

              const { findings } = checkToolCalls(mapped, self._policy);
              const blockedIds = new Set(
                findings
                  .filter((f) => f.status === "block")
                  .map((f) => f.toolCallId)
              );

              if (blockedIds.size > 0) {
                const kept = rawCalls.filter((tc) => !blockedIds.has(tc.id));
                choice.message.tool_calls = kept.length > 0 ? kept : null;

                if (kept.length === 0 && !choice.message.content) {
                  choice.message.content = self._policy.block_message;
                  choice.finish_reason = "content_filter";
                }

                const firstBlocked = findings.find(
                  (f) => f.status === "block"
                );
                firewallMeta.action = "block";
                firewallMeta.stripped_tool_calls = [...blockedIds].sort();
                firewallMeta.rule_fired = "deterministic_rules";
                firewallMeta.reason = firstBlocked.reasons.join("; ");

                for (const f of findings) {
                  if (f.status === "block") {
                    firewallMeta.blocked_calls.push({
                      name: f.toolName,
                      reasons: f.reasons,
                    });
                  }
                }
              }
            }

            // Redact secrets from text output
            const content = choice.message?.content;
            if (typeof content === "string" && content) {
              const scan = scanAndRedact(content, self._policy, "completion");
              if (scan.status === "flag") {
                choice.message.content = scan.redacted;
                firewallMeta.action = "redact";
                firewallMeta.reason =
                  "secret/PII redacted from model output";
              }
            }
          }

          // Attach firewall metadata to the response
          response.firewall = firewallMeta;
          return response;
        },
      },
    };
  }

  // Proxy everything else to the original client
  get models() {
    return this._client.models;
  }
  get embeddings() {
    return this._client.embeddings;
  }
  get files() {
    return this._client.files;
  }
  get images() {
    return this._client.images;
  }
  get audio() {
    return this._client.audio;
  }
}
