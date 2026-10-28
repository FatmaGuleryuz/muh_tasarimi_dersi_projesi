"""Yetkin360 API — mevcut model çıktılarını (CSV/JSON) arayüze sunar.

Çalıştırma (repo kökünden):
    pip install -r backend/requirements.txt
    uvicorn backend.app.main:app --reload --port 8000
"""
import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .labels import CONTRACTS, label_for

ROOT = Path(__file__).resolve().parents[2]  # repo kökü
HIGH_THRESHOLD = 0.70  # >= yüksek risk
MID_THRESHOLD = 0.40   # >= orta risk
MODEL_LABELS = {
    "logistic_regression": "Lojistik Regresyon",
    "random_forest": "Random Forest",
    "xgboost": "XGBoost",
}

app = FastAPI(title="Yetkin360 API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])


def risk_level(p: float) -> str:
    return "high" if p >= HIGH_THRESHOLD else "mid" if p >= MID_THRESHOLD else "low"


@lru_cache
def load_json(name: str) -> dict:
    with open(ROOT / name, encoding="utf-8") as f:
        return json.load(f)


@lru_cache
def load_customers() -> pd.DataFrame:
    """test_customers.csv + ham veriden sözleşme / süre / aylık ücret."""
    df = pd.read_csv(ROOT / "test_customers.csv")
    raw = pd.read_csv(ROOT / "data" / "telco_churn_raw.csv")[
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
    df = load_customers()
    metrics = load_json("metrics.json")
    shap = load_json("shap_scores.json")
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
            "contract": CONTRACTS.get(r.Contract, r.Contract),
            "reason": r.reason_label,
            "action": r.suggested_action,
        }
        for r in top.itertuples()
    ]

    return {
        "dataset": {"name": "IBM Telco Customer Churn", "test_customers": total, "total_rows": metrics["dataset"]["rows"]},
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
            "name": "IBM Telco Customer Churn",
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
        "contract": CONTRACTS.get(r.Contract, r.Contract),
        "reason": r.reason_label,
        "action": r.suggested_action,
    }


@app.get("/api/customers")
def list_customers(risk: Optional[str] = None, q: Optional[str] = None, limit: int = 200):
    """Test setindeki müşteriler — risk seviyesine ve/veya müşteri ID'sine göre filtrelenebilir."""
    df = load_customers()
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
    df = load_customers()
    match = df[df["customerID"] == customer_id]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Müşteri bulunamadı: {customer_id}")
    r = match.iloc[0]
    shap = load_json("shap_scores.json")
    return {
        "customer_id": r.customerID,
        "probability": float(r.churn_probability),
        "actual_churn": bool(r.actual_churn),
        "risk": r.risk,
        "contract": CONTRACTS.get(r.Contract, r.Contract),
        "tenure_months": int(r.tenure),
        "monthly_charges": float(r.MonthlyCharges),
        "total_charges": float(r.TotalCharges) if pd.notna(r.TotalCharges) else None,
        "reason": r.reason_label,
        "reason_feature": r.top_reason,
        "action": r.suggested_action,
        "overall_top_drivers": [
            {"feature": k, "label": label_for(k), "score": round(v, 4)}
            for k, v in list(shap.items())[:8]
        ],
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
