/**
 * LangChain.js callback handler — intercepts tool execution and blocks
 * unauthorized actions before they run.
 *
 * Usage:
 *   import { FirewallCallbackHandler } from "voidhack-agent-defender/langchain";
 *
 *   const handler = new FirewallCallbackHandler({ policyPath: "policy.yaml" });
 *   const executor = AgentExecutor.fromAgentAndTools({
 *     agent, tools, callbacks: [handler]
 *   });
 */

import { loadPolicy } from "./policy.js";
import { checkToolCalls } from "./rules.js";

export class PolicyViolationError extends Error {
  constructor(message) {
    super(message);
    this.name = "PolicyViolationError";
  }
}

export class FirewallCallbackHandler {
  /**
   * @param {{ policyPath: string }} opts
   */
  constructor(opts) {
    if (!opts?.policyPath) {
      throw new Error("FirewallCallbackHandler requires opts.policyPath");
    }
    this.policy = loadPolicy(opts.policyPath);
    this.name = "AgentFirewall";
  }

  /**
   * Called by LangChain right before a tool executes.
   * @param {{ name?: string }} tool  — serialized tool metadata
   * @param {string} input             — tool input string
   * @param {string} [runId]
   */
  async handleToolStart(tool, input, runId) {
    const toolName = tool?.name || "";

    // Check denied tools
    if (this.policy.tool_denylist.includes(toolName)) {
      throw new PolicyViolationError(
        `Security Block: Tool '${toolName}' is restricted by security policy.`
      );
    }

    // Check allowed tools
    if (
      this.policy.tool_allowlist.length > 0 &&
      !this.policy.tool_allowlist.includes(toolName)
    ) {
      throw new PolicyViolationError(
        `Security Block: Tool '${toolName}' is not in the allowed tool list.`
      );
    }

    // Check argument-level rules
    const tc = {
      id: runId || "lc-run",
      function: { name: toolName, arguments: input || "" },
    };
    const { findings } = checkToolCalls([tc], this.policy);
    const blocked = findings.filter((f) => f.status === "block");

    if (blocked.length > 0) {
      const reasons = blocked[0].reasons.join("; ");
      throw new PolicyViolationError(
        `Security Block: Tool '${toolName}' argument check failed. Reason: ${reasons}`
      );
    }
  }
}
