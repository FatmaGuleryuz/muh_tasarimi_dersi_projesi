"""Ortak test kurulumu.

- Repo kökünü sys.path'e ekler ki `backend.app.main` her çalıştırma biçiminde import edilebilsin.
- `load_json` @lru_cache ile sarılı; her testten önce ve sonra cache temizlenir,
  böylece bir testteki sahte/geçici veri diğer testlere sızmaz.
- Gerçek proje kökündeki metrics.json / shap_scores.json dosyalarına dokunulmaz;
  dosya-eksik senaryoları testlerde `tmp_path` ile monkeypatch edilen ROOT üzerinden kurulur.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.main import load_json  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_load_json_cache():
    load_json.cache_clear()
    yield
    load_json.cache_clear()
