"use client";

import type { RadarV2SignalItem } from "@/lib/types";
import { cn, formatBRL, severityDotColor, severityColor } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import { relativeTime } from "@/lib/utils";

interface RadarSignalsListProps {
  items: RadarV2SignalItem[];
  onOpenPreview: (signalId: string) => void;
}

export function RadarSignalsList({ items, onOpenPreview }: RadarSignalsListProps) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-surface-card shadow-sm">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-border bg-surface-subtle">
          <tr>
            <th className="px-3 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted">Sev</th>
            <th className="px-3 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted">Tipo</th>
            <th className="px-3 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted">Titulo</th>
            <th className="px-3 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted">Entidade</th>
            <th className="px-3 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-muted">Valor</th>
            <th className="px-3 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted">Tempo</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {items.map((signal) => {
            const topEntity = signal.entity_count > 0 ? `${signal.entity_count} entidade${signal.entity_count !== 1 ? "s" : ""}` : null;
            const valueDisplay = typeof (signal as RadarV2SignalItem & { total_value_brl?: number }).total_value_brl === "number"
              ? formatBRL((signal as RadarV2SignalItem & { total_value_brl?: number }).total_value_brl as number)
              : null;

            return (
              <tr
                key={signal.id}
                onClick={() => onOpenPreview(signal.id)}
                className="cursor-pointer transition-colors hover:bg-surface-subtle"
              >
                {/* Severity dot + badge */}
                <td className="px-3 py-2.5">
                  <div className="flex items-center gap-1.5">
                    <span
                      className={cn("h-2 w-2 flex-shrink-0 rounded-full", severityDotColor(signal.severity))}
                    />
                    <Badge severity={signal.severity} className="hidden sm:inline-flex" />
                  </div>
                </td>

                {/* Typology code */}
                <td className="px-3 py-2.5">
                  <span className="font-mono text-xs font-bold text-primary tabular-nums">
                    {signal.typology_code}
                  </span>
                </td>

                {/* Title truncated */}
                <td className="max-w-[20rem] px-3 py-2.5">
                  <span className="block truncate text-xs font-medium text-primary" title={signal.title}>
                    {signal.title.length > 60 ? `${signal.title.slice(0, 60)}…` : signal.title}
                  </span>
                </td>

                {/* Top entity */}
                <td className="max-w-[10rem] px-3 py-2.5">
                  <span className="block truncate text-xs text-secondary">
                    {topEntity ?? "—"}
                  </span>
                </td>

                {/* Value */}
                <td className="px-3 py-2.5 text-right">
                  <span className="font-mono text-xs tabular-nums text-secondary">
                    {valueDisplay ?? "—"}
                  </span>
                </td>

                {/* Relative time */}
                <td className="whitespace-nowrap px-3 py-2.5">
                  <span className="text-xs text-muted">
                    {relativeTime(signal.created_at)}
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
