"""Telco Customer Churn: veri temizleme + feature engineering + hiperparametre
aramasi + model egitimi + SHAP neden skorlama.
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
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")

RAW_PATH = "data/telco_churn_raw.csv"
TARGET_ROC_AUC = 0.84
RANDOM_STATE = 42

REASON_SOLUTIONS = {
    "tenure": "Ilk aylara ozel karşilama / bağlilik programi",
    "MonthlyCharges": "Kullanima uygun daha duşuk paket onerisi",
    "TotalCharges": "Kullanima uygun daha duşuk paket onerisi",
    "AvgMonthlySpend": "Kullanima uygun daha duşuk paket onerisi",
    "NumAdditionalServices": "Belirli sure ucretsiz ek hizmet tanimlanmasi",
    "Contract_Month-to-month": "Uzun donem sozlesmeye gecişte indirim",
    "Contract_One year": "Iki yillik sozlesmeye gecişte ek indirim",
    "TechSupport_No": "Belirli sure ucretsiz teknik destek tanimlanmasi",
    "OnlineSecurity_No": "Belirli sure ucretsiz cevrim ici guvenlik hizmeti",
    "PaymentMethod_Electronic check": "Otomatik odemeye geçişte avantaj",
    "InternetService_Fiber optic": "Fiber hizmet kalitesi/fiyat gozden geçirme kampanyasi",
    "SeniorCitizen": "Yaşli musterilere ozel destek hatti/paket",
}
DEFAULT_SOLUTION = "Musteri temsilcisi tarafindan ozel teklif degerlendirilsin"


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df["AvgMonthlySpend"] = df["TotalCharges"] / (df["tenure"] + 1)

    service_cols = [
        "PhoneService", "MultipleLines", "OnlineSecurity", "OnlineBackup",
        "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies",
    ]
    df["NumAdditionalServices"] = (df[service_cols] == "Yes").sum(axis=1)

    df["tenure_group"] = pd.cut(
        df["tenure"], bins=[-1, 12, 24, 48, 72], labels=["0-12", "13-24", "25-48", "49-72"]
    ).astype(str)

    return df


def load_and_clean():
    df = pd.read_csv(RAW_PATH)
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
    n_missing = int(df["TotalCharges"].isna().sum())
    if n_missing:
        median_val = df["TotalCharges"].median()
        df["TotalCharges"] = df["TotalCharges"].fillna(median_val)
        print(f"[data_prep] TotalCharges: {n_missing} eksik deger median ({median_val:.2f}) ile dolduruldu.")

    customer_ids = df["customerID"]
    df = df.drop(columns=["customerID"])
    df["Churn"] = (df["Churn"] == "Yes").astype(int)

    df = engineer_features(df)

    cat_cols = df.select_dtypes(include="object").columns.tolist()
    df_encoded = pd.get_dummies(df, columns=cat_cols, drop_first=False)

    return df_encoded, customer_ids, n_missing


def build_param_search(estimator, param_distributions, X, y, n_iter=20):
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    search = RandomizedSearchCV(
        estimator,
        param_distributions=param_distributions,
        n_iter=n_iter,
        scoring="roc_auc",
        cv=cv,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    search.fit(X, y)
    return search.best_estimator_, search.best_score_


def main():
    df, customer_ids, n_missing_filled = load_and_clean()
    X = df.drop(columns=["Churn"])
    y = df["Churn"]

    X_train, X_test, y_train, y_test, id_train, id_test = train_test_split(
        X, y, customer_ids, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )

    scaler = StandardScaler()
    X_train_scaled = pd.DataFrame(scaler.fit_transform(X_train), columns=X_train.columns, index=X_train.index)
    X_test_scaled = pd.DataFrame(scaler.transform(X_test), columns=X_test.columns, index=X_test.index)

    class_weight_ratio = (y_train == 0).sum() / (y_train == 1).sum()

    print("[train] Hiperparametre aramasi basladi (5-fold CV, ROC-AUC)...")

    lr_best, lr_cv_auc = build_param_search(
        LogisticRegression(max_iter=2000, class_weight="balanced"),
        {"C": [0.01, 0.03, 0.1, 0.3, 1, 3, 10], "penalty": ["l2"], "solver": ["lbfgs"]},
        X_train_scaled, y_train,
    )
    print(f"[train] logistic_regression CV best ROC-AUC={lr_cv_auc:.4f} params={lr_best.get_params()['C']}")

    rf_best, rf_cv_auc = build_param_search(
        RandomForestClassifier(class_weight="balanced", random_state=RANDOM_STATE),
        {
            "n_estimators": [200, 300, 400, 500],
            "max_depth": [4, 6, 8, 10, None],
            "min_samples_leaf": [1, 2, 4, 8],
            "max_features": ["sqrt", "log2"],
        },
        X_train, y_train,
    )
    print(f"[train] random_forest CV best ROC-AUC={rf_cv_auc:.4f}")

    xgb_best, xgb_cv_auc = build_param_search(
        XGBClassifier(
            scale_pos_weight=class_weight_ratio, random_state=RANDOM_STATE, eval_metric="logloss"
        ),
        {
            "n_estimators": [150, 250, 350],
            "max_depth": [3, 4, 5, 6],
            "learning_rate": [0.01, 0.03, 0.05, 0.1],
            "subsample": [0.7, 0.85, 1.0],
            "colsample_bytree": [0.7, 0.85, 1.0],
            "reg_lambda": [1, 2, 5],
        },
        X_train, y_train,
    )
    print(f"[train] xgboost CV best ROC-AUC={xgb_cv_auc:.4f}")

    models = {
        "logistic_regression": lr_best,
        "random_forest": rf_best,
        "xgboost": xgb_best,
    }

    results = {}
    for name, model in models.items():
        if name == "logistic_regression":
            y_proba = model.predict_proba(X_test_scaled)[:, 1]
        else:
            y_proba = model.predict_proba(X_test)[:, 1]
        y_pred = (y_proba >= 0.5).astype(int)
        results[name] = {
            "roc_auc": float(roc_auc_score(y_test, y_proba)),
            "precision": float(precision_score(y_test, y_pred)),
            "recall": float(recall_score(y_test, y_pred)),
            "f1": float(f1_score(y_test, y_pred)),
        }
        print(f"[train] {name} test ROC-AUC={results[name]['roc_auc']:.4f}")

    best_name = max(results, key=lambda k: results[k]["roc_auc"])
    best_model = models[best_name]
    best_auc = results[best_name]["roc_auc"]
    target_met = best_auc >= TARGET_ROC_AUC

    print(f"[train] En iyi model: {best_name} (ROC-AUC={best_auc:.4f}, hedef={TARGET_ROC_AUC}, karsilandi={target_met})")

    # --- SHAP neden skorlama (en iyi modelle) ---
    if best_name == "logistic_regression":
        explainer = shap.LinearExplainer(best_model, X_train_scaled)
        shap_values = explainer.shap_values(X_test_scaled)
    elif best_name == "random_forest":
        explainer = shap.TreeExplainer(best_model)
        raw = explainer.shap_values(X_test)
        shap_values = raw[1] if isinstance(raw, list) else raw
    else:
        explainer = shap.TreeExplainer(best_model)
        shap_values = explainer.shap_values(X_test)

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
    plt.barh(names, vals, color="#1E3A28")
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
        "cv_roc_auc": {
            "logistic_regression": float(lr_cv_auc),
            "random_forest": float(rf_cv_auc),
            "xgboost": float(xgb_cv_auc),
        },
        "best_model": best_name,
        "target_roc_auc": TARGET_ROC_AUC,
        "target_met": target_met,
        "dataset": {
            "rows": int(len(df)),
            "churn_rate": float(y.mean()),
            "missing_total_charges_filled": int(n_missing_filled),
            "feature_count": int(X.shape[1]),
        },
    }
    with open("metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    joblib.dump(best_model, "model.joblib")
    joblib.dump(
        {"scaler": scaler, "best_name": best_name, "feature_names": feature_names},
        "encoder.joblib",
    )

    print("[train] Tamamlandi: model.joblib, metrics.json, shap_scores.json, shap_summary.png, test_customers.csv yazildi.")


if __name__ == "__main__":
    main()
