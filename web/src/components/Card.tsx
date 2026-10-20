import type { ReactNode } from "react";

/** Beyaz yüzey + 1px #E5E1D8 kenarlık. Başlık altında ayırıcı çizgi. */
export default function Card({ title, subtitle, action, children, className = "", flush = false }: {
  title?: string; subtitle?: string; action?: ReactNode; children: ReactNode; className?: string;
  /** true: gövde iç boşluğu yok (tablo gibi kenardan kenara içerikler için) */
  flush?: boolean;
}) {
  return (
    <section className={`rounded border border-line bg-surface ${className}`}>
      {title && (
        <header className="flex items-start justify-between gap-4 border-b border-line px-6 py-4">
          <div>
            <h2 className="text-[15px] font-bold text-forest">{title}</h2>
            {subtitle && <p className="mt-0.5 text-xs text-ink-2">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      <div className={flush ? "" : "p-6"}>{children}</div>
    </section>
  );
}
