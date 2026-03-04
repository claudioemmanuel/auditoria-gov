import { cn } from "@/lib/utils";
import type { SignalSeverity } from "@/lib/types";

type BadgeVariant = SignalSeverity | "default";

const VARIANT_CLASSES: Record<BadgeVariant, string> = {
  critical: "bg-severity-critical-bg text-severity-critical border-severity-critical/20",
  high: "bg-severity-high-bg text-severity-high border-severity-high/20",
  medium: "bg-severity-medium-bg text-severity-medium border-severity-medium/20",
  low: "bg-severity-low-bg text-severity-low border-severity-low/20",
  default: "bg-surface-subtle text-secondary border-border",
};

const DOT_CLASSES: Record<BadgeVariant, string> = {
  critical: "bg-severity-critical",
  high: "bg-severity-high",
  medium: "bg-severity-medium",
  low: "bg-severity-low",
  default: "bg-muted",
};

const SEVERITY_LABELS: Record<SignalSeverity, string> = {
  critical: "Critico",
  high: "Alto",
  medium: "Medio",
  low: "Baixo",
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
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold",
        VARIANT_CLASSES[v],
        className,
      )}
    >
      {dot && <span className={cn("h-1.5 w-1.5 rounded-full", DOT_CLASSES[v])} />}
      {children ?? (severity ? SEVERITY_LABELS[severity] : null)}
    </span>
  );
}
