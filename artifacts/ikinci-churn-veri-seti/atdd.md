---
task_slug: ikinci-churn-veri-seti
jira_id: null  # proje kararı: Jira kullanılmıyor
threat_model: not-applicable
priority: medium
coverage_target: 80
performance_target: "openml_churn tam eğitimi tek çalıştırmada <=10 dk; testlerde tam eğitim yok"
memory_target: null
test_strategy:
  unit: 70
  integration: 25
  e2e: 5   # e2e = küçük örneklemli eğitim smoke testi (UI e2e yok)
affected_modules:
  - src/train_model.py
  - backend/app/main.py
  - backend/app/labels.py
  - backend/tests/ (yeni testler)
  - outputs/openml_churn/ (yeni, üretilmiş çıktılar)
  - web/src/lib/types.ts, web/src/pages/CustomerDetail.tsx, web/src/pages/Overview.tsx (yalnızca null-safe render — bkz. Unknowns U1)
---

# ATDD — ikinci-churn-veri-seti

## Jira Kaynağı
Jira'ya bağlı değil (projede Jira kullanılmıyor). Notion mirror: atlandı (Jira bağlantısı yok).

## Persona
Jüri/akademik değerlendirici ve proje ekibi. (Sonnet yedek alt-ajanı tarafından yanıtlandı)

## Hedef (Neden)
Bugünkü testler yalnızca Telco çıktılarına bağlı; uç durumlarda monkeypatch'li DataFrame'ler kullanılıyor.
Pipeline'ın (eğitim → çıktılar → API) Telco'ya özgü olmadığını, gerçek ve şeması farklı bir
ikinci churn veri setiyle uçtan uca çalıştığını kanıtlamak.

## User Story
As a proje ekibi
I want eğitim pipeline'ını ve API'yi ikinci, gerçek bir churn veri setiyle çalıştırıp aynı sözleşme testlerinden geçirmek
So that sistemin Telco'ya aşırı bağlı olmadığını jüriye kanıtlayabileyim

## Veri seti
`data/openml_churn.arff` — OpenML ID 40701 "churn" v1, lisans public, 5000 satır, %14.1 churn,
hedef `class` {0,1}. Müşteri ID sütunu yok. Sözleşme/tenure kavramı yok.
Kullanıcı onayıyla 2026-11-04'te indirildi (412.293 bayt).

## Tanımlar (kararlar)
- **Profil:** train_model.py, veri setine özgü her şeyi bir profil sözlüğünden alır: ham dosya yolu,
  yükleyici (CSV/ARFF), ID üretimi, hedef eşlemesi, feature engineering fonksiyonu (opsiyonel),
  düşürülecek sütunlar, REASON_SOLUTIONS ve çıktı klasörü.
  Profiller: `telco` (mevcut davranış birebir) ve `openml_churn`.
  Seçim CLI argümanıyla yapılır: `python src/train_model.py --dataset openml_churn`; varsayılan `telco`.
- **Çıktı yerleşimi:** `telco` → proje kökü (mevcut dosyalar, DEĞİŞMEZ). `openml_churn` → `outputs/openml_churn/`.
- **ID:** `openml_churn` için ARFF'teki satır sırasından üretilir: `OC-00000`…`OC-04999`. Modele girmez.
- **Özellikler (openml_churn):** `phone_number` düşürülür (ID benzeri). `state` ve `area_code` kategorik
  (one-hot) işlenir. Türev özellikler: `total_minutes`, `total_calls`, `total_charge`.
- **REASON_SOLUTIONS (openml_churn):** Türkçe öneriler en az şu özellikler için yazılır:
  international_plan, number_customer_service_calls, total_day_minutes/total_day_charge, total_charge,
  voice_mail_plan, total_intl_calls. Diğer özellikler DEFAULT_SOLUTION alır.
- **Backend seçimi:** `DATASET` ortam değişkeni (`telco` varsayılan | `openml_churn`).
  Değer yalnızca bu beyaz listeden kabul edilir. `telco` kökten okur, diğeri `outputs/<ad>/`'dan okur.
- **Telco'ya özgü alanlar:** openml_churn'de `contract`, `tenure_months`, `monthly_charges`, `total_charges` = null;
  `/api/summary` `by_contract` = []; dataset adı "OpenML Churn".

## Acceptance Criteria
1. [Critical] AC-1: Given `data/openml_churn.arff`, When `python src/train_model.py --dataset openml_churn`,
   Then çıkış kodu 0 olur ve `outputs/openml_churn/` altında 6 çıktı oluşur (model.joblib, encoder.joblib,
   metrics.json, shap_scores.json, shap_summary.png, test_customers.csv). metrics.json'da en iyi modelin
   ROC-AUC değeri ≥ 0.80'dir. Kökteki Telco çıktılarının içeriği (hash) değişmez.
2. [Critical] AC-2: Given AC-1'in çıktıları ve `DATASET=openml_churn`, When mevcut API sözleşme testleri
   (summary, model-report, customers, customers/{id}, postmortem liste/detay) iki veri seti üzerinde
   parametrize koşulur, Then hepsi 200 döner ve yanıt şemaları Telco ile aynı anahtar kümesine sahiptir.
   Testler gerçek çıktı dosyalarını okur; monkeypatch kullanılmaz.
3. [Critical] AC-3: `DATASET` verilmediğinde davranış bugünküyle birebir aynıdır; mevcut 27 test değişmeden geçer (regresyon).
4. [High] AC-4: openml_churn'de test_customers.csv'deki `customerID` değerleri `^OC-\d{5}$` kalıbına uyar ve benzersizdir;
   `phone_number` modelin özellik listesinde (encoder.joblib feature_names) yer almaz.
5. [High] AC-5: openml_churn'de `/api/customers/{id}` yanıtında `contract`, `tenure_months`, `monthly_charges`,
   `total_charges` null döner; `/api/summary` `by_contract == []` ve `dataset.name == "OpenML Churn"` olur.
   UI bu alanlar null olduğunda "—" gösterir; "null", "NaN" ya da "Invalid" metni görünmez.
6. [High] AC-6: `--dataset bilinmeyen` → çıkış kodu 2, stderr'de tam olarak
   `Bilinmeyen veri seti: bilinmeyen. Geçerli: telco, openml_churn`. Hiçbir dosya yazılmaz.
7. [High] AC-7: Ham dosya yoksa çıkış kodu 2 ve `Ham veri bulunamadı: <yol>` mesajı; hedef sütun yoksa çıkış 2 ve
   `Hedef sütun bulunamadı: class`; hedef tek sınıfsa çıkış 2 ve `Hedef tek sınıf içeriyor, eğitim yapılamaz`;
   0 satırsa çıkış 2 ve `Veri boş`. Hiçbirinde çıktı yazılmaz.
8. [High] AC-8: Çıktılar önce `outputs/<ad>/.tmp/` içine yazılır, hepsi başarıyla yazılınca hedefe taşınır.
   Eğitim yarıda istisna fırlatırsa `.tmp` silinir, önceki çıktılar korunur ve çıkış kodu 1 olur
   (testte istisna monkeypatch ile tetiklenir). Telco profili kök dizine yazdığı için bu kural yalnızca
   outputs/ altındaki profiller için geçerlidir (bkz. Assumptions A3).
9. [High] AC-9: `DATASET=xyz` ile backend modülü import edildiğinde/başlatıldığında `ValueError("Bilinmeyen DATASET: xyz. Geçerli: telco, openml_churn")`
   fırlar ve uygulama başlamaz.
10. [High] AC-10: `DATASET=openml_churn` ama `outputs/openml_churn/` yoksa veri okuyan uçlar
   503 `{"detail": "Veri kaynağı okunamadı"}` döner (mevcut `_load` deseni; summary ve customers uçları dahil).
11. [Medium] AC-11: Tekrarlanabilirlik: aynı seed ile, 300 satırlık örneklemde iki eğitim çalıştırması aynı
   ROC-AUC'yi (±1e-6) üretir. Bu test, eğitim fonksiyonunu küçük örneklemle ve düşük n_iter ile çağırır (smoke).
12. [Medium] AC-12: Eğitim logunun son satırı `Eğitim tamamlandı: profil=openml_churn ROC-AUC=<0.xxxx>` biçimindedir
   (operatör görünürlüğü).

## Threat Model
Tetikleyici yok. Değerlendirilen tetikleyiciler: kimlik doğrulama, kullanıcı girdisi, dosya yükleme/indirme,
ödeme, kişisel veri, multi-tenant sınırı, dış API, arka plan işi, yeni HTTP ucu, RLS atlayan anahtar.
Hiçbiri uymadı: yeni HTTP ucu yok; `DATASET` ve `--dataset` operatörün yerel ortamından geliyor ve
beyaz listeyle sınırlı (path traversal yok, AC-6/AC-9); ARFF dosyası tek seferlik, kullanıcı onaylı
yerel bir indirme ve çalışma anında ağa çıkılmıyor; veri anonim (state ve telefon kodlu sayılar).

## Davranış Sözleşmesi
| # | Durum | Dönen değer | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Eğitim happy path | exit 0; son log `Eğitim tamamlandı: profil=openml_churn ROC-AUC=0.9xxx` | outputs/openml_churn/ 6 dosya; kök değişmez | terminalde özet | AC-1, AC-12 |
| 1b | API, openml_churn | 200; summary `{"dataset": {"name": "OpenML Churn", ...}, "by_contract": [], ...}`; müşteri `{"customer_id": "OC-00042", "contract": null, ...}` | yok | UI veriyle dolar, sözleşme alanları "—" | AC-2, AC-5 |
| 2 | Bilinmeyen profil (eğitim) | exit 2; `Bilinmeyen veri seti: X. Geçerli: telco, openml_churn` | dosya yazılmaz | terminal hatası | AC-6 |
| 2b | Bilinmeyen DATASET (backend) | `ValueError("Bilinmeyen DATASET: X. Geçerli: telco, openml_churn")` | uygulama başlamaz | uvicorn hata çıktısı | AC-9 |
| 3 | Ham dosya yok | exit 2; `Ham veri bulunamadı: data/openml_churn.arff` | yazılmaz | terminal hatası | AC-7 |
| 3b | Çıktı klasörü yok (API) | 503 `{"detail": "Veri kaynağı okunamadı"}` + logger.exception | yok | UI genel hata kutusu | AC-10 |
| 5 | Şema uyumsuz (hedef/sütun eksik) | exit 2; `Hedef sütun bulunamadı: class` | yazılmaz | terminal hatası | AC-7 |
| 7 | Kısmi başarı (eğitim yarıda) | exit 1; `Eğitim yarıda kesildi, çıktılar yazılmadı` | .tmp silinir, önceki çıktılar korunur | eski tutarlı çıktı | AC-8 |
| 8 | 0 satır / tek sınıf | exit 2; `Veri boş` / `Hedef tek sınıf içeriyor, eğitim yapılamaz` | yazılmaz | terminal uyarısı (sessiz başarı yok) | AC-7 |
| 9 | Telco alanı yok (null) | 200, alanlar null, `by_contract: []` | yok | "—"; sözleşme kartı boş durum | AC-5 |

Silinen satırlar:
- 4 (yetkisiz erişim): auth yok; uygulama localhost-only ve tek kullanıcılı.
- 6 (zaman aşımı): 10 dakikalık eğitim sınırı hedef olarak raporlanır, zorlanmaz (bkz. A4). API'de ağ çağrısı yok.

Boş sonuç ↔ hata ayrımı: API'de çıktı yoksa 503 döner, hiçbir zaman 200 + [] dönmez. Eğitimde
sessiz başarı yok; 0 satır ve tek sınıf durumları exit 2 ile biter.
Nullable alanlar: `contract`, `tenure_months`, `monthly_charges`, `total_charges` → UI'da "—".
Enum: `DATASET`/`--dataset` ∈ {telco, openml_churn}; her değer ayrı test edilir (AC-2, AC-3, AC-6, AC-9).
LLM: yok.

## Test Strategy
Unit: 70% — profil seçimi, ID üretimi, feature engineering, sözleşmedeki hata yolları (AC-4, 6, 7, 8, 12).
Bu testler küçük, geçici sentetik ARFF/CSV fixture'ları kullanır.
Integration: 25% — API sözleşme testleri iki veri setinin GERÇEK çıktılarıyla, parametrize (AC-2, 3, 5, 9, 10).
Smoke/e2e: 5% — 300 satırlık örneklemle gerçek eğitim + tekrarlanabilirlik (AC-11).

## Benchmark / Başarı Ölçütü
Coverage: değişen/yeni kodda ≥ %80 (pytest-cov dev bağımlılığına eklenir).
openml_churn ROC-AUC ≥ 0.80; PR-AUC metrics.json'a ek bilgi olarak yazılır.
Tam eğitim ≤ 10 dk (ölçülüp raporlanır).
Görsel/UI kriteri: DATASET=openml_churn ile Genel Bakış ve Müşteri Detayı sayfaları bozulmadan açılır;
null alanlar "—" olarak görünür (verify'da tarayıcıyla kontrol edilir).

## Kapsam Dışı
- UI'da veri seti seçici
- Üçüncü bir veri seti
- Telco'nun yeniden eğitilmesi ya da çıktılarının taşınması
- Hiperparametre ince ayarı
- Mevcut monkeypatch'li uç durum testlerinin silinmesi (kalırlar)
- Deploy

## Etkilenen Dosyalar/Modüller
Frontmatter. Ayrıca `requirements.txt` için ARFF okuyucu gerekebilir (scipy.io.arff, scipy'nin zaten
sklearn bağımlılığı olduğu varsayımıyla); bkz. U2.

## Proje Ortamı Kısıtı
Git kökü proje klasörü. Aramalar proje klasörüyle sınırlı tutulur; data/, venv/ ve node_modules/ taranmaz.
`venv` bu oturumda Python 3.11 ile yeniden kuruldu. Kök requirements.txt'deki eğitim bağımlılıkları
(xgboost, shap…) henüz kurulu değil; kurulumu plan/verify adımında yapılacak.

## Rollback Beklentisi
Telco yolu değişmediği için revert güvenli. outputs/openml_churn/ silinebilir; DATASET verilmezse sistem bugünkü gibi çalışır.

## Risks
- R1: Telco regresyonu. train_model.py yeniden yapılandırılırken Telco çıktısı değişebilir. AC-3 ve AC-1'deki hash kontrolü bunu yakalar.
- R2: outputs/ altına ikili dosyalar (joblib, png) commit edilecek. Boyut verify adımında raporlanır.
- R3: Sınıf dengesizliği (%14). Mevcut class_weight ve scale_pos_weight kullanılmaya devam eder.
- R4: state ve phone_number alanlarının gerçek anlamı bilinmiyor (anonim kod olduğu varsayıldı).
- R5: `data/openml_churn.arff` commit edilmeli mi? data/telco_churn_raw.csv git'te takipli; tutarlılık için edilmesi önerilir (412 KB).

## Assumptions
- A1 (orkestratör): Profil seçimi alt-ajanın önerdiği gibi tek bir sözlükle yapılır; ayrı modül/sınıf hiyerarşisi kurulmaz (ponytail).
- A2 (orkestratör): Eğitimde profil, `--dataset` CLI argümanıyla seçilir. Alt-ajan eğitim tarafında seçim mekanizması belirtmemişti.
- A3 (orkestratör): Atomik .tmp yazımı yalnızca outputs/ profillerinde uygulanır. Telco kök dizine yazar ve bu davranış bilinçli olarak değiştirilmez (regresyon riski).
- A4 (orkestratör): Alt-ajan "10 dk aşılırsa exit 124" önerdi. Bu bir zamanlayıcı/alt süreç mekanizması gerektirir ve akademik bir proje için gereksiz karmaşıklıktır. Süre yalnızca ölçülüp raporlanır, zorlanmaz.
- A5 (orkestratör): Alt-ajan "çıktı CSV şeması bozuksa 500" önerdi. Bunun yerine mevcut `_load` deseni (503 "Veri kaynağı okunamadı") kullanılır; postmortem görevinde kararlaştırılan sözleşmeyle tutarlıdır.
- A6: Testlerde tam eğitim koşmaz. Integration testleri commit edilmiş outputs/openml_churn/ çıktılarını okur.

## Unknowns
- U1: Alt-ajan "UI'ya dokunulmaz" dedi, ama AC-5 null alanların "—" gösterilmesini istiyor. Bugün `types.ts`
  `tenure_months: number`, `contract: string` gibi non-null tipler kullanıyor ve CustomerDetail `num(null)` render ediyor.
  Bu yüzden küçük bir null-safe frontend değişikliği gerekecek; plan adımında dosya dosya netleşecek.
- U2: scipy.io.arff kök requirements'ta açıkça yok (sklearn üzerinden geliyor olabilir). Plan adımında doğrulanacak.

## Sorular ve Cevaplar (ham kayıt)
Codex başarısız (codex CLI bu makinede kurulu değil — aynı oturumda daha önce exit 127), yedek kullanıldı.
Cevaplar Sonnet yedek alt-ajanı tarafından verildi.
0. Veri seti türü → "Başka bir churn veri seti" (kullanıcı seçti). Somut veri setinin seçimi orkestratöre bırakıldı ("yap bişeyler"); OpenML 40701 önerildi, kullanıcı indirmeyi onayladı.
1. Persona → jüri ve ekip; "pipeline veri setinden bağımsız" kanıtı
2. Kapsam → (b) eğitim + backend DATASET seçimi; UI seçici yok
3. Çıktılar → Telco kökte kalır; yeni çıktılar outputs/openml_churn/
4. ID → satır indeksinden OC-00000
5. Özellikler → profil sözlüğü; phone_number düşer; state kategorik; Türkçe öneriler
6. Hedef → ROC-AUC ≥ 0.80; eğitim ≤ 10 dk; testlerde tam eğitim yok
7. Mock → monkeypatch'li testler kalır; ek olarak gerçek çıktı üzerinde parametrize sözleşme testleri
8. Tekrarlanabilirlik → aynı seed, ±1e-6, küçük örneklemle
9. Edge case'ler → exit 2 + net mesajlar; DATASET bilinmiyorsa ValueError; çıktı yoksa 503
10. Test stratejisi → 70/25/5, coverage ≥ %80
11. Kapsam dışı → yukarıdaki bölümde
12. Riskler → yukarıdaki bölümde
