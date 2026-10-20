import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, ArrowRight, Download, Gauge, RefreshCw, Target, Users } from "lucide-react";
import Button from "../components/Button";
import Card from "../components/Card";
import KpiCard from "../components/KpiCard";
import PageHeader from "../components/PageHeader";
import RiskBadge, { riskColor } from "../components/RiskBadge";
import { EXPORT_HIGH_RISK_URL, fetchSummary } from "../lib/api";
import { dec, num, pct } from "../lib/format";
import type { Summary } from "../lib/types";

export default function Overview() {
  const [data, setData] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const load = useCallback(() => {
    setError(null);
    setData(null);
    fetchSummary().then(setData).catch((e: Error) => setError(e.message));
  }, []);
  useEffect(load, [load]);

  const exportCsv = () => { window.location.href = EXPORT_HIGH_RISK_URL; };

  return (
    <>
      <PageHeader title="Genel Bakış" badge={data ? `Veri seti: IBM Telco · ${num(data.dataset.test_customers)} test müşterisi` : undefined}>
        <Button variant="secondary" icon={RefreshCw} onClick={load} title="Verileri yeniden yükle">Yenile</Button>
        <Button icon={Download} onClick={exportCsv} title="Yüksek riskli müşterileri CSV olarak indir">Dışa Aktar</Button>
      </PageHeader>

      <main className="mx-auto flex max-w-7xl flex-col gap-6 p-8">
        {error && (
          <div className="flex items-center justify-between rounded border border-brick/30 bg-brick/10 px-5 py-4 text-sm text-brick">
            <span>Veriler alınamadı: {error}. Backend (uvicorn) çalışıyor mu?</span>
            <Button variant="secondary" icon={RefreshCw} onClick={load}>Tekrar Dene</Button>
          </div>
        )}
        {!data && !error && <p className="text-sm text-ink-2">Yükleniyor…</p>}
        {data && <OverviewView data={data} onNavigate={navigate} />}
      </main>
    </>
  );
}

export function OverviewView({ data, onNavigate }: { data: Summary; onNavigate: (to: string) => void }) {
  const { kpis, model } = data;
  const maxDriver = Math.max(...data.top_drivers.map((d) => d.score), 0.0001);

  return (
    <>
      {/* KPI satırı */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Toplam müşteri" value={num(kpis.total)} unit="müşteri" tone="primary">
          Test seti · gerçekte ayrılan: <b className="text-ink">{pct(kpis.overall_actual_rate)}</b>
        </KpiCard>
        <KpiCard label="Yüksek riskli" value={num(kpis.high_risk_count)} unit="müşteri" tone="danger">
          Portföy payı: <b className="text-ink">{pct(kpis.high_risk_share)}</b> · eşik ≥ {pct(data.thresholds.high, 0)}
        </KpiCard>
        <KpiCard label="Ortalama churn olasılığı" value={pct(kpis.avg_probability)} tone="amber">
          Yüksek risk grubunda gerçek ayrılma: <b className="text-ink">{pct(kpis.high_risk_actual_rate)}</b>
        </KpiCard>
        <KpiCard label="Model ROC-AUC" value={dec(model.roc_auc)} tone="sage">
          {model.best_label} · hedef {dec(model.target, 2)} {model.target_met ? "karşılandı" : "karşılanmadı"}
        </KpiCard>
      </div>

      {/* Risk dağılımı + sözleşme kırılımı */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="Risk dağılımı" subtitle="Test setindeki müşterilerin risk düzeylerine göre dağılımı">
          <div className="flex h-3 w-full overflow-hidden rounded-full bg-canvas">
            {data.risk_distribution.map((r) => (
              <div key={r.level} className={riskColor[r.level]} style={{ width: `${r.share * 100}%` }} />
            ))}
          </div>
          <ul className="mt-5 divide-y divide-row-line">
            {data.risk_distribution.map((r) => (
              <li key={r.level}>
                <button
                  type="button"
                  onClick={() => onNavigate(`/musteri-riski?risk=${r.level}`)}
                  className="flex w-full items-center justify-between py-3 text-left text-sm hover:bg-row-hover"
                >
                  <span className="flex items-center gap-2.5 font-semibold">
                    <span className={`h-2.5 w-2.5 rounded-full ${riskColor[r.level]}`} />
                    {r.label}
                  </span>
                  <span className="num text-ink-2">
                    <b className="text-ink">{num(r.count)}</b> müşteri · {pct(r.share)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </Card>

        <Card title="Sözleşme tipine göre churn" subtitle="Modelin ortalama kayıp olasılığı ve test setindeki gerçek ayrılma oranı">
          <ul className="flex flex-col gap-5">
            {data.by_contract.map((c) => (
              <li key={c.contract}>
                <div className="mb-1.5 flex items-baseline justify-between text-sm">
                  <span className="font-semibold">{c.label}</span>
                  <span className="num text-ink-2">
                    <b className="text-ink">{pct(c.avg_probability)}</b> tahmin · {pct(c.actual_rate)} gerçek · {num(c.count)} müşteri
                  </span>
                </div>
                <div className="h-2.5 w-full rounded-full bg-canvas">
                  <div className="h-full rounded-full bg-forest" style={{ width: `${c.avg_probability * 100}%` }} />
                </div>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      {/* Neden sıralaması + en riskli müşteriler */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-5">
        <Card
          className="xl:col-span-2"
          title="Genel neden sıralaması"
          subtitle="Kayba en çok katkı veren değişkenler (ortalama mutlak SHAP)"
        >
          <ul className="flex flex-col gap-3.5">
            {data.top_drivers.map((d, i) => (
              <li key={d.feature}>
                <div className="mb-1 flex items-baseline justify-between text-xs">
                  <span className="font-semibold"><span className="num mr-1.5 text-ink-3">{i + 1}.</span>{d.label}</span>
                  <span className="num text-ink-2">{dec(d.score, 2)}</span>
                </div>
                <div className="h-2 w-full rounded-full bg-canvas">
                  <div className="h-full rounded-full bg-forest" style={{ width: `${(d.score / maxDriver) * 100}%` }} />
                </div>
              </li>
            ))}
          </ul>
        </Card>

        <Card
          className="xl:col-span-3"
          flush
          title="En riskli 5 müşteri"
          subtitle="Kayıp olasılığı en yüksek müşteriler"
          action={<Button variant="secondary" icon={Users} onClick={() => onNavigate("/musteri-riski?risk=high")}>Tüm Riskli Müşterileri Gör</Button>}
        >
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-line bg-canvas">
                  {["Müşteri ID", "Sözleşme", "Kayıp olasılığı", "Ana neden", ""].map((h) => (
                    <th key={h} className="px-6 py-3 text-[11px] font-semibold uppercase tracking-wider text-ink-3">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-row-line">
                {data.top_customers.map((c) => (
                  <tr key={c.customer_id} className="hover:bg-row-hover">
                    <td className="px-6 py-3.5 font-mono text-xs font-semibold">{c.customer_id}</td>
                    <td className="px-6 py-3.5 text-xs">
                      <span className="rounded border border-line bg-canvas px-2 py-1 font-semibold">{c.contract}</span>
                    </td>
                    <td className="px-6 py-3.5"><RiskBadge level={c.risk} probability={c.probability} /></td>
                    <td className="px-6 py-3.5 text-xs">{c.reason}</td>
                    <td className="px-6 py-3.5 text-right">
                      <button
                        type="button"
                        onClick={() => onNavigate(`/musteri-riski/${c.customer_id}`)}
                        className="inline-flex items-center gap-1 text-xs font-semibold text-forest hover:underline"
                      >
                        İncele <ArrowRight size={13} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {/* Alt bilgi şeridi */}
      <div className="flex items-center justify-between gap-4 rounded border border-line bg-surface px-6 py-4 text-xs text-ink-2">
        <span className="flex items-center gap-2.5">
          {model.target_met ? <Target size={17} className="text-sage" /> : <AlertTriangle size={17} className="text-amber" />}
          <span>
            Model: <b className="text-ink">{model.best_label}</b> · ROC-AUC {dec(model.roc_auc)} · Veri: {data.dataset.name} ({num(data.dataset.total_rows)} müşteri)
          </span>
        </span>
        <button type="button" onClick={() => onNavigate("/model-ve-raporlar")} className="inline-flex items-center gap-1.5 font-semibold text-forest hover:underline">
          <Gauge size={14} /> Model detayları <ArrowRight size={13} />
        </button>
      </div>
    </>
  );
}
