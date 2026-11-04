# Code Diff — kayip-musteri-postmortem (green, henüz doğrulanmadı)

Yazan: backend-copilot ve frontend-copilot (Haiku alt-ajanları). Kodu orkestratör satır satır okudu.

## Backend — backend/app/main.py
- `logger`, `OUTCOME_BY_RISK`, `_load()` eklendi. `_load()` (OSError/ValueError/KeyError) yakalar,
  `logger.exception` ile loglar ve 503 "Veri kaynağı okunamadı" döner.
- `GET /api/postmortem` (outcome Literal, limit 1..1000, varsayılan 1000): summary filtresiz hesaplanır,
  items probability'ye göre artan sıralanır.
- `GET /api/postmortem/{customer_id}`: eşleşme `==` ile yapılır; yoksa 404, kayıp değilse 409; rank shap anahtar sırasından,
  NaN total_charges → None.
- Mevcut uçlar değişmedi.
- Sınırlama: OSError/ValueError/KeyError dışındaki bir yükleme hatası 503 değil 500 döner.

## Frontend
- Yeni: `web/src/pages/LossAnalysis.tsx`, `web/src/components/OutcomeBadge.tsx`
- Değişen: `lib/types.ts`, `lib/api.ts`, `pages/CustomerDetail.tsx` (PostmortemSection yalnızca actual_churn true iken mount ediliyor),
  `components/Sidebar.tsx` (Kayıp Analizi, History ikonu), `App.tsx` (rota).
- `vite build` exit 0 (alt-ajanın raporu). `tsc --noEmit` exit 2: hata önceden var olan Button `icon` prop tipinden
  geliyor ve tüm sayfalarda görülüyor; yeni kodda tip hatası yok (alt-ajanın raporu, orkestratör tekrar çalıştırmadı).

## Doğrulanmayanlar
- pytest çalıştırılamadı: `venv/` başka bir kullanıcı yolunda (`C:\Users\YUSUF ÇİNAR\...Python3.13`) oluşturulmuş ve kırık.
  Sistem Python 3.11'de pandas/fastapi/pytest kurulu değil.
- Görsel doğrulama (vision-test) verify adımında yapılacak.
