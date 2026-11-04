# Plan — ikinci-churn-veri-seti
_Reference: atdd.md_

Frontend-pipeline: tetiklendi, ama kapsam yalnızca null-safe render (U1). Discover statik okumayla yapıldı:
`Overview.tsx:29` başlık rozetinde "IBM Telco" sabit yazılı; `Overview.tsx:101` `by_contract` listesini map'liyor
(boş listede kart boş kalır); `CustomerDetail.tsx` `num(tenure_months)` ve `dec(monthly_charges)` çağırıyor
(null'da "NaN" riski). Design Direction ve Audit uygulanmadı (bug-fix seviyesi). Ayrı frontend_contract.md
yazılmadı; sözleşme atdd.md'deki AC-5'te.

## Files to Modify
| File | Alan | Why | Risk |
|------|------|-----|------|
| src/train_model.py | backend | `PROFILES` sözlüğü (telco, openml_churn): `raw_path`, `load` (CSV/ARFF), `make_ids`, `target`, `drop`, `engineer`, `reasons`, `out_dir`. `main(dataset="telco", sample=None, n_iter=20)` + argparse `--dataset`. AC-6/7 doğrulamaları exit 2 ile yapılır; atomik .tmp yazımı (AC-8) outputs/ profillerinde; log satırı (AC-12). Telco yolu birebir korunur (aynı RANDOM_STATE, aynı adımlar, aynı çıktı dosyaları). metrics.json'a `dataset.name` ve `pr_auc` eklenir. | high (R1) |
| backend/app/main.py | backend | `DATASETS = {"telco": {"dir": ROOT, "name": "IBM Telco Customer Churn", "raw": "data/telco_churn_raw.csv"}, "openml_churn": {"dir": ROOT/"outputs"/"openml_churn", "name": "OpenML Churn", "raw": None}}`. Modül yüklenirken `DATASET = os.environ.get("DATASET", "telco")` doğrulanır, değilse ValueError (AC-9). `load_customers` ve `load_json` aktif dizinden okur; raw yoksa Contract/tenure/MonthlyCharges/TotalCharges sütunları NaN olarak eklenir. Telco alanları NaN olduğunda yanıtta null döner (customers/{id}, postmortem/{id}, `_customer_row.contract`). summary/model-report `dataset.name` aktif profilden gelir; `by_contract` yalnızca Contract dolu satırlardan hesaplanır (yeni sette []). summary ve customers uçları `_load` ile sarılır (AC-10). | high |
| backend/app/labels.py | backend | openml_churn özellik etiketleri (international_plan, number_customer_service_calls, total_day_minutes, …, state_*, area_code_*) | low |
| backend/requirements-dev.txt | devops | `pytest-cov` | low |
| requirements.txt | devops | `scipy` (ARFF okuyucu; sklearn bağımlılığı olsa da açıkça yazılır) | low |
| web/src/lib/types.ts | frontend | `CustomerDetail.contract/tenure_months/monthly_charges: … \| null`, `TopCustomer.contract: string \| null` | low |
| web/src/pages/CustomerDetail.tsx | frontend | null → "—" | low |
| web/src/pages/Overview.tsx | frontend | rozet `data.dataset.name` kullanır; `by_contract` boşsa "Bu veri setinde sözleşme bilgisi yok" | low |
| web/src/pages/CustomerRisk.tsx, LossAnalysis.tsx | frontend | `contract` null → "—" (listede gösteriliyorsa) | low |

## New Files
| File | Alan | Purpose |
|------|------|---------|
| backend/tests/test_training_profiles.py | backend | Unit + smoke: AC-1 (hash kontrolü dahil, kopyalanmış geçici kökte), 4, 6, 7, 8, 11, 12 |
| backend/tests/test_dataset_contract.py | backend | Integration: AC-2, 3, 5, 9, 10. Gerçek çıktıları kullanır, `DATASET` parametrize |
| outputs/openml_churn/* | (üretilmiş) | code-copilot sonrası orkestratör tam eğitimi koşar; çıktılar commit edilir |

## Dependencies
- Backend modülü `DATASET`'i import anında okuyor. Testler bu yüzden `importlib.reload(main)` ile ya da
  `main` içinde bir `set_dataset(name)` yardımcısıyla profili değiştirmeli. **Karar:** `main.py`, aktif profili
  modül global'i `ACTIVE` içinde tutar; testler `monkeypatch.setattr(main, "ACTIVE", main.DATASETS["openml_churn"])`
  yapar ve `load_customers.cache_clear()` + `load_json.cache_clear()` çağırır. AC-9 testi ise
  `monkeypatch.setenv("DATASET", "xyz")` + `importlib.reload` ile yapılır, ardından tekrar reload edilir.
  Bunun gerçek davranışı test ettiği, monkeypatch'in yalnızca profil seçimi olduğu not edilir.
- `load_customers` ve `load_json` @lru_cache'li: profil değişince cache temizlenmeli.
- Eğitim testleri proje köküne YAZMAMALI. `main()`, profilin `out_dir`'ini ve `raw_path`'ini override edebilen
  parametreler alır (`root: Path`). Testler `tmp_path` kullanır.
- AC-1 hash kontrolü: kökteki Telco çıktılarının SHA256'sı testten önce ve sonra karşılaştırılır.
  Tam openml eğitimi testte koşmaz; AC-1'in ROC-AUC ≥ 0.80 kısmı commit edilmiş metrics.json'dan okunur.

## Migration Required?
Hayır (DB yok).

## Risks
- R1 (Telco regresyonu): Telco'yu yeniden eğitmeden doğrulamak için mevcut 27 test + AC-1 hash kontrolü kullanılır.
  train_model.py'nin Telco yolu, refactor sonrası ayrıca bir kez kök kopya üzerinde çalıştırılıp metrics karşılaştırılmaz
  (çok yavaş); bunun yerine kod incelemesiyle "aynı adımlar" doğrulanır. Kabul edilen boşluk.
- Güvenlik kontrolü yolları: `DATASET` beyaz liste kontrolü tek yerde (modül yüklenirken); `--dataset` kontrolü tek yerde (argparse sonrası).

## ECC Danışman Notları
Koşul sağlandı (çok alanlı). Codex yok; yedek ajan çağrısı bu oturumda otomatik izin kontrolünde iki kez takılmıştı.
Kapsamı küçük tutmak için çağrılmadı; boşluk olarak kayda geçti.

## Open Questions
Yok. U1 bu planla çözüldü (null-safe frontend dosyaları listelendi). U2: scipy.io.arff kullanılacak ve
requirements.txt'ye açıkça eklenecek.
