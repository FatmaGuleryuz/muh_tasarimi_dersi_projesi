"""Müdahale planları uçları için backend entegrasyon testleri.

Kapsam: GET /api/intervention-plans, GET /api/intervention-plans/export.csv.
atdd.md AC-3, AC-4, AC-5 (plans/risk kısmı), AC-6 (OpenML plans), AC-7, AC-8, AC-S2 ve
Davranış Sözleşmesi satır 5, 6, 7, 8.

Beklenen değerler test_customers.csv'den (pandas) bağımsız hesaplanır; endpoint'in kendi
gruplamasına güvenilmez. Eşikler (0,40 / 0,70) bu dosyada sabit yazılır, main'den okunmaz.
Kısmi/hatalı veri senaryoları main.load_customers monkeypatch ile kurulur; load_customers
ve load_json @lru_cache olduğu için her testten önce ve sonra cache temizlenir.
"""
import csv
import io
import logging
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app import main
from backend.app.main import app

REPO_ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)

PLANS_URL = "/api/intervention-plans"
EXPORT_URL = "/api/intervention-plans/export.csv"
MID_T = 0.40
HIGH_T = 0.70
RATE_TOL = 1e-3

TOP_KEYS = {"summary", "plans", "insight"}
SUMMARY_KEYS = {"targeted", "plans", "avg_probability"}
PLAN_KEYS = {
    "action", "reason_feature", "reason", "count", "high", "mid",
    "share", "avg_probability", "probabilities", "customers",
}
CUSTOMER_KEYS = {"customer_id", "probability", "risk", "contract", "reason"}
INSIGHT_KEYS = {"top_action", "top_share"}
EXPORT_HEADER = ["Müşteri ID", "Kayıp Olasılığı (%)", "Risk", "Sözleşme", "Ana Neden"]
PLAN_NOT_FOUND = "Plan bulunamadı"
UNAVAILABLE_DETAIL = "Veri kaynağı okunamadı"
TELCO_ACTION_PROBE = "Uzun dönem sözleşmeye geçişte indirim"


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


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------

def _read_test_set() -> pd.DataFrame:
    return pd.read_csv(REPO_ROOT / "test_customers.csv")


def _targeted(df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    return df[df["churn_probability"] >= threshold]


def _plans(risk: str = "high_mid"):
    return client.get(PLANS_URL, params={"risk": risk})


def _export(action: str, risk: str = "high_mid"):
    return client.get(EXPORT_URL, params={"action": action, "risk": risk})


def _csv_rows(content: bytes) -> list[list[str]]:
    text = content.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(text)))


# ---------------------------------------------------------------------------
# AC-3: high_mid (varsayılan) -> özet, plan toplamları, sıralama, müşteri listesi
# ---------------------------------------------------------------------------

def test_ac3_high_mid_returns_200_with_exact_keys():
    resp = _plans("high_mid")

    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == TOP_KEYS
    assert set(body["summary"].keys()) == SUMMARY_KEYS
    assert set(body["insight"].keys()) == INSIGHT_KEYS
    for plan in body["plans"]:
        assert set(plan.keys()) == PLAN_KEYS
        for c in plan["customers"]:
            assert set(c.keys()) == CUSTOMER_KEYS


def test_ac3_targeted_equals_csv_count_at_mid_threshold():
    df = _read_test_set()
    body = _plans("high_mid").json()

    assert body["summary"]["targeted"] == len(_targeted(df, MID_T))


def test_ac3_plan_counts_sum_to_targeted_and_match_csv_groups():
    df = _read_test_set()
    targeted_df = _targeted(df, MID_T)
    expected_groups = targeted_df.groupby("suggested_action").size()
    body = _plans("high_mid").json()
    plans = body["plans"]

    assert sum(p["count"] for p in plans) == body["summary"]["targeted"]
    assert {p["action"] for p in plans} == set(expected_groups.index)
    for p in plans:
        assert p["count"] == int(expected_groups.loc[p["action"]])


def test_ac3_each_plan_high_plus_mid_equals_count_and_matches_thresholds():
    df = _read_test_set()
    body = _plans("high_mid").json()

    for p in body["plans"]:
        assert p["high"] + p["mid"] == p["count"]
        group = _targeted(df, MID_T)
        group = group[group["suggested_action"] == p["action"]]
        assert p["high"] == int((group["churn_probability"] >= HIGH_T).sum())


def test_ac3_share_sums_to_one_within_tolerance_and_is_count_over_targeted():
    body = _plans("high_mid").json()
    targeted = body["summary"]["targeted"]

    # share 3 haneye yuvarlanıyor; plan başına en fazla 0.0005 sapma
    assert sum(p["share"] for p in body["plans"]) == pytest.approx(1.0, abs=0.002)
    for p in body["plans"]:
        assert p["share"] == pytest.approx(p["count"] / targeted, abs=RATE_TOL)


def test_ac3_plans_sorted_by_count_descending_and_summary_plan_count():
    body = _plans("high_mid").json()
    counts = [p["count"] for p in body["plans"]]

    assert counts == sorted(counts, reverse=True)
    assert body["summary"]["plans"] == len(body["plans"])


def test_ac3_plan_probabilities_list_and_average_are_consistent():
    body = _plans("high_mid").json()

    for p in body["plans"]:
        assert len(p["probabilities"]) == p["count"]
        assert all(MID_T <= x <= 1.0 for x in p["probabilities"])
        assert p["avg_probability"] == pytest.approx(
            sum(p["probabilities"]) / len(p["probabilities"]), abs=RATE_TOL
        )


def test_ac3_plan_customers_are_top_five_by_probability_within_plan():
    df = _read_test_set()
    targeted_df = _targeted(df, MID_T)
    body = _plans("high_mid").json()

    for p in body["plans"]:
        group = targeted_df[targeted_df["suggested_action"] == p["action"]]
        expected_top = sorted(group["churn_probability"].tolist(), reverse=True)[:5]
        customers = p["customers"]

        assert len(customers) <= 5
        probs = [c["probability"] for c in customers]
        assert probs == sorted(probs, reverse=True)
        assert probs == pytest.approx(expected_top, abs=1e-6)
        assert {c["customer_id"] for c in customers} <= set(group["customerID"])


def test_ac3_insight_points_to_first_plan():
    body = _plans("high_mid").json()
    first = body["plans"][0]

    assert body["insight"]["top_action"] == first["action"]
    assert body["insight"]["top_share"] == pytest.approx(first["share"], abs=RATE_TOL)


def test_ac3_default_risk_equals_high_mid():
    default = client.get(PLANS_URL).json()
    explicit = _plans("high_mid").json()

    assert default == explicit


# ---------------------------------------------------------------------------
# AC-4: risk=high -> yalnızca >= 0,70; mid hiç yok
# ---------------------------------------------------------------------------

def test_ac4_risk_high_contains_only_high_customers_and_no_mid():
    df = _read_test_set()
    expected_targeted = len(_targeted(df, HIGH_T))

    resp = _plans("high")

    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"]["targeted"] == expected_targeted
    assert sum(p["count"] for p in body["plans"]) == expected_targeted
    for p in body["plans"]:
        assert p["mid"] == 0
        assert p["high"] == p["count"]
        assert all(x >= HIGH_T for x in p["probabilities"])
        for c in p["customers"]:
            assert c["probability"] >= HIGH_T
            assert c["risk"] == "high"


@pytest.mark.parametrize("risk", ["low", "critical"])
def test_ac4_invalid_risk_value_returns_422(risk):
    resp = _plans(risk)

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# AC-8: export.csv -> 200, text/csv, satır sayısı == plan count; bilinmeyen action -> 404
# ---------------------------------------------------------------------------

def test_ac8_export_first_plan_returns_csv_with_plan_count_rows():
    first = _plans("high_mid").json()["plans"][0]

    resp = _export(first["action"], "high_mid")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert resp.content.startswith(b"\xef\xbb\xbf")
    rows = _csv_rows(resp.content)
    assert rows[0] == EXPORT_HEADER
    assert len(rows) - 1 == first["count"]


def test_ac8_unknown_action_returns_404_with_exact_detail():
    resp = _export("yok böyle")

    assert resp.status_code == 404
    assert resp.json() == {"detail": PLAN_NOT_FOUND}


@pytest.mark.parametrize("risk", ["low", "critical"])
def test_ac8_export_invalid_risk_value_returns_422(risk):
    resp = _export(TELCO_ACTION_PROBE, risk)

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# AC-S2: action yalnızca birebir eşleşir (yol / regex / joker kullanılmaz)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "action",
    ["../metrics.json", "Uzun dönem sözleşmeye geçişte", ".*", "*"],
    ids=["path_traversal", "prefix_only", "regex_wildcard", "glob_star"],
)
def test_ac_s2_action_matches_exactly_or_returns_404(action):
    resp = _export(action)

    assert resp.status_code == 404
    assert resp.json() == {"detail": PLAN_NOT_FOUND}
    assert "best_model" not in resp.text
    assert "models" not in resp.text


# ---------------------------------------------------------------------------
# AC-S2 (CSV injection): =, +, -, @ ile başlayan hücreler başına ' alır
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "prefix",
    ["=", "+", "-", "@", "\t", "\r"],
    ids=["equals", "plus", "minus", "at", "tab", "cr"],
)
def test_ac_s2_csv_injection_cell_is_neutralised_with_apostrophe(monkeypatch, prefix):
    real = main.load_customers()
    idx = real.index[real["churn_probability"] >= MID_T][0]
    action = str(real.at[idx, "suggested_action"])
    payload_id = f"{prefix}cmd"

    fake = real.copy()
    fake.at[idx, "customerID"] = payload_id
    monkeypatch.setattr(main, "load_customers", lambda: fake)

    resp = _export(action, "high_mid")

    assert resp.status_code == 200
    rows = _csv_rows(resp.content)
    data = rows[1:]
    ids = [r[0] for r in data]
    assert f"'{payload_id}" in ids
    assert payload_id not in ids
    for row in data:
        for cell in row:
            assert cell[:1] not in ("=", "+", "-", "@", "\t", "\r"), cell


# ---------------------------------------------------------------------------
# AC-7: veri okunamazsa her iki uç 503 sabit gövde + logger.exception
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "path, params",
    [
        (PLANS_URL, {"risk": "high_mid"}),
        (EXPORT_URL, {"action": TELCO_ACTION_PROBE, "risk": "high_mid"}),
    ],
    ids=["plans", "export"],
)
def test_ac7_load_failure_returns_503_generic_body_and_logs(monkeypatch, caplog, path, params):
    def broken_loader():
        # Hata mesajı dosya yolu içeriyor; gövdede sızmamalı.
        raise RuntimeError("boom /secret/path.csv")

    monkeypatch.setattr(main, "load_customers", broken_loader)

    with caplog.at_level(logging.ERROR):
        resp = client.get(path, params=params)

    assert resp.status_code == 503
    assert resp.json() == {"detail": UNAVAILABLE_DETAIL}
    assert "boom" not in resp.text
    assert ".csv" not in resp.text
    assert "Traceback" not in resp.text

    error_records = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert error_records
    assert any(r.exc_info is not None for r in error_records)


# ---------------------------------------------------------------------------
# AC-6: OpenML profilinde plans 200 (OpenML çıktılarıyla)
# ---------------------------------------------------------------------------

def test_ac6_openml_profile_plans_returns_200_with_openml_counts(monkeypatch):
    monkeypatch.setattr(main, "ACTIVE", main.DATASETS["openml_churn"])
    openml_df = pd.read_csv(REPO_ROOT / "outputs" / "openml_churn" / "test_customers.csv")

    resp = _plans("high_mid")

    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == TOP_KEYS
    assert body["summary"]["targeted"] == len(_targeted(openml_df, MID_T))
    assert sum(p["count"] for p in body["plans"]) == body["summary"]["targeted"]


def test_ac8_openml_profile_export_first_plan_returns_csv_with_plan_count_rows(monkeypatch):
    monkeypatch.setattr(main, "ACTIVE", main.DATASETS["openml_churn"])
    plans = _plans("high_mid").json()["plans"]
    assert plans, "OpenML profilinde en az bir plan beklenir"
    first = plans[0]

    resp = _export(first["action"], "high_mid")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    rows = _csv_rows(resp.content)
    assert len(rows) - 1 == first["count"]
