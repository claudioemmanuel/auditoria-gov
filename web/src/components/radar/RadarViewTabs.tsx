"use client";

export type RadarViewMode = "signals" | "cases";

interface RadarViewTabsProps {
  value: RadarViewMode;
  onChange: (value: RadarViewMode) => void;
}

export function RadarViewTabs({ value, onChange }: RadarViewTabsProps) {
  return (
    <div className="inline-flex gap-1">
      <button
        type="button"
        onClick={() => onChange("signals")}
        className={`px-3 py-1.5 text-sm font-medium transition ${
          value === "signals"
            ? "border-b-2 border-accent text-accent"
            : "text-muted hover:text-secondary"
        }`}
      >
        Visão por Sinais
      </button>
      <button
        type="button"
        onClick={() => onChange("cases")}
        className={`px-3 py-1.5 text-sm font-medium transition ${
          value === "cases"
            ? "border-b-2 border-accent text-accent"
            : "text-muted hover:text-secondary"
        }`}
      >
        Visão por Casos
      </button>
    </div>
  );
}
