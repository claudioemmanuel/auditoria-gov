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
import { TYPOLOGY_LABELS, TYPOLOGY_META, CORRUPTION_TYPE_LABELS, SPHERE_LABELS } from "@/lib/constants";
import { ChevronDown, ChevronRight, ChevronLeft, Radio, CalendarRange } from "lucide-react";

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
  const spheres = [...new Set(item.typology_codes.flatMap((c) => TYPOLOGY_META[c]?.spheres ?? []))];

  return (
    <div className="flex flex-col overflow-hidden rounded-xl border border-border bg-surface-card transition-all hover:border-accent/40 hover:shadow-md">

      {/* Header: title + severity badge */}
      <div className="flex items-start justify-between gap-2 px-4 pt-4 pb-2">
        <p className="min-w-0 flex-1 text-sm font-bold text-primary leading-snug line-clamp-2" title={item.title}>
          {item.title}
        </p>
        <span className={`shrink-0 inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${s.border} ${s.bg} ${s.text}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
          {s.label}
        </span>
      </div>

      {/* Subheader: found date */}
      <p className="px-4 pb-3 font-mono text-[10px] tabular-nums text-muted">{foundDate}</p>

      {/* Accent line */}
      <div className={`h-0.5 w-full ${s.bar} opacity-60`} />

      {/* Body */}
      <div className="flex-1 px-4 py-3 space-y-2.5">

        {/* Typology pills */}
        <div className="flex flex-wrap gap-1">
          {item.typology_codes.map((code) => (
            <span key={code} className="rounded-full border border-accent/20 bg-accent/10 px-2 py-0.5 font-mono text-[10px] font-bold text-accent" title={TYPOLOGY_LABELS[code]}>
              {code}
            </span>
          ))}
        </div>

        {/* Signals + period */}
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1 text-[11px]">
            <Radio className={`h-3 w-3 shrink-0 ${s.text}`} />
            <span className={`font-bold tabular-nums ${s.text}`}>{item.signal_count}</span>
            <span className="text-muted">{item.signal_count !== 1 ? "sinais" : "sinal"}</span>
          </span>
          {periodStr && (
            <span className="flex items-center gap-1 text-[11px] text-muted">
              <CalendarRange className="h-3 w-3 shrink-0" />
              <span className="tabular-nums">{periodStr}</span>
            </span>
          )}
        </div>

        {/* Corruption types */}
        {corruptionTypes.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {corruptionTypes.map((ct) => (
              <span key={ct} className="rounded bg-surface-subtle px-1.5 py-0.5 text-[10px] text-secondary">
                {CORRUPTION_TYPE_LABELS[ct] ?? ct}
              </span>
            ))}
            {spheres.map((sp) => (
              <span key={sp} className="rounded bg-surface-subtle px-1.5 py-0.5 text-[10px] text-muted">
                {SPHERE_LABELS[sp] ?? sp}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-border px-4 py-2.5">
        <span className="text-[11px] text-accent">Ver dossiê →</span>
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
    <div className={`rounded-xl border ${s.border} overflow-hidden`}>
      {/* Header */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-colors ${s.bg} hover:opacity-90`}
      >
        <span className={`h-2 w-2 rounded-full shrink-0 ${s.dot}`} />
        <span className={`text-sm font-semibold ${s.text}`}>{s.label}</span>
        <span className={`ml-1 rounded-full border px-2 py-0.5 text-[10px] font-bold tabular-nums ${s.border} ${s.text}`}>
          {count.toLocaleString("pt-BR")} caso{count !== 1 ? "s" : ""}
        </span>
        <div className="flex-1" />
        {open
          ? <ChevronDown className={`h-4 w-4 ${s.text}`} />
          : <ChevronRight className={`h-4 w-4 ${s.text}`} />
        }
      </button>

      {/* Body */}
      {open && (
        <div className="border-t border-border bg-surface-base px-4 py-4">
          {loading && <TableSkeleton rows={3} />}

          {error && (
            <p className="text-xs text-error text-center py-4">{error}</p>
          )}

          {!loading && !error && filteredCases.length === 0 && (
            <p className="text-xs text-muted text-center py-4">
              {search.trim() ? "Nenhum caso encontrado para esta busca." : "Nenhum caso nesta severidade."}
            </p>
          )}

          {!loading && !error && filteredCases.length > 0 && (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {filteredCases.map((c) => (
                <Link key={c.id} href={`/radar/dossie/${c.id}`} className="block">
                  <CaseListCard item={c} />
                </Link>
              ))}
            </div>
          )}

          {/* Pagination */}
          {!loading && !search.trim() && totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-border pt-3 mt-1">
              <span className="text-xs text-muted">
                Página {currentPage} de {totalPages}
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={currentPage <= 1}
                  onClick={(e) => { e.preventDefault(); setOffset(Math.max(0, offset - PAGE_SIZE)); }}
                >
                  <ChevronLeft className="h-3.5 w-3.5" />
                  Anterior
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={currentPage >= totalPages}
                  onClick={(e) => { e.preventDefault(); setOffset(offset + PAGE_SIZE); }}
                >
                  Próxima
                  <ChevronRight className="h-3.5 w-3.5" />
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
      {/* Summary strip */}
      <div className="border-b border-border bg-surface-card">
        <div className="mx-auto max-w-[1280px] px-4 py-4 sm:px-6">
          <RadarSummaryStrip
            summary={summary}
            loading={summaryLoading}
            activeSeverity=""
            onSeverityClick={() => {}}
          />
        </div>
      </div>

      <div className="mx-auto w-full max-w-[1280px] px-4 py-6 sm:px-6">
        {/* Header + filters */}
        <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
          <div>
            <RadarBreadcrumb crumbs={[{ label: "Radar" }]} />
            <p className="text-xs text-secondary mt-0.5">
              Casos agrupados por severidade — clique em uma seção para expandir
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
            onCoverageClick={openCoverage}
          />
        </div>

        {/* Severity accordions */}
        <div className="space-y-3">
          {SEVERITY_ORDER.map((sev, i) => (
            <SeverityAccordionSection
              key={sev}
              severity={sev}
              count={summary?.severity_counts[sev] ?? 0}
              filters={filters}
              search={search}
              defaultOpen={i === 0}
            />
          ))}
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
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center"><TableSkeleton rows={6} /></div>}>
      <RadarPageInner />
    </Suspense>
  );
}
