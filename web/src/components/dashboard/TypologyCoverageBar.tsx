import { cn } from "@/lib/utils";
import type { AnalyticalCoverageItem } from "@/lib/types";

interface TypologyCoverageBarProps {
  items: AnalyticalCoverageItem[];
}

function coveragePct(item: AnalyticalCoverageItem): number {
  const required = item.required_domains.length;
  if (required === 0) return 100;
  const available = item.domains_available.length;
  return Math.round((available / required) * 100);
}

export function TypologyCoverageBar({ items }: TypologyCoverageBarProps) {
  return (
    <div className="rounded-lg border border-border bg-surface-card">
      <div className="border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold text-primary">Cobertura de Tipologias</h2>
      </div>
      <ul className="divide-y divide-border">
        {items.map((item) => {
          const pct = coveragePct(item);
          return (
            <li key={item.typology_code} className="px-4 py-3">
              <div className="mb-1.5 flex items-center justify-between gap-2">
                <div className="flex min-w-0 items-center gap-2">
                  <span className="shrink-0 font-mono tabular-nums text-xs font-semibold text-accent">
                    {item.typology_code}
                  </span>
                  <span className="truncate text-xs text-secondary">
                    {item.typology_name}
                  </span>
                </div>
                <span className="shrink-0 font-mono tabular-nums text-xs font-medium text-primary">
                  {pct}%
                </span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-subtle">
                <div
                  className={cn(
                    "h-full rounded-full transition-all",
                    pct >= 80
                      ? "bg-severity-low"
                      : pct >= 50
                        ? "bg-severity-medium"
                        : "bg-severity-high",
                  )}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
