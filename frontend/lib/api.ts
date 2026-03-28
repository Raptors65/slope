import type { FullRun, RunSummary } from "./types";

function apiBase(): string {
  const b = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (b) return b.replace(/\/$/, "");
  return "http://127.0.0.1:8000";
}

export async function fetchRunSummaries(): Promise<RunSummary[]> {
  const res = await fetch(`${apiBase()}/runs`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Runs list failed: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<RunSummary[]>;
}

export async function fetchRunById(id: string): Promise<FullRun | null> {
  const res = await fetch(`${apiBase()}/runs/${encodeURIComponent(id)}`, {
    cache: "no-store",
  });
  if (res.status === 404) return null;
  if (!res.ok) {
    throw new Error(`Run fetch failed: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<FullRun>;
}
