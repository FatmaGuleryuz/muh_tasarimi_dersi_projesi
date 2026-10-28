import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, RefreshCw, Target } from "lucide-react";
import Button from "../components/Button";
import Card from "../components/Card";
import PageHeader from "../components/PageHeader";
import { fetchModelReport } from "../lib/api";
import { dec, num, pct } from "../lib/format";
import type { ModelReport } from "../lib/types";

const DRIVER_PREVIEW = 10;

export default function ModelReports() {
  const [data, setData] = useState<ModelReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    setData(null);
    fetchModelReport().then(setData).catch((e: Error) => setError(e.message));
  }, []);
  useEffect(load, [load]);

  return (
    <>
      <PageHeader title="Model ve Raporlar" badge={data ? `En iyi model: ${data.best_label}` : undefined}>
        <Button variant="secondary" icon={RefreshCw} onClick={load} title="Verileri yeniden yükle">Yenile</Button>
      </PageHeader>

      <main className="mx-auto flex max-w-7xl flex-col gap-6 p-8">
        {error && (
          <div className="flex items-center justify-between rounded border border-brick/30 bg-brick/10 px-5 py-4 text-sm text-brick">
            <span>Sunucuya ulaşılamadı — veriler alınamadı: {error}. Backend (uvicorn) çalışıyor mu?</span>
            <Button variant="secondary" icon={RefreshCw} onClick={load}>Tekrar Dene</Button>
          </div>
        )}
        {!data && !error && <p className="text-sm text-ink-2">Yükleniyor…</p>}
        {data && <ModelReportView data={data} />}
      </main>
    </>
  );
}

function ModelReportView({ data }: { data: ModelReport }) {
  const [showAll, setShowAll] = useState(false);
  const maxDriver = Math.max(...data.drivers.map((d) => d.score), 0.0001);
  const drivers = showAll ? data.drivers : data.drivers.slice(0, DRIVER_PREVIEW);

  return (
    <>
      {/* Hedef doğrulama şeridi */}
      <div className="flex items-center justify-between gap-4 rounded border border-line bg-surface px-6 py-4 text-sm text-ink-2">
        <span className="flex items-center gap-2.5">
          {data.target_met ? <Target size={17} className="text-sage" /> : <AlertTriangle size={17} className="text-amber" />}
          <span>
            Hedef ROC-AUC <b className="text-ink">{dec(data.target, 2)}</b> · En iyi model: <b className="text-ink">{data.best_label}</b>
          </span>
        </span>
        {data.target_met ? (
          <span className="rounded border border-sage/30 bg-sage/10 px-2.5 py-1 text-[11px] font-semibold text-sage">✓ Karşılandı</span>
        ) : (
          <span className="rounded border border-amber/30 bg-amber/10 px-2.5 py-1 text-[11px] font-semibold text-amber">Karşılanmadı</span>
        )}
      </div>

      {/* Model karşılaştırma kartları */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {data.models.map((m) => {
          const isBest = m.key === data.best;
          const metrics: [string, string][] = [
            ["ROC-AUC", dec(m.roc_auc)],
            ["Precision", pct(m.precision)],
            ["Recall", pct(m.recall)],
            ["F1", dec(m.f1)],
          ];
          return (
            <Card
              key={m.key}
              title={m.label}
              className={isBest ? "ring-1 ring-forest" : ""}
              action={isBest ? <span className="rounded bg-forest px-2.5 py-1 text-[11px] font-semibold text-white">En İyi Model</span> : undefined}
            >
              <dl className="num flex flex-col gap-3 text-sm">
                {metrics.map(([label, value]) => (
                  <div key={label} className="flex items-baseline justify-between">
                    <dt className="text-ink-2">{label}</dt>
                    <dd className="font-semibold">{value}</dd>
                  </div>
                ))}
              </dl>
            </Card>
          );
        })}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        {/* Veri seti künyesi */}
        <Card className="lg:col-span-2" title="Veri seti künyesi" subtitle="Modelin eğitildiği ve değerlendirildiği veri">
          <dl className="num flex flex-col gap-3 text-sm">
            <div className="flex items-baseline justify-between">
              <dt className="text-ink-2">Ad</dt>
              <dd className="font-semibold">{data.dataset.name}</dd>
            </div>
            <div className="flex items-baseline justify-between">
              <dt className="text-ink-2">Satır sayısı</dt>
              <dd className="font-semibold">{num(data.dataset.rows)}</dd>
            </div>
            <div className="flex items-baseline justify-between">
              <dt className="text-ink-2">Churn oranı</dt>
              <dd className="font-semibold">{pct(data.dataset.churn_rate)}</dd>
            </div>
          </dl>
        </Card>

        {/* Tüm SHAP değişken sıralaması */}
        <Card
          className="lg:col-span-3"
          title="Değişken önem sıralaması"
          subtitle="Kayba katkı veren değişkenler — ortalama mutlak SHAP (modelin karar üzerindeki ortalama etkisi)"
        >
          {data.drivers.length === 0 ? (
            <p className="text-sm text-ink-2">Henüz değişken önem skoru yok</p>
          ) : (
            <>
              <ul className="flex flex-col gap-3.5">
                {drivers.map((d, i) => (
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
              {data.drivers.length > DRIVER_PREVIEW && (
                <div className="mt-5 flex justify-center">
                  <Button variant="secondary" onClick={() => setShowAll((v) => !v)}>
                    {showAll ? "Daha Az Göster" : `Tümünü Göster (${data.drivers.length})`}
                  </Button>
                </div>
              )}
            </>
          )}
        </Card>
      </div>
    </>
  );
}
