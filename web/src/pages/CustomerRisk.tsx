import { useCallback, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ArrowRight, RefreshCw, Search } from "lucide-react";
import Card from "../components/Card";
import PageHeader from "../components/PageHeader";
import Button from "../components/Button";
import RiskBadge from "../components/RiskBadge";
import { fetchCustomers } from "../lib/api";
import type { CustomerList, RiskLevel } from "../lib/types";

const RISK_OPTIONS: { value: RiskLevel | ""; label: string }[] = [
  { value: "", label: "Tümü" },
  { value: "high", label: "Yüksek risk" },
  { value: "mid", label: "Orta risk" },
  { value: "low", label: "Düşük risk" },
];

export default function CustomerRisk() {
  const [params, setParams] = useSearchParams();
  const risk = (params.get("risk") as RiskLevel | null) ?? "";
  const [q, setQ] = useState(params.get("q") ?? "");
  const [data, setData] = useState<CustomerList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const load = useCallback(() => {
    setError(null);
    fetchCustomers({ risk, q: params.get("q") ?? "" })
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, [risk, params]);
  useEffect(load, [load]);

  const setRisk = (next: RiskLevel | "") => {
    const p = new URLSearchParams(params);
    if (next) p.set("risk", next); else p.delete("risk");
    setParams(p);
  };

  const submitSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const p = new URLSearchParams(params);
    if (q) p.set("q", q); else p.delete("q");
    setParams(p);
  };

  return (
    <>
      <PageHeader title="Müşteri Riski" badge={data ? `${data.total} müşteri` : undefined}>
        <Button variant="secondary" icon={RefreshCw} onClick={load}>Yenile</Button>
      </PageHeader>

      <main className="mx-auto flex max-w-7xl flex-col gap-6 p-8">
        {error && (
          <div className="rounded border border-brick/30 bg-brick/10 px-5 py-4 text-sm text-brick">
            Veriler alınamadı: {error}
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex gap-1.5">
            {RISK_OPTIONS.map((opt) => (
              <button
                key={opt.value || "all"}
                type="button"
                onClick={() => setRisk(opt.value)}
                className={`rounded px-3.5 py-2 text-xs font-semibold transition-colors ${
                  risk === opt.value ? "bg-forest text-white" : "border border-line bg-surface text-ink-2 hover:bg-canvas"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <form onSubmit={submitSearch} className="flex items-center gap-2">
            <div className="relative">
              <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-3" />
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Müşteri ID ara…"
                className="rounded border border-line bg-surface py-2 pl-8 pr-3 text-xs outline-none focus:border-forest"
              />
            </div>
            <Button variant="secondary">Ara</Button>
          </form>
        </div>

        <Card flush>
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
                {data?.customers.map((c) => (
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
                        onClick={() => navigate(`/musteri-riski/${c.customer_id}`)}
                        className="inline-flex items-center gap-1 text-xs font-semibold text-forest hover:underline"
                      >
                        İncele <ArrowRight size={13} />
                      </button>
                    </td>
                  </tr>
                ))}
                {data && data.customers.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-6 py-10 text-center text-sm text-ink-2">
                      Eşleşen müşteri bulunamadı.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </main>
    </>
  );
}
