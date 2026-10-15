"""Musteri Kaybi (Churn) Karar Destek Arayuzu — Streamlit.
Calistirma: streamlit run app.py
"""
import json
import sys

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Churn Karar Destek", page_icon="📉", layout="wide")


@st.cache_data
def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_customers():
    return pd.read_csv("test_customers.csv")


def inject_palette_css(palette: dict):
    st.markdown(
        f"""
        <style>
        .stApp {{ background-color: {palette['background']}; color: {palette['text_primary']}; }}
        .card {{
            background-color: {palette['surface']};
            border: 1px solid {palette['border']};
            border-radius: 10px;
            padding: 1.2rem;
            margin-bottom: 1rem;
        }}
        .metric-big {{ font-size: 2.2rem; font-weight: 700; }}
        .muted {{ color: {palette['text_secondary']}; font-size: 0.85rem; }}
        .badge-danger {{ color: {palette['danger']}; font-weight: 700; }}
        .badge-success {{ color: {palette['success']}; font-weight: 700; }}
        .badge-warning {{ color: {palette['warning']}; font-weight: 700; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


REQUIRED_FILES = ["palette.json", "metrics.json", "shap_scores.json", "test_customers.csv"]


def main():
    missing = [f for f in REQUIRED_FILES if not __import__("os").path.exists(f)]
    if missing:
        st.error(
            "Gerekli dosyalar bulunamadı: "
            + ", ".join(missing)
            + ". Önce `python src/train_model.py` ve `python src/palette.py` çalıştırın."
        )
        st.stop()

    palette = load_json("palette.json")
    metrics = load_json("metrics.json")
    shap_scores = load_json("shap_scores.json")
    customers = load_customers()

    inject_palette_css(palette)

    st.title("📉 Müşteri Kaybı Karar Destek Uygulaması")
    st.caption("Fırat Üniversitesi — 76. Proje Grubu — Hafta 1 prototipi (IBM Telco Customer Churn veri seti)")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("### Müşteri Sorgula")
        customer_ids = customers["customerID"].tolist()
        selected = st.selectbox("Müşteri ID seçin", options=customer_ids)

        row = customers[customers["customerID"] == selected]
        if row.empty:
            st.warning("Müşteri bulunamadı.")
            st.stop()
        row = row.iloc[0]

        prob = float(row["churn_probability"])
        reason = row["top_reason"]
        action = row["suggested_action"]

        badge_class = "badge-danger" if prob >= 0.5 else "badge-success"
        st.markdown(
            f"""
            <div class="card">
              <div class="muted">Kayıp Olasılığı</div>
              <div class="metric-big {badge_class}">%{prob * 100:.1f}</div>
              <hr style="border-color:{palette['border']}">
              <div class="muted">Ana Neden</div>
              <div style="font-size:1.1rem; font-weight:600;">{reason}</div>
              <div class="muted" style="margin-top:0.6rem;">Önerilen Çözüm</div>
              <div style="font-size:1.0rem;">{action}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown("### En Önemli Churn Nedenleri (SHAP)")
        top_n = dict(list(shap_scores.items())[:8])
        st.bar_chart(pd.Series(top_n))
        st.image("shap_summary.png", use_container_width=True)

    st.markdown("---")
    st.markdown("### 🔧 Teknik Bilgiler")
    tcol1, tcol2, tcol3 = st.columns(3)

    with tcol1:
        st.markdown("**Kullanılan Modeller**")
        for name, m in metrics["models"].items():
            st.write(f"- `{name}`: ROC-AUC {m['roc_auc']:.3f}")
        st.write(f"**En iyi model:** `{metrics['best_model']}`")

    with tcol2:
        target_status = "✅ Karşılandı" if metrics["target_met"] else "⚠️ Karşılanmadı"
        st.markdown("**Hedef Doğrulama**")
        st.write(f"- Hedef ROC-AUC: {metrics['target_roc_auc']}")
        st.write(f"- Durum: {target_status}")
        st.write(f"- Veri seti: {metrics['dataset']['rows']} müşteri")
        st.write(f"- Churn oranı: %{metrics['dataset']['churn_rate'] * 100:.1f}")

    with tcol3:
        st.markdown("**Kütüphane Sürümleri**")
        st.write(f"- Python: {sys.version.split()[0]}")
        import sklearn
        import xgboost
        import shap as shap_lib
        st.write(f"- scikit-learn: {sklearn.__version__}")
        st.write(f"- xgboost: {xgboost.__version__}")
        st.write(f"- shap: {shap_lib.__version__}")
        st.write(f"- streamlit: {st.__version__}")


if __name__ == "__main__":
    main()
