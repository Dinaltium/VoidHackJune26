/**
 * Policy loader — reads a YAML policy file and returns a structured Policy object.
 * Port of proxy/app/policy.py to JavaScript.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import yaml from "js-yaml";

/**
 * @typedef {Object} SecretPattern
 * @property {string} name
 * @property {string} regex
 */

/**
 * @typedef {Object} ArgRule
 * @property {string} name
 * @property {string} reason
 * @property {string} regex
 * @property {string[]} tools
 */

/**
 * @typedef {Object} PolicyData
 * @property {number}          version
 * @property {string}          description
 * @property {string[]}        tool_allowlist
 * @property {string[]}        tool_denylist
 * @property {string[]}        egress_allowlist
 * @property {SecretPattern[]} secret_patterns
 * @property {ArgRule[]}       arg_rules
 * @property {string[]}        injection_phrases
 * @property {number}          injection_threshold
 * @property {number}          token_budget_per_session
 * @property {boolean}         fail_closed
 * @property {string}          block_message
 */

const DEFAULTS = {
  version: 1,
  description: "",
  tool_allowlist: [],
  tool_denylist: [],
  egress_allowlist: [],
  secret_patterns: [],
  arg_rules: [],
  injection_phrases: [],
  injection_threshold: 0.8,
  token_budget_per_session: 20000,
  fail_closed: true,
  block_message: "[Agent Firewall] Action blocked by policy.",
};

/**
 * Compile a regex string that may contain Python-style inline flags like (?i).
 * JavaScript doesn't support inline flag groups, so we extract them and pass
 * as RegExp constructor flags.
 * @param {string} pattern
 * @returns {RegExp}
 */
function compileRegex(pattern) {
  let flags = "";
  let cleaned = pattern;
  // Extract leading (?flags) group — Python uses (?i), (?s), (?m), etc.
  const inlineMatch = cleaned.match(/^\(\?([imsu]+)\)/);
  if (inlineMatch) {
    flags = inlineMatch[1];
    cleaned = cleaned.slice(inlineMatch[0].length);
  }
  return new RegExp(cleaned, flags);
}

export class Policy {
  constructor(raw = {}) {
    const d = { ...DEFAULTS, ...raw };
    this.version = d.version;
    this.description = d.description;
    this.tool_allowlist = d.tool_allowlist || [];
    this.tool_denylist = d.tool_denylist || [];
    this.egress_allowlist = d.egress_allowlist || [];
    this.secret_patterns = (d.secret_patterns || []).map((p) => ({
      name: p.name,
      regex: compileRegex(p.regex),
    }));
    this.arg_rules = (d.arg_rules || []).map((r) => ({
      name: r.name,
      reason: r.reason,
      regex: compileRegex(r.regex),
      tools: r.tools || ["*"],
    }));
    this.injection_phrases = d.injection_phrases || [];
    this.injection_threshold = d.injection_threshold;
    this.token_budget_per_session = d.token_budget_per_session;
    this.fail_closed = d.fail_closed;
    this.block_message = d.block_message;
  }

  /** @param {string} name */
  toolAllowed(name) {
    if (this.tool_denylist.includes(name)) return false;
    if (this.tool_allowlist.length === 0) return true;
    return this.tool_allowlist.includes(name);
  }

  /** @param {string} host */
  hostAllowed(host) {
    const h = host.toLowerCase().trim();
    for (const a of this.egress_allowlist) {
      const allowed = a.toLowerCase().trim();
      if (h === allowed || h.endsWith("." + allowed)) return true;
    }
    return false;
  }
}

/**
 * Load a policy from a YAML file path.
 * @param {string} filePath
 * @returns {Policy}
 */
export function loadPolicy(filePath) {
  const abs = resolve(filePath);
  const text = readFileSync(abs, "utf8");
  const raw = yaml.load(text) || {};
  return new Policy(raw);
}
