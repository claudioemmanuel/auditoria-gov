interface ScoreBarProps {
  label: string;
  value: number; // 0–100
  color?: "accent" | "warning" | "error";
}

export function ScoreBar({ label, value, color = "accent" }: ScoreBarProps) {
  const barColor = {
    accent:  "linear-gradient(90deg, var(--color-brand), var(--color-brand-light))",
    warning: "linear-gradient(90deg, var(--color-medium), #fcd34d)",
    error:   "linear-gradient(90deg, var(--color-critical), #fca5a5)",
  }[color];
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex justify-between text-xs" style={{ color: "var(--color-text-muted)" }}>
        <span className="data-value">{label}</span>
        <span className="data-value text-[var(--color-text)]">{clamped}/100</span>
      </div>
      <div className="ow-score-bar-track h-2.5 w-full rounded-full">
        <div
          className="ow-score-bar-fill h-full"
          style={{ width: `${clamped}%`, background: barColor }}
        />
      </div>
    </div>
  );
}
