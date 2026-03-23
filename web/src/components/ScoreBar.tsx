interface ScoreBarProps {
  label: string;
  value: number; // 0–100
  color?: "blue" | "amber" | "red";
}

export function ScoreBar({ label, value, color = "blue" }: ScoreBarProps) {
  const colorClass = {
    blue: "bg-blue-500",
    amber: "bg-amber-500",
    red: "bg-red-500",
  }[color];
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between text-xs text-gray-600">
        <span>{label}</span>
        <span>{clamped}/100</span>
      </div>
      <div className="h-2 w-full rounded bg-gray-200">
        <div className={`h-2 rounded ${colorClass}`} style={{ width: `${clamped}%` }} />
      </div>
    </div>
  );
}
