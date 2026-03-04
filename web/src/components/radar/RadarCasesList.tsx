"use client";

import type { RadarV2CaseItem, RadarV2CasePreviewResponse } from "@/lib/types";
import { cn, formatBRL, severityDotColor } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import { relativeTime } from "@/lib/utils";

interface RadarCasesListProps {
  items: RadarV2CaseItem[];
  onOpenPreview: (caseId: string) => void;
}

export function RadarCasesList({ items, onOpenPreview }: RadarCasesListProps) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-surface-card">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-border bg-surface-subtle">
          <tr>
            <th className="px-3 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted">Sev</th>
            <th className="px-3 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted">Sinais</th>
            <th className="px-3 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted">Titulo</th>
            <th className="px-3 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted">Entidades</th>
            <th className="px-3 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-muted">Valor</th>
            <th className="px-3 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted">Tempo</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {items.map((item) => {
            const caseWithValue = item as RadarV2CaseItem & { total_value_brl?: number; entity_names?: string[] };
            const entityNames: string[] = caseWithValue.entity_names ?? [];
            const entityDisplay = entityNames.length > 0
              ? entityNames.slice(0, 2).join(", ") + (entityNames.length > 2 ? ` +${entityNames.length - 2}` : "")
              : `${item.entity_count} entidade${item.entity_count !== 1 ? "s" : ""}`;
            const valueDisplay = typeof caseWithValue.total_value_brl === "number"
              ? formatBRL(caseWithValue.total_value_brl)
              : null;

            return (
              <tr
                key={item.id}
                onClick={() => onOpenPreview(item.id)}
                className="linear-row cursor-pointer transition-colors hover:bg-surface-subtle"
              >
                {/* Severity dot + badge */}
                <td className="px-3 py-2">
                  <div className="flex items-center gap-1.5">
                    <span
                      className={cn("h-2 w-2 flex-shrink-0 rounded-full", severityDotColor(item.severity))}
                    />
                    <Badge severity={item.severity} className="hidden sm:inline-flex" />
                  </div>
                </td>

                {/* Signal count */}
                <td className="px-3 py-2">
                  <span className="font-mono text-xs font-bold tabular-nums text-primary">
                    {item.signal_count}
                  </span>
                </td>

                {/* Title */}
                <td className="max-w-[20rem] px-3 py-2">
                  <span className="block truncate text-xs font-medium text-primary" title={item.title}>
                    {item.title}
                  </span>
                </td>

                {/* Entity names (first 2) */}
                <td className="max-w-[12rem] px-3 py-2">
                  <span className="block truncate text-xs text-secondary">
                    {entityDisplay}
                  </span>
                </td>

                {/* Total value */}
                <td className="px-3 py-2 text-right">
                  <span className="font-mono text-xs tabular-nums text-secondary">
                    {valueDisplay ?? "—"}
                  </span>
                </td>

                {/* Relative time */}
                <td className="whitespace-nowrap px-3 py-2">
                  <span className="text-xs text-muted">
                    {relativeTime(item.created_at)}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
