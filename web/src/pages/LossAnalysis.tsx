import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { RefreshCw } from "lucide-react";
import Button from "../components/Button";
import Card from "../components/Card";
import KpiCard from "../components/KpiCard";
import OutcomeBadge from "../components/OutcomeBadge";
import PageHeader from "../components/PageHeader";
import RiskBadge from "../components/RiskBadge";
import { fetchPostmortem } from "../lib/api";
import { num, pct } from "../lib/format";
import type { Outcome, PostmortemList, PostmortemSummary } from "../lib/types";

const OUTCOME_OPTIONS: { value: Outcome | ""; label: string }[] = [
  { value: "", label: "Tümü" },
  { value: "caught", label: "Yakalandı" },
  { value: "partial", label: "Kısmen" },
  { value: "missed", label: "Kaçırıldı" },
];

export default function LossAnalysis() {
  const navigate = useNavigate();
  const [outcome, setOutcome] = useState<Outcome | "">("");
  const [attempt, setAttempt] = useState(0);
  // Backend her yanıtta filtresiz summary döner; özet kartları bunu kullanır (AC-3).
  const [summary, setSummary] = useState<PostmortemSummary | null>(null);
  const [data, setData] = useState<PostmortemList | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setError(null);
    setData(null);
    fetchPostmortem({ outcome })
      .then((r) => {
        if (!active) return;
        setSummary(r.summary);
        setData(r);
      })
      .catch((e: Error) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [outcome, attempt]);

  return (
    <>
      <PageHeader title="Kayıp Analizi" badge={summary ? `${num(summary.lost_total)} kayıp müşteri` : undefined} />

      <main className="mx-auto flex max-w-7xl flex-col gap-6 p-8">
        <p className="text-xs text-ink-2">
          Analiz etiketli test seti üzerindedir; aksiyonların uygulanıp uygulanmadığı verisi tutulmuyor.
        </p>

        {error && (
          <div className="flex items-center justify-between rounded border border-brick/30 bg-brick/10 px-5 py-4 text-sm text-brick">
            <span>Veri yüklenemedi: {error}</span>
            <Button variant="secondary" icon={RefreshCw} onClick={() => setAttempt((a) => a + 1)}>Tekrar Dene</Button>
          </div>
        )}
        {!summary && !error && <p className="text-sm text-ink-2">Yükleniyor…</p>}

        {summary && (
          <div className="grid grid-cols-2 gap-5 lg:grid-cols-3">
            <KpiCard label="Kaybedilen" value={num(summary.lost_total)} />
            <KpiCard label="Yakalandı" value={num(summary.caught)} tone="sage" />
            <KpiCard label="Kısmen" value={num(summary.partial)} tone="amber" />
            <KpiCard label="Kaçırıldı" value={num(summary.missed)} tone="danger" />
            <KpiCard label="Yakalama oranı" value={pct(summary.catch_rate)}>
              Kesin yakalama: {pct(summary.strict_catch_rate)}
            </KpiCard>
            <KpiCard label="Yanlış alarm" value={num(summary.false_alarm_count)}>
              Yüksek risk isabeti: {pct(summary.precision_high)}
            </KpiCard>
          </div>
        )}

        {summary && summary.lost_total === 0 && (
          <Card>
            <p className="text-sm text-ink-2">Kaybedilmiş müşteri bulunamadı</p>
          </Card>
        )}

        {summary && summary.lost_total > 0 && (
          <>
            <div className="flex gap-1.5">
              {OUTCOME_OPTIONS.map((opt) => (
                <button
                  key={opt.value || "all"}
                  type="button"
                  onClick={() => setOutcome(opt.value)}
                  className={`rounded px-3.5 py-2 text-xs font-semibold transition-colors ${
                    outcome === opt.value ? "bg-forest text-white" : "border border-line bg-surface text-ink-2 hover:bg-canvas"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>

            <Card flush>
              {!data && !error && <p className="px-6 py-10 text-center text-sm text-ink-2">Yükleniyor…</p>}
              {data && (
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse text-left">
                    <thead>
                      <tr className="border-b border-line bg-canvas">
                        {["Müşteri ID", "Sonuç", "Kayıp olasılığı", "Risk", "Ana neden", "Önerilen aksiyon"].map((h) => (
                          <th key={h} className="px-6 py-3 text-[11px] font-semibold uppercase tracking-wider text-ink-3">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-row-line">
                      {data.items.map((it) => (
                        <tr
                          key={it.customer_id}
                          onClick={() => navigate(`/musteri-riski/${encodeURIComponent(it.customer_id)}`)}
                          className="cursor-pointer hover:bg-row-hover"
                        >
                          <td className="px-6 py-3.5 font-mono text-xs font-semibold">
                            <button type="button" className="hover:underline">{it.customer_id}</button>
                          </td>
                          <td className="px-6 py-3.5"><OutcomeBadge outcome={it.outcome} /></td>
                          <td className="num px-6 py-3.5 text-xs font-semibold">{pct(it.probability)}</td>
                          <td className="px-6 py-3.5"><RiskBadge level={it.risk} probability={it.probability} /></td>
                          <td className="px-6 py-3.5 text-xs">{it.reason}</td>
                          <td className="px-6 py-3.5 text-xs">{it.action}</td>
                        </tr>
                      ))}
                      {data.items.length === 0 && (
                        <tr>
                          <td colSpan={6} className="px-6 py-10 text-center text-sm text-ink-2">Bu filtrede müşteri yok</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </>
        )}
      </main>
    </>
  );
}
