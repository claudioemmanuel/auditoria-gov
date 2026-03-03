import { cn } from "@/lib/utils";
import type { RadarV2SeverityCounts } from "@/lib/types";

interface SeverityCountCardsProps {
  counts: RadarV2SeverityCounts;
}

const CARDS = [
  {
    key: "critical" as const,
    label: "Criticos",
    accent: "text-severity-critical",
    bg: "border-l-red-600",
  },
  {
    key: "high" as const,
    label: "Altos",
    accent: "text-severity-high",
    bg: "border-l-orange-600",
  },
  {
    key: "medium" as const,
    label: "Medios",
    accent: "text-severity-medium",
    bg: "border-l-yellow-600",
  },
  {
    key: "low" as const,
    label: "Baixos",
    accent: "text-severity-low",
    bg: "border-l-blue-600",
  },
] as const;

export function SeverityCountCards({ counts }: SeverityCountCardsProps) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {CARDS.map((card) => (
        <div
          key={card.key}
          className={cn(
            "rounded-lg border border-gov-gray-200 bg-white p-4 shadow-sm border-l-4",
            card.bg,
          )}
        >
          <p className="text-xs font-medium uppercase tracking-wide text-gov-gray-600">
            {card.label}
          </p>
          <p
            className={cn(
              "mt-1 font-mono tabular-nums text-3xl font-bold leading-none",
              card.accent,
            )}
          >
            {counts[card.key]}
          </p>
        </div>
      ))}
    </div>
  );
}
