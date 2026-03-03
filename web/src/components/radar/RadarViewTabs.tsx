"use client";

export type RadarViewMode = "signals" | "cases";

interface RadarViewTabsProps {
  value: RadarViewMode;
  onChange: (value: RadarViewMode) => void;
}

export function RadarViewTabs({ value, onChange }: RadarViewTabsProps) {
  return (
    <div className="mt-6 inline-flex rounded-lg border border-gov-gray-200 bg-white p-1 shadow-sm">
      <button
        type="button"
        onClick={() => onChange("signals")}
        className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
          value === "signals"
            ? "bg-gov-blue-600 text-white"
            : "text-gov-gray-600 hover:bg-gov-gray-50"
        }`}
      >
        Sinais
      </button>
      <button
        type="button"
        onClick={() => onChange("cases")}
        className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
          value === "cases"
            ? "bg-gov-blue-600 text-white"
            : "text-gov-gray-600 hover:bg-gov-gray-50"
        }`}
      >
        Casos
      </button>
    </div>
  );
}
