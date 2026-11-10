// backend/app/main.py -> GET /api/summary yanıtı
export type RiskLevel = "high" | "mid" | "low";

export interface ModelMetrics { key: string; label: string; roc_auc: number; precision: number; recall: number; f1: number }
// contract: ikinci veri setinde (openml_churn) null olabilir
export interface TopCustomer { customer_id: string; probability: number; risk: RiskLevel; contract: string | null; reason: string; action: string }

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
  // contract/tenure_months/monthly_charges/total_charges: openml_churn'de null (Telco'ya özgü alanlar)
  contract: string | null;
  tenure_months: number | null;
  monthly_charges: number | null;
  total_charges: number | null;
  reason: string;
  reason_feature: string;
  action: string;
  overall_top_drivers: { feature: string; label: string; score: number }[];
}

// backend/app/main.py -> GET /api/postmortem yanıtı (kayıp müşteri postmortem)
export type Outcome = "caught" | "partial" | "missed";

export interface PostmortemSummary {
  lost_total: number; caught: number; partial: number; missed: number;
  catch_rate: number; strict_catch_rate: number; false_alarm_count: number; precision_high: number;
}

export interface PostmortemItem {
  customer_id: string; probability: number; risk: RiskLevel; outcome: Outcome;
  contract: string | null; reason: string; reason_feature: string; action: string;
}

export interface PostmortemList { summary: PostmortemSummary; total: number; items: PostmortemItem[] }

// backend/app/main.py -> GET /api/postmortem/{id} yanıtı
export interface PostmortemDetail {
  customer_id: string; actual_churn: boolean; probability: number; risk: RiskLevel; outcome: Outcome;
  contract: string | null; tenure_months: number | null; monthly_charges: number | null; total_charges: number | null;
  reason: string; reason_feature: string; top_reason_global_rank: number | null;
  action: string; action_applied: boolean | null; action_applied_note: string;
}

// backend/app/main.py -> GET /api/model-report yanıtı
export interface ModelReport {
  models: ModelMetrics[];
  best: string;
  best_label: string;
  target: number;
  target_met: boolean;
  dataset: { name: string; rows: number; churn_rate: number };
  drivers: { feature: string; label: string; score: number }[];
}

// backend/app/main.py -> POST /api/predict (yalnızca Telco)
export type ContractType = "Month-to-month" | "One year" | "Two year";
export type InternetService = "DSL" | "Fiber optic" | "No";
export type PaymentMethod = "Electronic check" | "Mailed check" | "Bank transfer (automatic)" | "Credit card (automatic)";

export interface PredictRequest {
  contract: ContractType;
  tenure: number;
  monthly_charges: number;
  internet_service: InternetService;
  tech_support: boolean;
  online_security: boolean;
  payment_method: PaymentMethod;
  senior_citizen: boolean;
}

export interface PredictDriver { feature: string; label: string; contribution: number }

export interface PredictResponse {
  probability: number;
  risk: RiskLevel;
  model: string;
  model_label: string;
  roc_auc: number;
  drivers: PredictDriver[];
  action: string;
  similar_count: number;
}

// backend/app/main.py -> GET /api/intervention-plans
export type PlanRisk = "high_mid" | "high";

export interface PlanCustomer { customer_id: string; probability: number; risk: RiskLevel; contract: string | null; reason: string }

export interface InterventionPlan {
  action: string; reason_feature: string; reason: string;
  count: number; high: number; mid: number; share: number; avg_probability: number;
  probabilities: number[]; customers: PlanCustomer[];
}

export interface InterventionPlans {
  summary: { targeted: number; plans: number; avg_probability: number };
  plans: InterventionPlan[];
  insight: { top_action: string; top_share: number };
}
