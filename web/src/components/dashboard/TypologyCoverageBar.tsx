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
    <div className="rounded-lg border border-gov-gray-200 bg-white">
      <div className="border-b border-gov-gray-200 px-4 py-3">
        <h2 className="text-lg font-semibold text-gov-gray-900">Cobertura de Tipologias</h2>
      </div>
      <ul className="divide-y divide-gov-gray-200">
        {items.map((item) => {
          const pct = coveragePct(item);
          return (
            <li key={item.typology_code} className="px-4 py-3">
              <div className="mb-1.5 flex items-center justify-between gap-2">
                <div className="flex min-w-0 items-center gap-2">
                  <span className="shrink-0 font-mono tabular-nums text-xs font-semibold text-gov-blue-700">
                    {item.typology_code}
                  </span>
                  <span className="truncate text-xs text-gov-gray-600">
                    {item.typology_name}
                  </span>
                </div>
                <span className="shrink-0 font-mono tabular-nums text-xs font-medium text-gov-gray-900">
                  {pct}%
                </span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-gov-gray-100">
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
