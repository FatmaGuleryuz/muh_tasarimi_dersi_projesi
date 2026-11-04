"""İki veri seti (telco, openml_churn) için API sözleşme testleri (integration).

Kapsam: atdd.md AC-2, AC-3, AC-5, AC-9, AC-10 ve Davranış Sözleşmesi 1b, 2b, 3b, 9.
Testler GERÇEK çıktı dosyalarını okur (telco: kök; openml_churn: outputs/openml_churn/).
monkeypatch yalnızca aktif profil seçimi için kullanılır (main.ACTIVE). AC-9 modülü
DATASET ortam değişkeniyle yeniden yükler; bu yüzden dosyanın sonunda ve finally ile
modül geri yüklenir.
"""
import importlib
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import main
from backend.app.main import app

REPO_ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)

ENDPOINT_KINDS = [
    "summary",
    "model-report",
    "customers-list",
    "customers-detail",
    "postmortem-list",
    "postmortem-detail",
]
TELCO_ONLY_FIELDS = ("contract", "tenure_months", "monthly_charges", "total_charges")
OPENML_ID_PATTERN = r"OC-\d{5}"
DATASET_ENV_ERROR = "Bilinmeyen DATASET: xyz. Geçerli: telco, openml_churn"


def _activate(monkeypatch, name: str) -> None:
    """Aktif profili değiştirir ve veri okuyan önbellekleri temizler."""
    monkeypatch.setattr(main, "ACTIVE", main.DATASETS[name])
    main.load_customers.cache_clear()
    main.load_json.cache_clear()


@pytest.fixture(autouse=True)
def _clear_caches_around_each_test():
    main.load_customers.cache_clear()
    main.load_json.cache_clear()
    yield
    main.load_customers.cache_clear()
    main.load_json.cache_clear()


@pytest.fixture(params=["telco", "openml_churn"])
def dataset(request, monkeypatch):
    _activate(monkeypatch, request.param)
    yield request.param
    main.load_customers.cache_clear()
    main.load_json.cache_clear()


def _fetch_all() -> dict:
    """Aktif profil için her uç çağrısını yapar; id'leri listelerden türetir."""
    summary = client.get("/api/summary")
    model_report = client.get("/api/model-report")
    listed = client.get("/api/customers", params={"limit": 5})
    postmortem = client.get("/api/postmortem", params={"limit": 5})
    assert listed.status_code == 200
    assert postmortem.status_code == 200

    cid = listed.json()["customers"][0]["customer_id"]
    lost_id = postmortem.json()["items"][0]["customer_id"]
    return {
        "summary": summary,
        "model-report": model_report,
        "customers-list": listed,
        "customers-detail": client.get(f"/api/customers/{cid}"),
        "postmortem-list": postmortem,
        "postmortem-detail": client.get(f"/api/postmortem/{lost_id}"),
    }


# ---------------------------------------------------------------------------
# AC-2: her iki profilde tüm sözleşme uçları 200
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("kind", ENDPOINT_KINDS)
def test_ac2_endpoint_returns_200_for_each_dataset(dataset, kind):
    resp = _fetch_all()[kind]

    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# AC-2: openml_churn yanıtlarının top-level anahtar kümesi telco ile aynı
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("kind", ENDPOINT_KINDS)
def test_ac2_openml_top_level_keys_equal_telco_keys(monkeypatch, kind):
    _activate(monkeypatch, "telco")
    telco = _fetch_all()
    _activate(monkeypatch, "openml_churn")
    openml = _fetch_all()

    assert telco[kind].status_code == 200
    assert openml[kind].status_code == 200
    assert set(openml[kind].json()) == set(telco[kind].json())


# ---------------------------------------------------------------------------
# AC-5 (openml_churn): Telco'ya özgü alanlar null, by_contract boş, dataset adı
# ---------------------------------------------------------------------------

def test_ac5_openml_customer_detail_has_null_telco_only_fields(monkeypatch):
    _activate(monkeypatch, "openml_churn")
    listed = client.get("/api/customers", params={"limit": 1})
    assert listed.status_code == 200
    cid = listed.json()["customers"][0]["customer_id"]

    resp = client.get(f"/api/customers/{cid}")

    assert resp.status_code == 200
    body = resp.json()
    for field in TELCO_ONLY_FIELDS:
        assert body[field] is None, field


def test_ac5_openml_summary_has_empty_by_contract_and_dataset_name(monkeypatch):
    _activate(monkeypatch, "openml_churn")

    resp = client.get("/api/summary")

    assert resp.status_code == 200
    body = resp.json()
    assert body["by_contract"] == []
    assert body["dataset"]["name"] == "OpenML Churn"


def test_ac5_openml_model_report_dataset_name(monkeypatch):
    _activate(monkeypatch, "openml_churn")

    resp = client.get("/api/model-report")

    assert resp.status_code == 200
    assert resp.json()["dataset"]["name"] == "OpenML Churn"


def test_ac5_openml_customer_ids_match_oc_pattern(monkeypatch):
    _activate(monkeypatch, "openml_churn")

    resp = client.get("/api/customers", params={"limit": 1000})

    assert resp.status_code == 200
    ids = [row["customer_id"] for row in resp.json()["customers"]]
    assert ids
    assert all(re.fullmatch(OPENML_ID_PATTERN, cid) for cid in ids)


# ---------------------------------------------------------------------------
# AC-3: DATASET verilmediğinde varsayılan telco; davranış bugünküyle aynı
# (Bu test, süreç başında DATASET ortam değişkeninin tanımsız olduğunu varsayar.)
# ---------------------------------------------------------------------------

def test_ac3_default_profile_is_telco_and_summary_is_ibm_telco():
    assert main.ACTIVE is main.DATASETS["telco"]

    resp = client.get("/api/summary")

    assert resp.status_code == 200
    assert resp.json()["dataset"]["name"] == "IBM Telco Customer Churn"


# ---------------------------------------------------------------------------
# AC-10: çıktı klasörü yoksa veri okuyan uçlar 503
# ---------------------------------------------------------------------------

def test_ac10_missing_output_dir_returns_503_on_data_endpoints(monkeypatch, tmp_path):
    missing_dir = tmp_path / "yok"
    broken_profile = {**main.DATASETS["openml_churn"], "dir": missing_dir}
    monkeypatch.setattr(main, "ACTIVE", broken_profile)
    main.load_customers.cache_clear()
    main.load_json.cache_clear()

    for path in ("/api/summary", "/api/customers", "/api/postmortem"):
        resp = client.get(path)

        assert resp.status_code == 503, path
        assert resp.json() == {"detail": "Veri kaynağı okunamadı"}, path


# ---------------------------------------------------------------------------
# AC-9: DATASET=xyz ile modül import edilirken ValueError; modül sonra geri yüklenir.
# DİKKAT: bu test dosyanın sonunda; reload sonrası modül durumu finally'de düzeltilir.
# ---------------------------------------------------------------------------

def test_ac9_unknown_dataset_env_raises_value_error_on_import(monkeypatch):
    monkeypatch.setenv("DATASET", "xyz")
    try:
        with pytest.raises(ValueError) as excinfo:
            importlib.reload(main)
        assert str(excinfo.value) == DATASET_ENV_ERROR
    finally:
        monkeypatch.delenv("DATASET", raising=False)
        importlib.reload(main)
