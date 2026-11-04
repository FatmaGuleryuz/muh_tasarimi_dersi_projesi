"""Churn egitim pipeline'i: veri temizleme + feature engineering + hiperparametre
aramasi + model egitimi + SHAP neden skorlama.

Profiller (PROFILES) veri setine ozgu her seyi tutar:
  - telco        : IBM Telco Customer Churn, ciktilar proje kokune (mevcut davranis)
  - openml_churn : OpenML 40701 churn, ciktilar outputs/openml_churn/ altina (.tmp uzerinden atomik)

Kullanim (proje kokunden):
    python src/train_model.py --dataset openml_churn
"""
import argparse
import json
import os
import shutil
import sys
import warnings
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from scipy.io import arff
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]  # proje koku
TARGET_ROC_AUC = 0.84
RANDOM_STATE = 42

REASON_SOLUTIONS = {
    "tenure": "İlk aylara özel karşılama / bağlılık programı",
    "MonthlyCharges": "Kullanıma uygun daha düşük paket önerisi",
    "TotalCharges": "Kullanıma uygun daha düşük paket önerisi",
    "AvgMonthlySpend": "Kullanıma uygun daha düşük paket önerisi",
    "NumAdditionalServices": "Belirli süre ücretsiz ek hizmet tanımlanması",
    "Contract_Month-to-month": "Uzun dönem sözleşmeye geçişte indirim",
    "Contract_One year": "İki yıllık sözleşmeye geçişte ek indirim",
    "TechSupport_No": "Belirli süre ücretsiz teknik destek tanımlanması",
    "OnlineSecurity_No": "Belirli süre ücretsiz çevrimiçi güvenlik hizmeti",
    "PaymentMethod_Electronic check": "Otomatik ödemeye geçişte avantaj",
    "InternetService_Fiber optic": "Fiber hizmet kalitesi/fiyat gözden geçirme kampanyası",
    "SeniorCitizen": "Yaşlı müşterilere özel destek hattı/paket",
}
OPENML_REASON_SOLUTIONS = {
    "international_plan": "Uluslararası arama paketine özel indirim tanımlanması",
    "number_customer_service_calls": "Çok sık destek arayan müşteriye proaktif çözüm görüşmesi",
    "total_day_minutes": "Gündüz kullanımına uygun daha düşük paket önerisi",
    "total_day_charge": "Gündüz kullanımına uygun daha düşük paket önerisi",
    "total_charge": "Kullanıma uygun daha düşük paket önerisi",
    "voice_mail_plan": "Sesli mesaj paketinde ücretsiz deneme önerisi",
    "total_intl_calls": "Uluslararası arama kullanımına özel tarife önerisi",
}
DEFAULT_SOLUTION = "Müşteri temsilcisi tarafından özel teklif değerlendirilsin"

OPENML_MINUTES = ["total_day_minutes", "total_eve_minutes", "total_night_minutes", "total_intl_minutes"]
OPENML_CALLS = ["total_day_calls", "total_eve_calls", "total_night_calls", "total_intl_calls"]
OPENML_CHARGES = ["total_day_charge", "total_eve_charge", "total_night_charge", "total_intl_charge"]


def _err(msg):
    print(msg, file=sys.stderr)


def _decode(v):
    return v.decode("utf-8") if isinstance(v, bytes) else v


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


def engineer_openml(df: pd.DataFrame) -> pd.DataFrame:
    df["total_minutes"] = df[OPENML_MINUTES].sum(axis=1)
    df["total_calls"] = df[OPENML_CALLS].sum(axis=1)
    df["total_charge"] = df[OPENML_CHARGES].sum(axis=1)
    df["state"] = df["state"].astype(int)
    return pd.get_dummies(df, columns=["state", "area_code"], drop_first=False)


def load_telco(path):
    df = pd.read_csv(path)
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
    n_missing = int(df["TotalCharges"].isna().sum())
    if n_missing:
        median_val = df["TotalCharges"].median()
        df["TotalCharges"] = df["TotalCharges"].fillna(median_val)
        print(f"[data_prep] TotalCharges: {n_missing} eksik deger median ({median_val:.2f}) ile dolduruldu.")
    if "Churn" in df.columns:
        df["Churn"] = (df["Churn"] == "Yes").astype(int)
    return df, n_missing


def load_openml(path):
    data, meta = arff.loadarff(str(path))
    df = pd.DataFrame(data)
    for col in meta.names():
        if meta[col][0] == "nominal":
            df[col] = pd.to_numeric(df[col].map(_decode)).astype(int)
    return df, 0


def ids_telco(df):
    return df["customerID"]


def ids_openml(df):
    return pd.Series([f"OC-{i:05d}" for i in range(len(df))], index=df.index, name="customerID")


PROFILES = {
    "telco": {
        "raw_path": "data/telco_churn_raw.csv",
        "out_dir": ".",
        "target": "Churn",
        "load": load_telco,
        "make_ids": ids_telco,
        "drop": ["customerID"],
        "engineer": engineer_features,
        "reasons": REASON_SOLUTIONS,
        "name": "IBM Telco Customer Churn",
    },
    "openml_churn": {
        "raw_path": "data/openml_churn.arff",
        "out_dir": "outputs/openml_churn",
        "target": "class",
        "load": load_openml,
        "make_ids": ids_openml,
        "drop": ["phone_number"],
        "engineer": engineer_openml,
        "reasons": OPENML_REASON_SOLUTIONS,
        "name": "OpenML Churn",
    },
}


def _prepare(df, prof):
    """Id'leri satir sirasindan/ham kolondan alir, dusurur, feature engineering ve one-hot uygular."""
    ids = prof["make_ids"](df)
    df = df.drop(columns=prof["drop"])
    df = prof["engineer"](df)
    cat_cols = df.select_dtypes(include="object").columns.tolist()
    return pd.get_dummies(df, columns=cat_cols, drop_first=False), ids


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


def _train(raw_df, n_missing, prof, dst, sample, n_iter):
    """Egitir ve ciktilari dst klasorune yazar. En iyi test ROC-AUC'yi dondurur."""
    target = prof["target"]
    df, customer_ids = _prepare(raw_df, prof)
    if sample:
        keep, _ = train_test_split(df.index, train_size=sample, stratify=df[target], random_state=RANDOM_STATE)
        df = df.loc[keep]
        customer_ids = customer_ids.loc[keep]

    X = df.drop(columns=[target])
    y = df[target]

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
        X_train_scaled, y_train, n_iter=n_iter,
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
        X_train, y_train, n_iter=n_iter,
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
        X_train, y_train, n_iter=n_iter,
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
            "pr_auc": float(average_precision_score(y_test, y_proba)),
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
    if np.ndim(shap_values) == 3:  # yeni shap: (n, ozellik, sinif) -> pozitif sinif
        shap_values = shap_values[:, :, 1]

    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    feature_names = X.columns.tolist()
    shap_ranking = sorted(
        zip(feature_names, mean_abs_shap.tolist()), key=lambda t: t[1], reverse=True
    )
    shap_scores = {name: float(score) for name, score in shap_ranking}

    with open(dst / "shap_scores.json", "w", encoding="utf-8") as f:
        json.dump(shap_scores, f, ensure_ascii=False, indent=2)

    plt.figure(figsize=(8, 6))
    top10 = shap_ranking[:10]
    names = [t[0] for t in top10][::-1]
    vals = [t[1] for t in top10][::-1]
    plt.barh(names, vals, color="#1E3A28")
    plt.xlabel("Ortalama |SHAP| katkisi")
    plt.title(f"Churn nedenleri (en iyi model: {best_name})")
    plt.tight_layout()
    plt.savefig(dst / "shap_summary.png", dpi=120)
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
        lambda r: prof["reasons"].get(r, DEFAULT_SOLUTION)
    )
    test_table.to_csv(dst / "test_customers.csv", index=False)

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
            "name": prof["name"],
            "rows": int(len(df)),
            "churn_rate": float(y.mean()),
            "missing_total_charges_filled": int(n_missing),
            "feature_count": int(X.shape[1]),
        },
    }
    with open(dst / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    joblib.dump(best_model, dst / "model.joblib")
    joblib.dump(
        {"scaler": scaler, "best_name": best_name, "feature_names": feature_names},
        dst / "encoder.joblib",
    )

    print("[train] Tamamlandi: model.joblib, metrics.json, shap_scores.json, shap_summary.png, test_customers.csv yazildi.")
    return best_auc


def main(dataset="telco", root=None, sample=None, n_iter=20) -> int:
    """Secilen profili egitir. Basarida 0, girdi hatasinda 2, egitim hatasinda 1 doner."""
    if dataset not in PROFILES:
        _err(f"Bilinmeyen veri seti: {dataset}. Geçerli: {', '.join(PROFILES)}")
        return 2

    prof = PROFILES[dataset]
    root = ROOT if root is None else Path(root)
    raw = root / prof["raw_path"]
    if not raw.is_file():
        _err(f"Ham veri bulunamadı: {prof['raw_path']}")
        return 2

    df, n_missing = prof["load"](raw)
    if prof["target"] not in df.columns:
        _err(f"Hedef sütun bulunamadı: {prof['target']}")
        return 2
    if len(df) == 0:
        _err("Veri boş")
        return 2
    if df[prof["target"]].nunique() < 2:
        _err("Hedef tek sınıf içeriyor, eğitim yapılamaz")
        return 2

    out = root / prof["out_dir"]
    if prof["out_dir"] == ".":
        # telco: kok dizine dogrudan yazar (mevcut davranis, atomik degil)
        auc = _train(df, n_missing, prof, out, sample, n_iter)
    else:
        # outputs/ profilleri: once .tmp'ye yaz, hepsi basarili olunca hedefe tasi
        out.mkdir(parents=True, exist_ok=True)
        tmp = out / ".tmp"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir()
        try:
            auc = _train(df, n_missing, prof, tmp, sample, n_iter)
        except Exception:
            shutil.rmtree(tmp, ignore_errors=True)
            _err("Eğitim yarıda kesildi, çıktılar yazılmadı")
            return 1
        for p in tmp.iterdir():
            os.replace(p, out / p.name)
        tmp.rmdir()

    print(f"Eğitim tamamlandı: profil={dataset} ROC-AUC={auc:.4f}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Churn egitim profilini calistirir.")
    parser.add_argument("--dataset", default="telco", help="telco | openml_churn (varsayilan: telco)")
    args = parser.parse_args()
    sys.exit(main(args.dataset))
