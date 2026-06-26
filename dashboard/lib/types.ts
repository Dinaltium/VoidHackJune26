export type Action = "allow" | "redact" | "block";
export type Status = "pass" | "flag" | "block";

export interface CheckResult {
  name: string;
  status: Status;
  detail: string;
  score: number | null;
  latency_ms: number;
  meta: Record<string, unknown>;
}

export interface FirewallEvent {
  id: string;
  ts: string;
  session_id: string;
  action: Action;
  status: Status;
  title: string;
  detail: string;
  rule: string | null;
  receipt_id: string | null;
  checks: CheckResult[];
}

export interface Stats {
  allow: number;
  redact: number;
  block: number;
  total: number;
}

export interface Policy {
  version: number;
  description: string;
  tool_allowlist: string[];
  tool_denylist: string[];
  egress_allowlist: string[];
  injection_threshold: number;
  token_budget_per_session: number;
}
