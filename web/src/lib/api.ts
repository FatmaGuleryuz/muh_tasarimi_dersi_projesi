import type { Summary } from "./types";

export async function fetchSummary(): Promise<Summary> {
  const res = await fetch("/api/summary");
  if (!res.ok) throw new Error(`API hatası (${res.status})`);
  return res.json();
}

export const EXPORT_HIGH_RISK_URL = "/api/export/high-risk.csv";
