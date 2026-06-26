import type { Policy, Stats } from "./types";

export const FIREWALL_URL = process.env.NEXT_PUBLIC_FIREWALL_URL ?? "http://127.0.0.1:8000";

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${FIREWALL_URL}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return (await res.json()) as T;
}

async function postJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${FIREWALL_URL}${path}`, { method: "POST" });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return (await res.json()) as T;
}

export const getPolicy = () => getJSON<Policy>("/api/policy");
export const getStats = () => getJSON<Stats>("/api/stats");
export const runDemo = () => postJSON<{ ok: boolean }>("/api/demo/run");
export const resetStore = () => postJSON<{ ok: boolean }>("/api/reset");
