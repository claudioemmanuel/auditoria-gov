// apps/web/src/components/watchdog/SignalTag.tsx
import clsx from "clsx";

export interface SignalTagProps {
  label: string;
  className?: string;
}

export function SignalTag({ label, className }: SignalTagProps) {
  return (
    // text-xs (0.75rem) intentionally smaller than .data (0.875rem) — tags are compact labels, not data values
    <span
      className={clsx(
        "text-xs font-mono border border-[var(--color-border)] px-2 py-0.5 rounded-md text-[var(--color-text-2)]",
        className,
      )}
    >
      {label}
    </span>
  );
}
