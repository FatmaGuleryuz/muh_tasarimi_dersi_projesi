"""Yetkin360 API — mevcut model çıktılarını (CSV/JSON) arayüze sunar.

Çalıştırma (repo kökünden):
    pip install -r backend/requirements.txt
    uvicorn backend.app.main:app --reload --port 8000
"""
import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt

from .labels import CONTRACTS, label_for
from .scenario import DEFAULT_SOLUTION, REASON_SOLUTIONS, build_row, explain, load_model

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]  # repo kökü
HIGH_THRESHOLD = 0.70  # >= yüksek risk
MID_THRESHOLD = 0.40   # >= orta risk
MODEL_LABELS = {
    "logistic_regression": "Lojistik Regresyon",
    "random_forest": "Random Forest",
    "xgboost": "XGBoost",
}

# dir None: proje koku (cagri aninda cozulur). raw None: sozlesme/sure/ucret verisi yok.
DATASETS = {
    "telco": {"dir": None, "name": "IBM Telco Customer Churn", "raw": "data/telco_churn_raw.csv"},
    "openml_churn": {"dir": ROOT / "outputs" / "openml_churn", "name": "OpenML Churn", "raw": None},
}

def resolve_active(value):
    if value is None:
        return DATASETS["telco"]
    if value in DATASETS:
        return DATASETS[value]
    raise ValueError(f"Bilinmeyen DATASET: {value}. Geçerli: {', '.join(DATASETS)}")


ACTIVE = resolve_active(os.environ.get("DATASET"))


def _data_dir() -> Path:
    return ROOT if ACTIVE["dir"] is None else ACTIVE["dir"]


def _contract(value):
    """Sözleşme etiketi; veri yoksa (NaN/None) None."""
    if pd.isna(value):
        return None
    return CONTRACTS.get(value, value)


def _opt(value, conv):
    """Değer NaN/None ise None, değilse conv(value)."""
    return None if pd.isna(value) else conv(value)


app = FastAPI(title="Yetkin360 API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])


def risk_level(p: float) -> str:
    return "high" if p >= HIGH_THRESHOLD else "mid" if p >= MID_THRESHOLD else "low"


@lru_cache
def load_json(name: str) -> dict:
    with open(_data_dir() / name, encoding="utf-8") as f:
        return json.load(f)


@lru_cache
def load_customers() -> pd.DataFrame:
    """test_customers.csv + (varsa) ham veriden sözleşme / süre / aylık ücret."""
    df = pd.read_csv(_data_dir() / "test_customers.csv")
    if ACTIVE["raw"] is None:
        df["Contract"] = None
        for col in ("tenure", "MonthlyCharges", "TotalCharges"):
            df[col] = float("nan")
    else:
        raw = pd.read_csv(_data_dir() / ACTIVE["raw"])[
            ["customerID", "Contract", "tenure", "MonthlyCharges", "TotalCharges"]
        ]
        df = df.merge(raw, on="customerID", how="left")
    df["risk"] = df["churn_probability"].map(risk_level)
    df["reason_label"] = df["top_reason"].map(label_for)
    return df


def _model_rows(metrics: dict) -> list[dict]:
    return [
        {"key": k, "label": MODEL_LABELS.get(k, k), **{m: round(v[m], 6) for m in ("roc_auc", "precision", "recall", "f1")}}
        for k, v in metrics["models"].items()
    ]


@app.get("/api/summary")
def summary():
    df = _load(load_customers)
    metrics = _load(load_json, "metrics.json")
    shap = _load(load_json, "shap_scores.json")
    total = len(df)
    high = df[df["risk"] == "high"]

    best = metrics["best_model"]
    models = _model_rows(metrics)

    risk_distribution = []
    for level, label in (("high", "Yüksek risk"), ("mid", "Orta risk"), ("low", "Düşük risk")):
        n = int((df["risk"] == level).sum())
        risk_distribution.append({"level": level, "label": label, "count": n, "share": n / total})

    by_contract = []
    for contract, label in CONTRACTS.items():
        sub = df[df["Contract"] == contract]
        if len(sub):
            by_contract.append({
                "contract": contract, "label": label, "count": len(sub),
                "avg_probability": float(sub["churn_probability"].mean()),
                "actual_rate": float(sub["actual_churn"].mean()),
            })

    top_drivers = [
        {"feature": k, "label": label_for(k), "score": round(v, 4)}
        for k, v in list(shap.items())[:8]
    ]

    top = df.sort_values("churn_probability", ascending=False).head(5)
    top_customers = [
        {
            "customer_id": r.customerID,
            "probability": float(r.churn_probability),
            "risk": r.risk,
            "contract": _contract(r.Contract),
            "reason": r.reason_label,
            "action": r.suggested_action,
        }
        for r in top.itertuples()
    ]

    return {
        "dataset": {"name": ACTIVE["name"], "test_customers": total, "total_rows": metrics["dataset"]["rows"]},
        "thresholds": {"high": HIGH_THRESHOLD, "mid": MID_THRESHOLD},
        "model": {
            "best": best, "best_label": MODEL_LABELS.get(best, best),
            "roc_auc": round(metrics["models"][best]["roc_auc"], 6),
            "target": metrics["target_roc_auc"], "target_met": metrics["target_met"],
            "models": models,
        },
        "kpis": {
            "total": total,
            "high_risk_count": len(high),
            "high_risk_share": len(high) / total,
            "avg_probability": float(df["churn_probability"].mean()),
            "high_risk_actual_rate": float(high["actual_churn"].mean()) if len(high) else 0.0,
            "overall_actual_rate": float(df["actual_churn"].mean()),
        },
        "risk_distribution": risk_distribution,
        "by_contract": by_contract,
        "top_drivers": top_drivers,
        "top_customers": top_customers,
    }


@app.get("/api/model-report")
def model_report():
    try:
        metrics = load_json("metrics.json")
        shap = load_json("shap_scores.json")
    except (FileNotFoundError, json.JSONDecodeError):
        raise HTTPException(status_code=503, detail="Model çıktıları bulunamadı; train_model.py çalıştırın")

    best = metrics["best_model"]
    drivers = [
        {"feature": k, "label": label_for(k), "score": round(v, 4)}
        for k, v in sorted(shap.items(), key=lambda kv: kv[1], reverse=True)
    ]
    return {
        "models": _model_rows(metrics),
        "best": best,
        "best_label": MODEL_LABELS.get(best, best),
        "target": metrics["target_roc_auc"],
        "target_met": metrics["target_met"],
        "dataset": {
            "name": ACTIVE["name"],
            "rows": metrics["dataset"]["rows"],
            "churn_rate": metrics["dataset"]["churn_rate"],
        },
        "drivers": drivers,
    }


def _customer_row(r) -> dict:
    return {
        "customer_id": r.customerID,
        "probability": float(r.churn_probability),
        "risk": r.risk,
        "contract": _contract(r.Contract),
        "reason": r.reason_label,
        "action": r.suggested_action,
    }


@app.get("/api/customers")
def list_customers(risk: Optional[str] = None, q: Optional[str] = None, limit: int = 200):
    """Test setindeki müşteriler — risk seviyesine ve/veya müşteri ID'sine göre filtrelenebilir."""
    df = _load(load_customers)
    if risk is not None:
        if risk not in ("high", "mid", "low"):
            raise HTTPException(status_code=400, detail="risk 'high', 'mid' veya 'low' olmalı")
        df = df[df["risk"] == risk]
    if q:
        df = df[df["customerID"].str.contains(q, case=False, na=False)]
    df = df.sort_values("churn_probability", ascending=False).head(max(1, min(limit, 1000)))
    return {"total": len(df), "customers": [_customer_row(r) for r in df.itertuples()]}


@app.get("/api/customers/{customer_id}")
def get_customer(customer_id: str):
    """Tek bir müşterinin kayıp olasılığı, sözleşme/kullanım bilgileri ve önerilen aksiyonu.

    Not: SHAP katkı dökümü şu an sadece agregat (tüm test seti) düzeyinde
    hesaplanıyor (shap_scores.json) — müşteri bazlı tam SHAP vektörü
    saklanmıyor, bu yüzden burada uydurma bir kırılım döndürülmüyor;
    `top_reason` (modelin bu müşteri için bulduğu gerçek en yüksek katkılı
    değişken) ve genel neden sıralaması birlikte sunuluyor.
    """
    df = _load(load_customers)
    match = df[df["customerID"] == customer_id]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Müşteri bulunamadı: {customer_id}")
    r = match.iloc[0]
    shap = _load(load_json, "shap_scores.json")
    return {
        "customer_id": r.customerID,
        "probability": float(r.churn_probability),
        "actual_churn": bool(r.actual_churn),
        "risk": r.risk,
        "contract": _contract(r.Contract),
        "tenure_months": _opt(r.tenure, int),
        "monthly_charges": _opt(r.MonthlyCharges, float),
        "total_charges": _opt(r.TotalCharges, float),
        "reason": r.reason_label,
        "reason_feature": r.top_reason,
        "action": r.suggested_action,
        "overall_top_drivers": [
            {"feature": k, "label": label_for(k), "score": round(v, 4)}
            for k, v in list(shap.items())[:8]
        ],
    }


OUTCOME_BY_RISK = {"high": "caught", "mid": "partial", "low": "missed"}


def _load(loader, *args):
    """Veri yükleme çağrısını sarar; her istisnada loglayıp 503 döner (HTTPException yutulmaz)."""
    try:
        return loader(*args)
    except Exception:
        logger.exception("Veri kaynağı okunamadı: %s", getattr(loader, "__name__", loader))
        raise HTTPException(status_code=503, detail="Veri kaynağı okunamadı")


@app.get("/api/postmortem")
def postmortem_list(outcome: Optional[Literal["caught", "partial", "missed"]] = None,
                    limit: int = Query(1000, ge=1, le=1000)):
    """Kaybedilmiş müşteriler (actual_churn==1): modelin önceden yakaladığı, kısmen yakaladığı ya da kaçırdığı."""
    df = _load(load_customers)
    lost = df[df["actual_churn"] == 1]
    lost_total = len(lost)
    caught = int((lost["risk"] == "high").sum())
    partial = int((lost["risk"] == "mid").sum())
    missed = int((lost["risk"] == "low").sum())
    high = df[df["risk"] == "high"]

    items = lost if outcome is None else lost[lost["risk"].map(OUTCOME_BY_RISK) == outcome]
    rows = [
        {**_customer_row(r), "outcome": OUTCOME_BY_RISK[r.risk], "reason_feature": r.top_reason}
        for r in items.sort_values("churn_probability").head(limit).itertuples()
    ]
    return {
        "summary": {
            "lost_total": lost_total,
            "caught": caught,
            "partial": partial,
            "missed": missed,
            "catch_rate": (caught + partial) / lost_total if lost_total else 0.0,
            "strict_catch_rate": caught / lost_total if lost_total else 0.0,
            "false_alarm_count": int((high["actual_churn"] == 0).sum()),
            "precision_high": float((high["actual_churn"] == 1).mean()) if len(high) else 0.0,
        },
        "total": len(rows),
        "items": rows,
    }


@app.get("/api/postmortem/{customer_id}")
def postmortem_detail(customer_id: str):
    """Kaybedilmiş tek müşterinin geriye dönük model değerlendirmesi."""
    df = _load(load_customers)
    match = df[df["customerID"] == customer_id]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Müşteri bulunamadı: {customer_id}")
    r = match.iloc[0]
    if not r.actual_churn:
        raise HTTPException(status_code=409, detail=f"Müşteri kaybedilmemiş: {customer_id}")

    keys = list(_load(load_json, "shap_scores.json").keys())
    return {
        "customer_id": r.customerID,
        "actual_churn": True,
        "probability": float(r.churn_probability),
        "risk": r.risk,
        "outcome": OUTCOME_BY_RISK[r.risk],
        "contract": _contract(r.Contract),
        "tenure_months": _opt(r.tenure, int),
        "monthly_charges": _opt(r.MonthlyCharges, float),
        "total_charges": _opt(r.TotalCharges, float),
        "reason": r.reason_label,
        "reason_feature": r.top_reason,
        "top_reason_global_rank": keys.index(r.top_reason) + 1 if r.top_reason in keys else None,
        "action": r.suggested_action,
        "action_applied": None,
        "action_applied_note": "Veri yok",
    }


@app.get("/api/export/high-risk.csv")
def export_high_risk():
    df = load_customers()
    out = df[df["risk"] == "high"].sort_values("churn_probability", ascending=False)
    out = pd.DataFrame({
        "Müşteri ID": out["customerID"],
        "Sözleşme": out["Contract"].map(CONTRACTS),
        "Kayıp Olasılığı (%)": (out["churn_probability"] * 100).round(1),
        "Ana Neden": out["reason_label"],
        "Önerilen Aksiyon": out["suggested_action"],
    })
    body = out.to_csv(index=False, encoding="utf-8-sig")
    return Response(
        body.encode("utf-8-sig"), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="yuksek_riskli_musteriler.csv"'},
    )


NO_ACTION = "Şimdilik müdahale gerekmiyor; izlemeye devam edin."
PLAN_RISKS = Literal["high_mid", "high"]


class ScenarioIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract: Literal["Month-to-month", "One year", "Two year"]
    tenure: StrictInt = Field(ge=0, le=72)
    monthly_charges: float = Field(ge=18, le=120, allow_inf_nan=False)
    internet_service: Literal["DSL", "Fiber optic", "No"]
    tech_support: StrictBool
    online_security: StrictBool
    payment_method: Literal["Electronic check", "Mailed check", "Bank transfer (automatic)", "Credit card (automatic)"]
    senior_citizen: StrictBool


def _predict(body: ScenarioIn) -> dict:
    metrics = load_json("metrics.json")
    row = build_row(body.model_dump())
    prob = float(load_model().predict_proba(row)[0, 1])
    drivers = explain(row)
    risk = risk_level(prob)

    top_pos = next((d for d in drivers if d["contribution"] > 0), None)
    if risk == "low" or top_pos is None:
        action = NO_ACTION
    else:
        action = REASON_SOLUTIONS.get(top_pos["feature"], DEFAULT_SOLUTION)

    df = load_customers()
    similar = int(((df["Contract"] == body.contract) & (df["risk"] == risk)).sum())
    best = metrics["best_model"]
    return {
        "probability": round(prob, 6),
        "risk": risk,
        "model": best,
        "model_label": MODEL_LABELS.get(best, best),
        "roc_auc": round(metrics["models"][best]["roc_auc"], 3),
        "drivers": drivers,
        "action": action,
        "similar_count": similar,
    }


@app.post("/api/predict")
def predict(body: ScenarioIn):
    if ACTIVE is not DATASETS["telco"]:
        raise HTTPException(status_code=409, detail="Senaryo tahmini yalnızca Telco veri setinde destekleniyor")
    return _load(_predict, body)


def _threshold(risk: str) -> float:
    return MID_THRESHOLD if risk == "high_mid" else HIGH_THRESHOLD


def _plan_groups(df: pd.DataFrame, risk: str) -> list[tuple[str, pd.DataFrame]]:
    """Hedeflenen müşterileri önerilen aksiyona göre gruplar; en kalabalık plan önce."""
    t = df[df["churn_probability"] >= _threshold(risk)]
    groups = [(action, g.sort_values("churn_probability", ascending=False)) for action, g in t.groupby("suggested_action")]
    return sorted(groups, key=lambda ag: len(ag[1]), reverse=True)


def _plan_row(action: str, g: pd.DataFrame, targeted: int) -> dict:
    count = len(g)
    reason_feature = g["top_reason"].mode().iloc[0]
    return {
        "action": action,
        "reason_feature": reason_feature,
        "reason": label_for(reason_feature),
        "count": count,
        "high": int((g["risk"] == "high").sum()),
        "mid": int((g["risk"] == "mid").sum()),
        "share": round(count / targeted, 3),
        "avg_probability": round(float(g["churn_probability"].mean()), 3),
        "probabilities": [round(float(p), 3) for p in g["churn_probability"]],
        "customers": [
            {
                "customer_id": r.customerID,
                "probability": float(r.churn_probability),
                "risk": r.risk,
                "contract": _contract(r.Contract),
                "reason": r.reason_label,
            }
            for r in g.head(5).itertuples()
        ],
    }


def _plans_payload(risk: str) -> dict:
    df = load_customers()
    targeted_df = df[df["churn_probability"] >= _threshold(risk)]
    targeted = len(targeted_df)
    plans = [_plan_row(a, g, targeted) for a, g in _plan_groups(df, risk)]
    return {
        "summary": {
            "targeted": targeted,
            "plans": len(plans),
            "avg_probability": round(float(targeted_df["churn_probability"].mean()), 3) if targeted else 0.0,
        },
        "plans": plans,
        "insight": {
            "top_action": plans[0]["action"] if plans else "",
            "top_share": plans[0]["share"] if plans else 0.0,
        },
    }


@app.get("/api/intervention-plans")
def intervention_plans(risk: PLAN_RISKS = "high_mid"):
    return _load(_plans_payload, risk)


def _csv_safe(value):
    """CSV injection: formül başlatan karakterleri metin olarak işaretler."""
    return "'" + value if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r") else value


def _export_group(action: str, risk: str) -> pd.DataFrame | None:
    for a, g in _plan_groups(load_customers(), risk):
        if a == action:  # tam eşleşme; dosya yolu ya da regex olarak kullanılmaz
            return g
    return None


@app.get("/api/intervention-plans/export.csv")
def export_intervention_plan(action: str, risk: PLAN_RISKS = "high_mid"):
    g = _load(_export_group, action, risk)
    if g is None:
        raise HTTPException(status_code=404, detail="Plan bulunamadı")
    out = pd.DataFrame({
        "Müşteri ID": g["customerID"],
        "Kayıp Olasılığı (%)": (g["churn_probability"] * 100).round(1),
        "Risk": g["risk"].map({"high": "Yüksek", "mid": "Orta"}),
        "Sözleşme": g["Contract"].map(CONTRACTS),
        "Ana Neden": g["reason_label"],
    })
    for col in ("Müşteri ID", "Risk", "Sözleşme", "Ana Neden"):
        out[col] = out[col].map(_csv_safe)
    return Response(
        out.to_csv(index=False).encode("utf-8-sig"), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="mudahale_plani.csv"'},
    )
