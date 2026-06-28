/**
 * Deterministic rules engine — sub-millisecond, zero network, never flaky.
 * Port of proxy/app/detect/rules.py to JavaScript.
 *
 * Checks: tool allow/deny, egress host allowlist, secret leaks in args,
 * and argument-level danger patterns (Trail of Bits class).
 */

// Matches any scheme URL or scheme-relative //host
const URL_RE = /(?:[a-z][a-z0-9+.\-]*:)?\/\/[^\s"'<>]+/gi;
const EMAIL_RE = /[A-Za-z0-9._%+\-]+@([A-Za-z0-9.\-]+\.[A-Za-z]{2,})/g;

/**
 * Extract hostnames from tool-call argument text.
 * @param {string} args
 * @returns {string[]}
 */
function extractHosts(args) {
  const hosts = [];
  // Reset lastIndex for global regexes
  URL_RE.lastIndex = 0;
  EMAIL_RE.lastIndex = 0;

  let m;
  while ((m = URL_RE.exec(args)) !== null) {
    try {
      const url = new URL(m[0]);
      const host = url.hostname.toLowerCase();
      if (host) hosts.push(host);
    } catch {
      // malformed URL — skip
    }
  }
  while ((m = EMAIL_RE.exec(args)) !== null) {
    hosts.push(m[1].toLowerCase());
  }
  return hosts;
}

/**
 * Check a list of tool calls against the policy.
 * @param {Array<{id: string, function: {name: string, arguments: string}}>} toolCalls
 * @param {import('./policy.js').Policy} policy
 * @returns {{findings: Array<Object>, blocked: boolean, detail: string}}
 */
export function checkToolCalls(toolCalls, policy) {
  const t0 = performance.now();
  const findings = toolCalls.map((tc) => inspectToolCall(tc, policy));
  const blocked = findings.filter((f) => f.status === "block");
  const detail = blocked.length
    ? blocked.map((f) => f.reasons.join("; ")).join(" | ")
    : `${toolCalls.length} tool call(s) within policy`;

  return {
    findings,
    blocked: blocked.length > 0,
    detail,
    latencyMs: performance.now() - t0,
  };
}

/**
 * Inspect a single tool call against policy rules.
 * @param {{id: string, function: {name: string, arguments: string}}} tc
 * @param {import('./policy.js').Policy} policy
 */
function inspectToolCall(tc, policy) {
  const name = tc.function?.name || "(unnamed)";
  const args = tc.function?.arguments || "";
  const finding = {
    toolCallId: tc.id,
    toolName: name,
    status: "allow",
    reasons: [],
    hosts: [],
    secrets: [],
    argHits: [],
  };

  // 1. Tool allow/deny
  if (!policy.toolAllowed(name)) {
    finding.status = "block";
    const verb = policy.tool_denylist.includes(name)
      ? "denied"
      : "not on allowlist";
    finding.reasons.push(`tool '${name}' is ${verb}`);
  }

  // 2. Egress allowlist
  const hosts = extractHosts(args);
  finding.hosts = hosts;
  const badHosts = hosts.filter((h) => !policy.hostAllowed(h));
  if (badHosts.length > 0) {
    finding.status = "block";
    const unique = [...new Set(badHosts)].sort();
    finding.reasons.push(
      `egress to non-allowlisted host(s): ${unique.join(", ")}`
    );
  }

  // 3. Secret leak in args
  const secrets = findSecrets(args, policy);
  finding.secrets = secrets;
  if (secrets.length > 0) {
    finding.status = "block";
    finding.reasons.push(`secret(s) in tool args: ${secrets.join(", ")}`);
  }

  // 4. Argument-level danger (Trail of Bits class)
  const argHits = checkArgRules(name, args, policy);
  finding.argHits = argHits;
  if (argHits.length > 0) {
    finding.status = "block";
    finding.reasons.push(...argHits);
  }

  return finding;
}

/**
 * Find secret patterns in text.
 * @param {string} text
 * @param {import('./policy.js').Policy} policy
 * @returns {string[]}
 */
function findSecrets(text, policy) {
  const hits = [];
  for (const { name, regex } of policy.secret_patterns) {
    if (regex.test(text || "")) {
      hits.push(name);
    }
    regex.lastIndex = 0; // reset for global-safe patterns
  }
  return hits;
}

/**
 * Check argument-level danger rules.
 * @param {string} toolName
 * @param {string} args
 * @param {import('./policy.js').Policy} policy
 * @returns {string[]}
 */
function checkArgRules(toolName, args, policy) {
  const hits = [];
  for (const rule of policy.arg_rules) {
    const applies =
      rule.tools.includes("*") || rule.tools.includes(toolName);
    if (applies && rule.regex.test(args || "")) {
      hits.push(rule.reason);
    }
    rule.regex.lastIndex = 0;
  }
  return hits;
}
