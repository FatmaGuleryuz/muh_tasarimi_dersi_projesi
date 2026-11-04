"""Model özellik adlarını (SHAP / encoder) ekranda gösterilecek Türkçe etiketlere çevirir."""

FEATURES = {
    "tenure": "Müşteri olma süresi",
    "MonthlyCharges": "Aylık ücret",
    "TotalCharges": "Toplam ücret",
    "AvgMonthlySpend": "Ortalama aylık harcama",
    "SeniorCitizen": "65 yaş üstü müşteri",
    "NumAdditionalServices": "Ek hizmet sayısı",
    # openml_churn özellikleri
    "account_length": "Hesap süresi (gün)",
    "international_plan": "Uluslararası arama paketi",
    "voice_mail_plan": "Sesli mesaj paketi",
    "number_vmail_messages": "Sesli mesaj sayısı",
    "total_day_minutes": "Gündüz dakika",
    "total_day_calls": "Gündüz çağrı sayısı",
    "total_day_charge": "Gündüz ücreti",
    "total_eve_minutes": "Akşam dakika",
    "total_eve_calls": "Akşam çağrı sayısı",
    "total_eve_charge": "Akşam ücreti",
    "total_night_minutes": "Gece dakika",
    "total_night_calls": "Gece çağrı sayısı",
    "total_night_charge": "Gece ücreti",
    "total_intl_minutes": "Uluslararası dakika",
    "total_intl_calls": "Uluslararası çağrı sayısı",
    "total_intl_charge": "Uluslararası ücret",
    "number_customer_service_calls": "Müşteri hizmetlerini arama sayısı",
    "total_minutes": "Toplam dakika",
    "total_calls": "Toplam çağrı sayısı",
    "total_charge": "Toplam ücret",
}

GROUPS = {
    "state": "Eyalet",
    "area_code": "Alan kodu",
    "Contract": "Sözleşme",
    "OnlineSecurity": "Çevrimiçi güvenlik",
    "OnlineBackup": "Çevrimiçi yedekleme",
    "DeviceProtection": "Cihaz koruma",
    "TechSupport": "Teknik destek",
    "StreamingTV": "TV yayın hizmeti",
    "StreamingMovies": "Film yayın hizmeti",
    "InternetService": "İnternet hizmeti",
    "PhoneService": "Telefon hizmeti",
    "MultipleLines": "Çoklu hat",
    "PaperlessBilling": "E-fatura",
    "PaymentMethod": "Ödeme yöntemi",
    "Partner": "Eş/partner",
    "Dependents": "Bakmakla yükümlü olduğu kişi",
    "gender": "Cinsiyet",
    "tenure_group": "Süre grubu",
}

VALUES = {
    "Month-to-month": "Aylık",
    "One year": "1 yıllık",
    "Two year": "2 yıllık",
    "Yes": "var",
    "No": "yok",
    "Fiber optic": "Fiber optik",
    "DSL": "DSL",
    "Electronic check": "Elektronik çek",
    "Mailed check": "Posta çeki",
    "Bank transfer (automatic)": "Banka havalesi (otomatik)",
    "Credit card (automatic)": "Kredi kartı (otomatik)",
    "No internet service": "internet hizmeti yok",
    "No phone service": "telefon hizmeti yok",
    "Female": "Kadın",
    "Male": "Erkek",
}

CONTRACTS = {"Month-to-month": "Aylık", "One year": "1 yıllık", "Two year": "2 yıllık"}


def label_for(feature: str) -> str:
    """'Contract_Month-to-month' -> 'Sözleşme: Aylık'."""
    if feature in FEATURES:
        return FEATURES[feature]
    for prefix in sorted(GROUPS, key=len, reverse=True):  # en uzun önek önce (tenure_group)
        if feature.startswith(prefix + "_"):
            value = feature[len(prefix) + 1:]
            if prefix == "tenure_group":
                return f"{GROUPS[prefix]}: {value} ay"
            return f"{GROUPS[prefix]}: {VALUES.get(value, value)}"
    return feature
