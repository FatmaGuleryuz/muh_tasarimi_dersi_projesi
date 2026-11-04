# Code Diff — ikinci-churn-veri-seti

Yazan: backend-copilot ve frontend-copilot (Haiku). Orkestratör main.py'deki DATASET bloğunu okudu, testleri ve
tam eğitimi kendisi çalıştırdı.

## Backend / eğitim
- `src/train_model.py`: `PROFILES` (telco, openml_churn), ARFF yükleyici (scipy.io.arff), `OC-%05d` ID'leri,
  phone_number düşürülüyor, state/area_code one-hot, türev toplamlar. `main(dataset, root, sample, n_iter) -> int`,
  argparse `--dataset`. outputs/ profillerinde atomik `.tmp` yazımı. metrics.json'a `dataset.name` ve `pr_auc` eklendi.
  Son log satırı `Eğitim tamamlandı: profil=… ROC-AUC=…`.
  - Alt-ajanın yaptığı kapsam dışı küçük düzeltme: kurulu shap sürümü RandomForest için 3 boyutlu dizi döndürüyor.
    Pozitif sınıf `[:, :, 1]` ile alınıyor. Bu düzeltme olmadan RF en iyi model olduğunda eğitim kırılıyordu (Telco'yu da etkiler).
- `backend/app/main.py`: `DATASETS` + `ACTIVE` (env `DATASET`, beyaz liste, import anında ValueError). Telco `dir` değeri None
  bırakıldı ve çağrı anında `ROOT` olarak çözülüyor; böylece mevcut `main.ROOT` monkeypatch testi çalışmaya devam ediyor.
  Null yardımcıları `_opt`/`_contract`. summary, customers ve customers/{id} uçları `_load` ile sarıldı (AC-10).
  - Yan etki: summary'de metrics.json eksikse artık 500 değil 503 dönüyor (AC-10 ile uyumlu).
- `backend/app/labels.py`: openml için Türkçe etiketler.
- `requirements.txt` (+scipy), `backend/requirements-dev.txt` (+pytest-cov).

## Frontend
`types.ts` (contract/tenure_months/monthly_charges `| null`), `CustomerDetail.tsx`, `Overview.tsx` (rozette dataset.name kullanılıyor,
by_contract boşsa boş durum mesajı), `CustomerRisk.tsx`. tsc hata sayısı değişikliklerden önce de sonra da 11 (önceden var olan Button tip hatası).

## Üretilmiş çıktılar — outputs/openml_churn/
`python src/train_model.py --dataset openml_churn` → exit 0, **53 sn**. En iyi model random_forest, test ROC-AUC **0.9288**
(xgb 0.9251, lr 0.8197). Dosyalar: model.joblib (5.2 MB), encoder.joblib, metrics.json, shap_scores.json, shap_summary.png, test_customers.csv (1000 satır).
Kökteki Telco çıktılarına dokunulmadı (SHA256 testi geçiyor).
