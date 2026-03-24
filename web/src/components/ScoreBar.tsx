interface ScoreBarProps {
  label: string;
  value: number; // 0–100
  color?: "accent" | "warning" | "error";
}

export function ScoreBar({ label, value, color = "accent" }: ScoreBarProps) {
  const barColor = {
    accent:  "var(--color-accent)",
    warning: "var(--color-warning)",
    error:   "var(--color-error)",
  }[color];
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between text-xs" style={{ color: "var(--color-text-muted)" }}>
        <span className="data-value">{label}</span>
        <span className="data-value">{clamped}/100</span>
      </div>
      <div className="h-2 w-full" style={{ background: "var(--color-surface-card)" }}>
        <div className="h-2" style={{ width: `${clamped}%`, background: barColor }} />
      </div>
    </div>
  );
}
