"""Model özellik adlarını (SHAP / encoder) ekranda gösterilecek Türkçe etiketlere çevirir."""

FEATURES = {
    "tenure": "Müşteri olma süresi",
    "MonthlyCharges": "Aylık ücret",
    "TotalCharges": "Toplam ücret",
    "AvgMonthlySpend": "Ortalama aylık harcama",
    "SeniorCitizen": "65 yaş üstü müşteri",
    "NumAdditionalServices": "Ek hizmet sayısı",
}

GROUPS = {
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
