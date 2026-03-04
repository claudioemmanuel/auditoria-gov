import { cn } from "@/lib/utils";

type StatusDotSize = "sm" | "md" | "lg";
type StatusDotStatus =
  | "ok"
  | "warning"
  | "error"
  | "stale"
  | "pending"
  | "critical"
  | "high"
  | "medium"
  | "low";

const SIZE_CLASSES: Record<StatusDotSize, string> = {
  sm: "h-1.5 w-1.5",
  md: "h-2 w-2",
  lg: "h-2.5 w-2.5",
};

const STATUS_CLASSES: Record<StatusDotStatus, string> = {
  ok: "bg-success",
  warning: "bg-amber",
  error: "bg-error",
  stale: "bg-amber",
  pending: "bg-placeholder",
  critical: "bg-severity-critical",
  high: "bg-severity-high",
  medium: "bg-severity-medium",
  low: "bg-severity-low",
};

interface StatusDotProps {
  size?: StatusDotSize;
  status?: StatusDotStatus;
  className?: string;
  pulse?: boolean;
}

export function StatusDot({ size = "md", status = "ok", className, pulse }: StatusDotProps) {
  return (
    <span
      className={cn(
        "inline-block rounded-full",
        SIZE_CLASSES[size],
        STATUS_CLASSES[status],
        pulse && "animate-pulse",
        className,
      )}
    />
  );
}
