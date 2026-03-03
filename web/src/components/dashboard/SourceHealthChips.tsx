import { cn } from "@/lib/utils";
import type { CoverageV2SourceItem, CoverageStatus } from "@/lib/types";

interface SourceHealthChipsProps {
  items: CoverageV2SourceItem[];
}

function statusDotClass(status: CoverageStatus): string {
  const map: Record<CoverageStatus, string> = {
    ok: "bg-green-500",
    warning: "bg-amber-400",
    stale: "bg-yellow-400",
    error: "bg-red-500",
    pending: "bg-gray-400",
  };
  return map[status];
}

function statusLabel(status: CoverageStatus): string {
  const map: Record<CoverageStatus, string> = {
    ok: "ok",
    warning: "atencao",
    stale: "defasado",
    error: "erro",
    pending: "pendente",
  };
  return map[status];
}

function relativeTimeFrom(dateStr: string | null | undefined): string {
  if (!dateStr) return "nunca";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h`;
  return `${Math.floor(hours / 24)}d`;
}

export function SourceHealthChips({ items }: SourceHealthChipsProps) {
  return (
    <div className="rounded-lg border border-gov-gray-200 bg-white">
      <div className="border-b border-gov-gray-200 px-4 py-3">
        <h2 className="text-lg font-semibold text-gov-gray-900">Fontes de Dados</h2>
      </div>
      <ul className="divide-y divide-gov-gray-100">
        {items.map((item) => (
          <li key={item.connector} className="flex items-center gap-3 px-4 py-3">
            {/* Status dot */}
            <span
              className={cn(
                "h-2 w-2 shrink-0 rounded-full",
                statusDotClass(item.worst_status),
              )}
            />

            {/* Name */}
            <span className="min-w-0 flex-1 truncate text-sm text-gov-gray-900">
              {item.connector_label}
            </span>

            {/* Status label + last success */}
            <div className="shrink-0 text-right">
              <span className="font-mono tabular-nums text-xs text-gov-gray-600">
                {statusLabel(item.worst_status)}
              </span>
              <p className="font-mono tabular-nums text-xs text-gov-gray-400">
                {relativeTimeFrom(item.last_success_at)} atrás
              </p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
