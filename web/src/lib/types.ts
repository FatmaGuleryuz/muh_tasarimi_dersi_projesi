// backend/app/main.py -> GET /api/summary yanıtı
export type RiskLevel = "high" | "mid" | "low";

export interface ModelMetrics { key: string; label: string; roc_auc: number; precision: number; recall: number; f1: number }
export interface TopCustomer { customer_id: string; probability: number; risk: RiskLevel; contract: string; reason: string; action: string }

export interface Summary {
  dataset: { name: string; test_customers: number; total_rows: number };
  thresholds: { high: number; mid: number };
  model: { best: string; best_label: string; roc_auc: number; target: number; target_met: boolean; models: ModelMetrics[] };
  kpis: {
    total: number; high_risk_count: number; high_risk_share: number; avg_probability: number;
    high_risk_actual_rate: number; overall_actual_rate: number;
  };
  risk_distribution: { level: RiskLevel; label: string; count: number; share: number }[];
  by_contract: { contract: string; label: string; count: number; avg_probability: number; actual_rate: number }[];
  top_drivers: { feature: string; label: string; score: number }[];
  top_customers: TopCustomer[];
}

// backend/app/main.py -> GET /api/customers yanıtı
export interface CustomerList { total: number; customers: TopCustomer[] }

// backend/app/main.py -> GET /api/customers/{id} yanıtı
export interface CustomerDetail {
  customer_id: string;
  probability: number;
  actual_churn: boolean;
  risk: RiskLevel;
  contract: string;
  tenure_months: number;
  monthly_charges: number;
  total_charges: number | null;
  reason: string;
  reason_feature: string;
  action: string;
  overall_top_drivers: { feature: string; label: string; score: number }[];
}
