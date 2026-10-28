# Plan — model-ve-raporlar-sayfasi
_Reference: atdd.md_

Frontend-pipeline: tetikleyici var (`.tsx`), ama Design Direction adımı
atlandı — mevcut, tutarlı tasarım sistemi (Card/Button/PageHeader/
Yetkin360 teması) aynen yeniden kullanılıyor, yeni UI yönü gerekmiyor.
Discover/Audit de atlandı (bu sayfa yeni, henüz denetlenecek bir mevcut UI
yok); Validate/Review, kod yazıldıktan sonra Playwright+vision-test ile
yapılacak (bkz. "Validate" notu en altta).

ECC Danışman Notları: `ecc-planner` agent'ı çağrıldı (görev backend+frontend
alanlarına yayıldığı için). 10 madde döndürdü, hepsi kabul edildi ve
aşağıdaki plana işlendi (reddedilen öneri yok — hepsi atdd.md kapsamı
içindeydi, scope creep değildi):
1. pytest/httpx eksik → `backend/requirements-dev.txt` eklenecek.
2. `load_json` `FileNotFoundError`/`JSONDecodeError` yakalamıyor → yeni uç
   kendi try/except'iyle 503'e çevirecek, `load_json`'ın kendisi değişmeyecek.
3. `@lru_cache` test tuzağı → testler `load_json.cache_clear()` fixture'ı
   kullanacak.
4. `dataset.test_customers` CSV'den geliyor → bu uçta kullanılmayacak
   (atdd.md Unknowns'ta çözüldü, sadece metrics.json'daki alanlar).
5. `shap_scores.json` dict, liste değil → `drivers` backend'de açıkça
   `sorted(..., reverse=True)` ile üretilecek, dosya sırasına güvenilmeyecek.
6. `api.ts`'teki `getJson` 503 detail mesajını göstermiyor → düzeltilecek,
   404 dalı korunacak.
7. Model satırı üretimi tekrarlanıyor (`summary()` içinde satır içi) →
   `_model_rows(metrics)` yardımcısına çıkarılacak, iki uçta da kullanılacak.
8. 51 değişken gösterimi → ilk 10 + "Tümünü Göster (N)" (atdd.md'ye işlendi).
9. Uygulama sırası önerisi → aşağıda "Uygulama Sırası" olarak alındı.
10. Proxy/ağ hatası → Overview'daki `catch`→`setError` deseni yeterli, ek dal yok.

## Files to Modify
| File | Why | Alan | Risk |
|------|-----|------|------|
| `backend/app/main.py` | Yeni `GET /api/model-report` ucu eklenir: `metrics.json`+`shap_scores.json` okur (`load_json` ile), `FileNotFoundError`/`json.JSONDecodeError`'ı yakalayıp `HTTPException(503, "Model çıktıları bulunamadı; train_model.py çalıştırın")` fırlatır; `drivers` `sorted(shap.items(), key=lambda kv: kv[1], reverse=True)` ile üretilir; model satırları mevcut satır-içi listeden `_model_rows(metrics)` yardımcısına çıkarılıp hem `summary()` hem yeni uçta kullanılır (davranış değişmez, sadece tekrar kaldırılır) | backend | low |
| `backend/requirements.txt` | Üretim bağımlılığı değişmez — dokunulmaz (not: dev bağımlılıkları ayrı dosyada, bkz. New Files) | backend | — |
| `web/src/lib/types.ts` | `ModelReport` tipi eklenir: `{ models: ModelMetrics[]; best: string; best_label: string; target: number; target_met: boolean; dataset: { name: string; rows: number; churn_rate: number }; drivers: { feature: string; label: string; score: number }[] }` — mevcut `ModelMetrics` tipi yeniden kullanılır, yeni bir model-satırı tipi tanımlanmaz | frontend | low |
| `web/src/lib/api.ts` | `fetchModelReport()` eklenir (`getJson<ModelReport>("/api/model-report")` deseniyle). `getJson` düzeltilir: hata yanıtında `res.json()`'dan `detail` alanını okumaya çalışır, okunamazsa mevcut `API hatası (${status})` mesajına düşer — 404 özel dalı (CustomerDetail için) korunur | frontend | medium (ortak yardımcıya dokunuyor — CustomerDetail'in 404 davranışı manuel yeniden test edilecek) |
| `web/src/App.tsx` | `/model-ve-raporlar` route'u `<ComingSoon title="Model ve Raporlar" />`'dan `<ModelReports />`'a değişir. Diğer `ComingSoon` kullanımları (`kayip-tahmini`, `mudahale-planlari`, `*`) KALIR — import silinmez | frontend | low |

## New Files
| File | Purpose |
|------|---------|
| `web/src/pages/ModelReports.tsx` | Yeni sayfa: 3 model karşılaştırma kartı (Card bileşeni, en iyi model + hedef rozeti vurgulu), dataset künye kartı, SHAP driver listesi (ilk 10 + "Tümünü Göster (N)" genişletme, Overview'daki bar-list deseniyle). Hata durumu Overview/CustomerRisk ile aynı desen (`error` state + "Tekrar Dene" butonu) |
| `backend/requirements-dev.txt` | `pytest`, `httpx` — sadece test için, üretim `requirements.txt`'e karışmaz |
| `backend/tests/__init__.py` | Boş, pytest paket keşfi için |
| `backend/tests/conftest.py` | `load_json.cache_clear()` fixture'ı (her testten önce) + `monkeypatch.setattr(main, "ROOT", tmp_path)` yardımcı fixture'ı (dosya-eksik testi için, gerçek `metrics.json`/`shap_scores.json`'a DOKUNULMAZ) |
| `backend/tests/test_model_report.py` | 3 test: (a) happy path → 200, `len(drivers) == len(shap_scores.json'daki anahtar sayısı)`, azalan sıralı; (b) `shap_scores.json` boş dict → 200 + `drivers: []`; (c) dosyalardan biri `tmp_path`'te yok → 503 |

## Dependencies
- `load_json(name: str) -> dict` (mevcut, `@lru_cache`) — yeni uç bunu çağırır,
  kendisi DEĞİŞTİRİLMEZ (başka uçlar da kullanıyor).
- `MODEL_LABELS` sözlüğü (mevcut) — `_model_rows` yardımcısında yeniden kullanılır.
- `label_for()` (`labels.py`, mevcut) — `drivers`'ın `label` alanı için.
- Frontend: `Card`, `Button`, `PageHeader` bileşenleri (mevcut, değişmez);
  `dec`/`pct`/`num` format fonksiyonları (`lib/format.ts`, mevcut).

## Migration Required?
Hayır — şema/veri değişikliği yok, sadece yeni bir salt-okunur HTTP ucu ve
yeni bir frontend sayfası.

## Risks
- (atdd.md'den taşındı) Kabul edilen risk: `/api/*` uçlarında auth/rate-limit
  yok — lokal tek-kullanıcılı akademik araç olduğu için kabul edildi.
- `getJson` değişikliği ortak bir yardımcıya dokunuyor — CustomerDetail
  sayfasının 404 davranışı (AC-7, önceki görev) bu değişiklikten sonra
  manuel olarak yeniden doğrulanmalı (regresyon riski düşük ama sıfır değil).
- `@lru_cache` testler arası veri sızdırabilir — `conftest.py`'deki
  `cache_clear()` fixture'ı atlanırsa testler yanlış pozitif/negatif verir;
  `test-copilot`'un bu fixture'ı gerçekten kullandığını `code-copilot`/
  `verify` doğrulamalı.

## ECC Danışman Notları
Yukarıda (plan.md başında) özetlendi — 10 madde, hepsi kabul edildi, reddedilen yok.

## Open Questions
Yok — atdd.md'nin Unknowns bölümündeki 2 madde (51 değişken gösterimi,
dataset künye kaynağı) bu adımda ecc-planner önerisiyle çözülüp atdd.md'ye
geri yazıldı (bkz. atdd.md Unknowns bölümü, "Çözüldü" notlarıyla).

## Uygulama Sırası (ecc-planner önerisi, kabul edildi)
1. `backend/requirements-dev.txt` + `backend/tests/` iskeleti
2. `backend/app/main.py` — yeni uç (503 eşlemesi + sıralama dahil), pytest a/b/c yeşil olana kadar
3. `web/src/lib/types.ts` + `web/src/lib/api.ts` (`getJson` detail düzeltmesi dahil)
4. `web/src/pages/ModelReports.tsx`
5. `web/src/App.tsx` route değişikliği (en son — yarım sayfa yayına çıkmasın)

## Validate (frontend-pipeline, kod yazıldıktan sonra)
`verify` adımı sırasında/sonrasında: Playwright ile desktop (1280px) ve
mobile (375px) ekran görüntüsü al, `read_console_messages` ile konsol
hatası kontrol et, `vision-test` ile (varsa) layout/okunabilirlik
bulgusu çıkar. Sadece kanıtlanan sorun varsa tek bir iterasyon turu yapılır.
