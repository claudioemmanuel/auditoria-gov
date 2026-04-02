import { cn } from "@/lib/utils";
import type { CoverageV2SourceItem, CoverageStatus } from "@/lib/types";

interface SourceHealthChipsProps {
  items: CoverageV2SourceItem[];
}

function statusDotClass(status: CoverageStatus): string {
  const map: Record<CoverageStatus, string> = {
    ok: "bg-success",
    warning: "bg-amber",
    stale: "bg-amber",
    error: "bg-error",
    pending: "bg-placeholder",
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
    <div className="surface-card rounded-lg border border-border bg-surface-card">
      <div className="border-b border-border px-4 py-3">
        <h2 className="font-display text-sm font-semibold text-primary">Fontes de Dados</h2>
      </div>
      <ul className="divide-y divide-border">
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
            <span className="min-w-0 flex-1 truncate text-sm text-primary">
              {item.connector_label}
            </span>

            {/* Status label + last success */}
            <div className="shrink-0 text-right">
              <span className="font-mono tabular-nums text-xs text-secondary">
                {statusLabel(item.worst_status)}
              </span>
              <p className="font-mono tabular-nums text-xs text-muted">
                {relativeTimeFrom(item.last_success_at)} atrás
              </p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
