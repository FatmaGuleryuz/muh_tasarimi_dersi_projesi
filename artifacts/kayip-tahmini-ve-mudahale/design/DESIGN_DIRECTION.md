# Tasarım Yönü — Kayıp Tahmini & Müdahale Planları

Durum: prototip (`prototip.html`), kullanıcı onayı bekleniyor. Stitch'in ürettiği "form + kart ızgarası"
şablonu kullanıcı tarafından reddedildi ("yazılar bağımsız kare kutularda, klasik şablon").

## İlke: veri gazeteciliği, kutu yok
- Kart/kutu yok. Bölümler ince çizgilerle (hairline) ve büyük tipografiyle ayrılıyor.
- Tipografi: başlıklar ve büyük sayılar **Fraunces** (serif, ince/italik), arayüz metni **Plus Jakarta Sans** (mevcut marka fontu).
- Palet aynı (krem #F6F3EC, orman yeşili #1E3A28, amber #C77D2E, kiremit #BA3C2A). Risk her yerde renk ile birlikte metin ve konum olarak da kodlanıyor.
- Her sayfada tek bir güçlü görsel: Tahmin'de **risk spektrumu**, Planlar'da **kampanya nehri**.

## Kayıp Tahmini — "Senaryo Laboratuvarı"
- Form yerine okunan bir cümle: altı çizili kelimeler (sözleşme, süre, ücret, internet, teknik destek, ödeme, yaş) tıklanıp değiştirilir. Tahmin anında güncellenir.
- Sağda dev yüzde (rengi riske göre), tek cümlelik hüküm, 0,40 ve 0,70 eşikli spektrum üzerinde kayan işaret.
- "Olasılığı ne çekiyor?": iki yöne açılan çubuklar (sol azaltıyor, sağ artırıyor), en etkili 5 etken.
- "İlk hamle": en güçlü artırıcı etkene göre önerilen aksiyon.
- Gereken backend: model ile tek kayıt skorlayan bir tahmin ucu ve kayıt bazlı SHAP katkıları (bugün yok).

## Müdahale Planları — "Kampanya Nehri"
- Üstte üç büyük sayı: hedeflenen müşteri, plan sayısı, ortalama olasılık; sağda filtre (Yüksek + orta / Yalnızca yüksek).
- Her plan bir satır: sıra no, aksiyon, tetikleyen neden, müşteri sayısıyla orantılı kalınlık ve uzunlukta bant (kırmızı kısım yüksek risk payı).
- Satır açılınca: o plandaki her müşteri olasılık ekseninde bir nokta; ilk müşteri ID'leri ve CSV indirme.
- Altta otomatik içgörü cümlesi (ör. "Riskli müşterilerin %84'ü tek bir hamleye düşüyor").
- Gerçek veri (Telco, olasılık ≥ 0,40): 669 müşteri, 3 plan (560 / 108 / 1). Bu dengesizlik gizlenmiyor, bulgu olarak gösteriliyor.

## Açık konular
- Mobilde (≤900px) tek sütun; prototipte yalnızca masaüstünde (1440px) bakıldı.
- Nokta şeridinde 0,40'a yakın noktalar sol kenara biraz taşıyor; uygulamada düzeltilecek.
