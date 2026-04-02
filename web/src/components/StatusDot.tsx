import { clsx } from "clsx";

type StatusDotSize = "sm" | "md" | "lg";
type StatusDotStatus = "ok" | "warning" | "error" | "stale" | "pending" | "critical" | "high" | "medium" | "low";

const SIZE: Record<StatusDotSize, string> = {
  sm: "w-1.5 h-1.5",
  md: "w-2 h-2",
  lg: "w-2.5 h-2.5",
};

const COLOR: Record<StatusDotStatus, string> = {
  ok:       "ow-status-ok",
  warning:  "ow-status-warning",
  stale:    "ow-status-stale",
  error:    "ow-status-error",
  pending:  "ow-status-pending",
  critical: "ow-status-error",
  high:     "ow-status-stale",
  medium:   "ow-status-warning",
  low:      "ow-status-ok",
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
      className={clsx(
        "ow-status-dot inline-block rounded-full",
        SIZE[size],
        COLOR[status],
        pulse && "animate-pulse",
        className
      )}
    />
  );
}
