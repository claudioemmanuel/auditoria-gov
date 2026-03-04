"use client";

import type { CoverageV2AnalyticsResponse } from "@/lib/types";
import { ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "@/lib/utils";

interface CoverageAnalyticsPanelProps {
  open: boolean;
  loading: boolean;
  data: CoverageV2AnalyticsResponse | null;
  onToggle: () => void;
}

export function CoverageAnalyticsPanel({
  open,
  loading,
  data,
  onToggle,
}: CoverageAnalyticsPanelProps) {
  return (
    <div className="rounded-xl border border-border bg-surface-card">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
      >
        <div>
          <h2 className="font-display text-sm font-semibold text-primary">Cobertura por Tipologia</h2>
          <p className="text-xs text-muted">Aptidão das tipologias e bloqueios de domínio</p>
        </div>
        {open ? (
          <ChevronUp className="h-4 w-4 flex-shrink-0 text-muted" />
        ) : (
          <ChevronDown className="h-4 w-4 flex-shrink-0 text-muted" />
        )}
      </button>

      {open && (
        <div className="border-t border-border px-4 pb-4 pt-3">
          {loading ? (
            <div className="h-24 animate-pulse rounded-lg bg-surface-subtle" />
          ) : !data ? (
            <p className="text-sm text-muted">Não foi possível carregar os indicadores analíticos.</p>
          ) : (
            <>
              {/* Summary counters */}
              <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
                <div className="rounded-lg border border-border bg-surface-subtle p-3">
                  <p className="text-xs uppercase tracking-wide text-muted">Tipologias</p>
                  <p className="mt-1 text-lg font-semibold text-primary">{data.summary.total_typologies}</p>
                </div>
                <div className="rounded-lg border border-border bg-surface-subtle p-3">
                  <p className="text-xs uppercase tracking-wide text-muted">Aptas</p>
                  <p className="mt-1 text-lg font-semibold text-success">{data.summary.apt_count}</p>
                </div>
                <div className="rounded-lg border border-border bg-surface-subtle p-3">
                  <p className="text-xs uppercase tracking-wide text-muted">Bloqueadas</p>
                  <p className="mt-1 text-lg font-semibold text-error">{data.summary.blocked_count}</p>
                </div>
                <div className="rounded-lg border border-border bg-surface-subtle p-3">
                  <p className="text-xs uppercase tracking-wide text-muted">Sinais (30d)</p>
                  <p className="mt-1 text-lg font-semibold text-accent">{data.summary.with_signals_30d}</p>
                </div>
              </div>

              {/* Typology progress bars */}
              <div className="mt-4 space-y-2">
                {data.items.slice(0, 20).map((item) => {
                  const pct = item.apt
                    ? Math.min(
                        100,
                        item.domains_available.length > 0
                          ? Math.round(
                              (item.domains_available.length /
                                Math.max(item.required_domains.length, 1)) *
                                100,
                            )
                          : 100,
                      )
                    : Math.round(
                        (item.domains_available.length /
                          Math.max(item.required_domains.length, 1)) *
                          100,
                      );

                  return (
                    <div key={item.typology_code} className="flex items-center gap-3">
                      <span className="w-8 flex-shrink-0 font-mono tabular-nums text-xs text-muted">
                        {item.typology_code}
                      </span>
                      <div className="flex-1 overflow-hidden rounded-full bg-surface-subtle">
                        <div
                          className={cn(
                            "h-2 rounded-full transition-all",
                            item.apt ? "bg-success" : pct > 0 ? "bg-amber" : "bg-error",
                          )}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span
                        className={cn(
                          "w-8 flex-shrink-0 text-right font-mono tabular-nums text-xs",
                          item.apt ? "text-success" : "text-amber",
                        )}
                      >
                        {pct}%
                      </span>
                      {!item.apt && (
                        <span className="rounded-full bg-error-subtle px-1.5 py-0.5 text-[10px] font-medium text-error">
                          bloq.
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
