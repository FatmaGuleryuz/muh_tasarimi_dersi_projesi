import type { ReactNode } from "react";
import { Bell } from "lucide-react";

/** Üst bar: sayfa başlığı, bilgi rozeti ve sağda eylem butonları */
export default function PageHeader({ title, badge, children }: { title: string; badge?: string; children?: ReactNode }) {
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-line bg-surface px-8">
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-bold tracking-tight text-forest">{title}</h1>
        {badge && (
          <span className="hidden items-center gap-1.5 rounded border border-line bg-canvas px-2.5 py-1 text-[11px] font-semibold text-ink-2 lg:inline-flex">
            <span className="h-1.5 w-1.5 rounded-full bg-sage" />
            {badge}
          </span>
        )}
      </div>
      <div className="flex items-center gap-3">
        {children}
        <div className="mx-1 h-5 w-px bg-line" />
        <button type="button" title="Bildirimler" className="flex h-9 w-9 items-center justify-center rounded text-ink-2 hover:bg-canvas hover:text-ink">
          <Bell size={19} />
        </button>
      </div>
    </header>
  );
}
