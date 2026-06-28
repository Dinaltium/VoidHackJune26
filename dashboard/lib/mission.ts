import { FIREWALL_URL } from "./api";

export interface ToolCall {
  name: string;
  arguments: string;
}

export interface BlockedAction {
  name: string;
  arguments: string;
  reasons: string[];
}

export interface MissionStep {
  index: number;
  thought: string;
  executed: ToolCall[];
  blocked: BlockedAction[];
  firewall_action: string | null;
  firewall_reason: string | null;
}

export interface ExecutedAction {
  tool: string;
  summary: string;
  dangerous: boolean;
}

export interface MissionResult {
  firewall_on: boolean;
  model: string;
  session_id: string;
  steps: MissionStep[];
  executed_actions: ExecutedAction[];
  blocked_actions: BlockedAction[];
  final_answer: string;
  breached: boolean;
  summary: { steps: number; executed: number; blocked: number; dangerous_executed: number };
}

export interface Scenario {
  id: string;
  title: string;
  task: string;
  document: string;
}

export interface MissionRequest {
  scenario?: string;
  task?: string;
  document?: string;
  firewall: boolean;
}

export interface ExtractResult {
  filename: string;
  kind: "pdf" | "email" | "text";
  chars: number;
  text: string;
  suspicious: boolean;
  signals: string[];
}

export async function getScenarios(): Promise<Scenario[]> {
  const res = await fetch(`${FIREWALL_URL}/api/mission/scenarios`, { cache: "no-store" });
  if (!res.ok) throw new Error(`scenarios → ${res.status}`);
  return ((await res.json()) as { scenarios: Scenario[] }).scenarios;
}

export async function runMission(body: MissionRequest): Promise<MissionResult> {
  const res = await fetch(`${FIREWALL_URL}/api/mission/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`mission → ${res.status}`);
  return (await res.json()) as MissionResult;
}

/** Upload a real file (PDF / email / text) and get back the text an agent would
 *  read, plus an injection pre-scan. The text becomes the mission's document. */
export async function extractDocument(file: Blob, filename: string): Promise<ExtractResult> {
  const form = new FormData();
  form.append("file", file, filename);
  const res = await fetch(`${FIREWALL_URL}/api/mission/extract`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(`extract → ${res.status}`);
  return (await res.json()) as ExtractResult;
}

/** Fetch a bundled sample file from /public and run it through extraction. */
export async function extractSample(path: string, filename: string): Promise<ExtractResult> {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error(`sample → ${res.status}`);
  return extractDocument(await res.blob(), filename);
}
