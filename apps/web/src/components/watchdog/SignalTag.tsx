// apps/web/src/components/watchdog/SignalTag.tsx
import clsx from "clsx";

export interface SignalTagProps {
  label: string;
  className?: string;
}

export function SignalTag({ label, className }: SignalTagProps) {
  return (
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
