"""GET /api/model-report ucu için backend entegrasyon testleri (atdd.md AC-1, AC-2, AC-4, AC-5).

Davranış Sözleşmesi satır 1 (happy path), 3 (boş drivers) ve 4 (dosya yok -> 503).
"""
import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import main
from backend.app.labels import label_for
from backend.app.main import app

REPO_ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)

EXPECTED_MODEL_KEYS = {"logistic_regression", "random_forest", "xgboost"}
EXPECTED_LABELS = {
    "logistic_regression": "Lojistik Regresyon",
    "random_forest": "Random Forest",
    "xgboost": "XGBoost",
}
MODEL_METRIC_FIELDS = ("roc_auc", "precision", "recall", "f1")
EXPECTED_TOP_LEVEL_KEYS = {"models", "best", "best_label", "target", "target_met", "dataset", "drivers"}


def _read_real(name: str) -> dict:
    return json.loads((REPO_ROOT / name).read_text(encoding="utf-8"))


def test_happy_path_returns_all_models_and_sorted_drivers():
    metrics = _read_real("metrics.json")
    shap = _read_real("shap_scores.json")

    resp = client.get("/api/model-report")

    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == EXPECTED_TOP_LEVEL_KEYS

    # AC-1: 3 model, her birinde 4 metrik
    models = body["models"]
    assert len(models) == 3
    assert {m["key"] for m in models} == EXPECTED_MODEL_KEYS
    for m in models:
        assert m["label"] == EXPECTED_LABELS[m["key"]]
        for field in MODEL_METRIC_FIELDS:
            assert m[field] == round(metrics["models"][m["key"]][field], 6)

    # AC-1: en iyi model ve hedef durumu
    assert body["best"] == metrics["best_model"]
    assert body["best_label"] == EXPECTED_LABELS[body["best"]]
    assert body["target"] == metrics["target_roc_auc"]
    assert body["target_met"] == metrics["target_met"]

    # Veri seti künyesi (sadece metrics.json'dan)
    assert body["dataset"] == {
        "name": "IBM Telco Customer Churn",
        "rows": metrics["dataset"]["rows"],
        "churn_rate": metrics["dataset"]["churn_rate"],
    }

    # AC-2: shap_scores.json'daki TÜM değişkenler, skora göre azalan sırada
    drivers = body["drivers"]
    assert len(drivers) == len(shap)
    assert {d["feature"] for d in drivers} == set(shap.keys())
    for d in drivers:
        assert set(d.keys()) == {"feature", "label", "score"}
        assert d["label"] == label_for(d["feature"])
    for i in range(len(drivers) - 1):
        assert drivers[i]["score"] >= drivers[i + 1]["score"]


def test_empty_drivers_returns_empty_list_not_error(monkeypatch):
    # AC-4: shap_scores.json boş dict -> 200 + drivers [] (hata değil)
    main.load_json.cache_clear()
    real_load_json = main.load_json

    def fake_load_json(name: str):
        if name == "shap_scores.json":
            return {}
        return real_load_json(name)

    monkeypatch.setattr(main, "load_json", fake_load_json)

    resp = client.get("/api/model-report")

    assert resp.status_code == 200
    assert resp.json()["drivers"] == []


def test_missing_files_returns_503(monkeypatch, tmp_path):
    # AC-5: metrics.json ve shap_scores.json geçici boş dizinde yok -> 503
    main.load_json.cache_clear()
    monkeypatch.setattr(main, "ROOT", tmp_path)

    resp = client.get("/api/model-report")

    assert resp.status_code == 503
    assert resp.json() == {"detail": "Model çıktıları bulunamadı; train_model.py çalıştırın"}
