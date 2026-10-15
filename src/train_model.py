"""Telco Customer Churn: veri temizleme + model egitimi + SHAP neden skorlama.
Cikti: ../model.joblib, ../metrics.json, ../shap_scores.json, ../shap_summary.png,
       ../encoder.joblib, ../test_customers.csv (arayuzun secebilecegi test seti)
"""
import json
import warnings

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")

RAW_PATH = "data/telco_churn_raw.csv"
TARGET_ROC_AUC = 0.84

REASON_SOLUTIONS = {
    "Contract_Month-to-month": "Uzun donem sozlesmeye gecişte indirim",
    "Contract": "Uzun donem sozlesmeye gecişte indirim",
    "tenure": "Ilk aylara ozel karşilama / bağlilik programi",
    "MonthlyCharges": "Kullanima uygun daha duşuk paket onerisi",
    "TechSupport_No": "Belirli sure ucretsiz teknik destek tanimlanmasi",
    "TechSupport": "Belirli sure ucretsiz teknik destek tanimlanmasi",
    "OnlineSecurity_No": "Belirli sure ucretsiz cevrim ici guvenlik hizmeti",
    "OnlineSecurity": "Belirli sure ucretsiz cevrim ici guvenlik hizmeti",
    "PaymentMethod_Electronic check": "Otomatik odemeye geçişte avantaj",
    "PaymentMethod": "Otomatik odemeye geçişte avantaj",
    "TotalCharges": "Kullanima uygun daha duşuk paket onerisi",
    "InternetService_Fiber optic": "Fiber hizmet kalitesi/fiyat gozden geçirme kampanyasi",
    "InternetService": "Fiber hizmet kalitesi/fiyat gozden geçirme kampanyasi",
}
DEFAULT_SOLUTION = "Musteri temsilcisi tarafindan ozel teklif degerlendirilsin"


def load_and_clean():
    df = pd.read_csv(RAW_PATH)
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
    n_missing = df["TotalCharges"].isna().sum()
    if n_missing:
        median_val = df["TotalCharges"].median()
        df["TotalCharges"] = df["TotalCharges"].fillna(median_val)
        print(f"[data_prep] TotalCharges: {n_missing} eksik deger median ({median_val:.2f}) ile dolduruldu.")

    customer_ids = df["customerID"]
    df = df.drop(columns=["customerID"])

    df["Churn"] = (df["Churn"] == "Yes").astype(int)

    cat_cols = df.select_dtypes(include="object").columns.tolist()
    encoders = {}
    for col in cat_cols:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col])
        encoders[col] = le

    return df, customer_ids, encoders, n_missing


def main():
    df, customer_ids, encoders, n_missing_filled = load_and_clean()
    X = df.drop(columns=["Churn"])
    y = df["Churn"]

    X_train, X_test, y_train, y_test, id_train, id_test = train_test_split(
        X, y, customer_ids, test_size=0.2, random_state=42, stratify=y
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    class_weight_ratio = (y_train == 0).sum() / (y_train == 1).sum()

    models = {
        "logistic_regression": LogisticRegression(max_iter=1000, class_weight="balanced"),
        "random_forest": RandomForestClassifier(
            n_estimators=200, class_weight="balanced", random_state=42
        ),
        "xgboost": XGBClassifier(
            n_estimators=200,
            scale_pos_weight=class_weight_ratio,
            random_state=42,
            eval_metric="logloss",
        ),
    }

    results = {}
    fitted = {}
    for name, model in models.items():
        if name == "logistic_regression":
            model.fit(X_train_scaled, y_train)
            y_proba = model.predict_proba(X_test_scaled)[:, 1]
        else:
            model.fit(X_train, y_train)
            y_proba = model.predict_proba(X_test)[:, 1]
        y_pred = (y_proba >= 0.5).astype(int)
        results[name] = {
            "roc_auc": float(roc_auc_score(y_test, y_proba)),
            "precision": float(precision_score(y_test, y_pred)),
            "recall": float(recall_score(y_test, y_pred)),
            "f1": float(f1_score(y_test, y_pred)),
        }
        fitted[name] = model
        print(f"[train] {name}: ROC-AUC={results[name]['roc_auc']:.4f}")

    best_name = max(results, key=lambda k: results[k]["roc_auc"])
    best_model = fitted[best_name]
    best_auc = results[best_name]["roc_auc"]
    target_met = best_auc >= TARGET_ROC_AUC

    print(f"[train] En iyi model: {best_name} (ROC-AUC={best_auc:.4f}, hedef={TARGET_ROC_AUC}, karsilandi={target_met})")

    # --- SHAP neden skorlama (en iyi modelle) ---
    if best_name == "logistic_regression":
        explainer = shap.LinearExplainer(best_model, X_train_scaled)
        shap_values = explainer.shap_values(X_test_scaled)
        X_test_for_shap = X_test
    elif best_name == "random_forest":
        explainer = shap.TreeExplainer(best_model)
        raw = explainer.shap_values(X_test)
        shap_values = raw[1] if isinstance(raw, list) else raw
        X_test_for_shap = X_test
    else:
        explainer = shap.TreeExplainer(best_model)
        shap_values = explainer.shap_values(X_test)
        X_test_for_shap = X_test

    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    feature_names = X.columns.tolist()
    shap_ranking = sorted(
        zip(feature_names, mean_abs_shap.tolist()), key=lambda t: t[1], reverse=True
    )
    shap_scores = {name: float(score) for name, score in shap_ranking}

    with open("shap_scores.json", "w", encoding="utf-8") as f:
        json.dump(shap_scores, f, ensure_ascii=False, indent=2)

    plt.figure(figsize=(8, 6))
    top10 = shap_ranking[:10]
    names = [t[0] for t in top10][::-1]
    vals = [t[1] for t in top10][::-1]
    plt.barh(names, vals, color="#2E86AB")
    plt.xlabel("Ortalama |SHAP| katkisi")
    plt.title(f"Churn nedenleri (en iyi model: {best_name})")
    plt.tight_layout()
    plt.savefig("shap_summary.png", dpi=120)
    plt.close()

    # --- Her test musterisi icin ana neden + onerilen cozum ---
    per_customer_top_reason_idx = np.argmax(np.abs(shap_values), axis=1)
    per_customer_reason = [feature_names[i] for i in per_customer_top_reason_idx]
    if best_name == "logistic_regression":
        probs = best_model.predict_proba(X_test_scaled)[:, 1]
    else:
        probs = best_model.predict_proba(X_test)[:, 1]

    test_table = pd.DataFrame(
        {
            "customerID": id_test.values,
            "churn_probability": probs,
            "actual_churn": y_test.values,
            "top_reason": per_customer_reason,
        }
    )
    test_table["suggested_action"] = test_table["top_reason"].map(
        lambda r: REASON_SOLUTIONS.get(r, DEFAULT_SOLUTION)
    )
    test_table.to_csv("test_customers.csv", index=False)

    metrics = {
        "models": results,
        "best_model": best_name,
        "target_roc_auc": TARGET_ROC_AUC,
        "target_met": target_met,
        "dataset": {
            "rows": int(len(df)),
            "churn_rate": float(y.mean()),
            "missing_total_charges_filled": int(n_missing_filled),
        },
    }
    with open("metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    joblib.dump(best_model, "model.joblib")
    joblib.dump({"encoders": encoders, "scaler": scaler, "best_name": best_name, "feature_names": feature_names}, "encoder.joblib")

    print("[train] Tamamlandi: model.joblib, metrics.json, shap_scores.json, shap_summary.png, test_customers.csv yazildi.")


if __name__ == "__main__":
    main()
