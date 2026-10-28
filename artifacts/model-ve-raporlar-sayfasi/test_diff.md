# Test Diff — model-ve-raporlar-sayfasi (red step)

## Oluşturulan dosyalar
- `backend/requirements-dev.txt` — pytest, httpx
- `backend/tests/__init__.py` — boş (pytest paket keşfi)
- `backend/tests/conftest.py` — repo kökünü sys.path'e ekler, autouse fixture ile her testten önce/sonra `load_json.cache_clear()` çağırır
- `backend/tests/test_model_report.py` — 3 test, `GET /api/model-report` henüz yok, beklenen durum: kırmızı (404)

## AC → Test eşlemesi
| AC | Test fonksiyonu | Doğrulama |
|---|---|---|
| AC-1 | `test_happy_path_returns_all_models_and_sorted_drivers` | 3 model + 4 metrik tam eşleşme, best/best_label/target/target_met, dataset (sadece metrics.json'dan) |
| AC-2 | `test_happy_path_returns_all_models_and_sorted_drivers` | `len(drivers) == len(shap_scores.json)`, azalan sıra, `label_for()` eşleşmesi |
| AC-4 | `test_empty_drivers_returns_empty_list_not_error` | `shap_scores.json` boş dict → 200 + `drivers: []` |
| AC-5 | `test_missing_files_returns_503` | dosyalar `tmp_path`'te yok → 503 + tam `detail` mesajı |

Davranış Sözleşmesi satır 2 (backend'e ulaşılamıyor) frontend kapsamında —
backend testi yok, atdd.md'de de sadece a/b/c (bu 3 test) öngörülmüştü.

## Durum
Henüz çalıştırılmadı (implementasyon yok — `verify` adımında `code-copilot`
sonrası çalıştırılacak). Beklenen: `code-copilot`'tan önce 404/import
hatasıyla kırmızı.
