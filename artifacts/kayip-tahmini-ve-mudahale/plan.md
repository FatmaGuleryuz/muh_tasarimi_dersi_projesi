# Plan — kayip-tahmini-ve-mudahale
_Reference: atdd.md, designs/03_kayip_tahmini, designs/04_mudahale_planlari_

Frontend-pipeline: uygulandı. Discover/Design Direction bu konuşmada yapıldı (Stitch tasarımları kullanıcı onaylı);
contract atdd.md "Backend sözleşmesi" bölümünde. Görsel doğrulama verify'da tarayıcıyla (1440 ve 390 genişlik).

## Keşif bulguları
- Telco en iyi modeli **xgboost**, ölçeklenmemiş X kullanıyor (scaler yalnız LR için). `encoder.joblib`:
  `{"scaler", "best_name", "feature_names"(51)}`.
- Özellikler: SeniorCitizen, tenure, MonthlyCharges, TotalCharges, AvgMonthlySpend(=TotalCharges/(tenure+1)),
  NumAdditionalServices (8 hizmet sütununda "Yes" sayısı), one-hot kategorikler, tenure_group (0-12/13-24/25-48/49-72).
- `src/train_model.py`: `engineer_features(df)` ve `REASON_SOLUTIONS`, `DEFAULT_SOLUTION` yeniden kullanılabilir
  (importlib ile dosyadan yükleme ya da doğrudan import `src.train_model`).
- Frontend: Layout.tsx (`pl-64` + Outlet), index.css body `bg-canvas`, index.html yalnız Plus Jakarta Sans yüklüyor.
  App.tsx'te `kayip-tahmini` ve `mudahale-planlari` rotaları `ComingSoon`.

## Files
| File | Alan | Neden |
|---|---|---|
| backend/app/scenario.py (yeni) | backend | `build_row(payload)->DataFrame[feature_names]`: ham Telco'dan mod/medyan varsayılanlarla tam satır kur → `engineer_features` → one-hot → `reindex(feature_names, fill_value=0)`. `explain(row)`: SHAP TreeExplainer (lru_cache ile tek kez kurulur), yalnız formdan türeyen özellik sütunlarını (contract/tenure/MonthlyCharges/TotalCharges/AvgMonthlySpend/InternetService/TechSupport/OnlineSecurity/PaymentMethod/SeniorCitizen/tenure_group/NumAdditionalServices) döndürür. |
| backend/app/main.py | backend | `POST /api/predict` (Pydantic model, `extra="forbid"`, Literal enum'lar, `conint(0,72)`, `confloat(ge=18, le=120, allow_inf_nan=False)`), Telco dışı → 409. `GET /api/intervention-plans`, `GET /api/intervention-plans/export.csv` (CSV injection kaçışı). Hepsi `_load` ile 503. |
| backend/app/labels.py | backend | gerekirse tenure_group/NumAdditionalServices etiketleri |
| backend/tests/test_predict.py, test_intervention_plans.py (yeni) | backend | AC-1..8, AC-S1, AC-S2 |
| web/index.html | frontend | Fraunces fontu |
| web/tailwind.config.js | frontend | `fontFamily.serif: ["Fraunces", ...]` |
| web/src/index.css, web/src/components/Layout.tsx | frontend | arka plan katmanları (gren SVG data URI, ızgara, radyal geçişler) |
| web/src/lib/types.ts, api.ts | frontend | `PredictRequest/Response`, `InterventionPlans`, `predict()` (POST), `fetchInterventionPlans()`, `interventionExportUrl()` |
| web/src/pages/ChurnPrediction.tsx, InterventionPlans.tsx (yeni) | frontend | AC-9..11 |
| web/src/App.tsx | frontend | iki rota |

## Migration
Yok.

## Risks
- `api.ts::getJson` yalnızca GET; POST için ayrı küçük fonksiyon (aynı hata eşlemesi).
- SHAP yükleme süresi ilk istekte yavaş olabilir; explainer önbelleğe alınır.
- Güvenlik yolları: predict tek giriş noktası (Pydantic); export action eşleşmesi `==` ile tek yerde.

## ECC Danışman Notları
Koşul var (çok alanlı) ama Codex yok ve ajan tipleri bu oturumda değişti; çağrılmadı.

## Open Questions
Yok (U1 arka plan yoğunluğu verify'da kullanıcıya gösterilecek).
