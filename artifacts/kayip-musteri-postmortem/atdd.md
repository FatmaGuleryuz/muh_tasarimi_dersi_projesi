---
task_slug: kayip-musteri-postmortem
jira_id: null  # proje kararı: bu akademik projede Jira kullanılmıyor (bkz. model-ve-raporlar-sayfasi/atdd.md)
threat_model: done
priority: medium
coverage_target: 90
performance_target: "GET /api/postmortem p95 <300ms, GET /api/postmortem/{id} <100ms (localhost)"
memory_target: null
test_strategy:
  unit: 0
  integration: 100
  e2e: 0
affected_modules:
  - backend/app/main.py
  - backend/tests/test_postmortem.py (yeni)
  - web/src/pages/LossAnalysis.tsx (yeni)
  - web/src/pages/CustomerDetail.tsx
  - web/src/components/Sidebar.tsx
  - web/src/lib/types.ts
  - web/src/lib/api.ts
  - web/src/App.tsx
---

# ATDD — kayip-musteri-postmortem

## Jira Kaynağı
Jira'ya bağlı değil. Bu projede Jira kullanılmıyor (kullanıcının önceki kararı),
tek kaynak yerel `atdd.md`.
Notion mirror: atlandı (Jira bağlantısı yok).

## Persona
Tek kullanıcılı analist veya öğrenci (proje ekibi). Uygulamayı localhost'ta çalıştırıp
hoca ya da jüriye sunum yapar. (Sonnet yedek alt-ajanı tarafından yanıtlandı)

## Hedef (Neden)
Mevcut ekranlar yalnızca ileriye dönük risk gösteriyor. "Model haklı çıktı mı?"
sorusunu yanıtlayan bir yer yok. Bu özellik kaybedilen müşterilerde şunları geriye
dönük gösterir: modelin riski önceden görüp görmediği, öne çıkan neden (`top_reason`)
ve önerilen aksiyon. Modelin kaçırdığı müşteriler böylece görünür olur.

## User Story
As a proje analisti
I want kaybedilmiş her müşteri için modelin önceden ne dediğini görmek
So that modelin nerede yakaladığını ve nerede kaçırdığını kanıtlarla sunabileyim

## Tanımlar
- Kaybedilmiş müşteri: `test_customers.csv` içinde `actual_churn == 1`.
- `outcome`: mevcut `risk_level()` eşikleriyle belirlenir. `high` → `caught`,
  `mid` → `partial`, `low` → `missed`. Yeni eşik eklenmez.
- `catch_rate` = (caught + partial) / lost_total. `strict_catch_rate` = caught / lost_total.
  lost_total = 0 ise ikisi de 0.0 olur (sıfıra bölme yapılmaz).
- Yanlış alarm (`actual_churn == 0` ve `risk == high`) listede yer almaz. Yalnızca
  özette `false_alarm_count` ve `precision_high` olarak görünür.
  `precision_high` = gerçekten kaybedilen high müşteriler / tüm high müşteriler.
  High müşteri yoksa 0.0 olur.

## Acceptance Criteria (Given-When-Then)
1. [Critical] AC-1: Given test seti, When `GET /api/postmortem`, Then 200 döner ve
   `summary.lost_total` CSV'deki `actual_churn==1` sayısına birebir eşittir;
   `caught+partial+missed == lost_total`; `catch_rate` el hesabıyla ±0.001 tutar.
   Bu test CSV'yi doğrudan okuyarak beklenen değeri kendisi hesaplar (doğrudan tetikleme).
2. [Critical] AC-2: Given kaybedilmiş bir müşteri id'si, When `GET /api/postmortem/{id}`,
   Then 200 döner, gövde aşağıdaki şemaya uyar ve `outcome`, `risk` ile tutarlıdır.
3. [Critical] AC-3: Given `outcome=missed`, When liste istenir, Then `items` içindeki
   her öğe `outcome=="missed"` olur. `summary` filtreden etkilenmez ve tüm kayıpları kapsar.
4. [High] AC-4: Given var olmayan bir id, When detay istenir, Then
   404 `{"detail": "Müşteri bulunamadı: <id>"}` döner.
5. [High] AC-5: Given var olan ama `actual_churn==0` bir id, When detay istenir, Then
   409 `{"detail": "Müşteri kaybedilmemiş: <id>"}` döner.
6. [High] AC-6: Given `outcome=foo` ya da `limit=0` veya `limit=-5`, When liste istenir,
   Then 422 döner. `outcome` için Literal["caught","partial","missed"],
   `limit` için `ge=1, le=1000` kullanılır.
7. [High] AC-7: Given veri dosyası okunamıyor (load_customers bir exception fırlatır,
   testte monkeypatch ile tetiklenir), When herhangi bir postmortem ucu çağrılır,
   Then 503 `{"detail": "Veri kaynağı okunamadı"}` döner. Gövdede dosya yolu veya
   stack trace yer almaz ve hata `logger.exception` ile loglanır.
8. [High] AC-8: Given kayıp müşteri yok (testte filtrelenmiş boş DataFrame monkeypatch'lenir),
   When liste istenir, Then 200 döner, `items: []` ve summary'nin tüm sayıları 0 /
   oranları 0.0 olur. UI "Kaybedilmiş müşteri bulunamadı" mesajını gösterir.
9. [Medium] AC-9: Given `TotalCharges` boş olan bir kayıp müşteri, Then API
   `total_charges: null` döner ve UI "—" gösterir ("0", "NaN" ya da "null" göstermez).
10. [Medium] AC-10: Given `top_reason`, `shap_scores.json` anahtarlarında yok, Then
    `top_reason_global_rank: null` döner ve UI "sıralama bilgisi yok" yazar.
11. [Medium] AC-11 (UI): Sidebar'da "Kayıp Analizi" öğesi `/kayip-analizi` rotasına gider.
    Sayfa özet kartlarını (yakalandı/kısmen/kaçırıldı/yakalama oranı) ve `outcome`
    filtreli bir liste gösterir. Satıra tıklanınca `/musteri-riski/:id` açılır.
12. [Medium] AC-12 (UI): `CustomerDetail` sayfasında müşterinin `actual_churn == true`
    olduğu durumda "Postmortem" bölümü görünür. Bu bölüm outcome rozeti, birincil
    neden ve global rankı, önerilen aksiyon ve "Aksiyon uygulandı mı: Veri yok"
    satırını içerir. `actual_churn == false` olduğunda bölüm hiç render edilmez
    ve 409 isteği atılmaz.
13. [High] AC-S1 (Tampering): Given `GET /api/postmortem/{id}` ucuna `' OR 1=1--`,
    `.*` veya `..%2F..%2Fmetrics.json` gibi saldırgan id'ler, When istek yapılır,
    Then 404 döner. Yanıtta başka bir müşterinin alanı yer almaz; eşleşme regex ya da
    `contains` değil, birebir eşitlik (`==`) ile yapılır.
14. [Medium] AC-S2 (Info disclosure): Given AC-7'deki 503 yolu, Then yanıt gövdesi tam
    olarak `{"detail": "Veri kaynağı okunamadı"}` olur. Gövdede `ROOT`, `.csv` veya
    `Traceback` geçmez; test bu üç ifadenin gövdede bulunmadığını doğrular.

## Threat Model
Çağrıldı. Tetikleyiciler: yeni HTTP uçları ve kullanıcı girdisi (`{id}`, `outcome`, `limit`).
STRIDE-lite sonuçları:
- S/E: N/A. Auth yok; tek kullanıcılı localhost uygulaması olduğu için önceden kabul edilmiş risk.
- T: AC-S1 eklendi. `outcome` ve `limit` girdileri AC-6'da tip ve aralık kontrolüyle sınırlandı.
- R: N/A. Uçlar salt okunur.
- I: AC-S2 eklendi.
- D: `limit` ≤ 1000 (AC-6); veri bellekte tutuluyor.
Authz AC'si üretilmedi, bu yüzden `authz-test` gerekmedi.

## Davranış Sözleşmesi
Not: Alan adları, mevcut `/api/customers` yanıtıyla tutarlı olsun diye snake_case
(`customer_id`, `probability`) seçildi. Alt-ajan `customerID` ve `churn_probability`
önermişti; bu düzeltmeyi orkestratör yaptı (bkz. Assumptions).

Liste örneği — `GET /api/postmortem?outcome=missed&limit=50` → 200:
```json
{
  "summary": {"lost_total": 374, "caught": 210, "partial": 90, "missed": 74,
              "catch_rate": 0.802139, "strict_catch_rate": 0.561497,
              "false_alarm_count": 95, "precision_high": 0.688525},
  "total": 1,
  "items": [{"customer_id": "1234-ABCDE", "probability": 0.21, "risk": "low",
             "outcome": "missed", "contract": "Aylık", "reason": "Aylık sözleşme",
             "reason_feature": "Contract_Month-to-month",
             "action": "Uzun dönem sözleşmeye geçişte indirim"}]
}
```
(Sayılar örnektir. `total` filtrelenmiş liste uzunluğudur, sıralama `probability` artan:
en çok kaçırılan en üstte.)

Detay örneği — `GET /api/postmortem/1234-ABCDE` → 200:
```json
{"customer_id": "1234-ABCDE", "actual_churn": true, "probability": 0.21, "risk": "low",
 "outcome": "missed", "contract": "Aylık", "tenure_months": 3,
 "monthly_charges": 70.35, "total_charges": null,
 "reason": "Aylık sözleşme", "reason_feature": "Contract_Month-to-month",
 "top_reason_global_rank": 1,
 "action": "Uzun dönem sözleşmeye geçişte indirim",
 "action_applied": null, "action_applied_note": "Veri yok"}
```

| # | Durum | Dönen değer | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path liste | 200 + yukarıdaki liste şeması | Yok (salt okunur) | Özet kartları + filtreli liste | AC-1, AC-3 |
| 1b | Happy path detay | 200 + yukarıdaki detay şeması | Yok | CustomerDetail'de Postmortem bölümü | AC-2, AC-12 |
| 2 | Girdi geçersiz (`outcome`/`limit`) | 422 (FastAPI doğrulama gövdesi) | Yok | "Geçersiz filtre" hatası | AC-6 |
| 3 | id yok | 404 `{"detail": "Müşteri bulunamadı: X"}` | Yok | "Müşteri bulunamadı" + listeye dönüş linki | AC-4 |
| 3b | id var ama kaybedilmemiş | 409 `{"detail": "Müşteri kaybedilmemiş: X"}` | Yok | UI bu isteği atmaz; bölüm gizlidir | AC-5, AC-12 |
| 5 | Veri dosyası okunamıyor | 503 `{"detail": "Veri kaynağı okunamadı"}` | `logger.exception` kaydı | "Veri yüklenemedi" hata durumu | AC-7 |
| 7 | Kısmi veri (`total_charges` / rank yok) | 200, ilgili alan `null` | Yok | "—" / "sıralama bilgisi yok" | AC-9, AC-10 |
| 8 | 0 kayıp müşteri | 200, `items: []`, summary sayıları 0, oranları 0.0 | Yok | "Kaybedilmiş müşteri bulunamadı" boş durumu | AC-8 |

Silinen satırlar:
- 4 (Yetkisiz erişim): uygulamada auth yok. Tek kullanıcılı, localhost-only bir uygulama
  ve bu risk önceki görevde kabul edildi.
- 6 (Zaman aşımı): ağ çağrısı yok, okunan veri yerel dosyalardan ve bellekten geliyor.
  Frontend'deki fetch hatası mevcut genel hata durumuna düşer.

Kısmi başarı: yalnızca alan seviyesinde olur (satır 7). Bir müşterinin satırı
kurulamazsa yanıtın tamamı 503 döner; eksik liste dönülmez.
Hiçbir şey yapılamadı ama hata yok: satır 8. Boş durum açıkça gösterilir,
özet kartları 0 değerleriyle render edilir.
Boş sonuç ↔ hata ayrımı: `200 + items: []` yalnızca "bu filtrede kayıp yok" demektir.
Veri okunamazsa 503 döner, hiçbir zaman 200 + [] dönmez.
Operatör görünürlüğü: 503 yolunda `logger.exception` zorunludur. Happy path salt
okunur ve yan etkisizdir; doğruluğu AC-1'deki sayım eşitliğiyle gözlemlenebilir.
Nullable alanlar: `total_charges` → "—", `top_reason_global_rank` → "sıralama
bilgisi yok", `action_applied` → her zaman null, UI "Veri yok" gösterir.
Enum: `outcome` ∈ {caught, partial, missed}, `risk` ∈ {high, mid, low}.
Her değerin eşlemesi Tanımlar bölümünde ayrı ayrı yazılı. Testte her outcome
değeri için en az bir müşteri doğrulanır (CSV'de varsa).
LLM çağrısı: yok (satır silindi).

## Test Strategy
Unit: 0%
Integration: 100% — pytest + FastAPI TestClient, `backend/tests/test_postmortem.py`.
Her sözleşme satırı için en az bir test yazılır. Satır 5 ve 8 monkeypatch ile
doğrudan tetiklenir.
E2E: 0% — frontend'de test altyapısı yok. UI kriterleri `verify` adımında
tarayıcı ya da vision-test ile kontrol edilir.

## Benchmark / Başarı Ölçütü
Coverage Target: yeni backend kodu için satır kapsamı ≥ %90
Performance Target: liste p95 <300ms, detay <100ms (localhost)
Görsel/UI kriteri: Kayıp Analizi sayfasının layout'u bozulmamalı. Boş durum ve
hata mesajı görünür olmalı. Postmortem bölümü kaybedilmemiş müşteride görünmemeli
(vision-test).
Diğer: `caught + partial + missed == lost_total` ve `catch_rate` ±0.001.

## Kapsam Dışı
- "Aksiyon uygulandı" takibi ve bunun için yazma uçları ya da kalıcılık (DB/JSON)
- Müşteri bazlı SHAP'ın yeniden hesaplanması
- Auth ve rate limit
- Zaman serisi analizi
- Yanlış alarm müşterilerinin detay listesi
- `/kayip-tahmini` ve `/mudahale-planlari` sayfaları (ComingSoon olarak kalır)

## Etkilenen Dosyalar/Modüller
Frontmatter'daki `affected_modules` listesi. `load_customers`, `risk_level`,
`label_for`, `CONTRACTS` yeniden kullanılır.

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Git kökü proje klasörü (`musteri-kaybi-karar-destek`). Aramalar bu klasörle sınırlı
tutulur, `data/` altındaki büyük CSV'ler taranmaz.

## Rollback Beklentisi
Değişiklik salt okunur ve izole yeni uçlardan oluşur. Commit revert edilerek geri alınır;
veri migrasyonu yoktur.

## Risks
- Postmortem gerçek üretim kaybı değil, etiketli test seti üzerinde yapılıyor.
  Arayüzde bu açıkça belirtilmeli.
- Tek bir `top_reason`, kaybın tüm nedenini temsil etmez.
- Eşikler (`HIGH_THRESHOLD`/`MID_THRESHOLD`) değişirse outcome sınıflaması da değişir.
- Kabul edilen risk (threat-model): yeni uçlarda auth ve rate limit yok. Gerekçe:
  uygulama localhost-only ve tek kullanıcılı, ayrıca CORS yalnızca `localhost:5173`'e açık.

## Assumptions
- (Orkestratör) Alan adları mevcut API'yle tutarlı olsun diye snake_case seçildi
  (`customer_id`, `probability`, `reason`, `action`). Alt-ajan CSV kolon adlarını önermişti.
- (Orkestratör) Liste sıralaması `probability` artan seçildi: kaçırılanlar en üstte görünür.
- (Orkestratör) `strict_catch_rate` alanı eklendi. Alt-ajan "caught/lost_total ayrıca
  raporlanır" demişti, bu alana bir isim verildi.
- 503 davranışı yeni bir try/except sarmalayıcı gerektirir. Mevcut uçlar şu an 500 döner;
  onlara dokunulmaz.

## Unknowns
- `/kayip-analizi` sayfasının sidebar'daki tam konumu ve ikonu. Plan aşamasında
  mevcut Sidebar'a bakılarak seçilecek.

## Sorular ve Cevaplar (ham kayıt)
Codex başarısız (`codex: No such file or directory`, exit 127), yedek kullanıldı.
Cevaplar Sonnet yedek alt-ajanı tarafından verildi.
0. Yorum ve slug → kullanıcı seçti: ürün özelliği, `kayip-musteri-postmortem` (kullanıcı mesajından)
1. Persona → tek kullanıcılı analist/öğrenci, jüriye sunum yapıyor
2. Hedef → modelin kaybedilen müşterileri önceden görüp görmediğini göstermek
3. Kapsam → `actual_churn==1`; toplu özet + liste + tek müşteri görünümü
4. Sınıflama → high/mid/low = caught/partial/missed; yanlış alarm yalnızca özette
5. SHAP → `top_reason` + global rank, yeniden hesap yok
6. Aksiyon uygulandı mı → kapsam dışı, `action_applied: null` + "Veri yok"
7. Uçlar → `GET /api/postmortem?outcome=&limit=` + `GET /api/postmortem/{id}`
8. Frontend → yeni `/kayip-analizi` sayfası + CustomerDetail'de Postmortem bölümü
9. Edge case'ler → 404 / 409 / 422 / boş 200 / null → "—"
10. Başarı ölçütü → sayım eşitliği, ±0.001, p95 <300ms
11. Test stratejisi → 0/100/0, coverage ≥%90
12. Kapsam dışı/riskler → yukarıdaki bölümlerde
