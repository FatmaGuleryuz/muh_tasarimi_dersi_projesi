import type { ComponentType, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost";

const styles: Record<Variant, string> = {
  primary: "bg-forest text-white hover:bg-forest-dark",
  secondary: "bg-surface text-ink border border-line hover:bg-canvas",
  ghost: "text-forest hover:bg-canvas",
};

interface Props {
  children?: ReactNode;
  variant?: Variant;
  icon?: ComponentType<{ size?: number; className?: string }>;
  onClick?: () => void;
  title?: string;
  className?: string;
}

/** Tasarım sistemi butonu: 4px köşe, gölge yok. */
export default function Button({ children, variant = "primary", icon: Icon, onClick, title, className = "" }: Props) {
  return (
    <button
      type="button"
      title={title}
      onClick={onClick}
      className={`inline-flex items-center justify-center gap-1.5 rounded px-3.5 py-2 text-xs font-semibold transition-colors ${styles[variant]} ${className}`}
    >
      {Icon && <Icon size={15} />}
      {children}
    </button>
  );
}
