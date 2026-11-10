"""POST /api/predict (senaryo tahmini) için backend entegrasyon testleri.

Kapsam: atdd.md AC-1, AC-2, AC-5, AC-6, AC-7, AC-S1, enum kapsamı ve Davranış Sözleşmesi
satır 1, 2, 3, 4 (predict kısmı), 9.
Model (model.joblib) ve senaryo satırı (backend.app.scenario.build_row) gerçek dosyalarla
kullanılır; beklenen olasılık model doğrudan çağrılarak bağımsız hesaplanır.
Profil her testte telco'ya sabitlenir; OpenML testi kendi profilini ayrıca ayarlar.
"""
import logging
from pathlib import Path

import joblib
import pytest
from fastapi.testclient import TestClient

from backend.app import main
from backend.app.labels import label_for
from backend.app.main import app

REPO_ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)

PREDICT_URL = "/api/predict"
PREDICT_KEYS = {
    "probability", "risk", "model", "model_label", "roc_auc",
    "drivers", "action", "similar_count",
}
DRIVER_KEYS = {"feature", "label", "contribution"}
MONITOR_ACTION = "Şimdilik müdahale gerekmiyor; izlemeye devam edin."
OPENML_409_DETAIL = "Senaryo tahmini yalnızca Telco veri setinde destekleniyor"
UNAVAILABLE_DETAIL = "Veri kaynağı okunamadı"

# Formdan türeyen özellikler (atdd.md: "Yalnızca formdaki alanlardan türeyen özellikler").
FORM_FEATURE_EXACT = {
    "tenure", "MonthlyCharges", "TotalCharges", "AvgMonthlySpend",
    "SeniorCitizen", "NumAdditionalServices",
}
FORM_FEATURE_PREFIXES = (
    "Contract_", "InternetService_", "TechSupport_",
    "OnlineSecurity_", "PaymentMethod_", "tenure_group_",
)

CONTRACT_VALUES = ["Month-to-month", "One year", "Two year"]
INTERNET_VALUES = ["DSL", "Fiber optic", "No"]
PAYMENT_VALUES = [
    "Electronic check", "Mailed check",
    "Bank transfer (automatic)", "Credit card (automatic)",
]


def _payload(**overrides) -> dict:
    base = {
        "contract": "Month-to-month",
        "tenure": 41,
        "monthly_charges": 89.5,
        "internet_service": "Fiber optic",
        "tech_support": False,
        "online_security": False,
        "payment_method": "Electronic check",
        "senior_citizen": False,
    }
    base.update(overrides)
    return base


VALID = _payload()
RISKY = _payload(
    contract="Month-to-month", tenure=2, monthly_charges=95.0,
    internet_service="Fiber optic", tech_support=False, online_security=False,
    payment_method="Electronic check", senior_citizen=False,
)
SAFE = _payload(
    contract="Two year", tenure=60, monthly_charges=45.0,
    internet_service="DSL", tech_support=True, online_security=True,
    payment_method="Credit card (automatic)", senior_citizen=False,
)


def _clear_cache(fn) -> None:
    # Test bir fonksiyonu monkeypatch ile düz bir fonksiyonla değiştirmiş olabilir; o durumda cache_clear yoktur.
    clear = getattr(fn, "cache_clear", None)
    if clear is not None:
        clear()


@pytest.fixture(autouse=True)
def _telco_profile_and_clean_caches(monkeypatch):
    monkeypatch.setattr(main, "ACTIVE", main.DATASETS["telco"])
    _clear_cache(main.load_customers)
    _clear_cache(main.load_json)
    yield
    _clear_cache(main.load_customers)
    _clear_cache(main.load_json)


def _expected_risk(p: float) -> str:
    return "high" if p >= 0.70 else "mid" if p >= 0.40 else "low"


def _post(payload: dict):
    return client.post(PREDICT_URL, json=payload)


# Sayısal özellikler: one-hot değil, değerleri 0/1 olmayan doğrudan sütunlar.
NUMERIC_DRIVER_FEATURES = {
    "SeniorCitizen", "tenure", "MonthlyCharges", "TotalCharges",
    "AvgMonthlySpend", "NumAdditionalServices",
}

# One-hot grup adları (encoder sütunlarının "<Grup>_" önekleri).
ONE_HOT_GROUPS = [
    "Contract", "InternetService", "OnlineSecurity", "OnlineBackup", "DeviceProtection",
    "TechSupport", "StreamingTV", "StreamingMovies", "PaymentMethod", "PaperlessBilling",
    "Partner", "Dependents", "PhoneService", "MultipleLines", "gender", "tenure_group",
]


def _row_for(payload: dict):
    from backend.app import scenario

    return scenario.build_row(payload)


def _group_prefix(feature: str, columns) -> str:
    """Bir one-hot sütunun grup önekini (ör. 'OnlineSecurity_') encoder sütun adlarından türetir.
    Kategorik değerler alt çizgi içerebildiği için son '_' yerine bilinen grup adlarından bulunur."""
    for group in ONE_HOT_GROUPS:
        prefix = group + "_"
        if feature.startswith(prefix):
            return prefix
    raise AssertionError(f"bilinen grup bulunamadı: {feature}")


def _expected_driver_label(feature: str, row) -> str:
    """Sürücü etiketi sözleşmesi:
    - sayısal -> label_for;
    - one-hot 1 -> label_for;
    - one-hot 0 ve '_No' ile biten özellik -> aynı gruptaki 1 olan kardeşin label_for'u (yoksa label_for + ' değil');
    - diğer one-hot 0 -> label_for + ' değil'."""
    base = label_for(feature)
    if feature in NUMERIC_DRIVER_FEATURES:
        return base
    assert feature in row.columns, f"senaryo satırında yok: {feature}"
    value = float(row[feature].iloc[0])
    if value == 1.0:
        return base
    assert value == 0.0, f"one-hot özellik 0/1 dışında değer taşıyor: {feature}={value}"
    if feature.endswith("_No"):
        prefix = _group_prefix(feature, row.columns)
        for other in row.columns:
            if other != feature and other.startswith(prefix) and float(row[other].iloc[0]) == 1.0:
                return label_for(other)
    return base + " değil"


# ---------------------------------------------------------------------------
# AC-1: geçerli senaryo -> 200, şema, model olasılığıyla birebir eşleşme, sürücüler
# ---------------------------------------------------------------------------

def test_ac1_valid_scenario_returns_200_with_exact_keys():
    resp = _post(VALID)

    assert resp.status_code == 200
    assert set(resp.json().keys()) == PREDICT_KEYS


def test_ac1_probability_equals_model_predict_proba_on_built_row():
    from backend.app import scenario

    row = scenario.build_row(VALID)
    model = joblib.load(REPO_ROOT / "model.joblib")
    expected = float(model.predict_proba(row)[0, 1])

    body = _post(VALID).json()

    assert body["probability"] == pytest.approx(expected, abs=1e-6)


def test_ac1_risk_matches_thresholds_and_model_metadata():
    body = _post(VALID).json()
    metrics = main.load_json("metrics.json")

    assert body["risk"] == _expected_risk(body["probability"])
    assert body["model"] == metrics["best_model"] == "xgboost"
    assert body["model_label"] == "XGBoost"
    assert round(body["roc_auc"], 3) == round(metrics["models"][body["model"]]["roc_auc"], 3)


def test_ac1_similar_count_matches_contract_and_risk_in_dataset():
    body = _post(VALID).json()
    df = main.load_customers()
    expected = int(((df["Contract"] == VALID["contract"]) & (df["risk"] == body["risk"])).sum())

    assert body["similar_count"] == expected


def test_ac1_drivers_are_max_five_sorted_by_abs_contribution_with_exact_shape():
    drivers = _post(VALID).json()["drivers"]
    row = _row_for(VALID)

    assert 1 <= len(drivers) <= 5
    for d in drivers:
        assert set(d.keys()) == DRIVER_KEYS
        assert isinstance(d["contribution"], float)
        assert d["label"] == _expected_driver_label(d["feature"], row)
    magnitudes = [abs(d["contribution"]) for d in drivers]
    assert magnitudes == sorted(magnitudes, reverse=True)


def test_ac1_one_hot_driver_with_zero_value_gets_degil_label_for_two_year_contract():
    payload = _payload(contract="Two year")
    row = _row_for(payload)
    drivers = _post(payload).json()["drivers"]

    # Two year senaryosunda Month-to-month one-hot sütunu 0 olmalı.
    assert float(row["Contract_Month-to-month"].iloc[0]) == 0.0
    matches = [d for d in drivers if d["feature"] == "Contract_Month-to-month"]
    for d in matches:
        assert d["label"] == label_for("Contract_Month-to-month") + " değil"


def test_ac1_no_internet_service_never_yields_var_label_for_no_columns():
    payload = _payload(internet_service="No", tech_support=True, online_security=True)
    row = _row_for(payload)
    drivers = _post(payload).json()["drivers"]

    # internet_service "No" iken OnlineSecurity_No / TechSupport_No sütunları 0; gerçek 1 sütunu
    # "No internet service" kardeşleridir.
    assert float(row["OnlineSecurity_No"].iloc[0]) == 0.0
    assert float(row["TechSupport_No"].iloc[0]) == 0.0
    assert float(row["OnlineSecurity_No internet service"].iloc[0]) == 1.0
    assert float(row["TechSupport_No internet service"].iloc[0]) == 1.0
    for d in drivers:
        assert d["label"] == _expected_driver_label(d["feature"], row)
    targeted = {d["feature"]: d["label"] for d in drivers if d["feature"] in {"OnlineSecurity_No", "TechSupport_No"}}
    for feature, label in targeted.items():
        assert label == label_for(f"{feature} internet service")
    assert not any(d["label"].endswith(": var") for d in drivers)


def test_ac1_drivers_only_contain_features_derived_from_form_fields():
    drivers = _post(VALID).json()["drivers"]

    for d in drivers:
        feature = d["feature"]
        allowed = feature in FORM_FEATURE_EXACT or feature.startswith(FORM_FEATURE_PREFIXES)
        assert allowed, f"formdan türemeyen özellik sürücü olarak döndü: {feature}"


@pytest.mark.parametrize("payload", [VALID, RISKY, SAFE], ids=["valid", "risky", "safe"])
def test_ac1_action_is_monitor_text_only_when_low_risk_or_no_positive_driver(payload):
    body = _post(payload).json()
    positive = [d for d in body["drivers"] if d["contribution"] > 0]
    expect_monitor = body["risk"] == "low" or not positive

    if expect_monitor:
        assert body["action"] == MONITOR_ACTION
    else:
        assert body["action"] != MONITOR_ACTION
        assert isinstance(body["action"], str) and body["action"].strip()


# ---------------------------------------------------------------------------
# AC-2: riskli senaryo, güvenli senaryodan daha yüksek olasılık (yön kontrolü)
# ---------------------------------------------------------------------------

def test_ac2_risky_scenario_has_higher_probability_than_safe_scenario():
    risky = _post(RISKY)
    safe = _post(SAFE)

    assert risky.status_code == 200
    assert safe.status_code == 200
    assert risky.json()["probability"] > safe.json()["probability"]


# ---------------------------------------------------------------------------
# Enum kapsamı: her değer en az bir kez 200 döner
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("contract", CONTRACT_VALUES, ids=CONTRACT_VALUES)
def test_enum_contract_each_value_returns_200(contract):
    resp = _post(_payload(contract=contract))

    assert resp.status_code == 200


@pytest.mark.parametrize("internet", INTERNET_VALUES, ids=INTERNET_VALUES)
def test_enum_internet_service_each_value_returns_200(internet):
    resp = _post(_payload(internet_service=internet))

    assert resp.status_code == 200


@pytest.mark.parametrize("payment", PAYMENT_VALUES, ids=PAYMENT_VALUES)
def test_enum_payment_method_each_value_returns_200(payment):
    resp = _post(_payload(payment_method=payment))

    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# AC-5 / AC-S1: geçersiz girdi -> 422 (yalnızca durum kodu; gövde yankısı kontrol edilmez)
# ---------------------------------------------------------------------------

def _without(key: str) -> dict:
    payload = dict(VALID)
    payload.pop(key)
    return payload


INVALID_PAYLOADS = [
    pytest.param({**VALID, "contract": "Weekly"}, id="unknown_contract"),
    pytest.param({**VALID, "tenure": 73}, id="tenure_above_72"),
    pytest.param({**VALID, "tenure": -1}, id="tenure_negative"),
    pytest.param({**VALID, "tenure": "41; drop"}, id="tenure_injection_string"),
    pytest.param({**VALID, "monthly_charges": 0}, id="charges_zero"),
    pytest.param({**VALID, "monthly_charges": 500}, id="charges_above_120"),
    pytest.param({**VALID, "monthly_charges": "nan"}, id="charges_nan_string"),
    pytest.param({**VALID, "monthly_charges": "inf"}, id="charges_inf_string"),
    pytest.param(_without("contract"), id="missing_contract"),
    pytest.param({**VALID, "admin": True}, id="extra_field"),
]


@pytest.mark.parametrize("payload", INVALID_PAYLOADS)
def test_ac5_invalid_predict_input_returns_422(payload):
    resp = _post(payload)

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# AC-6: OpenML profilinde senaryo tahmini desteklenmez -> 409 sabit mesaj
# ---------------------------------------------------------------------------

def test_ac6_openml_profile_predict_returns_409_with_exact_detail(monkeypatch):
    monkeypatch.setattr(main, "ACTIVE", main.DATASETS["openml_churn"])

    resp = _post(VALID)

    assert resp.status_code == 409
    assert resp.json() == {"detail": OPENML_409_DETAIL}


# ---------------------------------------------------------------------------
# AC-7: veri/metrik okunamazsa 503 sabit gövde + logger.exception
# ---------------------------------------------------------------------------

def test_ac7_predict_load_failure_returns_503_generic_body_and_logs(monkeypatch, caplog):
    def broken_load_json(*args, **kwargs):
        # Hata mesajı dosya yolu içeriyor; gövdede sızmamalı.
        raise RuntimeError("boom /secret/path.csv")

    monkeypatch.setattr(main, "load_json", broken_load_json)

    with caplog.at_level(logging.ERROR):
        resp = _post(VALID)

    assert resp.status_code == 503
    assert resp.json() == {"detail": UNAVAILABLE_DETAIL}
    assert "boom" not in resp.text
    assert ".csv" not in resp.text
    assert "Traceback" not in resp.text

    error_records = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert error_records
    assert any(r.exc_info is not None for r in error_records)


# ---------------------------------------------------------------------------
# build_row sözleşmesi: sütun sırası encoder ile birebir, değerler sonlu, tenure=0 medyanı
# ---------------------------------------------------------------------------

def test_build_row_columns_equal_encoder_feature_names_in_order():
    row = _row_for(VALID)
    expected = joblib.load(REPO_ROOT / "encoder.joblib")["feature_names"]

    assert list(row.columns) == list(expected)


def test_build_row_values_are_all_finite_numbers():
    import numpy as np

    row = _row_for(VALID)

    assert np.isfinite(row.to_numpy(dtype=float)).all()


def test_build_row_tenure_zero_total_charges_equals_training_median():
    import pandas as pd

    raw = pd.read_csv(REPO_ROOT / "data" / "telco_churn_raw.csv")
    train_median = float(pd.to_numeric(raw["TotalCharges"], errors="coerce").median())

    row = _row_for(_payload(tenure=0))

    assert abs(float(row["TotalCharges"].iloc[0]) - train_median) < 1e-6
