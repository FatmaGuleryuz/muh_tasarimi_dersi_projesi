"""Telco senaryo tahmini: form alanlarindan model satirini kurar, SHAP katkilarini hesaplar."""
import importlib.util
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap

from .labels import label_for

ROOT = Path(__file__).resolve().parents[2]  # repo kökü

_spec = importlib.util.spec_from_file_location("train_model", ROOT / "src" / "train_model.py")
_train = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_train)
engineer_features = _train.engineer_features
REASON_SOLUTIONS = _train.REASON_SOLUTIONS
DEFAULT_SOLUTION = _train.DEFAULT_SOLUTION

NET_COLS = ["OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies"]
EXPLAIN_EXACT = {"tenure", "MonthlyCharges", "TotalCharges", "AvgMonthlySpend", "SeniorCitizen", "NumAdditionalServices"}
EXPLAIN_PREFIXES = ("Contract_", "InternetService_", "TechSupport_", "OnlineSecurity_", "PaymentMethod_", "tenure_group_")


@lru_cache
def load_model():
    return joblib.load(ROOT / "model.joblib")


@lru_cache
def _encoder() -> dict:
    return joblib.load(ROOT / "encoder.joblib")


@lru_cache
def _defaults() -> dict:
    """Ham Telco verisinden: sayısalda medyan, kategorikte mod."""
    raw = pd.read_csv(ROOT / "data" / "telco_churn_raw.csv").drop(columns=["customerID", "Churn"])
    raw["TotalCharges"] = pd.to_numeric(raw["TotalCharges"], errors="coerce")
    return {
        c: raw[c].median() if pd.api.types.is_numeric_dtype(raw[c]) else raw[c].mode().iloc[0]
        for c in raw.columns
    }


def _yes_no(flag: bool) -> str:
    return "Yes" if flag else "No"


def build_row(payload: dict) -> pd.DataFrame:
    """Form alanlarını Telco satırına çevirir; eğitimle aynı özellik sırasında tek satırlık float DataFrame döner."""
    row = dict(_defaults())
    tenure = payload["tenure"]
    monthly = payload["monthly_charges"]
    row.update({
        "Contract": payload["contract"],
        "tenure": tenure,
        "MonthlyCharges": monthly,
        # tenure 0: toplam ücret yok; eğitimdeki load_telco ile aynı kural (medyan) kullanılır
        "TotalCharges": monthly * tenure if tenure > 0 else _defaults()["TotalCharges"],
        "InternetService": payload["internet_service"],
        "TechSupport": _yes_no(payload["tech_support"]),
        "OnlineSecurity": _yes_no(payload["online_security"]),
        "PaymentMethod": payload["payment_method"],
        "SeniorCitizen": int(payload["senior_citizen"]),
    })
    if row["InternetService"] == "No":
        row.update({c: "No internet service" for c in NET_COLS})

    df = engineer_features(pd.DataFrame([row]))
    df = pd.get_dummies(df, columns=df.select_dtypes(exclude="number").columns.tolist())
    return df.reindex(columns=_encoder()["feature_names"], fill_value=0).astype(float)


@lru_cache
def _explainer():
    return shap.TreeExplainer(load_model())


ONE_HOT_GROUPS = [
    "Contract", "InternetService", "OnlineSecurity", "OnlineBackup", "DeviceProtection",
    "TechSupport", "StreamingTV", "StreamingMovies", "PaymentMethod", "PaperlessBilling",
    "Partner", "Dependents", "PhoneService", "MultipleLines", "gender", "tenure_group",
]


def _group_prefix(feature: str) -> str | None:
    """Özelliğin grup önekini ('OnlineSecurity_' gibi) bilinen grup adlarından bulur; en uzun eşleşme kazanır."""
    matches = [g + "_" for g in ONE_HOT_GROUPS if feature.startswith(g + "_")]
    return max(matches, key=len) if matches else None


def _driver_label(row: pd.DataFrame, feature: str) -> str:
    """Sayısal özellik: düz etiket.
    One-hot özellik, değer 1 ise: düz etiket.
    One-hot özellik, değer 0 ise:
      - '_No' ile bitiyorsa ve aynı gruptaki değeri 1 olan kardeş varsa: kardeşin etiketi
        (ör. 'OnlineSecurity_No' -> 'OnlineSecurity_No internet service' etiketi);
      - diğer durumlarda: düz etiket + ' değil'."""
    base = label_for(feature)
    if feature in EXPLAIN_EXACT:
        return base
    values = row.iloc[0]
    if values[feature] != 0:
        return base
    if feature.endswith("_No"):
        prefix = _group_prefix(feature)
        if prefix is not None:
            for other in row.columns:
                if other != feature and other.startswith(prefix) and values[other] == 1:
                    return label_for(other)
    return f"{base} değil"


def explain(row: pd.DataFrame) -> list[dict]:
    """Yalnızca formdan türeyen özelliklerin SHAP katkıları; mutlak değere göre ilk 5."""
    raw = _explainer().shap_values(row)
    values = np.asarray(raw[1] if isinstance(raw, list) else raw)
    if values.ndim == 3:  # (n, özellik, sınıf) -> pozitif sınıf
        values = values[:, :, 1]
    contrib = [(f, float(v)) for f, v in zip(row.columns, values[0])]
    form = [(f, v) for f, v in contrib if f in EXPLAIN_EXACT or f.startswith(EXPLAIN_PREFIXES)]
    form.sort(key=lambda t: abs(t[1]), reverse=True)
    return [
        {"feature": f, "label": _driver_label(row, f), "contribution": round(v, 4)}
        for f, v in form[:5]
    ]
