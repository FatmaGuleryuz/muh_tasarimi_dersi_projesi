import type { ReactNode } from "react";

const bar = { danger: "bg-brick", primary: "bg-forest", sage: "bg-sage", amber: "bg-amber" };

/** Solunda 3px renkli şerit olan KPI kartı */
export default function KpiCard({ label, value, unit, tone = "primary", children }: {
  label: string; value: string; unit?: string; tone?: keyof typeof bar; children?: ReactNode;
}) {
  return (
    <div className="relative overflow-hidden rounded border border-line bg-surface py-5 pl-7 pr-5">
      <div className={`absolute inset-y-0 left-0 w-[3px] ${bar[tone]}`} />
      <p className="text-[11px] font-semibold uppercase tracking-wider text-ink-3">{label}</p>
      <p className="num mt-2 flex items-baseline gap-2">
        <span className="text-4xl font-bold leading-none tracking-tight text-forest">{value}</span>
        {unit && <span className="text-sm font-medium text-ink-2">{unit}</span>}
      </p>
      {children && <div className="mt-3 text-xs text-ink-2">{children}</div>}
    </div>
  );
}
