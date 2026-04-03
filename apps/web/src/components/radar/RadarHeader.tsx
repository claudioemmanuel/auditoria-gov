"use client";

import { Radar, ScanSearch } from "lucide-react";

export function RadarHeader() {
  return (
    <div className="ow-card ow-card-glass ow-card-signal p-4 md:p-5">
      <div className="flex items-start gap-4">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-[color:var(--color-brand-border)] bg-[color:var(--color-brand-dim)] shadow-[var(--shadow-brand)]">
          <Radar className="h-6 w-6 text-[var(--color-brand-light)]" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--color-brand-light)]">
            <ScanSearch className="h-3.5 w-3.5" />
            Signal Lens
          </div>
          <h1 className="font-display text-2xl font-bold tracking-tight text-[var(--color-text)] sm:text-3xl">
            Investigação
          </h1>
          <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-[var(--color-text-2)]">
            Centro de sinais, casos e inteligência exploratória sobre dados públicos federais.
          </p>
        </div>
      </div>
    </div>
  );
}
