import {
  getRadarV2Summary,
  getRadarV2Signals,
  getRadarV2Coverage,
  getCoverageV2Sources,
} from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { SeverityCountCards } from "@/components/dashboard/SeverityCountCards";
import { RecentSignalsFeed } from "@/components/dashboard/RecentSignalsFeed";
import { TypologyCoverageBar } from "@/components/dashboard/TypologyCoverageBar";
import { SourceHealthChips } from "@/components/dashboard/SourceHealthChips";
import type {
  RadarV2SummaryResponse,
  RadarV2CoverageResponse,
  CoverageV2SourcesResponse,
  PaginatedResponse,
  RadarV2SignalItem,
} from "@/lib/types";

export default async function HomePage() {
  type Results = [
    RadarV2SummaryResponse | null,
    PaginatedResponse<RadarV2SignalItem> | null,
    RadarV2CoverageResponse | null,
    CoverageV2SourcesResponse | null,
  ];

  const [summary, signals, coverage, sources]: Results = await Promise.all([
    getRadarV2Summary().catch(() => null),
    getRadarV2Signals({ limit: 5, sort: "analysis_date" }).catch(() => null),
    getRadarV2Coverage().catch(() => null),
    getCoverageV2Sources({ limit: 6, sort: "status_desc" }).catch(() => null),
  ]);

  const snapshotAt = summary?.snapshot_at
    ? formatDate(summary.snapshot_at)
    : null;

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-6">
      {/* ── Header ───────────────────────────────────────────────── */}
      <div className="flex items-baseline justify-between gap-4">
        <h1 className="text-xl font-bold text-primary">Panorama de Riscos</h1>
        {snapshotAt && (
          <p className="text-xs text-muted">
            snapshot:{" "}
            <span className="font-mono tabular-nums">{snapshotAt}</span>
          </p>
        )}
      </div>

      {/* ── Error banner if everything failed ────────────────────── */}
      {!summary && !signals && !coverage && !sources && (
        <div className="rounded-lg border border-border bg-surface-card px-4 py-6 text-center text-sm text-secondary">
          Não foi possível carregar os dados. Verifique a conectividade com a
          API.
        </div>
      )}

      {/* ── Severity count cards ──────────────────────────────────── */}
      {summary ? (
        <SeverityCountCards counts={summary.severity_counts} />
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {["Críticos", "Altos", "Médios", "Baixos"].map((label) => (
            <div
              key={label}
              className="rounded-lg border border-border bg-surface-card p-4"
            >
              <p className="text-xs font-medium uppercase tracking-wide text-secondary">
                {label}
              </p>
              <p className="mt-1 font-mono tabular-nums text-3xl font-bold text-muted">
                —
              </p>
            </div>
          ))}
        </div>
      )}

      {/* ── Recent signals ────────────────────────────────────────── */}
      <RecentSignalsFeed signals={signals?.items ?? []} />

      {/* ── Bottom row: coverage + sources ───────────────────────── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {coverage ? (
          <TypologyCoverageBar items={coverage.items.slice(0, 8)} />
        ) : (
          <div className="rounded-lg border border-border bg-surface-card px-4 py-8 text-center text-sm text-secondary">
            Cobertura indisponível.
          </div>
        )}

        {sources ? (
          <SourceHealthChips items={sources.items} />
        ) : (
          <div className="rounded-lg border border-border bg-surface-card px-4 py-8 text-center text-sm text-secondary">
            Fontes indisponíveis.
          </div>
        )}
      </div>
    </div>
  );
}
