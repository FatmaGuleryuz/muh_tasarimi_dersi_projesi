import type { CustomerDetail, CustomerList, RiskLevel, Summary } from "./types";

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    if (res.status === 404) throw new Error("Müşteri bulunamadı");
    throw new Error(`API hatası (${res.status})`);
  }
  return res.json();
}

export const fetchSummary = () => getJson<Summary>("/api/summary");

export function fetchCustomers(opts: { risk?: RiskLevel | ""; q?: string } = {}): Promise<CustomerList> {
  const params = new URLSearchParams();
  if (opts.risk) params.set("risk", opts.risk);
  if (opts.q) params.set("q", opts.q);
  const qs = params.toString();
  return getJson<CustomerList>(`/api/customers${qs ? `?${qs}` : ""}`);
}

export const fetchCustomer = (id: string) => getJson<CustomerDetail>(`/api/customers/${encodeURIComponent(id)}`);

export const EXPORT_HIGH_RISK_URL = "/api/export/high-risk.csv";
