"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  getRadarV2Cases,
  getRadarV2Summary,
  getRadarV2Signals,
} from "@/lib/api";
import type {
  RadarV2CaseItem,
  RadarV2SummaryResponse,
  RadarV2SignalItem,
} from "@/lib/types";
import { SeverityBadge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { SkeletonCard } from "@/components/Skeleton";
import { EmptyState } from "@/components/EmptyState";
import { Input } from "@/components/Input";
import { Select } from "@/components/Input";
import { PageHeader } from "@/components/PageHeader";
import {
  ChevronDown, ChevronRight, ChevronLeft, Search,
  Radar, GitBranch, AlertTriangle, SlidersHorizontal, X,
} from "lucide-react";
import { relativeTime } from "@/lib/utils";

const PAGE_SIZE = 20;
const SEVERITY_ORDER = ["critical", "high", "medium", "low"] as const;
type SeverityLevel = (typeof SEVERITY_ORDER)[number];

const SEV_COLORS: Record<SeverityLevel, string> = {
  critical: "var(--color-critical)",
  high:     "var(--color-high)",
  medium:   "var(--color-medium)",
  low:      "var(--color-low)",
};

const SEV_LABELS: Record<SeverityLevel, string> = {
  critical: "Crítico",
  high:     "Alto",
  medium:   "Médio",
  low:      "Baixo",
};

/* ── Summary Strip ─────────────────────────────────────────────── */
function SummaryStrip({
  summary,
  loading,
}: {
  summary: RadarV2SummaryResponse | null;
  loading: boolean;
}) {
  const counts: Partial<Record<SeverityLevel, number>> = summary?.severity_counts ?? {};
  const total = summary?.totals?.signals ?? 0;
  const cases = summary?.totals?.cases ?? 0;

  if (loading) {
    return (
      <div className="ow-strip grid-cols-2 md:grid-cols-6 mb-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="ow-strip-item">
            <div className="ow-skeleton h-7 w-16 mb-1" />
            <div className="ow-skeleton h-3 w-20" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="ow-strip grid-cols-2 md:grid-cols-6 mb-6">
      <div className="ow-strip-item">
        <div className="ow-strip-value">{total.toLocaleString("pt-BR")}</div>
        <div className="ow-strip-label">Total Sinais</div>
      </div>
      <div className="ow-strip-item">
        <div className="ow-strip-value">{cases.toLocaleString("pt-BR")}</div>
        <div className="ow-strip-label">Total Casos</div>
      </div>
      {SEVERITY_ORDER.map((sev) => (
        <div key={sev} className="ow-strip-item">
          <div
            className="ow-strip-value"
            style={{ color: SEV_COLORS[sev] }}
          >
            {(counts[sev] ?? 0).toLocaleString("pt-BR")}
          </div>
          <div className="ow-strip-label">{SEV_LABELS[sev]}</div>
        </div>
      ))}
    </div>
  );
}

/* ── Signal Row ─────────────────────────────────────────────────── */
function SignalRow({ signal }: { signal: RadarV2SignalItem }) {
  const color = SEV_COLORS[signal.severity as SeverityLevel] ?? "var(--color-text-3)";
  return (
    <Link
      href={`/signal/${signal.id}`}
      className="ow-signal-card block"
      style={{ borderLeftColor: color, borderLeftWidth: 3 }}
    >
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
            <span className="text-mono-xs text-[var(--color-text-3)]">
              {signal.typology_code}
            </span>
            <SeverityBadge severity={signal.severity as SeverityLevel} />
            {signal.has_graph && (
              <span className="ow-badge ow-badge-neutral text-[10px]">graph</span>
            )}
          </div>
          <h3 className="text-body font-semibold text-[var(--color-text)] mb-1 truncate-2">
            {signal.title}
          </h3>
          <p className="text-body-sm text-[var(--color-text-2)] truncate-2">
            {signal.summary}
          </p>
        </div>
        <div className="text-right flex-shrink-0 space-y-1">
          <p className="text-mono-xs text-[var(--color-text-3)]">
            {relativeTime(signal.created_at)}
          </p>
          {signal.entity_count > 0 && (
            <p className="text-caption text-[var(--color-text-3)]">
              {signal.entity_count} entidades
            </p>
          )}
        </div>
      </div>
    </Link>
  );
}

/* ── Case Card ──────────────────────────────────────────────────── */
function CaseCard({ item }: { item: RadarV2CaseItem }) {
  const color = SEV_COLORS[item.severity as SeverityLevel] ?? "var(--color-text-3)";

  return (
    <Link
      href={`/radar/dossie/${item.id}`}
      className="ow-card ow-card-hover block group"
      style={{ borderLeft: `3px solid ${color}` }}
    >
      <div className="ow-card-section">
        {/* Typology codes */}
        <div className="flex items-center gap-1.5 mb-3 flex-wrap">
          {(item.typology_codes ?? []).slice(0, 3).map((code) => (
            <span key={code} className="ow-badge ow-badge-neutral text-mono-xs">
              {code}
            </span>
          ))}
          {(item.typology_codes ?? []).length > 3 && (
            <span className="text-caption text-[var(--color-text-3)]">
              +{(item.typology_codes ?? []).length - 3}
            </span>
          )}
        </div>

        <h3 className="text-body font-semibold text-[var(--color-text)] mb-2 truncate-2 group-hover:text-[var(--color-brand)] transition-colors">
          {item.title}
        </h3>

        <div className="flex items-center gap-3 flex-wrap mt-3 pt-3 border-t border-[var(--color-border)]">
          <SeverityBadge severity={item.severity as SeverityLevel} />
          <span className="text-caption text-[var(--color-text-3)]">
            {item.signal_count} sinais
          </span>
          <span className="text-caption text-[var(--color-text-3)]">
            {item.entity_count} entidades
          </span>
          <span className="text-mono-xs text-[var(--color-text-3)] ml-auto">
            {relativeTime(item.created_at)}
          </span>
        </div>
      </div>
    </Link>
  );
}

/* ── Severity Section ───────────────────────────────────────────── */
function SeveritySection({
  severity,
  count,
  filters,
  search,
  view,
  defaultOpen,
}: {
  severity: SeverityLevel;
  count: number;
  filters: Record<string, string>;
  search: string;
  view: "signals" | "cases";
  defaultOpen: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const [offset, setOffset] = useState(0);
  const [items, setItems] = useState<(RadarV2SignalItem | RadarV2CaseItem)[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const filterKey = JSON.stringify(filters);

  useEffect(() => { setOffset(0); }, [filterKey, view]);

  useEffect(() => {
    if (!open) return;
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    setError(null);

    const params = {
      severity,
      offset,
      limit: PAGE_SIZE,
      typology: filters.typology || undefined,
      period_from: filters.periodFrom || undefined,
      period_to: filters.periodTo || undefined,
    };

    const fetch = view === "cases"
      ? getRadarV2Cases(params)
      : getRadarV2Signals(params);

    fetch
      .then((data) => {
        if (ctrl.signal.aborted) return;
        setTotal(data.total);
        setItems(data.items as (RadarV2SignalItem | RadarV2CaseItem)[]);
      })
      .catch(() => { if (!ctrl.signal.aborted) setError("Erro ao carregar dados."); })
      .finally(() => { if (!ctrl.signal.aborted) setLoading(false); });

    return () => ctrl.abort();
  }, [open, offset, filterKey, severity, view]);

  const color = SEV_COLORS[severity];
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  const filtered = search.trim()
    ? items.filter((i) =>
        ("title" in i ? i.title : "").toLowerCase().includes(search.toLowerCase())
      )
    : items;

  return (
    <div className="ow-card overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full ow-card-section flex items-center gap-3 text-left hover:bg-[var(--color-surface-3)] transition-colors"
      >
        <span
          className="w-2.5 h-2.5 rounded-full flex-shrink-0"
          style={{ background: color }}
        />
        <span
          className="text-label font-bold"
          style={{ color }}
        >
          {SEV_LABELS[severity]}
        </span>
        <span
          className="ow-badge text-mono-xs ml-1"
          style={{
            background: `${color}18`,
            color,
            borderColor: `${color}40`,
          }}
        >
          {count.toLocaleString("pt-BR")}
        </span>
        <span className="flex-1" />
        <ChevronDown
          size={16}
          className="text-[var(--color-text-3)] transition-transform"
          style={{ transform: open ? "rotate(180deg)" : "none" }}
        />
      </button>

      {/* Body */}
      {open && (
        <div className="border-t border-[var(--color-border)] p-4">
          {loading && (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <SkeletonCard key={i} rows={2} />
              ))}
            </div>
          )}

          {error && (
            <div className="ow-alert ow-alert-error">
              <AlertTriangle size={16} className="flex-shrink-0 mt-0.5" />
              {error}
            </div>
          )}

          {!loading && !error && filtered.length === 0 && (
            <EmptyState
              title="Nenhum item encontrado"
              description={search ? "Tente outros termos de busca." : "Nenhum item nesta severidade com os filtros aplicados."}
            />
          )}

          {!loading && !error && filtered.length > 0 && (
            view === "cases" ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
                {filtered.map((item) => (
                  <CaseCard key={item.id} item={item as RadarV2CaseItem} />
                ))}
              </div>
            ) : (
              <div className="space-y-2">
                {filtered.map((item) => (
                  <SignalRow key={item.id} signal={item as RadarV2SignalItem} />
                ))}
              </div>
            )
          )}

          {/* Pagination */}
          {!loading && !search && totalPages > 1 && (
            <div className="ow-pagination mt-4">
              <span className="ow-pagination-info">
                pág. {currentPage}/{totalPages} — {total} total
              </span>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={currentPage <= 1}
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                >
                  <ChevronLeft size={14} />
                  Anterior
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={currentPage >= totalPages}
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                >
                  Próxima
                  <ChevronRight size={14} />
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Main page ──────────────────────────────────────────────────── */
function RadarPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const view         = (searchParams.get("view") as "signals" | "cases") || "cases";
  const typology     = searchParams.get("typology") || "";
  const periodFrom   = searchParams.get("period_from") || "";
  const periodTo     = searchParams.get("period_to") || "";
  const [search, setSearch] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(false);

  const [summary, setSummary] = useState<RadarV2SummaryResponse | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);

  const updateParam = useCallback(
    (updates: Record<string, string>) => {
      const params = new URLSearchParams(searchParams.toString());
      for (const [k, v] of Object.entries(updates)) {
        if (v) params.set(k, v); else params.delete(k);
      }
      router.replace(`?${params.toString()}`, { scroll: false });
    },
    [router, searchParams]
  );

  const hasFilters = !!(typology || periodFrom || periodTo);
  const filters = { typology, periodFrom, periodTo };

  useEffect(() => {
    setSummaryLoading(true);
    getRadarV2Summary({
      typology: typology || undefined,
      period_from: periodFrom || undefined,
      period_to: periodTo || undefined,
    })
      .then(setSummary)
      .catch(() => setSummary(null))
      .finally(() => setSummaryLoading(false));
  }, [typology, periodFrom, periodTo]);


  const headerStats = [
    {
      label: "Sinais",
      value: summaryLoading ? "—" : (summary?.totals?.signals ?? 0).toLocaleString("pt-BR"),
      mono: true,
      tone: "brand" as const,
    },
    {
      label: "Casos",
      value: summaryLoading ? "—" : (summary?.totals?.cases ?? 0).toLocaleString("pt-BR"),
      mono: true,
    },
    {
      label: "Crítico",
      value: summaryLoading ? "—" : (summary?.severity_counts?.critical ?? 0).toLocaleString("pt-BR"),
      mono: true,
      tone: "danger" as const,
    },
    {
      label: "Alto",
      value: summaryLoading ? "—" : (summary?.severity_counts?.high ?? 0).toLocaleString("pt-BR"),
      mono: true,
      tone: "warning" as const,
    },
  ];

  // Only show typologies present in current data, sorted by count desc
  const presentTypologies = (summary?.typology_counts ?? [])
    .filter((t) => t.count > 0)
    .sort((a, b) => b.count - a.count);

  const hasPeriodFilter = !!(periodFrom || periodTo);

  return (
    <div className="ow-content">
      {/* Page Header — no view toggle here */}
      <PageHeader
        eyebrow="Investigação"
        title="Radar de Risco"
        description="Sinais e casos de corrupção detectados em licitações e contratos federais."
        variant="hero"
        icon={<Radar className="h-5 w-5" />}
        stats={headerStats}
        actions={
          hasFilters ? (
            <button
              onClick={() => router.replace("/radar", { scroll: false })}
              className="ow-btn ow-btn-ghost ow-btn-sm gap-1 !text-[var(--color-critical-text)]"
            >
              <X size={13} />
              Limpar filtros
            </button>
          ) : null
        }
      />

      {/* Summary Strip */}
      <SummaryStrip summary={summary} loading={summaryLoading} />

      {/* Filter + Search bar */}
      <div className="mb-1 flex flex-col sm:flex-row gap-2">
        {/* Typology — only present typologies */}
        <Select
          value={typology}
          onChange={(e) => updateParam({ typology: e.target.value })}
          className="sm:w-72 shrink-0"
        >
          <option value="">Todas as tipologias</option>
          {presentTypologies.map((t) => (
            <option key={t.code} value={t.code}>
              {t.code} — {t.name} ({t.count.toLocaleString("pt-BR")})
            </option>
          ))}
        </Select>

        {/* Search */}
        <Input
          iconLeft={<Search size={14} />}
          placeholder="Buscar por título..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1"
        />

        {/* Period filter toggle */}
        <button
          onClick={() => setFiltersOpen(!filtersOpen)}
          className={`ow-btn ow-btn-sm gap-1.5 shrink-0 ${filtersOpen || hasPeriodFilter ? "ow-btn-amber" : "ow-btn-ghost"}`}
        >
          <SlidersHorizontal size={14} />
          Período
          {hasPeriodFilter && <span className="w-1.5 h-1.5 rounded-full bg-current" />}
        </button>
      </div>

      {/* Period filter panel */}
      {filtersOpen && (
        <div className="ow-card ow-card-section mb-3 animate-slide-up">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="ow-label">De</label>
              <input
                type="date"
                className="ow-input"
                value={periodFrom}
                onChange={(e) => updateParam({ period_from: e.target.value })}
              />
            </div>
            <div>
              <label className="ow-label">Até</label>
              <input
                type="date"
                className="ow-input"
                value={periodTo}
                onChange={(e) => updateParam({ period_to: e.target.value })}
              />
            </div>
          </div>
        </div>
      )}

      {/* Tabs — Casos / Sinais */}
      <div className="flex items-end gap-0 border-b border-[var(--color-border)] mb-5 mt-3">
        <button
          onClick={() => updateParam({ view: "cases" })}
          className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors relative"
          style={{
            color: view === "cases" ? "var(--color-brand)" : "var(--color-text-3)",
            borderBottom: view === "cases" ? "2px solid var(--color-brand)" : "2px solid transparent",
            marginBottom: -1,
          }}
        >
          <GitBranch size={14} />
          Casos
          {!summaryLoading && summary && (
            <span
              className="text-xs tabular-nums px-1.5 py-0.5 rounded"
              style={{
                background: view === "cases" ? "var(--color-amber-dim)" : "var(--color-surface-3)",
                color: view === "cases" ? "var(--color-brand)" : "var(--color-text-3)",
              }}
            >
              {summary.totals.cases.toLocaleString("pt-BR")}
            </span>
          )}
        </button>
        <button
          onClick={() => updateParam({ view: "signals" })}
          className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors relative"
          style={{
            color: view === "signals" ? "var(--color-brand)" : "var(--color-text-3)",
            borderBottom: view === "signals" ? "2px solid var(--color-brand)" : "2px solid transparent",
            marginBottom: -1,
          }}
        >
          <Radar size={14} />
          Sinais
          {!summaryLoading && summary && (
            <span
              className="text-xs tabular-nums px-1.5 py-0.5 rounded"
              style={{
                background: view === "signals" ? "var(--color-amber-dim)" : "var(--color-surface-3)",
                color: view === "signals" ? "var(--color-brand)" : "var(--color-text-3)",
              }}
            >
              {summary.totals.signals.toLocaleString("pt-BR")}
            </span>
          )}
        </button>
      </div>

      {/* Sections by severity */}
      <div className="space-y-3">
        {summaryLoading
          ? Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} rows={1} />)
          : SEVERITY_ORDER.filter(
              (sev) => (summary?.severity_counts[sev] ?? 0) > 0
            ).map((sev, i) => (
              <SeveritySection
                key={sev}
                severity={sev}
                count={summary!.severity_counts[sev]!}
                filters={filters}
                search={search}
                view={view}
                defaultOpen={i === 0}
              />
            ))}

        {!summaryLoading && summary &&
          SEVERITY_ORDER.every((s) => (summary.severity_counts[s] ?? 0) === 0) && (
            <EmptyState
              icon={<Radar size={40} />}
              title="Nenhum resultado"
              description="Nenhum item encontrado com os filtros aplicados. Tente remover alguns filtros."
              action={
                <button
                  onClick={() => router.replace("/radar", { scroll: false })}
                  className="ow-btn ow-btn-outline ow-btn-sm"
                >
                  Limpar Filtros
                </button>
              }
            />
          )}
      </div>
    </div>
  );
}

export default function RadarPage() {
  return (
    <Suspense fallback={
      <div className="ow-content space-y-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <SkeletonCard key={i} rows={2} />
        ))}
      </div>
    }>
      <RadarPageInner />
    </Suspense>
  );
}
