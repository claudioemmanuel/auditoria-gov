"use client";

import type { RadarV2TypologyCount } from "@/lib/types";

interface TypologyHeatmapProps {
  counts: RadarV2TypologyCount[];
  onTypologyClick?: (code: string) => void;
}

export function TypologyHeatmap({ counts, onTypologyClick }: TypologyHeatmapProps) {
  if (counts.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-surface-card p-6 text-center">
        <p className="text-sm text-muted">Nenhuma tipologia com sinais detectados.</p>
      </div>
    );
  }

  const sorted = [...counts].sort((a, b) => b.count - a.count);
  const maxCount = sorted[0].count;

  return (
    <div className="space-y-1.5">
      {sorted.map((t) => {
        const pct = maxCount > 0 ? (t.count / maxCount) * 100 : 0;
        return (
          <button
            key={t.code}
            onClick={() => onTypologyClick?.(t.code)}
            className="group flex w-full items-center gap-3 rounded-lg px-2 py-1.5 text-left transition-colors hover:bg-surface-subtle"
          >
            <span className="w-10 shrink-0 font-mono text-xs text-muted">{t.code}</span>
            <span className="flex-1 min-w-0 truncate text-xs text-secondary group-hover:text-primary">
              {t.name}
            </span>
            <div className="w-32 shrink-0">
              <div className="h-2 rounded-full bg-surface-subtle overflow-hidden">
                <div
                  className="h-full rounded-full bg-accent transition-all duration-300"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
            <span className="w-10 shrink-0 text-right font-mono text-xs font-medium text-primary">
              {t.count}
            </span>
          </button>
        );
      })}
    </div>
  );
}
