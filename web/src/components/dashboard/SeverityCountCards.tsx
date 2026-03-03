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
    bg: "border-l-severity-critical",
  },
  {
    key: "high" as const,
    label: "Altos",
    accent: "text-severity-high",
    bg: "border-l-severity-high",
  },
  {
    key: "medium" as const,
    label: "Medios",
    accent: "text-severity-medium",
    bg: "border-l-severity-medium",
  },
  {
    key: "low" as const,
    label: "Baixos",
    accent: "text-severity-low",
    bg: "border-l-severity-low",
  },
] as const;

export function SeverityCountCards({ counts }: SeverityCountCardsProps) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {CARDS.map((card) => (
        <div
          key={card.key}
          className={cn(
            "rounded-lg border border-border bg-surface-card p-4 border-l-4",
            card.bg,
          )}
        >
          <p className="text-xs font-medium uppercase tracking-wide text-secondary">
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
