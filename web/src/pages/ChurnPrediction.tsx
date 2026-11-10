import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import PageHeader from "../components/PageHeader";
import { predict } from "../lib/api";
import { dec, num, pct } from "../lib/format";
import type { ContractType, InternetService, PaymentMethod, PredictRequest, PredictResponse, RiskLevel } from "../lib/types";

const DEFAULTS: PredictRequest = {
  contract: "Month-to-month",
  tenure: 12,
  monthly_charges: 75,
  internet_service: "Fiber optic",
  tech_support: false,
  online_security: false,
  payment_method: "Electronic check",
  senior_citizen: false,
};

const UNSUPPORTED_MSG = "Senaryo tahmini yalnızca Telco veri setinde destekleniyor";

const PAYMENTS: { value: PaymentMethod; label: string }[] = [
  { value: "Electronic check", label: "Elektronik çek" },
  { value: "Mailed check", label: "Posta çeki" },
  { value: "Bank transfer (automatic)", label: "Otomatik banka havalesi" },
  { value: "Credit card (automatic)", label: "Otomatik kredi kartı" },
];

const VERDICT: Record<RiskLevel, string> = {
  high: "Ayrılma eğilimi kritik eşiğin üzerinde; bu profil için hemen müdahale önerilir.",
  mid: "Ayrılma riski orta düzeyde; profil yakından izlenmeli ve önleyici hamle düşünülmeli.",
  low: "Ayrılma eğilimi düşük; bu profil şu an güvenli bölgede görünüyor.",
};

const RISK_TEXT: Record<RiskLevel, { label: string; text: string; bg: string }> = {
  high: { label: "Kritik risk alanı (≥ %70)", text: "text-brick", bg: "bg-brick/10 border-brick/20" },
  mid: { label: "Orta risk alanı (%40 – %70)", text: "text-amber", bg: "bg-amber/10 border-amber/20" },
  low: { label: "Düşük risk alanı (< %40)", text: "text-sage", bg: "bg-sage/10 border-sage/20" },
};

function Segment<T extends string | boolean>({
  label, options, value, onChange, disabled = false, describedBy,
}: { label: string; options: { value: T; label: string }[]; value: T; onChange: (v: T) => void; disabled?: boolean; describedBy?: string }) {
  return (
    <div
      role="radiogroup" aria-label={label} aria-disabled={disabled || undefined} aria-describedby={describedBy}
      className={`flex flex-wrap items-center justify-end gap-x-4 gap-y-1 ${disabled ? "opacity-50" : ""}`}
    >
      {options.map((o) => {
        const on = o.value === value;
        return (
          <button
            key={String(o.value)}
            type="button"
            role="radio"
            aria-checked={on}
            aria-disabled={disabled || undefined}
            onClick={() => { if (!disabled) onChange(o.value); }}
            className={`focus-ring border-b-2 pb-0.5 text-xs transition-colors ${disabled ? "cursor-not-allowed " : ""}${
              on ? "border-forest font-bold text-forest" : "border-transparent font-semibold text-ink-2 hover:text-ink"
            }`}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

function Row({ title, hint, htmlFor, note, noteId, children }: {
  title: string; hint?: string; htmlFor?: string; note?: string; noteId?: string; children: ReactNode;
}) {
  return (
    <div className="border-b border-line py-3.5">
      <div className="flex items-center justify-between gap-4">
        <div className="flex min-w-0 flex-col">
          {htmlFor ? (
            <label htmlFor={htmlFor} className="text-sm font-medium">{title}</label>
          ) : (
            <span className="text-sm font-medium">{title}</span>
          )}
          {hint && <span className="text-[11px] text-ink-2">{hint}</span>}
        </div>
        <div className="min-w-0 shrink-0">{children}</div>
      </div>
      {note && <p id={noteId} className="pt-1.5 text-right text-[11px] text-ink-2">{note}</p>}
    </div>
  );
}

export default function ChurnPrediction() {
  const [form, setForm] = useState<PredictRequest>(DEFAULTS);
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [unsupported, setUnsupported] = useState(false);

  const [chargesText, setChargesText] = useState(String(DEFAULTS.monthly_charges));
  const [chargesInvalid, setChargesInvalid] = useState(false);
  const noNet = form.internet_service === "No";

  const set = <K extends keyof PredictRequest>(k: K, v: PredictRequest[K]) => setForm((f) => ({ ...f, [k]: v }));

  const parseCharges = (t: string) => {
    const n = Number(t.trim().replace(",", "."));
    return t.trim() !== "" && Number.isFinite(n) ? n : null;
  };
  const onChargesChange = (t: string) => {
    setChargesText(t);
    const n = parseCharges(t);
    const ok = n !== null && n >= 18 && n <= 120;
    setChargesInvalid(!ok);
    if (ok) set("monthly_charges", n);
  };
  const onChargesBlur = () => {
    const n = parseCharges(chargesText);
    const v = n === null ? form.monthly_charges : Math.min(120, Math.max(18, n));
    setChargesText(String(v));
    setChargesInvalid(false);
    set("monthly_charges", v);
  };
  const resetForm = () => {
    setForm(DEFAULTS);
    setChargesText(String(DEFAULTS.monthly_charges));
    setChargesInvalid(false);
  };

  useEffect(() => {
    const ctrl = new AbortController();
    setLoading(true);
    const timer = setTimeout(() => {
      const body = form.internet_service === "No" ? { ...form, tech_support: false, online_security: false } : form;
      predict(body, ctrl.signal)
        .then((r) => {
          setResult(r);
          setError(null);
          setUnsupported(false);
          setLoading(false);
        })
        .catch((e: Error) => {
          if (ctrl.signal.aborted) return;
          setResult(null);
          if (e.message === UNSUPPORTED_MSG) {
            setUnsupported(true);
            setError(null);
          } else {
            setError(e.message);
          }
          setLoading(false);
        });
    }, 300);
    return () => {
      clearTimeout(timer);
      ctrl.abort();
    };
  }, [form]);

  const isDefault = JSON.stringify(form) === JSON.stringify(DEFAULTS);
  const maxAbs = result ? Math.max(0.0001, ...result.drivers.map((d) => Math.abs(d.contribution))) : 1;
  const riskTone = result ? RISK_TEXT[result.risk] : null;

  return (
    <>
      <PageHeader title="Kayıp Tahmini" badge="What-if simülasyonu" />

      <main className="mx-auto flex max-w-7xl flex-col px-5 pb-16 pt-8 sm:px-8">
        <header className="flex flex-col justify-between gap-4 border-b border-line pb-6 md:flex-row md:items-end">
          <div className="max-w-2xl">
            <h2 className="font-serif text-4xl font-normal tracking-tight text-forest">Kayıp Tahmini</h2>
            <p className="pt-2 text-sm text-ink-2">
              Varsayımsal müşteri parametrelerini değiştirerek anlık model çıktısını ve SHAP etkenlerini izleyin.
            </p>
          </div>
          {result && (
            <p className="text-[11px] font-semibold tracking-wide text-ink-2">
              <span className="text-forest">{result.model_label}</span> · ROC-AUC <span className="num text-ink">{dec(result.roc_auc)}</span>
            </p>
          )}
        </header>

        <div className="grid grid-cols-12 gap-8 pt-8 lg:gap-14">
          {/* SOL: parametreler */}
          <section className="col-span-12 min-w-0 lg:col-span-5">
            <div className="flex items-baseline justify-between border-b border-line pb-3">
              <h3 className="text-[11px] font-semibold uppercase tracking-widest text-ink-2">01 / Senaryo parametreleri</h3>
              <button
                type="button"
                onClick={resetForm}
                disabled={isDefault}
                className="focus-ring text-[11px] font-semibold text-ink-2 underline decoration-line underline-offset-4 hover:text-forest disabled:opacity-50"
              >
                Varsayılana sıfırla
              </button>
            </div>

            <form onSubmit={(e) => e.preventDefault()} className="flex flex-col">
              <Row title="Sözleşme" hint="Taahhüt süresi">
                <Segment<ContractType>
                  label="Sözleşme"
                  value={form.contract}
                  onChange={(v) => set("contract", v)}
                  options={[{ value: "Month-to-month", label: "Aylık" }, { value: "One year", label: "1 Yıl" }, { value: "Two year", label: "2 Yıl" }]}
                />
              </Row>

              <div className="border-b border-line py-3.5">
                <div className="flex items-center justify-between">
                  <label htmlFor="tenure" className="text-sm font-medium">Müşteri süresi</label>
                  <output htmlFor="tenure" className="num font-serif text-lg font-medium text-forest">{form.tenure} ay</output>
                </div>
                <input
                  id="tenure" type="range" min={0} max={72} step={1} value={form.tenure}
                  onChange={(e) => set("tenure", Number(e.target.value))}
                  className="scn-range focus-ring mt-3"
                />
                <div className="flex justify-between pt-1 text-[10px] text-ink-2">
                  <span>Yeni (0 ay)</span><span>Sadık (72 ay)</span>
                </div>
              </div>

              <Row title="Aylık hizmet tutarı" hint="18 – 120 aralığında" htmlFor="charges" note={chargesInvalid ? "18 – 120 arasında olmalı" : undefined} noteId="charges-hint">
                <div className="flex items-baseline gap-1">
                  <span className="text-sm text-ink-2">₺</span>
                  <input
                    id="charges" type="text" inputMode="decimal" autoComplete="off"
                    value={chargesText}
                    aria-invalid={chargesInvalid}
                    aria-describedby={chargesInvalid ? "charges-hint" : undefined}
                    onChange={(e) => onChargesChange(e.target.value)}
                    onBlur={onChargesBlur}
                    className="focus-ring num w-20 border-0 border-b border-ink-3 bg-transparent p-0 text-right text-lg font-bold text-forest focus:border-forest"
                  />
                  <span className="text-[11px] text-ink-2">/ ay</span>
                </div>
              </Row>

              <Row title="İnternet" hint="Bağlantı teknolojisi">
                <Segment<InternetService>
                  label="İnternet"
                  value={form.internet_service}
                  onChange={(v) => set("internet_service", v)}
                  options={[{ value: "Fiber optic", label: "Fiber optik" }, { value: "DSL", label: "DSL" }, { value: "No", label: "Yok" }]}
                />
              </Row>

              <Row title="Teknik destek" note={noNet ? "İnternet hizmeti olmadan uygulanmaz" : undefined} noteId="tech-note">
                <Segment<boolean>
                  label="Teknik destek" disabled={noNet} describedBy={noNet ? "tech-note" : undefined} value={noNet ? false : form.tech_support} onChange={(v) => set("tech_support", v)}
                  options={[{ value: true, label: "Var" }, { value: false, label: "Yok" }]}
                />
              </Row>

              <Row title="Çevrimiçi güvenlik" note={noNet ? "İnternet hizmeti olmadan uygulanmaz" : undefined} noteId="sec-note">
                <Segment<boolean>
                  label="Çevrimiçi güvenlik" disabled={noNet} describedBy={noNet ? "sec-note" : undefined} value={noNet ? false : form.online_security} onChange={(v) => set("online_security", v)}
                  options={[{ value: true, label: "Var" }, { value: false, label: "Yok" }]}
                />
              </Row>

              <Row title="Ödeme" hint="Tahsilat şekli" htmlFor="payment">
                <select
                  id="payment" value={form.payment_method}
                  onChange={(e) => set("payment_method", e.target.value as PaymentMethod)}
                  className="focus-ring max-w-[11rem] cursor-pointer border-0 border-b border-ink-3 bg-transparent py-0.5 pl-0 pr-1 text-xs font-semibold text-forest focus:border-forest sm:max-w-none"
                >
                  {PAYMENTS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
                </select>
              </Row>

              <Row title="65 yaş üstü">
                <Segment<boolean>
                  label="65 yaş üstü" value={form.senior_citizen} onChange={(v) => set("senior_citizen", v)}
                  options={[{ value: false, label: "Hayır" }, { value: true, label: "Evet" }]}
                />
              </Row>
            </form>

            <p className="pt-4 text-[11px] italic text-ink-2">
              Parametre değişiklikleri anlık olarak modele yansıtılır. Formda olmayan alanlar tipik müşteri değerleriyle dolduruluyor.
            </p>
          </section>

          {/* SAĞ: çıkarım */}
          <section className="col-span-12 flex min-w-0 flex-col lg:col-span-7">
            <div className="border-b border-line pb-3">
              <h3 className="text-[11px] font-semibold uppercase tracking-widest text-ink-2">02 / Çıkarım ve risk analizi</h3>
            </div>

            {unsupported && (
              <p className="py-16 font-serif text-xl italic text-ink-2">Bu veri setinde senaryo tahmini desteklenmiyor</p>
            )}

            {error && (
              <div role="alert" className="mt-4 border-y border-brick/40 bg-brick/5 px-1 py-2.5 text-xs text-brick">
                Tahmin alınamadı: {error}
              </div>
            )}

            {!result && !error && !unsupported && <p className="py-10 text-sm text-ink-2">Yükleniyor…</p>}

            {result && riskTone && (
              <div className={`flex flex-col transition-opacity duration-200 ${loading ? "opacity-50" : "opacity-100"}`} aria-busy={loading}>
                <div className="flex flex-col gap-6 pb-8 pt-6 sm:flex-row sm:items-center sm:gap-10">
                  <div className="flex flex-col">
                    <span aria-live="polite" className={`num font-serif text-7xl font-normal leading-none tracking-tighter sm:text-8xl lg:text-9xl ${riskTone.text}`}>
                      {pct(result.probability, 0)}
                    </span>
                    <span className={`mt-3 inline-block self-start rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${riskTone.bg} ${riskTone.text}`}>
                      {riskTone.label}
                    </span>
                  </div>
                  <div className="flex flex-1 items-center border-line sm:border-l sm:pl-8">
                    <p className="font-serif text-xl italic leading-snug text-ink lg:text-2xl">{VERDICT[result.risk]}</p>
                  </div>
                </div>

                {/* Spektrum */}
                <div className="pb-10">
                  <div className="relative w-full">
                    <div className="flex h-1.5 w-full overflow-hidden">
                      <div className="w-[40%] bg-sage/80" />
                      <div className="w-[30%] bg-amber" />
                      <div className="w-[30%] bg-brick" />
                    </div>
                    <span
                      aria-hidden
                      className="absolute top-[3px] h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rotate-45 bg-forest-dark transition-all duration-300"
                      style={{ left: `${Math.min(100, Math.max(0, result.probability * 100))}%` }}
                    />
                  </div>
                  <div className="relative flex w-full justify-between pt-3 text-[11px] text-ink-2">
                    <span>Düşük risk (0,00)</span>
                    <span className="absolute left-[40%] -translate-x-1/2 text-[10px]">Eşik: 0,40</span>
                    <span className="absolute left-[70%] -translate-x-1/2 text-[10px]">Eşik: 0,70</span>
                    <span>Kritik (1,00)</span>
                  </div>
                  <p className="pt-3 text-[11px] font-bold text-forest">Mevcut senaryo: {pct(result.probability)}</p>
                </div>

                {/* SHAP */}
                <div className="flex flex-col">
                  <div className="flex flex-col justify-between gap-1 border-b border-line pb-3 sm:flex-row sm:items-center">
                    <div className="flex flex-col">
                      <h4 className="text-[11px] font-bold uppercase tracking-wider text-forest">Risk sürücüleri (SHAP)</h4>
                      <span className="text-[10px] text-ink-2">Katkılar log-odds biriminde; büyüklükler göreli.</span>
                    </div>
                    <span className="text-[11px] text-ink-2">← Olasılığı azaltanlar | Olasılığı artıranlar →</span>
                  </div>
                  <ul className="flex flex-col divide-y divide-line">
                    {result.drivers.map((d) => {
                      const pos = d.contribution >= 0;
                      const w = (Math.abs(d.contribution) / maxAbs) * 62;
                      const val = `${pos ? "+" : "−"}${dec(Math.abs(d.contribution), 2)}`;
                      return (
                        <li key={d.feature} className="grid grid-cols-12 items-center gap-2 py-2.5 text-xs">
                          <span className="col-span-5 min-w-0 truncate font-medium" title={d.label}>{d.label}</span>
                          <div className="col-span-7 flex items-center">
                            <div className="flex w-1/2 items-center justify-end gap-1.5 border-r border-ink-3 pr-1.5">
                              {!pos && (
                                <>
                                  <span className="num font-mono text-[11px] font-semibold text-sage">{val}</span>
                                  <div className="h-3 bg-sage transition-all duration-300" style={{ width: `${w}%` }} />
                                </>
                              )}
                            </div>
                            <div className="flex w-1/2 items-center gap-1.5 pl-1.5">
                              {pos && (
                                <>
                                  <div className="h-3 bg-brick transition-all duration-300" style={{ width: `${w}%` }} />
                                  <span className="num font-mono text-[11px] font-semibold text-brick">{val}</span>
                                </>
                              )}
                            </div>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                </div>

                {/* İlk hamle */}
                <div className="mt-8 flex flex-col justify-between gap-4 border-t border-line pt-6 md:flex-row md:items-center">
                  <div className="flex flex-1 flex-col gap-3 sm:flex-row sm:items-center sm:gap-3.5">
                    <span className="shrink-0 self-start bg-forest-dark px-2 py-1 font-mono text-[11px] font-bold tracking-wider text-white">İLK HAMLE</span>
                    <p className="font-serif text-base italic leading-snug text-ink">“{result.action}”</p>
                  </div>
                  <p className="text-xs font-bold text-forest md:text-right">
                    Bu senaryoya benzeyen {num(result.similar_count)} müşteri
                  </p>
                </div>
              </div>
            )}
          </section>
        </div>
      </main>
    </>
  );
}
