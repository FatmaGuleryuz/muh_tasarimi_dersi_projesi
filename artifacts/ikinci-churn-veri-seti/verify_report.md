# Verify Report — ikinci-churn-veri-seti

| # | Gate | Result | Evidence / Reason |
|---|------|--------|--------------------|
| 1 | Dosya konumu | PASS | git status: 5 backend/src, 4 web dosyası değişti; 2 yeni test dosyası; outputs/openml_churn/ (6 dosya); data/openml_churn.arff |
| 2 | Build | PASS (backend) / önceden var olan FAIL (tsc) | Backend import OK; frontend tsc hata sayısı önce de sonra da 11 (Button icon tipi, bu görevden değil) |
| 3 | Supabase | N/A | yok |
| 4 | Lint | N/A | config yok |
| 5 | Type check | önceden var olan FAIL | gate 2 |
| 6 | Testler | PASS | `pytest backend/tests -q` → **63 passed**; coverage: main.py %93, train_model.py %87, toplam %84 (hedef %80) |
| 7 | E2E (manuel) | PASS | DATASET=openml_churn: Genel Bakış'ta "OpenML Churn · 1.000 test müşterisi", sözleşme kartında boş durum mesajı; OC-02874 detayında 4 Telco alanı "—", Postmortem ve Türkçe SHAP etiketleri doğru. Bilinmeyen id (OC-00010, eğitim setinde) 404 "bulunamadı". |
| 8-9 | Lighthouse / a11y | N/A | araç kurulu değil |
| 10 | Güvenlik taraması | INCONCLUSIVE | security-scan runner'ı bu makinede yok |
| 11 | AI review | PENDING (red-team) | |
| 12 | Görsel | PARTIAL | vision-test yok (Codex yok); ekran görüntüsü doğrudan incelendi, masaüstünde layout düzgün |
| 13 | DAST | N/A | AC-S yok |
| 14 | İnsan onayı | PENDING | |

## Benchmark
- ROC-AUC 0.9288 (hedef ≥ 0.80) ✓; PR-AUC metrics.json'da.
- Tam eğitim süresi 53 sn (hedef ≤ 10 dk) ✓.
- Tekrarlanabilirlik (AC-11) smoke testte ✓.

## Notlar
- Eğitim logu ve UI "hedef 0,84 karşılandı" gösteriyor: `TARGET_ROC_AUC` profil başına değil, global 0.84. atdd'deki
  openml eşiği (0.80) yalnızca testte uygulanıyor. Sonuç hedefin üstünde olduğu için etkisi yok, ama tutarsızlık var.
- outputs/openml_churn/model.joblib 5.2 MB; commit'e girecek (R2).

## Refactor Aday Kontrolü
Refactor adayı: `src/train_model.py::_train` uzun (eski main gövdesi taşındı). Ölçülebilir bir tekrar yok, davranışı koruyor.
Kullanıcıya isteğe bağlı olarak önerilir; otomatik çalıştırılmadı.
