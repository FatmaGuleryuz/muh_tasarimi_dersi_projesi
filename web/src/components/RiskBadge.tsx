import type { RiskLevel } from "../lib/types";
import { pct } from "../lib/format";

const tone: Record<RiskLevel, { text: string; label: string; cls: string; dot: string }> = {
  high: { text: "Yüksek", label: "Yüksek risk", cls: "text-brick bg-brick/10 border-brick/20", dot: "bg-brick" },
  mid: { text: "Orta", label: "Orta risk", cls: "text-amber bg-amber/10 border-amber/20", dot: "bg-amber" },
  low: { text: "Düşük", label: "Düşük risk", cls: "text-sage bg-sage/10 border-sage/20", dot: "bg-sage" },
};

export const riskColor: Record<RiskLevel, string> = { high: "bg-brick", mid: "bg-amber", low: "bg-sage" };

/** "%84 · Yüksek" biçiminde hap (pill) rozeti */
export default function RiskBadge({ level, probability }: { level: RiskLevel; probability: number }) {
  const t = tone[level];
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-3 py-1 text-[11px] font-semibold ${t.cls}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${t.dot}`} />
      {pct(probability, 0)} · {t.text}
    </span>
  );
}
