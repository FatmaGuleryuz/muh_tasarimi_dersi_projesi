# Verify Report — kayip-musteri-postmortem
_Reference: atdd.md, code_diff.md, test_diff.md_

Ortam: proje `venv/` başka bir kullanıcı yoluna bağlı ve kırıktı (kullanıcı onayıyla yeniden oluşturuldu: Python 3.11,
backend/requirements*.txt). Eski venv silinmedi, scratchpad'e (`venv-broken`) taşındı. CI workflow dosyası yok.

## Verification Gates
| # | Gate | Result | Evidence / Reason |
|---|------|--------|--------------------|
| 1 | Dosya konumu | PASS | `git status`: main.py, App.tsx, Sidebar.tsx, api.ts, types.ts, CustomerDetail.tsx değişti (M); test_postmortem.py, LossAnalysis.tsx, OutcomeBadge.tsx yeni (??) |
| 2 | Build/derleme | FAIL (önceden var) / kısmi PASS | Backend import OK. `npm run build` = `tsc --noEmit && vite build`, tsc yüzünden exit 2. Hata, Button `icon` prop tipinin lucide ikonlarıyla uyuşmamasından geliyor ve değişmemiş dosyalarda da var (Overview 4, ModelReports 2, ComingSoon 1, CustomerRisk 1); yeni LossAnalysis'te 1 aynı sınıf hata. `vite build` tek başına exit 0. |
| 3 | Supabase | N/A | Supabase yok; veri CSV/JSON dosyalarından okunuyor. |
| 4 | Lint | N/A | Projede linter/formatter config'i yok (ruff/eslint/prettier yok). |
| 5 | Type check | FAIL (önceden var) | Gate 2'deki tsc çıktısı. Bu görevle gelen yeni bir hata sınıfı yok. |
| 6 | Unit/integration testler | PASS | `venv/Scripts/python.exe -m pytest backend/tests -q` → **24 passed** (postmortem + mevcut model_report). İlk koşuda AC-S1 traversal vakası test beklentisi yüzünden kırmızıydı; test-copilot düzeltti (router seviyesinde 404 "Not Found"). |
| 7 | E2E | PASS (manuel, Browser pane) | `/kayip-analizi`: 6 kart (374/211/107/56/%85,0/117), filtre düğmeleri ve liste geldi. Satır tıklandı → `/musteri-riski/8580-QVLOC`, Postmortem bölümü "Kaçırıldı / Genel sıralamada 1. / Veri yok" gösterdi. Kaybedilmemiş müşteride (4376-KFVRS) bölüm yok ve `/api/postmortem/4376…` isteği atılmadı (AC-12). |
| 8 | Lighthouse | N/A | Lighthouse MCP bu ortamda kurulu değil; atdd'de sayfa performans hedefi yok. |
| 9 | Erişilebilirlik | N/A | Gate 8 ile aynı. Not: liste satırına klavyeyle müşteri ID butonu üzerinden erişiliyor. |
| 10 | Güvenlik taraması | INCONCLUSIVE | `security-scan` runner'ı (`~/.claude/security-tools/venv`) bu makinede yok, tarama çalışmadı. |
| 11 | AI code review | PENDING (red-team) | |
| 12 | Görsel regresyon | PARTIAL | `vision-test` skill'i çalıştırılmadı (Codex CLI yok). Yerine Browser pane ekran görüntüsü doğrudan incelendi: masaüstünde (~800px) layout düzgün. 390px'te sabit 256px sidebar içeriği sıkıştırıyor; bu sorun tüm sayfalarda var (uygulama responsive değil) ve bu görevle gelmedi. |
| 13 | DAST (ZAP) | N/A | ZAP erişilebilir değil. AC-S1/S2 testlerle (gate 6) doğrulandı. |
| 14 | İnsan onayı | PENDING | |

## Red-team sonrası düzeltme turu
- `_load` artık `except Exception` ile her yükleme hatasını 503'e çeviriyor (red-team medium/reliability).
- Yeni testler: `test_ac7_unexpected_exception_type_returns_503[liste/detay]`, `test_ac7_detail_shap_load_failure_returns_503`.
- `pytest backend/tests -q` → **27 passed**.

## AC -> Test Mapping
AC-1..AC-10, AC-S1, AC-S2 → test_postmortem.py (test_diff.md tablosu) → hepsi PASS.
AC-11, AC-12 → gate 7 manuel tarayıcı kontrolü → PASS.

## Coverage / Quality Notes
- Coverage ölçülmedi (pytest-cov kurulu değil); hedef %90 doğrulanmadı.
- Canlı veri: lost_total 374, catch_rate 0.850, strict 0.564, precision_high 0.643.
- Veri tuhaflığı (bu görevden değil): 8580-QVLOC'un sözleşmesi "2 yıllık" ama `top_reason` "Sözleşme: Aylık".
  Kaynak test_customers.csv'deki top_reason; mevcut müşteri detay sayfası da aynı şeyi gösteriyor.

## ECC Danışman Bulguları
`ecc-build-error-resolver` (gate 2/5 FAIL) çağrılmadı: hata önceden var olan, kapsam dışı bir tip sorunu ve kök neden biliniyor.
`ecc-security-reviewer` (AC-S var) çağrılmadı: Codex yok, yedek ajan için ise bu oturumda otomatik izin kontrolü daha önce yanıt vermedi. red-team bu boşluğu kapsamalı.

## Refactor Aday Kontrolü
Refactor adayı yok. Diff minimal: tek yardımcı fonksiyon (`_load`), tekrar yok, derin nesting yok. `postmortem_detail` ile
`get_customer` arasında ~8 satırlık alan kopyası var; plan.md'de kabul edildi ve CAVEMAN'a uygun.
