# Code Diff — kayip-tahmini-ve-mudahale

Yazanlar: general-purpose alt-ajanlar (backend/test Haiku, frontend Sonnet). Orkestratör testleri ve tarayıcıyı kendisi çalıştırdı.

## Backend
- `backend/app/scenario.py` (yeni): `build_row` (8 alanlı senaryo → eğitimle aynı özellik hattı, eksik alanlar mod/medyan, tenure 0'da TotalCharges eğitim medyanı), `explain` (önbellekli TreeExplainer, yalnız formdan türeyen özellikler, ilk 5, etiket kuralı: 0 değerli "_No" sütunu → gruptaki seçili kardeşin etiketi; diğer 0 → "… değil").
- `backend/app/main.py`: `POST /api/predict` (sıkı Pydantic şema; Telco dışı 409), `GET /api/intervention-plans`, `GET /api/intervention-plans/export.csv` (tam eşleşme, CSV injection kaçışı = + - @ \t \r); `_load` log mesajı genelleşti.
- `backend/requirements.txt`: numpy, joblib, scikit-learn, xgboost, shap, matplotlib, scipy eklendi.

## Frontend
- Yeni sayfalar: `ChurnPrediction.tsx` (/kayip-tahmini), `InterventionPlans.tsx` (/mudahale-planlari) — designs/03 ve 04'e göre.
- `index.css` katmanlı arka plan; `index.html` + `tailwind.config.js` Fraunces; `api.ts`/`types.ts` yeni tipler ve çağrılar; `App.tsx` rotalar.
- `Layout.tsx`/`Sidebar.tsx`/`PageHeader.tsx`: lg altında gizli sidebar, menü butonu, perde, Escape, odak yönetimi, açıkken içerik inert (AC-11 için; tüm sayfaları etkiler).

## Testler
- `backend/tests/test_predict.py`, `backend/tests/test_intervention_plans.py` (yeni). Toplam 134 test geçiyor.

## Tasarım kaynakları
- `designs/03_kayip_tahmini/`, `designs/04_mudahale_planlari/`, `designs/DESIGN.md` (Stitch export'u).
