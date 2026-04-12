// apps/web/src/components/watchdog/SignalTag.tsx

export interface SignalTagProps {
  label: string;
}

export function SignalTag({ label }: SignalTagProps) {
  return (
    <span className="text-xs font-mono border border-[var(--color-border)] px-2 py-0.5 rounded-md text-[var(--color-text-2)]">
      {label}
    </span>
  );
}
