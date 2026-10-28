import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, RefreshCw } from "lucide-react";
import Card from "../components/Card";
import PageHeader from "../components/PageHeader";
import Button from "../components/Button";
import RiskBadge from "../components/RiskBadge";
import { fetchCustomer } from "../lib/api";
import { dec, num, pct } from "../lib/format";
import type { CustomerDetail as CustomerDetailType } from "../lib/types";

export default function CustomerDetail() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState<CustomerDetailType | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    setData(null);
    fetchCustomer(id).then(setData).catch((e: Error) => setError(e.message));
  }, [id]);
  useEffect(load, [load]);

  return (
    <>
      <PageHeader title="Müşteri Detayı">
        <Button variant="secondary" icon={ArrowLeft} onClick={() => navigate("/musteri-riski")}>Listeye Dön</Button>
      </PageHeader>

      <main className="mx-auto flex max-w-5xl flex-col gap-6 p-8">
        {error && (
          <div className="flex items-center justify-between rounded border border-brick/30 bg-brick/10 px-5 py-4 text-sm text-brick">
            <span>{error === "Müşteri bulunamadı" ? `"${id}" ID'li müşteri bulunamadı.` : `Veri alınamadı: ${error}`}</span>
            <Button variant="secondary" icon={RefreshCw} onClick={load}>Tekrar Dene</Button>
          </div>
        )}
        {!data && !error && <p className="text-sm text-ink-2">Yükleniyor…</p>}
        {data && <DetailView data={data} />}
      </main>
    </>
  );
}

function DetailView({ data }: { data: CustomerDetailType }) {
  const maxDriver = Math.max(...data.overall_top_drivers.map((d) => d.score), 0.0001);

  return (
    <>
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="font-mono text-sm font-semibold text-ink-2">{data.customer_id}</p>
            <p className="mt-1 text-2xl font-bold text-forest">{pct(data.probability)} kayıp olasılığı</p>
          </div>
          <RiskBadge level={data.risk} probability={data.probability} />
        </div>
        <div className="mt-6 grid grid-cols-2 gap-5 text-sm sm:grid-cols-4">
          <Field label="Sözleşme" value={data.contract} />
          <Field label="Müşteri olma süresi" value={`${num(data.tenure_months)} ay`} />
          <Field label="Aylık ücret" value={`₺${dec(data.monthly_charges, 2)}`} />
          <Field label="Toplam ücret" value={data.total_charges !== null ? `₺${dec(data.total_charges, 2)}` : "—"} />
        </div>
        {data.actual_churn && (
          <p className="mt-5 rounded border border-brick/20 bg-brick/10 px-4 py-2.5 text-xs font-semibold text-brick">
            Bu müşteri test setinde gerçekten ayrılmış (churn = evet).
          </p>
        )}
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="Ana neden" subtitle="Model için bu müşteride en yüksek katkılı değişken">
          <p className="text-lg font-semibold text-ink">{data.reason}</p>
          <p className="mt-1 font-mono text-[11px] text-ink-3">{data.reason_feature}</p>
        </Card>
        <Card title="Önerilen çözüm" subtitle="Literatürden derlenen müdahale önerisi">
          <p className="text-sm text-ink">{data.action}</p>
        </Card>
      </div>

      <Card title="Genel neden sıralaması" subtitle="Tüm test setinde kayba en çok katkı veren değişkenler (ortalama mutlak SHAP) — bu müşteriye özel tam kırılım henüz hesaplanmıyor">
        <ul className="flex flex-col gap-3.5">
          {data.overall_top_drivers.map((d, i) => (
            <li key={d.feature}>
              <div className="mb-1 flex items-baseline justify-between text-xs">
                <span className="font-semibold">
                  <span className="num mr-1.5 text-ink-3">{i + 1}.</span>
                  {d.label}
                  {d.feature === data.reason_feature && (
                    <span className="ml-2 rounded-full bg-forest/10 px-2 py-0.5 text-[10px] font-bold text-forest">Bu müşteride ana neden</span>
                  )}
                </span>
                <span className="num text-ink-2">{dec(d.score, 2)}</span>
              </div>
              <div className="h-2 w-full rounded-full bg-canvas">
                <div className="h-full rounded-full bg-forest" style={{ width: `${(d.score / maxDriver) * 100}%` }} />
              </div>
            </li>
          ))}
        </ul>
      </Card>
    </>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-wider text-ink-3">{label}</p>
      <p className="num mt-1 font-semibold text-ink">{value}</p>
    </div>
  );
}
