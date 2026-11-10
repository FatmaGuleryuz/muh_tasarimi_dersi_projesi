import type { CustomerDetail, CustomerList, InterventionPlans, ModelReport, Outcome, PlanRisk, PostmortemDetail, PostmortemList, PredictRequest, PredictResponse, RiskLevel, Summary } from "./types";

async function getJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    if (res.status === 404 && !init) throw new Error("Müşteri bulunamadı");
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

export function fetchPostmortem(opts: { outcome?: Outcome | "" } = {}): Promise<PostmortemList> {
  const params = new URLSearchParams();
  if (opts.outcome) params.set("outcome", opts.outcome);
  const qs = params.toString();
  return getJson<PostmortemList>(`/api/postmortem${qs ? `?${qs}` : ""}`);
}

export const fetchPostmortemDetail = (id: string) => getJson<PostmortemDetail>(`/api/postmortem/${encodeURIComponent(id)}`);

export const EXPORT_HIGH_RISK_URL = "/api/export/high-risk.csv";

export const predict = (body: PredictRequest, signal?: AbortSignal) =>
  getJson<PredictResponse>("/api/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });

export const fetchInterventionPlans = (risk: PlanRisk) =>
  getJson<InterventionPlans>(`/api/intervention-plans?risk=${encodeURIComponent(risk)}`);

export const interventionExportUrl = (action: string, risk: PlanRisk) =>
  `/api/intervention-plans/export.csv?action=${encodeURIComponent(action)}&risk=${encodeURIComponent(risk)}`;
