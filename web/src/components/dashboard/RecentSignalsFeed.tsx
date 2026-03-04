"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { cn, severityDotColor } from "@/lib/utils";
import type { RadarV2SignalItem } from "@/lib/types";

interface RecentSignalsFeedProps {
  signals: RadarV2SignalItem[];
}

function relativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h`;
  return `${Math.floor(hours / 24)}d`;
}

function truncate(str: string, max: number): string {
  return str.length > max ? str.slice(0, max) + "…" : str;
}

export function RecentSignalsFeed({ signals }: RecentSignalsFeedProps) {
  return (
    <div className="linear-card rounded-lg border border-border bg-surface-card">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold text-primary">
          Últimos Sinais{" "}
          <span className="ml-1 font-normal text-secondary">(últimas 24h)</span>
        </h2>
        <Link
          href="/radar"
          className="inline-flex items-center gap-1 text-xs font-medium text-accent hover:text-accent-hover hover:underline"
        >
          ver todos
          <ArrowRight className="h-3 w-3" />
        </Link>
      </div>

      {signals.length === 0 ? (
        <EmptyState
          title="Nenhum sinal recente"
          description="Não há sinais nas últimas 24h."
          className="rounded-none border-0"
        />
      ) : (
        <ul className="divide-y divide-border">
          {signals.map((signal) => (
            <li key={signal.id}>
              <Link
                href={`/signal/${signal.id}`}
                className="flex items-center gap-3 px-4 py-3 transition hover:bg-surface-subtle"
              >
                {/* Severity dot */}
                <span
                  className={cn(
                    "mt-0.5 h-2 w-2 shrink-0 rounded-full",
                    severityDotColor(signal.severity),
                  )}
                />

                {/* Badge + title block */}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <Badge severity={signal.severity} className="shrink-0" />
                    <span className="font-mono tabular-nums text-xs text-secondary">
                      {signal.typology_code}
                    </span>
                  </div>
                  <p className="mt-0.5 truncate text-sm text-primary">
                    {truncate(signal.title, 60)}
                  </p>
                </div>

                {/* Value + time */}
                <div className="shrink-0 text-right">
                  {signal.event_count > 0 && (
                    <p className="font-mono tabular-nums text-xs text-secondary">
                      {signal.event_count} ev.
                    </p>
                  )}
                  <p className="font-mono tabular-nums text-xs text-muted">
                    {relativeTime(signal.created_at)}
                  </p>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
