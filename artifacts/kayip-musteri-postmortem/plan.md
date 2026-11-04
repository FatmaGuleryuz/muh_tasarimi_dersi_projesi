# Plan — kayip-musteri-postmortem
_Reference: atdd.md, frontend_contract.md_

Frontend-pipeline: tetiklendi (.tsx dosyaları + Görsel/UI kriteri). Uygulanan adımlar:
- Discover: statik okuma yapıldı (Sidebar, CustomerDetail, api.ts, types.ts).
  Tarayıcıda keşif yapılmadı, bu yüzden "görsel olarak doğrulanmadı".
  Bulunan desen: sayfalar `lib/api.ts`'teki `getJson` sarmalayıcısını kullanıyor;
  hata durumu brick renkli kutu + "Tekrar Dene" ile, yükleme durumu "Yükleniyor…" metniyle gösteriliyor.
  Card, PageHeader, KpiCard, RiskBadge bileşenleri mevcut. Tailwind token'ları: forest, brick, ink, canvas, line.
- Audit: yeni sayfa için yapılmadı; mevcut UI'da bu görevin kapsamına giren bir bulgu yok.
- Design Direction: yeni bir estetik yön seçilmedi. Mevcut tasarım sistemi birebir izleniyor
  (ModelReports/CustomerRisk deseni), çünkü tutarlılık burada yeniden tasarımdan önemli.
- Contract: frontend_contract.md. Mock servis/adaptör eklenmiyor; backend aynı görevde yazılıyor.

## Files to Modify
| File | Alan | Why | Risk |
|------|------|-----|------|
| backend/app/main.py | backend | `GET /api/postmortem` (AC-1,3,6,8) ve `GET /api/postmortem/{id}` (AC-2,4,5,9,10,S1). `outcome` için `Literal`, `limit` için `Query(200, ge=1, le=1000)`. `_load_or_503()` yardımcısı `load_customers()`'ı try/except ile sarar, hata olursa `logger.exception` + 503 (AC-7, S2). Global rank `list(load_json("shap_scores.json")).index(feature)+1` ile hesaplanır, bulunamazsa None. | medium |
| web/src/lib/types.ts | frontend | `Outcome`, `PostmortemSummary`, `PostmortemItem`, `PostmortemList`, `PostmortemDetail` tipleri | low |
| web/src/lib/api.ts | frontend | `fetchPostmortem({outcome?})`, `fetchPostmortemDetail(id)` | low |
| web/src/pages/CustomerDetail.tsx | frontend | `actual_churn` true ise Postmortem bölümü (AC-12) | medium |
| web/src/components/Sidebar.tsx | frontend | "Kayıp Analizi" öğesi (ikon: `SearchX` ya da `History`), Müşteri Riski'nin altına (AC-11) | low |
| web/src/App.tsx | frontend | `kayip-analizi` rotası | low |

## New Files
| File | Alan | Purpose |
|------|------|---------|
| backend/tests/test_postmortem.py | backend | Sözleşmenin her satırı ve AC-S1/S2 (integration, TestClient) |
| web/src/pages/LossAnalysis.tsx | frontend | `/kayip-analizi` sayfası (özet + filtre + liste) |
| web/src/components/OutcomeBadge.tsx | frontend | caught/partial/missed rozeti (iki ekranda ortak) |

## Dependencies
- `load_customers()` ve `load_json()` **ikisi de** `@lru_cache` ile sarılı.
  `conftest.py` yalnızca `load_json`'ın cache'ini temizliyor. `load_customers` monkeypatch'lenen
  testlerde (AC-7, AC-8) ya `main.load_customers` doğrudan monkeypatch edilir ya da
  `load_customers.cache_clear()` çağrılır. Bu bilgi test-copilot'a iletilmeli.
- Endpoint'ler `main.load_customers` adını çalışma anında çözmeli (modül global'i),
  yoksa monkeypatch tutmaz.
- `risk_level`, `HIGH_THRESHOLD`/`MID_THRESHOLD`, `CONTRACTS`, `label_for` yeniden kullanılır.
- `api.ts::getJson` 404'ü sabit "Müşteri bulunamadı" mesajına çeviriyor; 409/503 için `detail` geçiyor.
  Bu yeterli, değişiklik gerekmez.
- Frontend'de test altyapısı yok (atdd e2e=0). UI, verify'da tarayıcı + vision-test ile doğrulanır.

## Migration Required?
Hayır. Değişiklik salt okunur; CSV/JSON dosyaları değişmiyor.

## Risks
- `load_customers` cache'i testler arasında sızabilir (yukarıdaki Dependencies maddesi).
- `/api/customers/{id}` ile `/api/postmortem/{id}` aynı müşteri için tutarlı alanlar dönmeli.
  Ortak bir `_detail_fields(r)` yardımcısı opsiyonel; kopyalamak da kabul edilebilir (ponytail).
- Güvenlik kontrolü yolları:
  - AC-S1: id eşleşmesi tek yoldan geçer (`df["customerID"] == customer_id`). `contains`/regex kullanılmaz.
  - AC-S2/AC-7: 503 sarmalayıcısı **her iki** uçta da `load_customers` ve `load_json` çağrılarını kapsar.
- Görsel/UI işleri (.tsx) olduğu için verify gate'i vision-test AKTİF olacak.

## ECC Danışman Notları
Koşul sağlandı (backend + frontend). Codex CLI bu makinede kurulu değil (exit 127).
Yedek `ecc-planner` ajanı çağrılmak istendi, ancak otomatik izin sınıflandırıcısı iki kez
yanıt vermedi (geçici hata) ve danışman çalıştırılamadı. Danışman notu yok; bu bir boşluk
olarak kayda geçti.

## Open Questions
Yok. atdd.md'deki tek Unknown (sidebar konumu ve ikon) keşifle çözüldü:
"Müşteri Riski"nin altına, lucide `History` ikonuyla.
