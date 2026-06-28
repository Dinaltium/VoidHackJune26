import type { Policy, Stats } from "./types";

export const FIREWALL_URL = process.env.NEXT_PUBLIC_FIREWALL_URL ?? "http://127.0.0.1:8000";

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${FIREWALL_URL}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return (await res.json()) as T;
}

async function postJSON<T>(path: string, body?: any): Promise<T> {
  const res = await fetch(`${FIREWALL_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `${path} → ${res.status}`);
  }
  return (await res.json()) as T;
}

export const getPolicy = () => getJSON<Policy>("/api/policy");
export const getStats = () => getJSON<Stats>("/api/stats");
export const runDemo = () => postJSON<{ ok: boolean }>("/api/demo/run");
export const resetStore = () => postJSON<{ ok: boolean }>("/api/reset");

export const getRawPolicy = () => getJSON<{ yaml: string }>("/api/policy/raw");
export const saveRawPolicy = (yaml: string) =>
  postJSON<{ ok: boolean; policy: Policy }>("/api/policy/raw", { yaml });
export const askAiToEditPolicy = (prompt: string) =>
  postJSON<{ yaml: string; explanation: string; error?: string }>(
    "/api/policy/ai-edit",
    { prompt }
  );

