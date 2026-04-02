"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  getRadarV2Cases,
  getRadarV2Coverage,
  getRadarV2Summary,
} from "@/lib/api";
import type {
  RadarV2CaseItem,
  RadarV2CoverageResponse,
  RadarV2SummaryResponse,
} from "@/lib/types";
import { RadarSummaryStrip } from "@/components/radar/RadarSummaryStrip";
import { RadarInlineFilters } from "@/components/radar/RadarInlineFilters";
import { RadarBreadcrumb } from "@/components/radar/RadarBreadcrumb";
import { RadarCoveragePanel } from "@/components/radar/RadarCoveragePanel";
import { TableSkeleton } from "@/components/Skeleton";
import { Button } from "@/components/Button";
import { TYPOLOGY_LABELS, TYPOLOGY_META, CORRUPTION_TYPE_LABELS } from "@/lib/constants";
import { ChevronDown, ChevronRight, ChevronLeft } from "lucide-react";

const PAGE_SIZE = 10;

const SEVERITY_ORDER = ["critical", "high", "medium", "low"] as const;
type SeverityLevel = typeof SEVERITY_ORDER[number];

const SEV: Record<SeverityLevel, { dot: string; text: string; border: string; bg: string; bar: string; label: string }> = {
  critical: { dot: "bg-error",      text: "text-error",      border: "border-error/25",      bg: "bg-error/5",      bar: "bg-error",      label: "Crítico" },
  high:     { dot: "bg-amber",      text: "text-amber",      border: "border-amber/25",      bg: "bg-amber/5",      bar: "bg-amber",      label: "Alto"    },
  medium:   { dot: "bg-yellow-500", text: "text-yellow-600", border: "border-yellow-500/25", bg: "bg-yellow-500/5", bar: "bg-yellow-500", label: "Médio"   },
  low:      { dot: "bg-sky-500",    text: "text-sky-500",    border: "border-sky-500/25",    bg: "bg-sky-500/5",    bar: "bg-sky-500",    label: "Baixo"   },
};

type FilterState = {
  typology: string;
  periodFrom: string;
  periodTo: string;
  corruptionType: string;
  sphere: string;
};

// ── Case card ────────────────────────────────────────────────────────────────

function CaseListCard({ item }: { item: RadarV2CaseItem }) {
  const s = SEV[item.severity as SeverityLevel] ?? SEV.low;
  const formatPeriod = (d?: string | null) =>
    d ? new Date(d).toLocaleDateString("pt-BR", { month: "short", year: "2-digit" }) : null;
  const periodFrom = formatPeriod(item.period_start);
  const periodTo = formatPeriod(item.period_end);
  const periodStr = periodFrom && periodTo ? `${periodFrom} → ${periodTo}` : periodFrom ?? periodTo ?? null;
  const foundDate = new Date(item.created_at).toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" });

  const corruptionTypes = [...new Set(item.typology_codes.flatMap((c) => TYPOLOGY_META[c]?.corruption_types ?? []))];

  return (
    <div className={`relative flex flex-col rounded-lg border border-[var(--color-border-light)] bg-white overflow-hidden transition-all hover:shadow-lg hover:shadow-[var(--color-primary-dark)]/10 hover:border-[var(--color-secondary-light)]`}>
      {/* Top severity bar */}
      <div className={`h-1 w-full ${s.bar}`} />

      <div className="flex-1 p-6">
        {/* KICKER: typology codes with background pills */}
        <div className="mb-3 flex flex-wrap items-center gap-2">
          {item.typology_codes.slice(0, 2).map((code) => (
            <span
              key={code}
              className="inline-flex items-center rounded-full border border-[var(--color-secondary-light)] bg-[var(--color-secondary-light)]/10 px-2.5 py-1 font-mono text-[11px] font-semibold text-[var(--color-secondary)] uppercase tracking-wide"
              title={TYPOLOGY_LABELS[code]}
            >
              {code}
            </span>
          ))}
          {item.typology_codes.length > 2 && (
            <span className="font-mono text-xs text-[var(--color-text-secondary)]">+{item.typology_codes.length - 2}</span>
          )}
        </div>

        {/* HEADLINE: case title - using new typography system */}
        <h3 className="font-display text-base font-bold leading-snug text-[var(--color-text-primary)] line-clamp-2 mb-3" title={item.title}>
          {item.title}
        </h3>

        {/* METADATA: date + period + signal count */}
        <div className="mb-4 flex flex-wrap items-center gap-3 text-sm text-[var(--color-text-secondary)]">
          <span className="font-mono text-xs">{foundDate}</span>
          {periodStr && (
            <>
              <span className="h-1 w-1 rounded-full bg-[var(--color-border-light)]" />
              <span className="font-mono text-xs">{periodStr}</span>
            </>
          )}
          <span className="h-1 w-1 rounded-full bg-[var(--color-border-light)]" />
          <span className="font-semibold">
            <span className={s.text}>{item.signal_count}</span>
            {` ${item.signal_count !== 1 ? "sinais" : "sinal"}`}
          </span>
        </div>

        {/* TAGS: corruption types - simpler inline layout */}
        {corruptionTypes.length > 0 && (
          <div className="mb-4 flex flex-wrap gap-2">
            {corruptionTypes.slice(0, 3).map((ct) => (
              <span
                key={ct}
                className="rounded-full border border-[var(--color-border-light)] bg-[var(--color-surface-hover)] px-3 py-1 font-mono text-[10px] text-[var(--color-text-secondary)]"
              >
                {CORRUPTION_TYPE_LABELS[ct] ?? ct}
              </span>
            ))}
          </div>
        )}

        {/* CTA Button - using new Button style inline */}
        <div className="inline-flex items-center gap-2 rounded-full border border-[var(--color-secondary)] bg-[var(--color-secondary)] px-4 py-2 text-sm font-semibold text-white transition-all hover:shadow-md hover:shadow-[var(--color-secondary)]/30">
          <span>Ver Dossiê</span>
          <span className="text-lg">→</span>
        </div>
      </div>
    </div>
  );
}

// ── Severity accordion section ───────────────────────────────────────────────

function SeverityAccordionSection({
  severity,
  count,
  filters,
  search,
  defaultOpen = false,
}: {
  severity: SeverityLevel;
  count: number;
  filters: FilterState;
  search: string;
  defaultOpen?: boolean;
}) {
  const s = SEV[severity];
  const [open, setOpen] = useState(defaultOpen);
  const [offset, setOffset] = useState(0);
  const [cases, setCases] = useState<RadarV2CaseItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const filterKey = JSON.stringify(filters);
  const abortRef = useRef<AbortController | null>(null);

  // Reset offset when filters change
  useEffect(() => {
    setOffset(0);
  }, [filterKey]); // eslint-disable-line react-hooks/exhaustive-deps

  // Fetch cases when open (or when offset/filters change while open)
  useEffect(() => {
    if (!open) return;
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    setLoading(true);
    setError(null);

    getRadarV2Cases({
      severity,
      offset,
      limit: PAGE_SIZE,
      typology: filters.typology || undefined,
      period_from: filters.periodFrom || undefined,
      period_to: filters.periodTo || undefined,
      corruption_type: filters.corruptionType || undefined,
      sphere: filters.sphere || undefined,
    })
      .then((data) => {
        if (ctrl.signal.aborted) return;
        setTotal(data.total);
        setCases(data.items as RadarV2CaseItem[]);
      })
      .catch(() => {
        if (!ctrl.signal.aborted) setError("Erro ao carregar casos.");
      })
      .finally(() => {
        if (!ctrl.signal.aborted) setLoading(false);
      });

    return () => ctrl.abort();
  }, [open, offset, filterKey, severity]); // eslint-disable-line react-hooks/exhaustive-deps

  const filteredCases = search.trim()
    ? cases.filter((c) => c.title.toLowerCase().includes(search.toLowerCase()))
    : cases;
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <div className={`rounded-lg border border-[var(--color-border-light)] overflow-hidden bg-white transition-all`}>
      {/* Modern header with gradient background */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={`w-full flex items-center gap-4 px-6 py-5 text-left transition-all hover:bg-[var(--color-surface-hover)]`}
        style={{
          backgroundImage: open 
            ? `linear-gradient(135deg, ${s.bg === 'bg-error/5' ? 'rgba(220, 38, 38, 0.05)' : s.bg === 'bg-amber/5' ? 'rgba(217, 119, 6, 0.05)' : s.bg === 'bg-yellow-500/5' ? 'rgba(234, 179, 8, 0.05)' : 'rgba(14, 165, 233, 0.05)'})`
            : 'none'
        }}
      >
        {/* Severity indicator dot + label */}
        <div className="flex items-center gap-3">
          <span className={`h-3 w-3 rounded-full ${s.dot}`} />
          <span className={`font-mono text-sm font-bold tracking-widest uppercase ${s.text}`}>{s.label}</span>
        </div>

        {/* Count badge */}
        <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 font-mono text-xs font-semibold tabular-nums ${s.border} ${s.text}`}>
          {count.toLocaleString("pt-BR")}
          <span className="font-normal opacity-70">{count !== 1 ? "casos" : "caso"}</span>
        </span>

        <div className="flex-1" />

        {/* Indicator chevron */}
        <div className={`transition-transform duration-300 ${open ? 'rotate-180' : ''}`}>
          {open
            ? <ChevronDown className={`h-5 w-5 ${s.text}`} />
            : <ChevronRight className={`h-5 w-5 ${s.text}`} />
          }
        </div>
      </button>

      {/* Body - cases grid */}
      {open && (
        <div className="border-t border-[var(--color-border-light)] bg-[var(--color-surface-base)] px-6 py-6">
          {loading && <TableSkeleton rows={3} />}

          {error && (
            <div className="rounded-lg border border-[var(--color-severity-critical)]/20 bg-[var(--color-severity-critical)]/5 px-4 py-3 text-sm text-[var(--color-severity-critical)]">
              {error}
            </div>
          )}

          {!loading && !error && filteredCases.length === 0 && (
            <p className="text-sm text-[var(--color-text-secondary)] text-center py-8">
              {search.trim() ? "Nenhum caso encontrado para esta busca." : "Nenhum caso nesta severidade."}
            </p>
          )}

          {!loading && !error && filteredCases.length > 0 && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {filteredCases.map((c) => (
                <Link key={c.id} href={`/radar/dossie/${c.id}`} className="block">
                  <CaseListCard item={c} />
                </Link>
              ))}
            </div>
          )}

          {/* Pagination */}
          {!loading && !search.trim() && totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-[var(--color-border-light)] pt-6 mt-6">
              <span className="text-sm text-[var(--color-text-secondary)] font-mono">
                Página {currentPage} de {totalPages}
              </span>
              <div className="flex items-center gap-3">
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={currentPage <= 1}
                  onClick={(e) => { e.preventDefault(); setOffset(Math.max(0, offset - PAGE_SIZE)); }}
                >
                  <ChevronLeft className="h-4 w-4" />
                  Anterior
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={currentPage >= totalPages}
                  onClick={(e) => { e.preventDefault(); setOffset(offset + PAGE_SIZE); }}
                >
                  Próxima
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main page inner ──────────────────────────────────────────────────────────

function RadarPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const typology       = searchParams.get("typology") || "";
  const periodFrom     = searchParams.get("period_from") || "";
  const periodTo       = searchParams.get("period_to") || "";
  const corruptionType = searchParams.get("corruption_type") || "";
  const sphere         = searchParams.get("sphere") || "";

  const updateParam = useCallback(
    (updates: Record<string, string>) => {
      const params = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(updates)) {
        if (value) { params.set(key, value); } else { params.delete(key); }
      }
      router.replace(`?${params.toString()}`, { scroll: false });
    },
    [router, searchParams],
  );

  const setTypology       = (v: string) => updateParam({ typology: v });
  const setPeriodFrom     = (v: string) => updateParam({ period_from: v });
  const setPeriodTo       = (v: string) => updateParam({ period_to: v });
  const setCorruptionType = (v: string) => updateParam({ corruption_type: v });
  const setSphere         = (v: string) => updateParam({ sphere: v });
  const clearAllFilters   = () => { router.replace("/radar", { scroll: false }); };

  const [summary, setSummary]               = useState<RadarV2SummaryResponse | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [search, setSearch]                 = useState("");

  const [coverageOpen, setCoverageOpen]       = useState(false);
  const [coverageLoading, setCoverageLoading] = useState(false);
  const [coverageError, setCoverageError]     = useState<string | null>(null);
  const [coverage, setCoverage]               = useState<RadarV2CoverageResponse | null>(null);

  const filters: FilterState = { typology, periodFrom, periodTo, corruptionType, sphere };

  useEffect(() => {
    setSummaryLoading(true);
    getRadarV2Summary({
      typology: typology || undefined,
      period_from: periodFrom || undefined,
      period_to: periodTo || undefined,
      corruption_type: corruptionType || undefined,
      sphere: sphere || undefined,
    })
      .then(setSummary)
      .catch(() => setSummary(null))
      .finally(() => setSummaryLoading(false));
  }, [typology, periodFrom, periodTo, corruptionType, sphere]);

  const openCoverage = () => {
    setCoverageOpen(true);
    if (coverage || coverageLoading) return;
    setCoverageLoading(true);
    setCoverageError(null);
    getRadarV2Coverage()
      .then(setCoverage)
      .catch(() => setCoverageError("Não foi possível carregar a cobertura analítica"))
      .finally(() => setCoverageLoading(false));
  };

  return (
    <>
      {/* Summary strip - modern card styling */}
      <div className="border-b border-[var(--color-border-light)] bg-white">
        <div className="mx-auto max-w-[1280px] px-4 py-6 sm:px-6">
          <RadarSummaryStrip
            summary={summary}
            loading={summaryLoading}
            activeSeverity=""
            onSeverityClick={() => {}}
          />
        </div>
      </div>

      <div className="mx-auto w-full max-w-[1280px] px-4 py-8 sm:px-6">
        {/* Header + filters section */}
        <div className="mb-8 flex flex-col gap-6">
          <div>
            <RadarBreadcrumb crumbs={[{ label: "Radar" }]} />
            <h1 className="font-display text-3xl font-bold text-[var(--color-text-primary)] mt-2">
              Análise de Risco por Severidade
            </h1>
            <p className="text-base text-[var(--color-text-secondary)] mt-2">
              Explore casos agrupados por nível de severidade. Clique em uma seção para visualizar os casos relacionados.
            </p>
          </div>
          <RadarInlineFilters
            search={search}
            onSearchChange={setSearch}
            typology={typology}
            periodFrom={periodFrom}
            periodTo={periodTo}
            corruptionType={corruptionType}
            sphere={sphere}
            onTypologyChange={setTypology}
            onPeriodFromChange={setPeriodFrom}
            onPeriodToChange={setPeriodTo}
            onCorruptionTypeChange={setCorruptionType}
            onSphereChange={setSphere}
            onClearAll={clearAllFilters}
          />
        </div>

        {/* Severity accordions - modern spacing */}
        <div className="space-y-4">
          {summaryLoading
            ? null
            : (() => {
                const activeSevs = SEVERITY_ORDER.filter(
                  (sev) => (summary?.severity_counts[sev] ?? 0) > 0,
                );
                if (activeSevs.length === 0) {
                  return (
                    <div className="rounded-lg border border-[var(--color-border-light)] bg-white p-12 text-center">
                      <p className="text-lg text-[var(--color-text-secondary)]">
                        Nenhum caso encontrado com os filtros aplicados.
                      </p>
                    </div>
                  );
                }
                return activeSevs.map((sev, i) => (
                  <SeverityAccordionSection
                    key={sev}
                    severity={sev}
                    count={summary!.severity_counts[sev]!}
                    filters={filters}
                    search={search}
                    defaultOpen={i === 0}
                  />
                ));
              })()
          }
        </div>
      </div>

      <RadarCoveragePanel
        open={coverageOpen}
        onClose={() => setCoverageOpen(false)}
        loading={coverageLoading}
        error={coverageError}
        data={coverage}
      />
    </>
  );
                    filters={filters}
                    search={search}
                    defaultOpen={i === 0}
                  />
                ));
              })()
          }
        </div>
      </div>

      <RadarCoveragePanel
        open={coverageOpen}
        onClose={() => setCoverageOpen(false)}
        loading={coverageLoading}
        error={coverageError}
        data={coverage}
      />
    </>
  );
}

export default function RadarPage() {
  return (
    <div className="min-h-screen bg-[var(--color-surface-base)]">
      <Suspense fallback={<div className="flex min-h-screen items-center justify-center"><TableSkeleton rows={6} /></div>}>
        <RadarPageInner />
      </Suspense>
    </div>
  );
}
