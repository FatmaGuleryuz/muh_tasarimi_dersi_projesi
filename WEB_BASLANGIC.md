# Web arayüzü (Genel Bakış) — çalıştırma

İki terminal gerekir. Repo kökünden:

```bash
# 1) Backend (Python)
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --port 8000   # http://localhost:8000/docs

# 2) Web (Node 18+)
cd web
npm install
npm run dev                                          # http://localhost:5173
```

Backend, repo kökündeki `test_customers.csv`, `metrics.json`, `shap_scores.json` ve
`data/telco_churn_raw.csv` dosyalarını okur; önce `python src/train_model.py` çalışmış olmalıdır.
