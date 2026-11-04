import type { Outcome } from "../lib/types";

const tone: Record<Outcome, { text: string; cls: string; dot: string }> = {
  caught: { text: "Yakalandı", cls: "text-forest bg-forest/10 border-forest/20", dot: "bg-forest" },
  partial: { text: "Kısmen", cls: "text-amber bg-amber/10 border-amber/20", dot: "bg-amber" },
  missed: { text: "Kaçırıldı", cls: "text-brick bg-brick/10 border-brick/20", dot: "bg-brick" },
};

/** Postmortem sonuç rozeti. Renge ek olarak metin de taşır. */
export default function OutcomeBadge({ outcome }: { outcome: Outcome }) {
  const t = tone[outcome];
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-3 py-1 text-[11px] font-semibold ${t.cls}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${t.dot}`} />
      {t.text}
    </span>
  );
}
