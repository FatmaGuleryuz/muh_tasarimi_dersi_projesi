import type { CustomerDetail, CustomerList, ModelReport, RiskLevel, Summary } from "./types";

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    if (res.status === 404) throw new Error("Müşteri bulunamadı");
    let detail: string | undefined;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // gövde JSON değil veya boş — detail olmadan devam
    }
    throw new Error(detail ?? `API hatası (${res.status})`);
  }
  return res.json();
}

export const fetchSummary = () => getJson<Summary>("/api/summary");

export const fetchModelReport = () => getJson<ModelReport>("/api/model-report");

export function fetchCustomers(opts: { risk?: RiskLevel | ""; q?: string } = {}): Promise<CustomerList> {
  const params = new URLSearchParams();
  if (opts.risk) params.set("risk", opts.risk);
  if (opts.q) params.set("q", opts.q);
  const qs = params.toString();
  return getJson<CustomerList>(`/api/customers${qs ? `?${qs}` : ""}`);
}

export const fetchCustomer = (id: string) => getJson<CustomerDetail>(`/api/customers/${encodeURIComponent(id)}`);

export const EXPORT_HIGH_RISK_URL = "/api/export/high-risk.csv";
