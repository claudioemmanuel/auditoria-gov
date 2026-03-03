import { cn } from "@/lib/utils";

interface DataValueProps {
  children: React.ReactNode;
  className?: string;
  /** Render as a block (div) instead of inline (span) */
  block?: boolean;
  /** Muted color for secondary data */
  muted?: boolean;
}

/**
 * Renders numeric data, IDs, and codes in JetBrains Mono.
 * Ensures consistent tabular rendering of financial and identifier values.
 */
export function DataValue({ children, className, block, muted }: DataValueProps) {
  const classes = cn(
    "font-mono tabular-nums text-sm",
    muted ? "text-muted" : "text-primary",
    className,
  );

  return block ? (
    <div className={classes}>{children}</div>
  ) : (
    <span className={classes}>{children}</span>
  );
}
