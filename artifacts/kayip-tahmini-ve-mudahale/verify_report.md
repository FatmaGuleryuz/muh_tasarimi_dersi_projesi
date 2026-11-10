# Verify Report — kayip-tahmini-ve-mudahale

| # | Gate | Sonuç | Kanıt |
|---|---|---|---|
| 1 | Dosya konumu | PASS | git status: main.py + 9 web dosyası değişti; scenario.py, 2 test, 2 sayfa, designs/03-04 yeni |
| 2 | Build | PASS (vite) / önceden var olan FAIL (tsc) | `vite build` başarılı; tsc 11 hata, değişiklik öncesiyle aynı (Button icon tipi) |
| 3 | Supabase | N/A | yok |
| 4 | Lint | N/A | config yok |
| 5 | Type check | önceden var olan FAIL | gate 2 |
| 6 | Testler | PASS | `pytest backend/tests` → **127 passed**; kapsam main.py %95, scenario.py %98, toplam %96 (hedef %85) |
| 7 | E2E (manuel, Browser pane) | PASS | Kayıp Tahmini: varsayılan senaryo %78 → 2 yıllık sözleşmede %26; spektrum, rozet, SHAP ve İlk hamle güncelleniyor; "Sözleşme: Aylık değil −1,25" etiketi doğru. Müdahale Planları: 669 / 3 / %67,9, ilk plan açık, nokta şeridi, ilk 5 müşteri, "CSV indir (560 kayıt)". Konsol hatası yok. |
| 8-9 | Lighthouse / a11y | N/A | araç yok; kontroller gerçek button/select, segmentler role=radio + aria-checked, mobil menü odak yönetimli |
| 10 | Güvenlik taraması | INCONCLUSIVE | security-scan aracı kurulu değil; AC-S1/AC-S2 testlerle doğrulandı |
| 11 | AI review | PENDING (red-team) | |
| 12 | Görsel | PASS (manuel) | 1440px: tasarım 03/04 ile uyumlu, kutusuz düzen, arka plan katmanları görünür. 390px: iki sayfada scrollWidth == 390 (yatay kaydırma yok), mobil menü açılıp kapanıyor |
| 13 | DAST | N/A | ZAP yok |
| 14 | İnsan onayı | PENDING | |

## Doğrulama sırasında bulunup düzeltilenler
1. SHAP sürücüleri log-odds biriminde olduğu halde yüzde gösteriliyordu; senaryoda 0 olan one-hot sütunlar yanıltıcı etiketleniyordu ("Sözleşme: Aylık" — müşteri 2 yıllıkken). Düzeltildi: etiket "… değil", değer işaretli log-odds (+0,29), açıklama notu.
2. Uygulama 390px'te kullanılamıyordu (sabit 256px sidebar; tüm sayfalarda önceden var olan sorun). Düzeltildi: lg altında gizli sidebar + menü butonu + overlay.
3. Testlerde 3 sorun (share yuvarlama toleransı, roc_auc yuvarlama, fixture'da yamalı fonksiyonda cache_clear) — test tarafında düzeltildi.

## Notlar
- Backend sunucusu otomatik yeniden yüklenmiyor (uvicorn --reload yok); kod değişikliğinden sonra yeniden başlatılmalı.
- Frontend alt-ajanı Sonnet ile çalıştı (görsel kalite için); diğerleri Haiku.

## Red-team sonrası düzeltme turu (2026-11-10)
- `pytest backend/tests` → **134 passed**; tsc 11 (değişmedi); vite build başarılı.
- Tarayıcı: ücret alanına klavyeyle "50" yazılabiliyor; internet "Yok" iken teknik destek/çevrimiçi güvenlik pasif ve notlu;
  SHAP etiketleri "Çevrimiçi güvenlik: internet hizmeti yok" (önceki "…: var" hatası düzeldi); "Sözleşme: Aylık değil" doğru.

## Refactor Aday Kontrolü
Aday yok: yeni kod tek modül (scenario.py) + uç başına tek fonksiyon; tekrar yok.
