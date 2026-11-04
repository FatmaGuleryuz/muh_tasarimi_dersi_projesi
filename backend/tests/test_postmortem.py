"""Kayıp müşteri postmortem uçları için backend entegrasyon testleri.

Kapsam: GET /api/postmortem (liste) ve GET /api/postmortem/{id} (detay).
atdd.md AC-1..AC-10, AC-S1, AC-S2 ve Davranış Sözleşmesi satırları 1, 1b, 2, 3, 3b, 5, 7, 8.
AC-11 / AC-12 UI kriterleridir, burada test edilmez.

Beklenen değerler CSV'den (pandas) bağımsız olarak yeniden hesaplanır; endpoint'in
kendi hesabına güvenilmez. Kısmi/boş veri senaryoları main.load_customers monkeypatch
ile kurulur; load_customers @lru_cache olduğu için her testten önce ve sonra cache temizlenir.
"""
import json
import logging
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app import main
from backend.app.main import app

REPO_ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)

RATE_TOL = 0.001
LIST_TOP_KEYS = {"summary", "total", "items"}
SUMMARY_KEYS = {
    "lost_total", "caught", "partial", "missed",
    "catch_rate", "strict_catch_rate", "false_alarm_count", "precision_high",
}
LIST_ITEM_KEYS = {
    "customer_id", "probability", "risk", "outcome",
    "contract", "reason", "reason_feature", "action",
}
DETAIL_KEYS = {
    "customer_id", "actual_churn", "probability", "risk", "outcome",
    "contract", "tenure_months", "monthly_charges", "total_charges",
    "reason", "reason_feature", "top_reason_global_rank",
    "action", "action_applied", "action_applied_note",
}
OUTCOME_BY_RISK = {"high": "caught", "mid": "partial", "low": "missed"}


@pytest.fixture(autouse=True)
def _clear_load_customers_cache():
    # load_customers @lru_cache ile sarılı. Monkeypatch geri alındıktan sonra
    # (fixture teardown sırası gereği) gerçek fonksiyonun cache'i de temizlenir.
    main.load_customers.cache_clear()
    yield
    main.load_customers.cache_clear()


# ---------------------------------------------------------------------------
# Yardımcılar: beklenen değerleri CSV'den bağımsız hesaplar
# ---------------------------------------------------------------------------

def _read_test_set() -> pd.DataFrame:
    return pd.read_csv(REPO_ROOT / "test_customers.csv")


def _risk_of(p: float) -> str:
    return "high" if p >= main.HIGH_THRESHOLD else "mid" if p >= main.MID_THRESHOLD else "low"


def _lost_with_outcome(df: pd.DataFrame, outcome: str) -> pd.DataFrame:
    lost = df[df["actual_churn"] == 1]
    p = lost["churn_probability"]
    if outcome == "caught":
        return lost[p >= main.HIGH_THRESHOLD]
    if outcome == "partial":
        return lost[(p >= main.MID_THRESHOLD) & (p < main.HIGH_THRESHOLD)]
    return lost[p < main.MID_THRESHOLD]


def _expected_summary(df: pd.DataFrame) -> dict:
    lost = df[df["actual_churn"] == 1]
    lost_total = len(lost)
    caught = len(_lost_with_outcome(df, "caught"))
    partial = len(_lost_with_outcome(df, "partial"))
    missed = len(_lost_with_outcome(df, "missed"))

    high_mask = df["churn_probability"] >= main.HIGH_THRESHOLD
    high_total = int(high_mask.sum())
    true_high = int((high_mask & (df["actual_churn"] == 1)).sum())
    false_alarm = int((high_mask & (df["actual_churn"] == 0)).sum())

    return {
        "lost_total": lost_total,
        "caught": caught,
        "partial": partial,
        "missed": missed,
        "catch_rate": (caught + partial) / lost_total if lost_total else 0.0,
        "strict_catch_rate": caught / lost_total if lost_total else 0.0,
        "false_alarm_count": false_alarm,
        "precision_high": true_high / high_total if high_total else 0.0,
    }


def _first_lost_id(df: pd.DataFrame) -> str:
    return str(df.loc[df["actual_churn"] == 1, "customerID"].iloc[0])


def _expected_rank(feature: str):
    keys = list(json.loads((REPO_ROOT / "shap_scores.json").read_text(encoding="utf-8")).keys())
    return keys.index(feature) + 1 if feature in keys else None


# ---------------------------------------------------------------------------
# Davranış Sözleşmesi satır 1 (happy path liste) -> AC-1, AC-3 (özet kısmı)
# ---------------------------------------------------------------------------

def test_ac1_list_summary_matches_csv_recount():
    df = _read_test_set()
    exp = _expected_summary(df)

    resp = client.get("/api/postmortem", params={"limit": 1000})

    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == LIST_TOP_KEYS

    summary = body["summary"]
    assert set(summary.keys()) == SUMMARY_KEYS
    assert summary["lost_total"] == exp["lost_total"]
    assert summary["caught"] == exp["caught"]
    assert summary["partial"] == exp["partial"]
    assert summary["missed"] == exp["missed"]
    assert summary["caught"] + summary["partial"] + summary["missed"] == summary["lost_total"]
    assert summary["catch_rate"] == pytest.approx(exp["catch_rate"], abs=RATE_TOL)
    assert summary["strict_catch_rate"] == pytest.approx(exp["strict_catch_rate"], abs=RATE_TOL)
    assert summary["false_alarm_count"] == exp["false_alarm_count"]
    assert summary["precision_high"] == pytest.approx(exp["precision_high"], abs=RATE_TOL)

    # Liste yalnızca kayıp müşterileri içerir; filtresiz toplam lost_total'a eşit
    assert body["total"] == exp["lost_total"]
    assert len(body["items"]) == exp["lost_total"]
    for item in body["items"]:
        assert set(item.keys()) == LIST_ITEM_KEYS
        assert item["outcome"] == OUTCOME_BY_RISK[item["risk"]]


# ---------------------------------------------------------------------------
# Davranış Sözleşmesi satır 1b (happy path detay) -> AC-2
# ---------------------------------------------------------------------------

def test_ac2_detail_schema_and_outcome_risk_consistency():
    df = _read_test_set()
    cid = _first_lost_id(df)
    row = df[df["customerID"] == cid].iloc[0]
    real_row = main.load_customers()
    real_row = real_row[real_row["customerID"] == cid].iloc[0]

    resp = client.get(f"/api/postmortem/{cid}")

    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == DETAIL_KEYS
    assert body["customer_id"] == cid
    assert body["actual_churn"] is True
    assert body["action_applied"] is None
    assert body["action_applied_note"] == "Veri yok"

    assert body["probability"] == pytest.approx(float(row["churn_probability"]), abs=1e-6)
    assert body["risk"] == _risk_of(float(row["churn_probability"]))
    assert body["outcome"] == OUTCOME_BY_RISK[body["risk"]]
    assert body["reason_feature"] == row["top_reason"]
    assert body["action"] == row["suggested_action"]
    assert body["tenure_months"] == int(real_row["tenure"])
    assert body["monthly_charges"] == pytest.approx(float(real_row["MonthlyCharges"]), abs=1e-6)
    assert body["top_reason_global_rank"] == _expected_rank(row["top_reason"])


# ---------------------------------------------------------------------------
# Davranış Sözleşmesi satır 2 (geçersiz girdi) -> AC-6
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "params",
    [{"outcome": "foo"}, {"limit": 0}, {"limit": -5}, {"limit": 1001}],
    ids=["outcome_foo", "limit_0", "limit_minus_5", "limit_1001"],
)
def test_ac6_invalid_outcome_or_limit_returns_422(params):
    resp = client.get("/api/postmortem", params=params)

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# AC-3: outcome filtresi
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("outcome", ["caught", "partial", "missed"])
def test_ac3_outcome_filter_returns_only_matching_items(outcome):
    df = _read_test_set()
    expected_count = len(_lost_with_outcome(df, outcome))

    resp = client.get("/api/postmortem", params={"outcome": outcome, "limit": 1000})
    unfiltered = client.get("/api/postmortem", params={"limit": 1000})

    assert resp.status_code == 200
    assert unfiltered.status_code == 200
    body = resp.json()

    # Her öğe istenen outcome'da
    for item in body["items"]:
        assert item["outcome"] == outcome

    # total filtrelenmiş liste uzunluğu; CSV'deki sayıyla da eşleşir
    assert body["total"] == len(body["items"])
    assert len(body["items"]) == expected_count

    # summary filtreden etkilenmez
    assert body["summary"] == unfiltered.json()["summary"]

    # Sıralama: probability artan (en çok kaçırılan en üstte)
    probs = [item["probability"] for item in body["items"]]
    assert probs == sorted(probs)


# ---------------------------------------------------------------------------
# Davranış Sözleşmesi satır 3 (id yok) -> AC-4
# ---------------------------------------------------------------------------

def test_ac4_unknown_id_returns_404_with_exact_detail():
    df = _read_test_set()
    cid = "NOPE-00000"
    assert cid not in set(df["customerID"])

    resp = client.get(f"/api/postmortem/{cid}")

    assert resp.status_code == 404
    assert resp.json() == {"detail": f"Müşteri bulunamadı: {cid}"}


# ---------------------------------------------------------------------------
# Davranış Sözleşmesi satır 3b (id var ama kaybedilmemiş) -> AC-5
# ---------------------------------------------------------------------------

def test_ac5_existing_non_churned_id_returns_409_with_exact_detail():
    df = _read_test_set()
    cid = str(df.loc[df["actual_churn"] == 0, "customerID"].iloc[0])

    resp = client.get(f"/api/postmortem/{cid}")

    assert resp.status_code == 409
    assert resp.json() == {"detail": f"Müşteri kaybedilmemiş: {cid}"}


# ---------------------------------------------------------------------------
# Davranış Sözleşmesi satır 5 (veri okunamıyor) -> AC-7, AC-S2
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", ["/api/postmortem", "/api/postmortem/{id}"])
def test_ac7_load_failure_returns_503_generic_body_and_logs(monkeypatch, caplog, path):
    df = _read_test_set()
    cid = _first_lost_id(df)
    secret = str(main.ROOT / "test_customers.csv")

    def broken_loader():
        # Hata mesajı bilerek dosya yolu içeriyor; gövdede sızmamalı.
        raise FileNotFoundError(secret)

    monkeypatch.setattr(main, "load_customers", broken_loader)

    with caplog.at_level(logging.ERROR):
        resp = client.get(path.replace("{id}", cid))

    assert resp.status_code == 503
    assert resp.json() == {"detail": "Veri kaynağı okunamadı"}

    # AC-S2: gövdede stack trace, dosya uzantısı ya da kök yol yok
    assert "Traceback" not in resp.text
    assert ".csv" not in resp.text
    assert str(main.ROOT) not in resp.text

    # Operatör görünürlüğü: logger.exception ile bir ERROR kaydı (exc_info dolu)
    error_records = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert error_records
    assert any(r.exc_info is not None for r in error_records)


# ---------------------------------------------------------------------------
# AC-7 (genel hata): FileNotFoundError dışındaki istisna tipleri de 503 olmalı
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", ["/api/postmortem", "/api/postmortem/{id}"])
def test_ac7_unexpected_exception_type_returns_503(monkeypatch, caplog, path):
    df = _read_test_set()
    cid = _first_lost_id(df)

    def broken_loader():
        # Beklenmeyen tip (RuntimeError); mesaj dosya yolu içeriyor, gövdede sızmamalı.
        raise RuntimeError("boom /secret/path.csv")

    monkeypatch.setattr(main, "load_customers", broken_loader)

    with caplog.at_level(logging.ERROR):
        resp = client.get(path.replace("{id}", cid))

    assert resp.status_code == 503
    assert resp.json() == {"detail": "Veri kaynağı okunamadı"}

    # AC-S2: istisna mesajı, stack trace ve dosya uzantısı gövdede olmamalı
    assert "boom" not in resp.text
    assert ".csv" not in resp.text
    assert "Traceback" not in resp.text

    # Operatör görünürlüğü: logger.exception ile bir ERROR kaydı (exc_info dolu)
    error_records = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert error_records
    assert any(r.exc_info is not None for r in error_records)


# ---------------------------------------------------------------------------
# AC-7 (detay, shap yükleme hatası): load_customers sağlam, shap_scores.json okunamıyor
# ---------------------------------------------------------------------------

def test_ac7_detail_shap_load_failure_returns_503(monkeypatch, caplog):
    df = _read_test_set()
    cid = _first_lost_id(df)
    real_load_json = main.load_json

    def load_json_failing_on_shap(name, *args, **kwargs):
        # Yalnızca shap_scores.json için hata; diğer dosyalar gerçek loader'a devredilir.
        if name == "shap_scores.json":
            raise FileNotFoundError(str(main.ROOT / name))
        return real_load_json(name, *args, **kwargs)

    monkeypatch.setattr(main, "load_json", load_json_failing_on_shap)

    with caplog.at_level(logging.ERROR):
        resp = client.get(f"/api/postmortem/{cid}")

    assert resp.status_code == 503
    assert resp.json() == {"detail": "Veri kaynağı okunamadı"}

    # AC-S2: gövdede dosya adı/yolu, uzantı ya da stack trace olmamalı
    assert "shap_scores" not in resp.text
    assert ".json" not in resp.text
    assert "Traceback" not in resp.text
    assert str(main.ROOT) not in resp.text

    # Operatör görünürlüğü: logger.exception ile bir ERROR kaydı (exc_info dolu)
    error_records = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert error_records
    assert any(r.exc_info is not None for r in error_records)


# ---------------------------------------------------------------------------
# Davranış Sözleşmesi satır 8 (0 kayıp müşteri) -> AC-8
# ---------------------------------------------------------------------------

def test_ac8_no_lost_customers_returns_empty_items_and_zero_summary(monkeypatch):
    real = main.load_customers()
    no_loss = real[real["actual_churn"] == 0]
    monkeypatch.setattr(main, "load_customers", lambda: no_loss)

    resp = client.get("/api/postmortem")

    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0
    summary = body["summary"]
    assert summary["lost_total"] == 0
    assert summary["caught"] == 0
    assert summary["partial"] == 0
    assert summary["missed"] == 0
    assert summary["catch_rate"] == 0.0
    assert summary["strict_catch_rate"] == 0.0
    # Bu DataFrame'de gerçek kayıp yok; doğru positive olmadığı için precision 0.0
    assert summary["precision_high"] == 0.0


def test_ac8_empty_dataframe_returns_all_summary_values_zero(monkeypatch):
    real = main.load_customers()
    empty = real.iloc[0:0]
    monkeypatch.setattr(main, "load_customers", lambda: empty)

    resp = client.get("/api/postmortem")

    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["summary"] == {
        "lost_total": 0,
        "caught": 0,
        "partial": 0,
        "missed": 0,
        "catch_rate": 0.0,
        "strict_catch_rate": 0.0,
        "false_alarm_count": 0,
        "precision_high": 0.0,
    }


# ---------------------------------------------------------------------------
# Davranış Sözleşmesi satır 7 (kısmi veri) -> AC-9, AC-10
# ---------------------------------------------------------------------------

def test_ac9_blank_total_charges_for_lost_customer_is_null(monkeypatch):
    real = main.load_customers()
    lost = real[real["actual_churn"] == 1]
    blank = lost[lost["TotalCharges"].isna()]

    if len(blank):
        # Gerçek veride TotalCharges boş bir kayıp müşteri var; onu kullan
        cid = str(blank["customerID"].iloc[0])
    else:
        # Yok: kayıp bir müşterinin TotalCharges değerini NaN yapan sahte veri
        cid = str(lost["customerID"].iloc[0])
        fake = real.copy()
        fake.loc[fake["customerID"] == cid, "TotalCharges"] = float("nan")
        monkeypatch.setattr(main, "load_customers", lambda: fake)

    resp = client.get(f"/api/postmortem/{cid}")

    assert resp.status_code == 200
    body = resp.json()
    assert "total_charges" in body
    assert body["total_charges"] is None


def test_ac10_top_reason_missing_from_shap_gives_null_rank(monkeypatch):
    real = main.load_customers()
    cid = str(real.loc[real["actual_churn"] == 1, "customerID"].iloc[0])
    unknown_feature = "BILINMEYEN_OZELLIK_XYZ"
    fake = real.copy()
    fake.loc[fake["customerID"] == cid, "top_reason"] = unknown_feature
    monkeypatch.setattr(main, "load_customers", lambda: fake)

    resp = client.get(f"/api/postmortem/{cid}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["reason_feature"] == unknown_feature
    assert body["top_reason_global_rank"] is None


def test_ac10_known_feature_rank_is_position_in_shap_keys(monkeypatch):
    keys = list(json.loads((REPO_ROOT / "shap_scores.json").read_text(encoding="utf-8")).keys())
    feature = keys[2]

    real = main.load_customers()
    cid = str(real.loc[real["actual_churn"] == 1, "customerID"].iloc[0])
    fake = real.copy()
    fake.loc[fake["customerID"] == cid, "top_reason"] = feature
    monkeypatch.setattr(main, "load_customers", lambda: fake)

    resp = client.get(f"/api/postmortem/{cid}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["reason_feature"] == feature
    assert body["top_reason_global_rank"] == keys.index(feature) + 1


# ---------------------------------------------------------------------------
# AC-S1 (Tampering): saldırgan id'ler birebir eşleşmeyle 404 döner
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "attack_id, expected_detail",
    [
        ("' OR 1=1--", "Müşteri bulunamadı: ' OR 1=1--"),
        (".*", "Müşteri bulunamadı: .*"),
        # %2F, Starlette yönlendiricisi tarafından "/" olarak çözülür; istek hiçbir
        # müşteri rotasına eşleşmez ve framework'ün kendi 404'ü döner. Bu, id'nin
        # hiç handler'a ulaşmadığı anlamına gelir (güvenli davranış). Detay metni
        # bu yüzden uygulamanın "Müşteri bulunamadı" mesajı değil, "Not Found"tur.
        ("..%2F..%2Fmetrics.json", "Not Found"),
    ],
    ids=["sql_like", "regex_wildcard", "encoded_traversal"],
)
def test_ac_s1_malicious_ids_return_404_without_other_customer_data(attack_id, expected_detail):
    # Yol parametresi olarak gönderilen değer aynen (literal) kalsın diye encode edilir
    resp = client.get("/api/postmortem/" + quote(attack_id, safe=""))

    assert resp.status_code == 404
    assert resp.json() == {"detail": expected_detail}
    # Başka müşterinin verisi (veya model/metrik alanları) yanıtta sızmamalı
    for leaked_key in ("customer_id", "probability", "roc_auc"):
        assert leaked_key not in resp.text
