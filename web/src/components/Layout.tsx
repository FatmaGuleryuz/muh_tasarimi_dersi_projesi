import { useEffect, useRef, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar";

/** PageHeader'daki menü butonu bu olayı yayınlar; Layout dinler (lg altı). */
export const OPEN_SIDEBAR_EVENT = "sidebar:open";

export default function Layout() {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const returnFocus = useRef<HTMLElement | null>(null);
  const contentRef = useRef<HTMLDivElement | null>(null);

  // React 18 `inert` özniteliğini tanımaz; elle yönetilir.
  useEffect(() => {
    const el = contentRef.current;
    if (!el) return;
    if (open) el.setAttribute("inert", "");
    else el.removeAttribute("inert");
  }, [open]);

  useEffect(() => {
    const onOpen = () => {
      returnFocus.current = document.activeElement as HTMLElement | null;
      setOpen(true);
    };
    window.addEventListener(OPEN_SIDEBAR_EVENT, onOpen);
    return () => window.removeEventListener(OPEN_SIDEBAR_EVENT, onOpen);
  }, []);

  useEffect(() => setOpen(false), [location.pathname]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  const close = () => {
    setOpen(false);
    returnFocus.current?.focus();
  };

  return (
    <div className="min-h-screen">
      <Sidebar open={open} onClose={close} />
      {open && <div className="fixed inset-0 z-40 bg-black/40 lg:hidden" onClick={close} aria-hidden="true" />}
      <div ref={contentRef} className="min-w-0 lg:pl-64">
        <Outlet />
      </div>
    </div>
  );
}
