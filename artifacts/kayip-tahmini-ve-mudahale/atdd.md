---
task_slug: kayip-tahmini-ve-mudahale
jira_id: null  # projede Jira kullanılmıyor
threat_model: done
priority: high
coverage_target: 85
performance_target: "POST /api/predict < 300ms (localhost, sıcak model); GET /api/intervention-plans < 300ms"
memory_target: null
test_strategy:
  unit: 0
  integration: 85   # FastAPI TestClient, gerçek model ve gerçek çıktı dosyaları
  e2e: 15           # tarayıcıda manuel akış + ekran görüntüsü (verify)
affected_modules:
  - backend/app/main.py (yeni uçlar)
  - backend/app/scenario.py (yeni — senaryo satırını model girdisine çevirme ve SHAP)
  - backend/tests/test_predict.py, backend/tests/test_intervention_plans.py (yeni)
  - web/src/pages/ChurnPrediction.tsx, web/src/pages/InterventionPlans.tsx (yeni)
  - web/src/App.tsx, web/src/lib/api.ts, web/src/lib/types.ts
  - web/src/components/Layout.tsx, web/src/index.css, web/index.html, web/tailwind.config.js (arka plan + Fraunces)
---

# ATDD — kayip-tahmini-ve-mudahale

## Kaynak
Jira yok. Tasarım kaynağı: Stitch remix projesi `11951075270987699250`, kullanıcı onaylı iki ekran →
`designs/03_kayip_tahmini/` ve `designs/04_mudahale_planlari/` (code.html + screen.png).
Notion mirror: atlandı (Jira yok).
Netleştirme notu: Codex kurulu değil. Kararlar bu konuşmada kullanıcıyla verilenlerden ve orkestratörün
önerilerinden oluşuyor; ayrı alt-ajana sorulmadı. Orkestratör kararları "(OK)" ile işaretli.

## Persona
Proje ekibi ve jüri; churn analisti rolünde uygulamayı localhost'ta kullanan kişi.

## Hedef
Kenar çubuğundaki iki "yakında" sayfasını (Kayıp Tahmini, Müdahale Planları) onaylı Stitch tasarımlarıyla,
gerçek modele ve gerçek veriye bağlı olarak hayata geçirmek; uygulamanın arka planını sade kremden daha zengin
bir dokuya taşımak.

## User Story
As a churn analisti
I want varsayımsal bir müşteri senaryosunu modelle anında skorlayıp etkenleri görmek ve riskli müşterileri önerilen aksiyona göre gruplanmış planlar olarak incelemek
So that hangi müşteriye hangi hamleyle başlanacağına karar verebileyim

## Tasarımdan uygulanacaklar / uygulanmayacaklar
Uygulanacak (designs/03, 04): kutusuz editöryel düzen, 12 sütunlu ızgara, ince çizgiler, serif büyük sayılar
(Fraunces), Kayıp Tahmini'nde alt çizgili parametre satırları + dev yüzde + eşikli spektrum + iki yönlü
SHAP grafiği + "İlk hamle"; Müdahale Planları'nda filtre, 3 büyük sayı, plan satırları (oranlı çubuk + sayılar),
açık planda olasılık nokta şeridi + müşteri tablosu + CSV, alt içgörü cümlesi.
Uygulanmayacak (OK — Stitch'in uydurduğu, sistemde karşılığı olmayanlar): müşteri unvanları ("Teknopark Lojistik"),
"Aksiyon durumu", "Atanan sorumlu", "CRM'e gönder", "Güven aralığı %95 CI", "Çıkarım ~6ms", "Erken Uyarılar" menüsü,
"Son senkronizasyon", kullanıcı adı "Dr. Engin Kutlay", "XGBoost v4.2" sürüm etiketi, "60 gün" iddiaları.
Mevcut kenar çubuğu ve üst başlık korunur.

## Arka plan (kullanıcı isteği: "arka planı biraz daha süsleyelim") (OK)
Tüm uygulamada (Layout seviyesinde) düz `#F6F3EC` yerine üç katman:
1. Çok hafif kâğıt grenı (inline SVG `feTurbulence` noise, opaklık ~%5).
2. 48px aralıklı, %4 opaklıkta orman yeşili ince ızgara çizgileri.
3. Sağ üst köşede çok yumuşak yeşil, sol altta çok yumuşak amber radyal renk geçişi.
Metin kontrastı WCAG AA altında kalmaz; `prefers-reduced-motion` gerektiren animasyon yok. Harici görsel dosyası yok.

## Backend sözleşmesi

### POST /api/predict (yalnızca Telco profili) (OK)
İstek (tüm alanlar zorunlu, ek alan 422):
```json
{"contract": "Month-to-month", "tenure": 41, "monthly_charges": 89.5, "internet_service": "Fiber optic",
 "tech_support": false, "online_security": false, "payment_method": "Electronic check", "senior_citizen": false}
```
- contract ∈ {"Month-to-month","One year","Two year"}; internet_service ∈ {"DSL","Fiber optic","No"};
  payment_method ∈ {"Electronic check","Mailed check","Bank transfer (automatic)","Credit card (automatic)"};
  tenure tam sayı 0–72; monthly_charges 18–120 (sonlu; NaN/inf reddedilir).
- Formda olmayan Telco özellikleri eğitim verisindeki en sık değer / medyan ile doldurulur; TotalCharges = monthly_charges × tenure;
  internet_service "No" ise internet bağımlı hizmetler "No internet service" olur.
Yanıt 200:
```json
{"probability": 0.6034, "risk": "mid", "model": "xgboost", "model_label": "XGBoost", "roc_auc": 0.847,
 "drivers": [{"feature": "Contract_Month-to-month", "label": "Sözleşme: Aylık", "contribution": 0.284}],
 "action": "Uzun dönem sözleşmeye geçişte indirim", "similar_count": 142}
```
- drivers: senaryoya özel SHAP katkıları, mutlak değere göre ilk 5, işaretli (+ artırır, − azaltır). Yalnızca formdaki
  alanlardan türeyen özellikler gösterilir (doldurulan varsayılanlar listelenmez).
- action: en büyük pozitif katkılı özelliğin REASON_SOLUTIONS karşılığı; pozitif katkı yoksa veya risk "low" ise
  `"Şimdilik müdahale gerekmiyor; izlemeye devam edin."`.
- similar_count: test setinde aynı sözleşme tipinde ve aynı risk seviyesindeki müşteri sayısı.

### GET /api/intervention-plans?risk=high_mid|high (her iki veri seti)
Yanıt 200:
```json
{"summary": {"targeted": 669, "plans": 3, "avg_probability": 0.679},
 "plans": [{"action": "Uzun dönem sözleşmeye geçişte indirim", "reason_feature": "Contract_Month-to-month",
   "reason": "Sözleşme: Aylık", "count": 560, "high": 284, "mid": 276, "share": 0.837, "avg_probability": 0.681,
   "probabilities": [0.97, 0.95], "customers": [{"customer_id": "7590-VHVEG", "probability": 0.97, "risk": "high",
   "contract": "Aylık", "reason": "Sözleşme: Aylık"}]}],
 "insight": {"top_action": "Uzun dönem sözleşmeye geçişte indirim", "top_share": 0.837}}
```
- Plan = suggested_action grubu; reason_feature = gruptaki en sık top_reason. Planlar count'a göre azalan.
- probabilities: plandaki tüm olasılıklar (nokta şeridi için), customers: olasılığa göre ilk 5.
- risk varsayılan "high_mid" (olasılık ≥ 0,40); "high" → ≥ 0,70.

### GET /api/intervention-plans/export.csv?action=<tam aksiyon metni>&risk=high_mid|high
Plandaki tüm müşteriler, UTF-8 BOM'lu CSV (mevcut high-risk.csv deseni). Sütunlar: Müşteri ID, Kayıp Olasılığı (%), Risk, Sözleşme, Ana Neden.

## Acceptance Criteria
1. [Critical] AC-1: Given geçerli bir senaryo, When POST /api/predict, Then 200 ve `probability` gerçek modelin
   `predict_proba` sonucuyla ±1e-6 eşleşir (test, aynı satırı scenario modülüyle kurup modeli doğrudan çağırarak doğrular);
   `risk` eşiklerle tutarlı; `drivers` en fazla 5 eleman, mutlak katkıya göre azalan.
2. [Critical] AC-2: Aylık sözleşme + kısa süre + fiber + destek yok senaryosu, iki yıllık + 60 ay + DSL + destek var
   senaryosundan daha yüksek olasılık verir (gerçek model, yön kontrolü).
3. [Critical] AC-3: GET /api/intervention-plans (Telco, high_mid) → summary.targeted == test setinde olasılığı ≥0,40
   olanların sayısı; plans count toplamı == targeted; her plan için high+mid == count; share toplamı ≈1 (±0,001);
   planlar count'a göre azalan; her planın customers'ı en fazla 5 ve olasılığa göre azalan.
4. [High] AC-4: risk=high → yalnızca ≥0,70 müşteriler; mid hepsi 0.
5. [High] AC-5: Geçersiz risk değeri → 422. Geçersiz predict girdisi (bilinmeyen contract, tenure 73 veya −1,
   monthly_charges 0 / 500 / "nan" / "inf", eksik alan, fazladan alan) → 422.
6. [High] AC-6: DATASET=openml_churn iken POST /api/predict → 409 `{"detail": "Senaryo tahmini yalnızca Telco veri setinde destekleniyor"}`;
   GET /api/intervention-plans 200 döner (OpenML çıktılarıyla).
7. [High] AC-7: Model/çıktı dosyası okunamazsa her iki uç 503 `{"detail": "Veri kaynağı okunamadı"}` + logger.exception (mevcut `_load` deseni).
8. [High] AC-8: export.csv geçerli action ile 200, `text/csv`, satır sayısı == ilgili planın count'u;
   bilinmeyen action → 404 `{"detail": "Plan bulunamadı"}`.
9. [High] AC-9 (UI, Kayıp Tahmini): Parametre değişince (300ms debounce) tahmin yeniden istenir; yüzde, risk rozeti,
   spektrum işaretçisi, SHAP çubukları ve İlk hamle güncellenir; istek sürerken önceki sonuç soluk gösterilir;
   hata olursa kiremit renkli ince uyarı satırı ve önceki sonuç kalmaz. "Varsayılana sıfırla" bağlantısı formu başlangıç
   senaryosuna döndürür. OpenML'de (409) sayfa "Bu veri setinde senaryo tahmini desteklenmiyor" boş durumunu gösterir.
10. [High] AC-10 (UI, Müdahale Planları): Filtre değişince liste yeniden yüklenir; ilk plan açık gelir; bir plana tıklayınca
   o plan açılır (diğerleri kapanır), nokta şeridi ve ilk 5 müşteri görünür, müşteri satırı /musteri-riski/:id'ye gider,
   "CSV indir (N kayıt)" export ucuna bağlanır. targeted 0 ise "Bu filtrede müdahale gerektiren müşteri yok".
11. [Medium] AC-11 (UI): İki sayfa da kutusuz editöryel düzende (beyaz kart yok), Fraunces başlık/sayılar;
   1440px'te yatay kaydırma yok; 390px'te tek sütuna iner ve yatay kaydırma yok; tüm kontroller klavyeyle kullanılabilir.
12. [Medium] AC-12 (UI): Arka plan katmanları tüm sayfalarda görünür; metin kontrastı ≥ 4.5:1.
13. [High] AC-S1: predict gövdesindeki ek alanlar (`extra="forbid"`) ve tip zorlaması: `"tenure": "41; drop"` → 422;
   yanıt hiçbir zaman istek alanlarını yankılamaz (yansıtma yok).
14. [Medium] AC-S2: export.csv `action` parametresi yalnızca mevcut aksiyon metinleriyle birebir eşleşir (dosya yolu
   veya regex olarak kullanılmaz); CSV hücreleri `=`, `+`, `-`, `@` ile başlıyorsa başına `'` eklenir (CSV injection).

## Threat Model
Çağrıldı (kısa STRIDE): tetikleyiciler yeni HTTP uçları + kullanıcı girdisi (POST gövdesi, query).
T: AC-5, AC-13 (sıkı şema, sonlu sayı). I: AC-7 (sızıntısız 503). D: girdiler sınırlı, model tek satır skorlar.
CSV injection: AC-14. S/E/R: N/A (auth yok, localhost tek kullanıcı — önceden kabul edilmiş risk).

## Davranış Sözleşmesi
| # | Durum | Dönen | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | predict happy | 200 + yukarıdaki şema | yok | yüzde, rozet, spektrum, sürücüler, ilk hamle | AC-1,2,9 |
| 2 | predict geçersiz | 422 (FastAPI gövdesi) | yok | UI geçersiz değer gönderemez; olursa hata satırı | AC-5,13 |
| 3 | predict OpenML | 409 + sabit mesaj | yok | "desteklenmiyor" boş durumu | AC-6 |
| 4 | model/çıktı okunamaz | 503 `{"detail": "Veri kaynağı okunamadı"}` + log | log | hata satırı / hata kutusu | AC-7 |
| 5 | plans happy | 200 + şema | yok | sayılar, plan listesi, açık plan | AC-3,10 |
| 6 | plans geçersiz risk | 422 | yok | — | AC-5 |
| 7 | plans boş (targeted 0) | 200, plans [], summary sıfırlar | yok | boş durum cümlesi | AC-10 |
| 8 | export bilinmeyen action | 404 `{"detail": "Plan bulunamadı"}` | yok | — | AC-8 |
| 9 | predict pozitif katkı yok | 200, action = izleme cümlesi | yok | "Şimdilik müdahale gerekmiyor…" | AC-1 |

Silinen: yetkisiz erişim (auth yok), zaman aşımı (yerel model, ağ yok).
Kısmi başarı: SHAP hesaplanamazsa yanıt 503 (olasılık tek başına dönülmez; eksik ekran yok).
Sessiz başarı yok: plans boşsa açıkça boş durum; predict her zaman olasılık veya hata döner.
Nullable: yok (tüm alanlar dolu). Enum her değer: contract 3, internet 3, payment 4 → test her değeri en az bir kez kullanır.

## Test Strategy
Integration %85: TestClient + gerçek model.joblib/encoder.joblib/test_customers.csv (monkeypatch yalnızca 503 ve OpenML profili için).
E2E %15: verify'da tarayıcı akışı (her iki sayfa, 1440 ve 390 genişlik, ekran görüntüsü).

## Benchmark
Coverage ≥ %85 (yeni backend kodu). predict < 300ms. Görsel: tasarıma yakınlık (yukarıdaki "uygulanacaklar" listesi), yatay kaydırma yok.

## Kapsam Dışı
Stitch'teki uydurma alanlar (yukarıda); OpenML için senaryo tahmini; aksiyon durumu takibi/CRM; plan düzenleme;
"Bu senaryoya uyan müşterileri gör" bağlantısının filtreli liste açması (yalnızca sayı gösterilir) (OK).

## Rollback
Yeni uçlar ve sayfalar izole; revert yeterli. Arka plan değişikliği tek CSS/Layout değişikliği.

## Risks
- SHAP TreeExplainer XGBoost için tek satırda hızlı olmalı; değilse explainer modül yüklenirken bir kez kurulur.
- Formdaki 8 alan dışındaki Telco özellikleri varsayılanla doldurulduğu için tahmin "tipik müşteri" varsayımı taşır; UI'da küçük not.
- Fraunces Google Fonts'tan yüklenir; çevrimdışı ortamda serif yedeğe düşer.

## Assumptions (OK)
- A1: Senaryo formu 8 alanla sınırlı (tasarımdaki alanlar).
- A2: Arka plan değişikliği tüm uygulamaya uygulanır, yalnızca iki sayfaya değil.
- A3: Müdahale Planları her iki veri setinde çalışır; Kayıp Tahmini yalnızca Telco'da.

## Unknowns
- U1: Kullanıcı arka plan katmanlarının yoğunluğunu ekranda görünce ayar isteyebilir.
