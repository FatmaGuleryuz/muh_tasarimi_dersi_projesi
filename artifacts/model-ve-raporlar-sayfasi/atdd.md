---
task_slug: model-ve-raporlar-sayfasi
jira_id: null
threat_model: done
priority: medium
coverage_target: null
performance_target: "sayfa <2sn'de yüklenir (lokal)"
memory_target: null
test_strategy:
  unit: 0
  integration: 100
  e2e: 0
affected_modules:
  - backend/app/main.py
  - web/src/pages/ModelReports.tsx
  - web/src/lib/types.ts
  - web/src/lib/api.ts
  - web/src/App.tsx
---

# ATDD — model-ve-raporlar-sayfasi

## Jira Kaynağı
Jira'ya bağlı değil — kullanıcı kararı: "musteri-kaybi-karar-destek" akademik
projesi için Jira kullanılmayacak, yerel `atdd.md` tek kaynak kalacak.

## Persona
Proje ekibi (76. Proje Grubu) ve dersi değerlendiren hoca/jüri — modelin nasıl
seçildiğini ve neye dayandığını gösteren bir şeffaflık/rapor sayfası, akademik
sunumda kanıt olarak kullanılır (Opus alt-ajanı tarafından yanıtlandı).

## Hedef (Neden)
Genel Bakış sayfası sadece özet metrik (en iyi modelin ROC-AUC'si) ve ilk 8
SHAP değişkenini gösteriyor. Bu sayfa "model neden seçildi, hangi 3 model
karşılaştırıldı, hangi değişkenler kayba ne kadar katkı veriyor" sorusunu
eksiksiz yanıtlar: 3 modelin tam metrik karşılaştırması + hedef doğrulama
rozeti + veri seti künyesi + TÜM SHAP değişken sıralaması (51 değişken, sadece
ilk 8 değil) (Opus alt-ajanı tarafından yanıtlandı).

## User Story
As a proje ekibi üyesi / değerlendirici
I want 3 modelin tam karşılaştırmasını ve tüm SHAP neden sıralamasını tek
sayfada görmek
So that modelin neye dayandığını doğrulayabileyim ve sunumda kanıt gösterebileyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given backend ayakta ve `metrics.json`/`shap_scores.json` diskte
   mevcut, When `/model-ve-raporlar` sayfası açılır, Then 3 modelin
   (Lojistik Regresyon, Random Forest, XGBoost) ROC-AUC/Precision/Recall/F1
   değerleri kart/tablo halinde gösterilir, en iyi model ve hedef durumu
   (0,84 karşılandı/karşılanmadı) vurgulanır.
2. [Critical] Given aynı koşullar, When sayfa açılır, Then `shap_scores.json`
   dosyasındaki **tüm** değişkenler (şu an 51 adet, sabit değil — dosyadaki
   gerçek sayı kadar) skora göre azalan sırada listelenir, sadece ilk 8 ile
   sınırlı kalınmaz.
3. [High] Given backend'e ulaşılamıyor (sunucu kapalı/ağ hatası), When sayfa
   açılır, Then Overview/CustomerRisk sayfalarındaki aynı desen kullanılır:
   "Sunucuya ulaşılamadı" hata kartı + "Tekrar Dene" butonu gösterilir,
   sayfa çökmez.
4. [Medium] Given `shap_scores.json` boş bir liste içeriyor (teorik — normal
   koşulda `train_model.py` her zaman doldurur), When sayfa açılır, Then
   model kartları normal gösterilir, SHAP bölümünde "Henüz değişken önem
   skoru yok" boş-durum mesajı gösterilir (hata değil).
5. [Medium] Given `metrics.json` veya `shap_scores.json` dosyası diskte yok
   ya da bozuk (JSON parse hatası), When `/api/model-report` çağrılır, Then
   backend 503 + `{"detail": "Model çıktıları bulunamadı; train_model.py
   çalıştırın"}` döner, frontend bunu hata kartı olarak gösterir (3 ve 4'ten
   ayrı, gerçek bir yapılandırma hatası).

## Threat Model
Çağrıldı — tetikleyici "yeni bir HTTP ucu" (`GET /api/model-report`) nedeniyle
STRIDE-lite analizi yapıldı. Sonuç: uç parametre almıyor (tampering yüzeyi
yok), kimlik/yetki kavramı yok (spoofing/elevation N/A), yazma yapmıyor
(repudiation N/A), döndürdüğü veri agregat model metrikleri ve değişken
isimleri — tek tek müşteri verisi içermiyor (info disclosure düşük), CORS
sadece `localhost:5173`'e açık ve uvicorn varsayılan host'u (`127.0.0.1`)
ile ağa kapalı. Gerçek, testedilebilir bir `AC-S<n>` üretecek somut bir açık
bulunmadı — bu yüzden ek güvenlik kriteri eklenmedi; kabul edilen risk
Risks bölümünde kayıtlı.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path | `200 {"models":[{"key":"xgboost","label":"XGBoost","roc_auc":0.847476,"precision":0.5227,"recall":0.7995,"f1":0.6321}, ...], "best":"xgboost", "best_label":"XGBoost", "target":0.84, "target_met":true, "dataset":{"name":"IBM Telco Customer Churn","rows":7043,"churn_rate":0.2654}, "drivers":[{"feature":"Contract_Month-to-month","label":"Sözleşme: Aylık","score":0.7015}, ...51 öğe, azalan sıralı...]}` | yok (salt okunur) | Model karşılaştırma kartları + hedef rozeti + dataset künyesi + ilk 10 SHAP değişkeni + "Tümünü Göster (51)" | AC-1, AC-2 |
| 2 | Backend'e ulaşılamıyor | fetch network hatası (status yok) | yok | "Sunucuya ulaşılamadı" kartı + Tekrar Dene | AC-3 |
| 3 | `drivers` boş liste | `200 {..., "drivers": []}` | yok | Model kartları normal, SHAP bölümünde "Henüz değişken önem skoru yok" | AC-4 |
| 4 | `metrics.json`/`shap_scores.json` yok veya bozuk | `503 {"detail": "Model çıktıları bulunamadı; train_model.py çalıştırın"}` | yok | Hata kartı + detay mesajı + Tekrar Dene | AC-5 |

Kısmi başarı: Uygulanmayan satır — uç salt-okunur tek bir GET, kısmi bir
yazma/işlem içermiyor; ya tam veri döner ya da 503 hatası, ara bir durum yok.
Hiçbir şey yapılamadı ama hata da yok: Uygulanmayan satır — dosyalar
okunamazsa (4. satır) her zaman açık bir 503 döner, sessiz boş yanıt yok.
Boş sonuç ↔ hata ayrımı: `drivers: []` (3. satır, veri gerçekten boş — hata
değil) ile 503 (4. satır, dosya hiç yok/bozuk — yapılandırma hatası) backend
tarafında açıkça ayrılır; ikisi de aynı "boş" görünümü vermez.

## Test Strategy
Unit: 0% — bu görevde saf transformasyon dışında birim test edilecek karmaşık mantık yok.
Integration: 100% — backend için 2-3 hafif pytest testi (FastAPI `TestClient`):
  (a) happy path → 200 + `len(drivers) == len(shap_scores.json)` ve azalan sıralı,
  (b) `drivers` boş liste → 200 + boş dizi,
  (c) dosya eksik/bozuk (monkeypatch veya geçici dizin) → 503.
E2E: 0% — frontend bu turda otomatik test altyapısı (vitest) kurulmadan,
önceki sayfalarla (Overview/CustomerRisk) tutarlı şekilde manuel tarayıcı
testiyle doğrulanacak (Opus alt-ajanı: "bu proje için hiç otomatik test
altyapısı yok, yeni uç saf veri dönüşümü olduğundan backend'de ucuza test
edilebilir, frontend'e bu tur için test altyapısı kurmak orantısız").

## Benchmark / Başarı Ölçütü
Coverage Target: belirtilmedi (bu projede coverage aracı yok)
Performance Target: sayfa lokal makinede <2sn'de yüklenir
Memory: belirtilmedi
Görsel/UI kriteri: `shap_scores.json`'daki değişkenlerin TAMAMI (dosyadaki
gerçek sayı, şu an 51 — sabit "8" veya "15-20" değil) listelenir; 3 modelin
4 metriği eksiksiz görünür; en iyi model ve hedef durumu doğru vurgulanır;
tarayıcı konsolunda hata olmaz.
Diğer ölçülebilir kriterler: backend pytest testleri (a/b/c) yeşil.

## Kapsam Dışı
- CSV/PDF rapor indirme (sonraki tur)
- Arayüzden model yeniden eğitimi tetikleme
- Geçmiş eğitim koşumlarının karşılaştırılması (versiyon geçmişi yok)
- ROC eğrisi/confusion matrix gibi ek grafikler (ilgili artifact dosyası yok)
- "Kayıp Tahmini" ve "Müdahale Planları" sayfaları (ayrı görevler)

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/app/main.py` — yeni `GET /api/model-report` ucu
- `web/src/pages/ModelReports.tsx` — yeni sayfa (ComingSoon'un yerini alır)
- `web/src/lib/types.ts` — `ModelReport` tipi
- `web/src/lib/api.ts` — `fetchModelReport()`
- `web/src/App.tsx` — `/model-ve-raporlar` route'u `ComingSoon`'dan `ModelReports`'a çevrilir

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulandı (önceki görevlerden) — bu makinede git reposunun kökü proje
klasörünün (`projelerim/musteri-kaybi-karar-destek/`) KENDİSİ değil, DAHA
GENİŞ bir dizin (ev dizini, `C:\Users\YUSUF ÇİNAR`); sınırsız arama
(`git log -p --all`, kök dizinden `grep -r`) devasa ve ilgisiz bir geçmişi
tarayabilir. Sonraki adımlarda (plan/code-copilot/test-copilot) arama her
zaman gerçek proje klasörüyle sınırlanmalı.

## Rollback Beklentisi
Üretim sistemi değil, akademik prototip. Hatalı bir değişiklik git commit
geçmişinden geri alınır; ayrı bir rollback mekanizması kapsam dışı.

## Risks
- **Kabul edilen risk (threat-model sonucu):** `/api/model-report` dahil
  tüm `/api/*` uçları kimlik doğrulama/yetkilendirme içermiyor, rate limit
  yok. Kabul edilme nedeni: uygulama tek kullanıcılı, localhost-only
  akademik bir araç (uvicorn varsayılan host `127.0.0.1`, CORS sadece
  `localhost:5173`'e açık, ağa açık değil). Gerçek bir üretim/çok kullanıcılı
  ortama taşınırsa bu karar yeniden değerlendirilmeli.
- 51 değişkenlik tam SHAP listesi UI'da okunabilirlik sorunu yaratabilir —
  (Opus alt-ajanı önerisi: varsayılan ilk 10 görünür + "Tümünü Göster"
  genişletme veya kaydırılabilir liste; plan adımında netleştirilecek).

## Assumptions
- `metrics.json`'daki anahtar adlarının (`models`, `best_model`,
  `target_roc_auc`, `target_met`, `dataset.rows`) `/api/summary`'nin zaten
  okuduğuyla aynı olduğu varsayılıyor — mevcut `load_json`/`MODEL_LABELS`
  yardımcıları yeniden kullanılacak (varsayım, kullanıcı onayı bekliyor).
- SHAP skorları için teknik olmayan okuyucuya kısa bir açıklama satırı
  eklenecek ("Ortalama |SHAP| — modelin karar üzerindeki ortalama etkisi")
  (Opus alt-ajanı önerisi, varsayım).

## Unknowns
- Çözüldü (plan adımı, ecc-planner danışmanı önerisiyle): 51 değişken
  varsayılan olarak ilk 10 gösterilir + "Tümünü Göster (N)" genişletme
  butonu; sayı sabit yazılmaz, `drivers.length` kullanılır. Genişletilince
  tüm 51 öğe DOM'a gelir — AC-2 ("tüm değişkenler listelenir") ihlal
  edilmiş sayılmaz.
- Çözüldü (plan adımı): `/api/model-report`'un `dataset` alanı SADECE
  `metrics.json`'daki `dataset.{rows,churn_rate,feature_count}`'tan
  üretilir — `test_customers.csv`/`telco_churn_raw.csv` okunmaz. Gerekçe:
  bu dosyalara bağımlılık eklemek AC-5'in "sadece metrics.json/
  shap_scores.json eksikse 503" sözleşmesini bozar (CSV eksikse 500
  olurdu). `test_customers` sayısı zaten Genel Bakış sayfasında var,
  burada tekrar gösterilmesine gerek yok.

## Sorular ve Cevaplar (ham kayıt)
1. Persona → ekip + hoca/jüri (Opus alt-ajanı tarafından yanıtlandı).
2. Ana hedef → tam model karşılaştırma + tam SHAP listesi + dataset künyesi (Opus alt-ajanı tarafından yanıtlandı).
3. Happy path/veri kaynağı → yeni `/api/model-report` ucu, `/api/summary` değiştirilmez (Opus alt-ajanı tarafından yanıtlandı).
4. Backend erişilemezse → mevcut Overview/CustomerRisk hata deseni (Opus alt-ajanı tarafından yanıtlandı).
5. Boş SHAP listesi → boş-durum mesajı, hata değil; dosya yoksa 503 (Opus alt-ajanı tarafından yanıtlandı).
6. Davranış sözleşmesi → yukarıdaki tablo (Opus alt-ajanı tarafından dolduruldu).
7. Başarı ölçütü → tüm 51 değişken listelenir, <2sn yükleme (Opus alt-ajanı tarafından yanıtlandı).
8. Kapsam dışı → CSV/PDF indirme, yeniden eğitim tetikleme, koşum karşılaştırma, ek grafikler (Opus alt-ajanı tarafından yanıtlandı).
9. Etkilenen dosyalar → yukarıdaki liste (Opus alt-ajanı tarafından yanıtlandı).
10. Test stratejisi → 0/100/0 (backend pytest, frontend manuel) (Opus alt-ajanı tarafından yanıtlandı).
11. Riskler → auth yokluğu (kabul edilen risk), 51 değişken okunabilirlik riski (Opus alt-ajanı tarafından yanıtlandı).
12. Jira → kullanılmayacak (kullanıcıdan AskUserQuestion ile doğrudan alındı).
13. Threat-model → çağrıldı, sonuç: ek AC-S gerekmedi, kabul edilen risk kaydedildi (bu oturumda yapıldı).
