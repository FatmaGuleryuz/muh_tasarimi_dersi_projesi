import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronDown, ChevronUp } from "lucide-react";
import Button from "../components/Button";
import PageHeader from "../components/PageHeader";
import { fetchInterventionPlans, interventionExportUrl } from "../lib/api";
import { num, pct } from "../lib/format";
import type { InterventionPlan, InterventionPlans as PlansData, PlanRisk, RiskLevel } from "../lib/types";

const FILTERS: { value: PlanRisk; label: string }[] = [
  { value: "high_mid", label: "Yüksek + Orta Risk" },
  { value: "high", label: "Yalnızca Yüksek Risk" },
];

const RISK_STYLE: Record<RiskLevel, { text: string; cls: string; label: string }> = {
  high: { text: "text-brick", cls: "bg-brick/10 border-brick/20 text-brick", label: "Yüksek risk" },
  mid: { text: "text-amber", cls: "bg-amber/10 border-amber/20 text-amber", label: "Orta risk" },
  low: { text: "text-sage", cls: "bg-sage/10 border-sage/20 text-sage", label: "Düşük risk" },
};

const dotColor = (p: number) => (p >= 0.7 ? "bg-brick" : "bg-amber");

/** Olasılık nokta şeridi: 0,40–1,00 ekseni; dikey yerleşim indekse bağlı deterministik. */
function DotStrip({ probabilities }: { probabilities: number[] }) {
  return (
    <div>
      <div className="relative h-24 w-full border-b border-ink-3/40" role="img" aria-label={`${probabilities.length} müşterinin olasılık dağılımı, 0,40 ile 1,00 arasında`}>
        <span className="absolute inset-y-0 border-l border-dashed border-ink-3" style={{ left: "50%" }} />
        {probabilities.map((p, i) => {
          const x = Math.min(100, Math.max(0, ((p - 0.4) / 0.6) * 100));
          const y = 8 + (((i * 37) % 100) / 100) * 78;
          const size = 4 + (i % 3);
          return (
            <span
              key={i}
              className={`absolute rounded-full opacity-70 ${dotColor(p)}`}
              style={{ left: `${x}%`, top: `${y}%`, width: size, height: size, transform: "translate(-50%, -50%)" }}
            />
          );
        })}
      </div>
      <div className="relative flex justify-between pt-2 font-mono text-[11px] text-ink-2">
        <span>0,40 (Eşik)</span>
        <span className="absolute left-1/2 -translate-x-1/2 text-brick">0,70 (Kritik eşik)</span>
        <span>1,00</span>
      </div>
    </div>
  );
}

function PlanBody({ plan, risk }: { plan: InterventionPlan; risk: PlanRisk }) {
  const navigate = useNavigate();
  return (
    <div className="pb-8 pl-0 sm:pl-10">
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 pt-2">
        <h4 className="text-[11px] font-bold uppercase tracking-wider text-forest">
          Olasılık dağılımı spektrumu{" "}
          <span className="font-normal normal-case tracking-normal text-ink-2">(0,40 – 1,00 aralığında {num(plan.count)} müşteri)</span>
        </h4>
        <span className="flex gap-4 text-[11px] text-ink-2">
          <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-amber" />Orta (0,40 – 0,70)</span>
          <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-brick" />Kritik (≥ 0,70)</span>
        </span>
      </div>
      <div className="pt-4"><DotStrip probabilities={plan.probabilities} /></div>

      <div className="mt-8 flex flex-wrap items-baseline justify-between gap-2 border-t border-line pt-6">
        <h4 className="font-serif text-lg font-semibold text-forest">
          Bu plana atanan öncelikli müşteriler <span className="font-sans text-xs font-normal text-ink-2">(ilk {plan.customers.length})</span>
        </h4>
        <a
          href={interventionExportUrl(plan.action, risk)}
          className="focus-ring text-xs font-semibold text-sage hover:underline"
        >
          CSV indir ({num(plan.count)} kayıt) ↓
        </a>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[34rem] border-collapse text-left">
          <thead>
            <tr className="border-b border-line">
              {["Müşteri ID", "Kayıp olasılığı", "Risk seviyesi", "Sözleşme", "Ana neden"].map((h) => (
                <th key={h} className="py-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-ink-3">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {plan.customers.map((c) => {
              const s = RISK_STYLE[c.risk];
              return (
                <tr
                  key={c.customer_id}
                  onClick={() => navigate(`/musteri-riski/${encodeURIComponent(c.customer_id)}`)}
                  className="cursor-pointer hover:bg-row-hover"
                >
                  <td className="py-3.5 pr-4 font-mono text-xs font-semibold">
                    <button type="button" className="focus-ring hover:underline">{c.customer_id}</button>
                  </td>
                  <td className={`num py-3.5 pr-4 font-serif text-lg font-semibold ${s.text}`}>{pct(c.probability)}</td>
                  <td className="py-3.5 pr-4">
                    <span className={`inline-block whitespace-nowrap rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${s.cls}`}>{s.label}</span>
                  </td>
                  <td className="py-3.5 pr-4 text-xs">{c.contract ?? "—"}</td>
                  <td className="py-3.5 text-xs">{c.reason}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function InterventionPlans() {
  const [risk, setRisk] = useState<PlanRisk>("high_mid");
  const [attempt, setAttempt] = useState(0);
  const [data, setData] = useState<PlansData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<number>(0);

  useEffect(() => {
    let active = true;
    setError(null);
    setData(null);
    setOpen(0);
    fetchInterventionPlans(risk)
      .then((r) => {
        if (active) setData(r);
      })
      .catch((e: Error) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [risk, attempt]);

  return (
    <>
      <PageHeader title="Müdahale Planları" />

      <main className="mx-auto flex max-w-7xl flex-col px-5 pb-16 sm:px-8">
        {/* Başlık */}
        <header className="flex flex-col justify-between gap-6 border-b border-line pb-8 pt-8 md:flex-row md:items-end">
          <div className="max-w-2xl">
            <h2 className="font-serif text-5xl font-semibold leading-[1.05] tracking-tight text-forest sm:text-6xl">Müdahale Planları</h2>
            <p className="pt-4 text-sm text-ink-2">
              Riskli müşterilerin model tarafından önerilen ilk proaktif aksiyona göre gruplandığı operasyonel müdahale havuzu.
            </p>
          </div>
          <div role="radiogroup" aria-label="Risk filtresi" className="inline-flex shrink-0 self-start rounded-lg border border-line p-1 md:self-end">
            {FILTERS.map((f) => {
              const on = f.value === risk;
              return (
                <button
                  key={f.value}
                  type="button"
                  role="radio"
                  aria-checked={on}
                  onClick={() => setRisk(f.value)}
                  className={`focus-ring rounded px-3.5 py-2 text-xs font-semibold transition-colors ${on ? "bg-forest text-white" : "text-ink-2 hover:bg-canvas"}`}
                >
                  {f.label}
                </button>
              );
            })}
          </div>
        </header>

        {error && (
          <div className="mt-6 flex items-center justify-between rounded border border-brick/30 bg-brick/10 px-5 py-4 text-sm text-brick">
            <span>Veri yüklenemedi: {error}</span>
            <Button variant="secondary" onClick={() => setAttempt((a) => a + 1)}>Tekrar Dene</Button>
          </div>
        )}
        {!data && !error && <p className="py-8 text-sm text-ink-2">Yükleniyor…</p>}

        {data && (
          <>
            {/* Üç büyük sayı */}
            <div className="grid grid-cols-1 gap-6 border-b border-line py-8 sm:grid-cols-3 sm:gap-0">
              {[
                { v: num(data.summary.targeted), l: "Hedeflenen müşteri" },
                { v: num(data.summary.plans), l: "Aktif müdahale planı" },
                { v: pct(data.summary.avg_probability), l: "Küme ortalama kayıp olasılığı" },
              ].map((k, i) => (
                <div key={k.l} className={`min-w-0 ${i > 0 ? "sm:border-l sm:border-line sm:pl-8" : ""}`}>
                  <div className="num font-serif text-5xl font-normal tracking-tight text-forest sm:text-6xl">{k.v}</div>
                  <div className="pt-2 text-[11px] font-semibold uppercase tracking-wider text-ink-2">{k.l}</div>
                </div>
              ))}
            </div>

            {data.summary.targeted === 0 || data.plans.length === 0 ? (
              <p className="py-16 font-serif text-xl italic text-ink-2">Bu filtrede müdahale gerektiren müşteri yok</p>
            ) : (
              <>
                {/* Plan listesi */}
                <section aria-labelledby="plan-list-title">
                  <div className="hidden grid-cols-12 items-center gap-4 border-b border-line py-5 text-[11px] font-semibold uppercase tracking-widest text-ink-2 md:grid">
                    <h3 id="plan-list-title" className="col-span-6">01 / Plan listesi ve dağılım</h3>
                    <span className="col-span-2 text-right">Müşteri adedi</span>
                    <span className="col-span-2 text-right">Ort. churn</span>
                    <span className="col-span-2 text-right">Yüksek risk payı</span>
                  </div>
                  <h3 className="border-b border-line py-4 text-[11px] font-semibold uppercase tracking-widest text-ink-2 md:hidden">01 / Plan listesi ve dağılım</h3>

                  <ol>
                    {data.plans.map((p, i) => {
                      const isOpen = open === i;
                      const total = Math.max(1, p.high + p.mid);
                      return (
                        <li key={p.action} className={`border-b border-line ${isOpen ? "border-l-[3px] border-l-forest pl-3 sm:pl-4" : "border-l-[3px] border-l-transparent pl-3 sm:pl-4"}`}>
                          <button
                            type="button"
                            aria-expanded={isOpen}
                            aria-controls={`plan-panel-${i}`}
                            onClick={() => setOpen(i)}
                            className="focus-ring grid w-full grid-cols-12 items-center gap-x-4 gap-y-3 py-6 text-left"
                          >
                            <div className="col-span-12 flex min-w-0 gap-4 md:col-span-6">
                              <span className="num pt-1 font-serif text-sm text-ink-2">{String(i + 1).padStart(2, "0")}</span>
                              <div className="min-w-0">
                                <div className="text-lg font-medium leading-snug">{p.action}</div>
                                <div className="pt-1 text-xs text-ink-2">
                                  Tetikleyen neden: <span className="font-medium text-ink">{p.reason}</span>
                                </div>
                              </div>
                            </div>
                            <div className="col-span-12 flex items-center gap-4 md:col-span-6 md:grid md:grid-cols-6 md:gap-4">
                              <div className="w-28 shrink-0 md:col-span-2 md:w-full">
                                <div className="flex h-1.5 w-full overflow-hidden" aria-hidden>
                                  <div className="bg-brick" style={{ width: `${(p.high / total) * 100}%` }} />
                                  <div className="bg-amber" style={{ width: `${(p.mid / total) * 100}%` }} />
                                </div>
                                <div className="num flex justify-between pt-1 text-[10px] text-ink-2">
                                  <span><span className="text-brick">●</span> {num(p.high)} Yüksek</span>
                                  <span><span className="text-amber">●</span> {num(p.mid)} Orta</span>
                                </div>
                              </div>
                              <div className="num flex flex-1 justify-between gap-2 text-right md:col-span-4 md:grid md:grid-cols-4 md:gap-4">
                                <div className="md:col-span-1" />
                                <div className="md:col-span-1">
                                  <div className="font-serif text-lg">{num(p.count)}</div>
                                  <div className="text-[11px] text-ink-2">{pct(p.share)} pay</div>
                                </div>
                                <div className="md:col-span-1">
                                  <div className="font-serif text-lg">{pct(p.avg_probability)}</div>
                                  <div className="text-[11px] text-ink-2">Ort. olasılık</div>
                                </div>
                                <div className="flex items-start justify-end gap-2 md:col-span-1">
                                  <div>
                                    <div className="font-serif text-lg text-brick">{num(p.high)}</div>
                                    <div className="text-[11px] text-ink-2">{pct(p.high / total)} yüksek</div>
                                  </div>
                                  {isOpen ? <ChevronUp size={16} className="mt-1.5 text-ink-2" aria-hidden /> : <ChevronDown size={16} className="mt-1.5 text-ink-2" aria-hidden />}
                                </div>
                              </div>
                            </div>
                          </button>
                          {isOpen && (
                            <div id={`plan-panel-${i}`}>
                              <PlanBody plan={p} risk={risk} />
                            </div>
                          )}
                        </li>
                      );
                    })}
                  </ol>
                </section>

                <p className="pt-10 font-serif text-2xl font-semibold italic leading-snug text-forest">
                  “Riskli müşterilerin {pct(data.insight.top_share, 0)} kadarı tek bir hamleye düşüyor: {data.insight.top_action}. Aksiyonların uygulanıp uygulanmadığı bu sistemde tutulmuyor.”
                </p>
              </>
            )}
          </>
        )}
      </main>
    </>
  );
}
