# Code Diff — model-ve-raporlar-sayfasi (green step)

## Değiştirilen dosyalar
- `backend/app/main.py` — `_model_rows()` yardımcısı eklendi (summary() refactor, davranış aynı), yeni `GET /api/model-report` ucu eklendi.
- `web/src/lib/types.ts` — `ModelReport` interface'i eklendi.
- `web/src/lib/api.ts` — `fetchModelReport()` eklendi; `getJson` düzeltildi (503/diğer hatalarda `detail` mesajı okunur, 404 davranışı korundu).
- `web/src/App.tsx` — `/model-ve-raporlar` route'u `ComingSoon`'dan `ModelReports`'a değişti, diğer route'lar/import'lar aynen kaldı.

## Yeni dosya
- `web/src/pages/ModelReports.tsx` — model karşılaştırma kartları, hedef doğrulama şeridi, dataset künyesi, ilk 10 + "Tümünü Göster (N)" SHAP listesi, Overview ile aynı hata deseni.

## AC → Uygulama eşlemesi
| AC | Durum |
|---|---|
| AC-1 (3 model + en iyi + hedef) | ✅ `_model_rows` + `best`/`best_label`/`target`/`target_met`, frontend'de kart grid + hedef şeridi |
| AC-2 (tüm SHAP, azalan sıra) | ✅ backend `sorted(..., reverse=True)`, frontend ilk 10 + genişlet (tam 51 öğe DOM'a gelir) |
| AC-3 (backend erişilemez) | ✅ Overview ile aynı hata kartı deseni |
| AC-4 (boş drivers) | ✅ backend `drivers: []` + 200, frontend "Henüz değişken önem skoru yok" |
| AC-5 (dosya eksik → 503 + detay) | ✅ backend 503 + tam `detail` mesajı, frontend artık `getJson` düzeltmesiyle bu mesajı gösteriyor |

## Doğrulama durumu
Kod okunarak (Read) incelendi, testlerin beklediği davranışla eşleşiyor.
Testler henüz ÇALIŞTIRILMADI (bu `verify` adımına ait) — pytest/httpx
kurulu değil, kurulum + çalıştırma sıradaki adımda yapılacak. Frontend
tarayıcıda henüz manuel test edilmedi — bu da `verify`/Validate adımında.

## Kalan sınırlamalar
Yok (plan.md'deki tüm maddeler uygulandı; `getJson` düzeltmesi dahil).
