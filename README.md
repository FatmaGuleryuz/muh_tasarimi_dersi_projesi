# Müşteri Kaybı Olasılığını Tahmin Eden Karar Destek Uygulaması

Fırat Üniversitesi — Bilgisayar Mühendisliği Tasarım Dersi — 76. Proje Grubu
(Remziye Beyzanur BIYIKLI, Fatma GÜLERYÜZ, Yusuf ÇİNAR)

Hafta 1 raporunda tanımlanan **H2** (churn tahmin modeli) ve **H6** (karar destek
arayüzü) hedeflerinin uçtan uca çalışan prototipi: veri seti indirme → temizleme →
model eğitimi → SHAP ile neden skorlama → Streamlit arayüzü.

## Veri Seti

**IBM Telco Customer Churn** (kamuya açık), 7.043 müşteri, 21 sütun, churn oranı ~%26,5.
`data/telco_churn_raw.csv` olarak GitHub mirror'ından (`IBM/telco-customer-churn-on-icp4d`)
indirilmiştir.

## Kurulum ve Çalıştırma

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

pip install pandas numpy scikit-learn xgboost shap streamlit matplotlib joblib

python src/train_model.py      # veri temizleme + 3 model eğitimi + SHAP skorlama
python src/palette.py          # renk paleti üretimi (WCAG AA kontrast kontrollü)

streamlit run app.py           # arayüzü başlatır (http://localhost:8501)
```

## Yöntem

1. **Veri hazırlama** (`src/train_model.py`): `TotalCharges` sütunundaki boş
   string'ler sayısala çevrilir, eksik değerler (11 satır) median ile doldurulur
   ve loglanır; kategorik alanlar `LabelEncoder` ile kodlanır; %80/%20 stratified
   train/test ayrımı yapılır.
2. **Model eğitimi**: Lojistik Regresyon, Random Forest ve XGBoost — sınıf
   dengesizliği `class_weight="balanced"` / `scale_pos_weight` ile ele alınır.
   Her model için ROC-AUC, Precision, Recall, F1 hesaplanır; en iyi model
   (en yüksek ROC-AUC) seçilir.
3. **SHAP neden skorlama**: En iyi modelin SHAP değerleri hesaplanır, her
   değişkenin kayıptaki ortalama mutlak katkısı ("neden skoru") büyükten
   küçüğe sıralanır (`shap_scores.json`, `shap_summary.png`). Her test
   müşterisi için en yüksek katkılı değişken "ana neden" olarak, literatürden
   derlenen neden→çözüm eşlemesiyle "önerilen çözüm" olarak atanır.
4. **Palet**: `src/palette.py`, arayüz renklerini WCAG AA kontrast oranı
   (≥4,5:1) kontrolünden geçirip `palette.json`'a kaydeder; arayüz renkleri
   hardcode değil bu dosyadan okunur.
5. **Arayüz** (`app.py`, Streamlit): test setindeki bir müşteri seçilince
   kayıp olasılığı, ana neden ve önerilen çözüm gösterilir; sağ panelde
   SHAP neden sıralaması grafiği, alt bölümde teknik bilgiler (kullanılan
   modeller, ROC-AUC, veri seti büyüklüğü, kütüphane sürümleri) yer alır.

## Sonuçlar (bu çalıştırma)

| Model | ROC-AUC | Precision | Recall | F1 |
|---|---|---|---|---|
| Logistic Regression | 0.840 | bkz. `metrics.json` | | |
| Random Forest | 0.822 | | | |
| XGBoost | 0.812 | | | |

**En iyi model:** Logistic Regression — ROC-AUC 0,840 (hedef 0,84'e çok yakın,
tam karşılanmadı; `metrics.json`'da `target_met: false` olarak işaretli).
Gerçek skorlar bir sonraki eğitim çalıştırmasında değişebilir — güncel
değerler her zaman `metrics.json`'dan okunmalıdır.

## Çıktı Dosyaları

| Dosya | İçerik |
|---|---|
| `model.joblib` | En iyi eğitilmiş model |
| `encoder.joblib` | Kategorik encoder'lar + scaler + özellik adları |
| `metrics.json` | 3 modelin metrikleri + hedef karşılama durumu |
| `shap_scores.json` | Değişken → ortalama mutlak SHAP katkısı (sıralı) |
| `shap_summary.png` | En önemli 10 nedenin grafiği |
| `palette.json` | Arayüz renk paleti + WCAG AA kontrast sonuçları |
| `test_customers.csv` | Test seti: müşteri ID, olasılık, neden, öneri |

## Kapsam Dışı (bu prototipte)

- Gerçek +1/−1 adım otomasyonu (Hafta 6–9 hedefi)
- Canlı CRM/veritabanı entegrasyonu, cloud deployment
- Kullanıcının kendi CSV'sini yükleyip serbest sorgu yapması (arayüz yalnızca
  mevcut test seti müşterilerinden seçim sunar)

## Kaynaklar

Rapordaki kaynakça (`Hafta1_Proje_Raporu_Postmortem.docx`, Bölüm "KAYNAKLAR")
ile aynıdır: Ahmad vd. (2019), Breiman (2001), Chawla vd. (2002) [SMOTE],
Chen & Guestrin (2016) [XGBoost], Lundberg & Lee (2017) [SHAP], Verbeke vd.
(2012), Wirth & Hipp (2000) [CRISP-DM], IBM Telco Customer Churn veri seti.
