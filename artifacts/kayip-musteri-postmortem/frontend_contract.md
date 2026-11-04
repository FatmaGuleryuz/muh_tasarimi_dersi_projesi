# Frontend Contract — kayip-musteri-postmortem
_Reference: atdd.md (Davranış Sözleşmesi)_

Not: Backend aynı görevde yazılıyor ve şekli atdd.md'de zaten sabitlendi.
Bu yüzden mock servis ve adaptör katmanı EKLENMEZ (ponytail). UI, mevcut
`lib/api.ts` desenini izleyerek gerçek uca bağlanır; bu desen sayfadan
fetch URL'sini zaten soyutluyor.

## Ekran 1 — `/kayip-analizi` (LossAnalysis.tsx)
Veri: `fetchPostmortem({outcome?})` → `{summary, total, items[]}` (atdd.md şeması).
- Özet kartları (KpiCard): Kaybedilen (lost_total), Yakalandı (caught), Kısmen (partial),
  Kaçırıldı (missed), Yakalama oranı (catch_rate, alt metinde strict_catch_rate),
  Yanlış alarm (false_alarm_count, alt metinde precision_high).
- Filtre: outcome düğmeleri, "Tümü / Yakalandı / Kısmen / Kaçırıldı". Bir filtre seçilince
  yalnızca liste yenilenir, özet değişmez (AC-3).
- Liste satırı: customer_id, outcome rozeti, olasılık (pct), RiskBadge, ana neden, aksiyon.
  Satıra tıklanınca `/musteri-riski/:id` açılır (AC-11).
- Bilgi notu: "Analiz etiketli test seti üzerindedir; aksiyonların uygulanıp uygulanmadığı
  verisi tutulmuyor."

Durumlar:
| UI durumu | Tetik | Gösterim | atdd satırı |
|---|---|---|---|
| loading | istek sürüyor | "Yükleniyor…" | — |
| success | 200, items ≥1 | kartlar + liste | 1 |
| empty (filtre) | 200, items=[], lost_total>0 | "Bu filtrede müşteri yok" | 1 |
| empty (hiç kayıp yok) | 200, lost_total=0 | kartlar 0 + "Kaybedilmiş müşteri bulunamadı" | 8 |
| error | 503 ya da ağ hatası | brick renkli hata kutusu + "Tekrar Dene" | 5 |
| invalid filter | 422 | UI yalnızca geçerli değer gönderdiği için oluşmaz; oluşursa genel hata kutusu gösterilir | 2 |

## Ekran 2 — CustomerDetail içinde "Postmortem" bölümü
Yalnızca `data.actual_churn === true` olduğunda render edilir ve yalnızca o durumda
`fetchPostmortemDetail(id)` çağrılır (AC-12). False ise istek atılmaz.
- outcome rozeti + açıklama ("Model bu müşteriyi yüksek riskte görmüştü" / "orta" / "düşük — kaçırıldı")
- Birincil neden + genel sıralamadaki yeri (`top_reason_global_rank`; null ise "sıralama bilgisi yok")
- Önerilen aksiyon + "Aksiyon uygulandı mı: Veri yok"
- Bölüm hatası (503 vb.) yalnızca bölüm içinde gösterilir, sayfanın geri kalanı bozulmaz.

## Ortak bileşen
`OutcomeBadge` (caught = forest, partial = amber, missed = brick). Her iki ekranda kullanılır.
Yalnızca renge dayanmaz, rozet metni de taşır.

## Backend'e istekler/sorular
Yok. Şekil atdd.md'de sabit.
