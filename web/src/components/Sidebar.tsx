import { NavLink, useNavigate } from "react-router-dom";
import { BarChart3, ClipboardList, LayoutDashboard, Play, TrendingDown, Users } from "lucide-react";

const items = [
  { to: "/", label: "Genel Bakış", icon: LayoutDashboard, end: true },
  { to: "/musteri-riski", label: "Müşteri Riski", icon: Users },
  { to: "/kayip-tahmini", label: "Kayıp Tahmini", icon: TrendingDown },
  { to: "/mudahale-planlari", label: "Müdahale Planları", icon: ClipboardList },
  { to: "/model-ve-raporlar", label: "Model ve Raporlar", icon: BarChart3 },
];

export default function Sidebar() {
  const navigate = useNavigate();
  return (
    <aside className="fixed inset-y-0 left-0 z-40 flex w-64 flex-col justify-between border-r border-line bg-surface px-4 py-6">
      <div className="flex flex-col gap-6">
        <div className="flex items-center gap-3 px-2">
          <div className="flex h-9 w-9 items-center justify-center rounded bg-forest text-white">
            <LayoutDashboard size={18} />
          </div>
          <div>
            <p className="text-[17px] font-bold leading-tight tracking-tight text-forest">Yetkin360</p>
            <p className="text-[11px] font-medium text-ink-2">Karar Destek Paneli</p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => navigate("/mudahale-planlari")}
          className="mx-2 flex items-center justify-center gap-2 rounded bg-forest px-3 py-2.5 text-xs font-semibold text-white transition-colors hover:bg-forest-dark"
        >
          <Play size={14} /> Müdahale Başlat
        </button>

        <nav className="flex flex-col gap-1">
          {items.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded px-3 py-2.5 text-xs font-semibold transition-colors ${
                  isActive ? "bg-forest text-white" : "text-ink-2 hover:bg-canvas"
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>
      </div>

      <div className="flex items-center gap-3 rounded border border-line bg-canvas px-3 py-2.5">
        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-forest text-[10px] font-bold text-white">76</div>
        <div className="min-w-0">
          <p className="truncate text-[11px] font-semibold">76. Proje Grubu</p>
          <p className="truncate text-[10px] text-ink-2">Tasarım Dersi · Fırat Üni.</p>
        </div>
      </div>
    </aside>
  );
}
