"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getRadarV2Cases, getRadarV2Signals } from "@/lib/api";
import type {
  RadarV2CaseItem,
  RadarV2SignalItem,
  RadarV2SummaryResponse,
  SignalSeverity,
} from "@/lib/types";
import { RadarCaseCard } from "@/components/radar/RadarCaseCard";
import { SignalCard } from "./SignalCard";
import { TypologyHeatmap } from "./TypologyHeatmap";
import { TableSkeleton } from "@/components/Skeleton";
import { cn } from "@/lib/utils";
import { ArrowRight } from "lucide-react";

const SEVERITY_CONFIG: { key: SignalSeverity; label: string; color: string; ring: string }[] = [
  { key: "critical", label: "Critico", color: "bg-error", ring: "ring-error/20" },
  { key: "high", label: "Alto", color: "bg-warning", ring: "ring-warning/20" },
  { key: "medium", label: "Medio", color: "bg-amber-500", ring: "ring-amber-500/20" },
  { key: "low", label: "Baixo", color: "bg-info", ring: "ring-info/20" },
];

interface OverviewSectionProps {
  summary: RadarV2SummaryResponse | null;
  summaryLoading: boolean;
  onSignalClick: (signalId: string) => void;
  onTypologyClick: (code: string) => void;
  onTabChange: (tab: "overview" | "dossie" | "rede" | "juridico") => void;
}

export function OverviewSection({ summary, summaryLoading, onSignalClick, onTypologyClick, onTabChange }: OverviewSectionProps) {
  const [topCases, setTopCases] = useState<RadarV2CaseItem[]>([]);
  const [topSignals, setTopSignals] = useState<RadarV2SignalItem[]>([]);
  const [casesLoading, setCasesLoading] = useState(true);
  const [signalsLoading, setSignalsLoading] = useState(true);

  useEffect(() => {
    getRadarV2Cases({ limit: 5 })
      .then((data) => setTopCases(data.items as RadarV2CaseItem[]))
      .catch(() => setTopCases([]))
      .finally(() => setCasesLoading(false));

    getRadarV2Signals({ limit: 5 })
      .then((data) => setTopSignals(data.items))
      .catch(() => setTopSignals([]))
      .finally(() => setSignalsLoading(false));
  }, []);

  const totalSeverity = summary
    ? summary.severity_counts.critical + summary.severity_counts.high + summary.severity_counts.medium + summary.severity_counts.low
    : 0;

  return (
    <div className="flex flex-1 mx-auto w-full max-w-[1280px] relative">
      <div className="flex-1 min-w-0 px-4 py-6 sm:px-6 space-y-8">
      {/* Top row: Cases + Signals side by side */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Top Cases */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-widest text-muted">Casos Prioritarios</p>
              <p className="text-xs text-secondary mt-0.5">Top 5 por severidade</p>
            </div>
            <button
              onClick={() => onTabChange("dossie")}
              className="flex items-center gap-1 text-xs text-accent hover:text-accent/80 transition-colors"
            >
              Ver todos <ArrowRight className="h-3 w-3" />
            </button>
          </div>

          {casesLoading && <TableSkeleton rows={3} />}

          {!casesLoading && topCases.length === 0 && (
            <div className="rounded-xl border border-border bg-surface-card p-8 text-center">
              <p className="text-sm text-muted">Nenhum caso detectado ainda.</p>
              <p className="text-xs text-muted mt-1">Execute o pipeline de sinais para gerar casos.</p>
            </div>
          )}

          {!casesLoading && topCases.length > 0 && (
            <div className="space-y-2">
              {topCases.map((c) => (
                <RadarCaseCard
                  key={c.id}
                  case={c}
                  preview={null}
                  previewLoading={false}
                  expanded={false}
                  onToggleExpand={() => {}}
                  onSignalClick={onSignalClick}
                  activeSignalId={null}
                />
              ))}
            </div>
          )}
        </div>

        {/* Top Signals */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-widest text-muted">Sinais Recentes</p>
              <p className="text-xs text-secondary mt-0.5">Top 5 mais recentes</p>
            </div>
            <button
              onClick={() => onTabChange("dossie")}
              className="flex items-center gap-1 text-xs text-accent hover:text-accent/80 transition-colors"
            >
              Ver todos <ArrowRight className="h-3 w-3" />
            </button>
          </div>

          {signalsLoading && <TableSkeleton rows={3} />}

          {!signalsLoading && topSignals.length === 0 && (
            <div className="rounded-xl border border-border bg-surface-card p-8 text-center">
              <p className="text-sm text-muted">Nenhum sinal detectado ainda.</p>
              <p className="text-xs text-muted mt-1">Execute o pipeline de sinais para gerar deteccoes.</p>
            </div>
          )}

          {!signalsLoading && topSignals.length > 0 && (
            <div className="space-y-2">
              {topSignals.map((s) => (
                <SignalCard key={s.id} signal={s} onClick={onSignalClick} />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Bottom row: Typology Heatmap + Severity Distribution */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Typology distribution */}
        <div>
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted">Distribuicao por Tipologia</p>
          <p className="text-xs text-secondary mt-0.5 mb-3">Sinais agrupados por tipo de irregularidade</p>
          {summaryLoading ? (
            <TableSkeleton rows={4} />
          ) : summary && summary.typology_counts.length > 0 ? (
            <TypologyHeatmap counts={summary.typology_counts} onTypologyClick={onTypologyClick} />
          ) : (
            <div className="rounded-xl border border-border bg-surface-card p-8 text-center">
              <p className="text-sm text-muted">Sem dados de tipologia.</p>
            </div>
          )}
        </div>

        {/* Severity distribution */}
        <div>
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted">Distribuicao por Severidade</p>
          <p className="text-xs text-secondary mt-0.5 mb-3">Sinais classificados por nivel de risco</p>
          {summaryLoading ? (
            <TableSkeleton rows={4} />
          ) : summary ? (
            <div className="space-y-3 rounded-xl border border-border bg-surface-card p-4">
              {SEVERITY_CONFIG.map((sev) => {
                const count = summary.severity_counts[sev.key];
                const pct = totalSeverity > 0 ? (count / totalSeverity) * 100 : 0;
                return (
                  <div key={sev.key} className="flex items-center gap-3">
                    <span className="w-14 shrink-0 text-xs font-medium text-secondary">{sev.label}</span>
                    <div className="flex-1 h-3 rounded-full bg-surface-subtle overflow-hidden">
                      <div
                        className={cn("h-full rounded-full transition-all duration-500", sev.color)}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="w-12 shrink-0 text-right font-mono text-xs text-primary">{count}</span>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="rounded-xl border border-border bg-surface-card p-8 text-center">
              <p className="text-sm text-muted">Sem dados de severidade.</p>
            </div>
          )}
        </div>
      </div>
      </div>
    </div>
  );
}
