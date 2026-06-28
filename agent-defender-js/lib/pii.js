/**
 * PII and secret redaction — regex-based, instant, deterministic.
 * Port of proxy/app/detect/pii.py to JavaScript.
 */

const PII_PATTERNS = [
  { name: "email",       regex: /[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}/g },
  { name: "ssn",         regex: /\b\d{3}-\d{2}-\d{4}\b/g },
  { name: "credit_card", regex: /\b(?:\d[ -]*?){13,16}\b/g },
  { name: "phone",       regex: /\b(?:\+?\d{1,2}[ -]?)?\(?\d{3}\)?[ -]?\d{3}[ -]?\d{4}\b/g },
  { name: "ipv4",        regex: /\b(?:\d{1,3}\.){3}\d{1,3}\b/g },
];

function mask(label) {
  return `[REDACTED:${label}]`;
}

/**
 * Redact secrets and PII from text.
 * @param {string} text
 * @param {import('./policy.js').Policy} policy
 * @returns {{ redacted: string, labels: string[] }}
 */
export function redact(text, policy) {
  if (!text) return { redacted: text, labels: [] };
  const labels = [];
  let out = text;

  // Secrets first (policy-defined patterns)
  for (const { name, regex } of policy.secret_patterns) {
    const re = new RegExp(regex.source, regex.flags.includes("g") ? regex.flags : regex.flags + "g");
    if (re.test(out)) {
      re.lastIndex = 0;
      out = out.replace(re, mask(name));
      labels.push(name);
    }
  }

  // Generic PII patterns
  for (const { name, regex } of PII_PATTERNS) {
    regex.lastIndex = 0;
    if (regex.test(out)) {
      regex.lastIndex = 0;
      out = out.replace(regex, mask(name));
      labels.push(name);
    }
  }

  return { redacted: out, labels };
}

/**
 * Scan text and return redacted version + check result.
 * @param {string} text
 * @param {import('./policy.js').Policy} policy
 * @param {string} [source="content"]
 * @returns {{ redacted: string, status: string, labels: string[], detail: string }}
 */
export function scanAndRedact(text, policy, source = "content") {
  const { redacted, labels } = redact(text, policy);
  const status = labels.length > 0 ? "flag" : "pass";
  const detail = labels.length
    ? `redacted in ${source}: ${labels.join(", ")}`
    : `no PII in ${source}`;
  return { redacted, status, labels, detail };
}
