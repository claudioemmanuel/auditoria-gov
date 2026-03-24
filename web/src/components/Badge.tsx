import { cn } from "@/lib/utils";
import type { SignalSeverity } from "@/lib/types";

type BadgeVariant = SignalSeverity | "default";

const SEVERITY_LABELS: Record<SignalSeverity, string> = {
  critical: "CRÍTICO",
  high:     "ALTO",
  medium:   "MÉDIO",
  low:      "BAIXO",
};

const VARIANT_STYLES: Record<BadgeVariant, React.CSSProperties> = {
  critical: { borderLeft: "2px solid var(--color-critical)" },
  high:     { borderLeft: "2px solid var(--color-high)" },
  medium:   { borderLeft: "2px solid var(--color-medium)" },
  low:      { borderLeft: "2px solid var(--color-low)" },
  default:  {},
};

interface BadgeProps {
  variant?: BadgeVariant;
  severity?: SignalSeverity;
  children?: React.ReactNode;
  className?: string;
  dot?: boolean;
}

export function Badge({ variant, severity, children, className, dot: _dot }: BadgeProps) {
  const v: BadgeVariant = severity ?? variant ?? "default";

  const baseStyle: React.CSSProperties = {
    padding: "2px 6px",
    fontFamily: "var(--font-mono)",
    fontSize: "0.6875rem",
    background: "transparent",
    borderRadius: 0,
    ...VARIANT_STYLES[v],
  };

  return (
    <span
      className={cn(
        "inline-flex items-center font-bold uppercase tracking-[0.15em]",
        className,
      )}
      style={baseStyle}
    >
      {children ?? (severity ? SEVERITY_LABELS[severity] : null)}
    </span>
  );
}
