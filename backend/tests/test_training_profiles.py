"""openml_churn eğitim profili için unit + smoke testleri (src/train_model.py).

Kapsam: atdd.md AC-1 (eşik ve hash kısmı), AC-4, AC-6, AC-7, AC-8, AC-11, AC-12.
Hiçbir test proje köküne yazmaz: her eğitim çağrısı tmp_path kökü ile yapılır.
Tam eğitim (1000+ satır, n_iter=20) bu dosyada koşulmaz; smoke testleri
sample=300, n_iter=2 kullanır. Gerçek kökteki Telco çıktıları yalnızca SHA256 ile okunur.

Test arayüzü (plan.md "Dependencies"): tm.PROFILES, tm.main(dataset, root, sample, n_iter) -> int.
main sys.exit çağırmaz; hata mesajları stderr'e, son başarı satırı stdout'a yazılır.
"""
import hashlib
import importlib.util
import json
import re
import shutil
from pathlib import Path

import joblib
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# src/ bir paket değil (__init__.py yok); modül dosyadan yüklenir.
_TM_PATH = REPO_ROOT / "src" / "train_model.py"
_spec = importlib.util.spec_from_file_location("train_model", _TM_PATH)
tm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tm)

REAL_ARFF = REPO_ROOT / "data" / "openml_churn.arff"
SIX_OUTPUTS = [
    "model.joblib", "encoder.joblib", "metrics.json",
    "shap_scores.json", "shap_summary.png", "test_customers.csv",
]
# Kök (Telco) çıktıları: smoke eğitimi bunlara dokunmamalı.
REAL_ROOT_FILES = ["model.joblib", "metrics.json", "shap_scores.json", "test_customers.csv", "encoder.joblib"]
OLD_METRICS = b'{"eski": true}\n'

# Gerçek ARFF başlığıyla aynı öznitelikler (class son öznitelik).
ATTRS = [
    ("state", "NUMERIC"),
    ("account_length", "NUMERIC"),
    ("area_code", "{408,415,510}"),
    ("phone_number", "NUMERIC"),
    ("international_plan", "{0,1}"),
    ("voice_mail_plan", "{0,1}"),
    ("number_vmail_messages", "NUMERIC"),
    ("total_day_minutes", "NUMERIC"),
    ("total_day_calls", "NUMERIC"),
    ("total_day_charge", "NUMERIC"),
    ("total_eve_minutes", "NUMERIC"),
    ("total_eve_calls", "NUMERIC"),
    ("total_eve_charge", "NUMERIC"),
    ("total_night_minutes", "NUMERIC"),
    ("total_night_calls", "NUMERIC"),
    ("total_night_charge", "NUMERIC"),
    ("total_intl_minutes", "NUMERIC"),
    ("total_intl_calls", "NUMERIC"),
    ("total_intl_charge", "NUMERIC"),
    ("number_customer_service_calls", "{0,1,2,3,4,5,6,7,8,9}"),
    ("class", "{0,1}"),
]


def _row(i, cls):
    """Gerçek ARFF satırının biçimini taklit eden sentetik satır (21 değer, son değer class)."""
    return [
        i % 20, 100 + i, (408, 415, 510)[i % 3], 2000 + i, i % 2, (i // 2) % 2, i % 30,
        100.5 + i, 100 + i % 7, 17.5, 200.25, 90 + i % 5, 17.0, 210.0, 95, 9.5,
        10.0 + i % 3, 4, 2.7, i % 10, cls,
    ]


def _arff(attrs, rows):
    lines = ["@RELATION churn"]
    lines += [f"@ATTRIBUTE {name} {typ}" for name, typ in attrs]
    lines.append("@DATA")
    lines += [",".join(str(v) for v in r) for r in rows]
    return "\n".join(lines) + "\n"


def _copy_real_arff(root: Path) -> None:
    dst = root / "data" / "openml_churn.arff"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REAL_ARFF, dst)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _boom(*args, **kwargs):
    raise RuntimeError("simulated SHAP failure")


def _files_under(root: Path) -> list:
    return sorted(p for p in root.rglob("*") if p.is_file())


# ---------------------------------------------------------------------------
# Profil tanımı (unit)
# ---------------------------------------------------------------------------

def test_profiles_have_telco_and_openml_churn_with_openml_paths_and_target():
    assert set(tm.PROFILES) == {"telco", "openml_churn"}
    prof = tm.PROFILES["openml_churn"]
    assert prof["raw_path"] == "data/openml_churn.arff"
    assert prof["out_dir"] == "outputs/openml_churn"
    assert prof["target"] == "class"


def test_profiles_carry_target_roc_auc_per_dataset():
    assert tm.PROFILES["telco"]["target_roc_auc"] == 0.84
    assert tm.PROFILES["openml_churn"]["target_roc_auc"] == 0.80


# ---------------------------------------------------------------------------
# AC-6: bilinmeyen veri seti -> exit 2, tam satır, dosya yok
# ---------------------------------------------------------------------------

def test_ac6_unknown_dataset_exits_2_with_exact_line_and_writes_nothing(tmp_path, capsys):
    rc = tm.main(dataset="bilinmeyen", root=tmp_path)

    assert rc == 2
    err_lines = capsys.readouterr().err.splitlines()
    assert "Bilinmeyen veri seti: bilinmeyen. Geçerli: telco, openml_churn" in err_lines
    assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------------------
# AC-7: girdi hataları -> exit 2 ve net mesaj; hiçbir çıktı yazılmaz
# ---------------------------------------------------------------------------

ARFF_NO_CLASS = _arff(ATTRS[:-1], [_row(i, 0)[:-1] for i in range(5)])
ARFF_ALL_ZERO = _arff(ATTRS, [_row(i, 0) for i in range(10)])
ARFF_EMPTY = _arff(ATTRS, [])


@pytest.mark.parametrize(
    "content, expected, is_prefix",
    [
        (None, "Ham veri bulunamadı: ", True),           # (a) dosya yok
        (ARFF_NO_CLASS, "Hedef sütun bulunamadı: class", False),  # (b) class yok
        (ARFF_ALL_ZERO, "Hedef tek sınıf içeriyor, eğitim yapılamaz", False),  # (c) tek sınıf
        (ARFF_EMPTY, "Veri boş", False),                  # (d) 0 satır
    ],
    ids=["dosya_yok", "hedef_yok", "tek_sinif", "bos_veri"],
)
def test_ac7_bad_input_exits_2_with_message_and_writes_nothing(tmp_path, capsys, content, expected, is_prefix):
    raw = tmp_path / "data" / "openml_churn.arff"
    if content is not None:
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_text(content, encoding="utf-8")

    rc = tm.main(dataset="openml_churn", root=tmp_path)

    assert rc == 2
    err_lines = capsys.readouterr().err.splitlines()
    if is_prefix:
        assert any(line.startswith(expected) for line in err_lines)
    else:
        assert expected in err_lines
    # Yalnızca girdi dosyası (varsa) bulunmalı; çıktı klasörü ya da .tmp oluşmamalı
    expected_files = [raw] if content is not None else []
    assert _files_under(tmp_path) == expected_files


# ---------------------------------------------------------------------------
# AC-8: eğitim yarıda kesilirse .tmp silinir, eski çıktılar korunur, exit 1
# ---------------------------------------------------------------------------

def test_ac8_failure_mid_training_keeps_previous_outputs_and_removes_tmp(tmp_path, monkeypatch, capsys):
    _copy_real_arff(tmp_path)
    out = tmp_path / "outputs" / "openml_churn"
    out.mkdir(parents=True)
    (out / "metrics.json").write_bytes(OLD_METRICS)

    # Eğitimin SHAP adımı (en iyi model ağaç ya da lineer olabilir; ikisi de kırılır)
    monkeypatch.setattr(tm.shap, "TreeExplainer", _boom)
    monkeypatch.setattr(tm.shap, "LinearExplainer", _boom)

    rc = tm.main(dataset="openml_churn", root=tmp_path, sample=300, n_iter=2)

    assert rc == 1
    assert "Eğitim yarıda kesildi, çıktılar yazılmadı" in capsys.readouterr().err.splitlines()
    assert (out / "metrics.json").read_bytes() == OLD_METRICS
    assert sorted(p.name for p in out.iterdir()) == ["metrics.json"]
    assert not (out / ".tmp").exists()


# ---------------------------------------------------------------------------
# AC-1 + AC-4 + AC-12: smoke eğitimi (300 satır, n_iter=2), tmp_path kökünde
# ---------------------------------------------------------------------------

def test_ac1_ac4_ac12_smoke_training_writes_six_outputs_and_logs_summary(tmp_path, capsys):
    _copy_real_arff(tmp_path)

    rc = tm.main(dataset="openml_churn", root=tmp_path, sample=300, n_iter=2)

    assert rc == 0
    out = tmp_path / "outputs" / "openml_churn"
    for name in SIX_OUTPUTS:
        assert (out / name).is_file(), name

    # AC-4: customerID ^OC-\d{5}$ kalıbında ve benzersiz
    ids = pd.read_csv(out / "test_customers.csv")["customerID"].astype(str).tolist()
    assert ids
    assert all(re.fullmatch(r"OC-\d{5}", cid) for cid in ids)
    assert len(set(ids)) == len(ids)

    # AC-4: phone_number modele girmez
    encoder = joblib.load(out / "encoder.joblib")
    assert "phone_number" not in encoder["feature_names"]

    # AC-12: stdout'un son boş olmayan satırı özet satırı
    nonblank = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert re.fullmatch(r"Eğitim tamamlandı: profil=openml_churn ROC-AUC=0\.\d{4}", nonblank[-1])

    # Hedef eşiği profilden gelir; target_met gerçek en iyi ROC-AUC ile tutarlı olmalı
    metrics = json.loads((out / "metrics.json").read_text(encoding="utf-8"))
    best_auc = metrics["models"][metrics["best_model"]]["roc_auc"]
    assert metrics["target_roc_auc"] == 0.80
    assert metrics["target_met"] == (best_auc >= 0.80)


# ---------------------------------------------------------------------------
# AC-1 (hash): smoke eğitimi kökteki Telco çıktılarını değiştirmez
# ---------------------------------------------------------------------------

def test_ac1_real_root_telco_outputs_unchanged_after_smoke_training(tmp_path):
    before = {name: _sha256(REPO_ROOT / name) for name in REAL_ROOT_FILES}

    _copy_real_arff(tmp_path)
    rc = tm.main(dataset="openml_churn", root=tmp_path, sample=300, n_iter=2)

    after = {name: _sha256(REPO_ROOT / name) for name in REAL_ROOT_FILES}
    assert rc == 0
    assert after == before


# ---------------------------------------------------------------------------
# AC-11: aynı seed, aynı örneklem -> aynı en iyi ROC-AUC (±1e-6)
# ---------------------------------------------------------------------------

def test_ac11_two_smoke_runs_with_same_seed_give_same_best_roc_auc(tmp_path, capsys):
    best_aucs = []
    for run in ("run_a", "run_b"):
        root = tmp_path / run
        _copy_real_arff(root)
        rc = tm.main(dataset="openml_churn", root=root, sample=300, n_iter=2)
        assert rc == 0
        metrics = json.loads((root / "outputs" / "openml_churn" / "metrics.json").read_text(encoding="utf-8"))
        best_aucs.append(metrics["models"][metrics["best_model"]]["roc_auc"])

    assert abs(best_aucs[0] - best_aucs[1]) <= 1e-6


# ---------------------------------------------------------------------------
# AC-1 (eşik): commit edilmiş gerçek openml çıktısı ROC-AUC >= 0.80
# Not: outputs/openml_churn/ henüz yok; tam eğitim orkestratör tarafından koşulacak.
# ---------------------------------------------------------------------------

def test_ac1_real_openml_metrics_meet_roc_auc_threshold():
    metrics_path = REPO_ROOT / "outputs" / "openml_churn" / "metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

    best = metrics["best_model"]
    assert metrics["target_roc_auc"] == 0.80
    assert metrics["models"][best]["roc_auc"] >= 0.80
    assert metrics["dataset"]["name"] == "OpenML Churn"
