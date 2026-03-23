import { cn } from "@/lib/utils";
import type { SignalSeverity } from "@/lib/types";

type BadgeVariant = SignalSeverity | "default";

const VARIANT_CLASSES: Record<BadgeVariant, string> = {
  critical: "bg-severity-critical/10 text-severity-critical border-severity-critical/40",
  high:     "bg-severity-high/10 text-severity-high border-severity-high/40",
  medium:   "bg-severity-medium/10 text-severity-medium border-severity-medium/40",
  low:      "bg-severity-low/10 text-severity-low border-severity-low/40",
  default:  "bg-transparent text-muted border-border",
};

const DOT_CLASSES: Record<BadgeVariant, string> = {
  critical: "bg-severity-critical",
  high:     "bg-severity-high",
  medium:   "bg-severity-medium",
  low:      "bg-severity-low",
  default:  "bg-muted",
};

const SEVERITY_LABELS: Record<SignalSeverity, string> = {
  critical: "CRÍTICO",
  high:     "ALTO",
  medium:   "MÉDIO",
  low:      "BAIXO",
};

interface BadgeProps {
  variant?: BadgeVariant;
  severity?: SignalSeverity;
  children?: React.ReactNode;
  className?: string;
  dot?: boolean;
}

export function Badge({ variant, severity, children, className, dot }: BadgeProps) {
  const v: BadgeVariant = severity ?? variant ?? "default";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-[3px] border px-2 py-0.5 font-mono text-[10px] font-bold tracking-[0.08em] uppercase",
        VARIANT_CLASSES[v],
        className,
      )}
    >
      {dot && <span className={cn("h-2 w-2 rounded-full", DOT_CLASSES[v])} />}
      {children ?? (severity ? SEVERITY_LABELS[severity] : null)}
    </span>
  );
}
