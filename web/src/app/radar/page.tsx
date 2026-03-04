"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  getRadarV2CasePreview,
  getRadarV2Cases,
  getRadarV2Coverage,
  getRadarV2SignalPreview,
  getRadarV2Signals,
  getRadarV2Summary,
} from "@/lib/api";
import type {
  RadarV2CaseItem,
  RadarV2CasePreviewResponse,
  RadarV2CoverageResponse,
  RadarV2SignalItem,
  RadarV2SignalPreviewResponse,
  RadarV2SummaryResponse,
} from "@/lib/types";
import { RadarFilterPanel } from "@/components/radar/RadarFilterPanel";
import { RadarPreviewDrawer } from "@/components/radar/RadarPreviewDrawer";
import { RadarCoveragePanel } from "@/components/radar/RadarCoveragePanel";
import { TableSkeleton } from "@/components/Skeleton";
import { Button } from "@/components/Button";
import { formatNumber, relativeTime } from "@/lib/utils";
import {
  AlertTriangle,
  ArrowRight,
  ArrowUpDown,
  Calendar,
  ChevronLeft,
  ChevronRight,
  FileText,
  Network,
  Radar,
  Search,
  ShieldCheck,
  Users,
} from "lucide-react";

const PAGE_SIZE = 20;

// ── Severity helpers ────────────────────────────────────────────────────────

const SEV: Record<string, { label: string; dot: string; text: string; border: string; bg: string }> = {
  critical: { label: "Crítico",  dot: "bg-error",        text: "text-error",        border: "border-error/30",        bg: "bg-error/5"        },
  high:     { label: "Alto",     dot: "bg-amber",         text: "text-amber",         border: "border-amber/30",         bg: "bg-amber/5"         },
  medium:   { label: "Médio",    dot: "bg-yellow-500",    text: "text-yellow-600",    border: "border-yellow-500/30",    bg: "bg-yellow-500/5"    },
  low:      { label: "Baixo",    dot: "bg-info",          text: "text-info",          border: "border-info/30",          bg: "bg-info/5"          },
};

function SeverityBadge({ severity }: { severity: string }) {
  const s = SEV[severity] ?? SEV.low;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${s.border} ${s.bg} ${s.text}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
      {s.label}
    </span>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 80 ? "bg-success" : pct >= 50 ? "bg-amber" : "bg-error";
  return (
    <div className="flex items-center gap-1.5">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-surface-subtle">
        <div className={`h-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-[10px] tabular-nums text-muted">{pct}%</span>
    </div>
  );
}

// ── Signal card ─────────────────────────────────────────────────────────────

function SignalCard({ item, onPreview }: { item: RadarV2SignalItem; onPreview: (id: string) => void }) {
  const s = SEV[item.severity] ?? SEV.low;
  const period = [item.period_start, item.period_end]
    .filter(Boolean)
    .map((d) => new Date(d!).toLocaleDateString("pt-BR", { month: "short", year: "2-digit" }))
    .join(" → ");

  return (
    <button
      onClick={() => onPreview(item.id)}
      className={`group w-full text-left rounded-xl border ${s.border} bg-surface-card p-4 transition-all hover:shadow-sm hover:bg-surface-base`}
    >
      {/* Top row: severity + typology + confidence */}
      <div className="flex items-start justify-between gap-3 mb-2.5">
        <div className="flex items-center gap-2 flex-wrap">
          <SeverityBadge severity={item.severity} />
          <span className="font-mono text-xs font-bold text-accent">{item.typology_code}</span>
          <span className="text-xs text-muted truncate max-w-[200px]">{item.typology_name}</span>
        </div>
        <div className="shrink-0">
          <ConfidenceBar value={item.confidence} />
        </div>
      </div>

      {/* Title */}
      <h3 className="font-display text-sm font-semibold text-primary leading-snug line-clamp-2 mb-1">
        {item.title}
      </h3>

      {/* Summary excerpt */}
      {item.summary && (
        <p className="text-xs text-secondary leading-relaxed line-clamp-2 mb-3">{item.summary}</p>
      )}

      {/* Footer: metadata + arrow */}
      <div className="flex items-center justify-between gap-2 mt-2">
        <div className="flex items-center gap-3 text-xs text-muted flex-wrap">
          <span className="flex items-center gap-1">
            <Users className="h-3 w-3 shrink-0" />
            {item.entity_count} {item.entity_count === 1 ? "entidade" : "entidades"}
          </span>
          <span className="flex items-center gap-1">
            <FileText className="h-3 w-3 shrink-0" />
            {item.event_count} eventos
          </span>
          {period && (
            <span className="flex items-center gap-1">
              <Calendar className="h-3 w-3 shrink-0" />
              {period}
            </span>
          )}
          {item.has_graph && (
            <span className="flex items-center gap-1 text-accent font-medium">
              <Network className="h-3 w-3 shrink-0" />
              Grafo
            </span>
          )}
          <span className="text-muted/60">{relativeTime(item.created_at)}</span>
        </div>
        <ArrowRight className="h-3.5 w-3.5 shrink-0 text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-accent" />
      </div>
    </button>
  );
}

// ── Case card ───────────────────────────────────────────────────────────────

function CaseCard({ item, onPreview }: { item: RadarV2CaseItem; onPreview: (id: string) => void }) {
  const s = SEV[item.severity] ?? SEV.low;
  const period = [item.period_start, item.period_end]
    .filter(Boolean)
    .map((d) => new Date(d!).toLocaleDateString("pt-BR", { month: "short", year: "2-digit" }))
    .join(" → ");

  return (
    <button
      onClick={() => onPreview(item.id)}
      className={`group w-full text-left rounded-xl border ${s.border} bg-surface-card p-4 transition-all hover:shadow-sm hover:bg-surface-base`}
    >
      {/* Top row: severity + signal count + typology badges */}
      <div className="flex items-start justify-between gap-3 mb-2.5">
        <div className="flex items-center gap-2 flex-wrap">
          <SeverityBadge severity={item.severity} />
          <span className="font-mono text-xs text-muted">
            {item.signal_count} {item.signal_count === 1 ? "sinal" : "sinais"}
          </span>
        </div>
        <div className="flex flex-wrap gap-1 justify-end shrink-0">
          {item.typology_codes.slice(0, 4).map((code) => (
            <span key={code} className="font-mono text-[10px] font-bold text-accent bg-accent-subtle border border-accent/20 px-1.5 py-0.5 rounded">
              {code}
            </span>
          ))}
          {item.typology_codes.length > 4 && (
            <span className="text-[10px] text-muted self-center">+{item.typology_codes.length - 4}</span>
          )}
        </div>
      </div>

      {/* Title */}
      <h3 className="font-display text-sm font-semibold text-primary leading-snug line-clamp-2 mb-1">
        {item.title}
      </h3>

      {/* Summary excerpt */}
      {item.summary && (
        <p className="text-xs text-secondary leading-relaxed line-clamp-2 mb-3">{item.summary}</p>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between gap-2 mt-2">
        <div className="flex items-center gap-3 text-xs text-muted flex-wrap">
          <span className="flex items-center gap-1">
            <Users className="h-3 w-3 shrink-0" />
            {item.entity_count} {item.entity_count === 1 ? "entidade" : "entidades"}
          </span>
          {period && (
            <span className="flex items-center gap-1">
              <Calendar className="h-3 w-3 shrink-0" />
              {period}
            </span>
          )}
          <span className="text-muted/60">{relativeTime(item.created_at)}</span>
        </div>
        <ArrowRight className="h-3.5 w-3.5 shrink-0 text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-accent" />
      </div>
    </button>
  );
}

// ── KPI strip ───────────────────────────────────────────────────────────────

function KpiStrip({ summary, loading }: { summary: RadarV2SummaryResponse | null; loading: boolean }) {
  const sevItems = [
    { key: "critical", label: "Crítico", dot: "bg-error",     count: summary?.severity_counts.critical ?? 0 },
    { key: "high",     label: "Alto",    dot: "bg-amber",      count: summary?.severity_counts.high     ?? 0 },
    { key: "medium",   label: "Médio",   dot: "bg-yellow-500", count: summary?.severity_counts.medium   ?? 0 },
    { key: "low",      label: "Baixo",   dot: "bg-info",       count: summary?.severity_counts.low      ?? 0 },
  ];

  if (loading) {
    return (
      <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-16 rounded-lg border border-border bg-surface-card animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
      <div className="rounded-lg border border-border bg-surface-card px-3 py-3">
        <p className="font-mono text-[9px] uppercase tracking-widest text-muted mb-1">Sinais</p>
        <p className="font-mono text-xl font-bold tabular-nums text-primary">{formatNumber(summary?.totals.signals ?? 0)}</p>
      </div>
      <div className="rounded-lg border border-border bg-surface-card px-3 py-3">
        <p className="font-mono text-[9px] uppercase tracking-widest text-muted mb-1">Casos</p>
        <p className="font-mono text-xl font-bold tabular-nums text-primary">{formatNumber(summary?.totals.cases ?? 0)}</p>
      </div>
      {sevItems.map((sev) => (
        <div key={sev.key} className="rounded-lg border border-border bg-surface-card px-3 py-3">
          <div className="flex items-center gap-1.5 mb-1">
            <span className={`h-1.5 w-1.5 rounded-full ${sev.dot}`} />
            <p className="font-mono text-[9px] uppercase tracking-widest text-muted">{sev.label}</p>
          </div>
          <p className="font-mono text-xl font-bold tabular-nums text-primary">{formatNumber(sev.count)}</p>
        </div>
      ))}
    </div>
  );
}

// ── Top typology breakdown ──────────────────────────────────────────────────

function TypologyBreakdown({ summary }: { summary: RadarV2SummaryResponse | null }) {
  if (!summary || summary.typology_counts.length === 0) return null;
  const top = summary.typology_counts.slice(0, 6);
  const max = top[0]?.count ?? 1;

  return (
    <div className="rounded-xl border border-border bg-surface-card p-4">
      <p className="font-mono text-[10px] uppercase tracking-widest text-muted mb-3">Tipologias ativas</p>
      <div className="space-y-2">
        {top.map((t) => (
          <div key={t.code}>
            <div className="flex items-center justify-between mb-0.5">
              <span className="font-mono text-[10px] font-bold text-accent">{t.code}</span>
              <span className="font-mono text-[10px] tabular-nums text-muted">{t.count}</span>
            </div>
            <div className="h-1 rounded-full bg-surface-subtle overflow-hidden">
              <div
                className="h-full bg-accent/60 rounded-full"
                style={{ width: `${(t.count / max) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main page inner ─────────────────────────────────────────────────────────

type RadarViewMode = "signals" | "cases";

function RadarPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const view          = (searchParams.get("view") as RadarViewMode) || "signals";
  const typology      = searchParams.get("typology") || "";
  const severity      = searchParams.get("severity") || "";
  const sort          = (searchParams.get("sort") as "analysis_date" | "ingestion_date") || "analysis_date";
  const periodFrom    = searchParams.get("period_from") || "";
  const periodTo      = searchParams.get("period_to") || "";
  const corruptionType = searchParams.get("corruption_type") || "";
  const sphere        = searchParams.get("sphere") || "";
  const offsetParam   = Number(searchParams.get("offset") || "0");

  const [search, setSearch] = useState("");

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

  const setView     = (v: RadarViewMode) => updateParam({ view: v, offset: "" });
  const setTypology = (v: string) => updateParam({ typology: v, offset: "" });
  const setSeverity = (v: string) => updateParam({ severity: v, offset: "" });
  const setSort     = (v: string) => updateParam({ sort: v, offset: "" });
  const setPeriodFrom      = (v: string) => updateParam({ period_from: v, offset: "" });
  const setPeriodTo        = (v: string) => updateParam({ period_to: v, offset: "" });
  const setCorruptionType  = (v: string) => updateParam({ corruption_type: v, offset: "" });
  const setSphere          = (v: string) => updateParam({ sphere: v, offset: "" });
  const setOffset          = (v: number) => updateParam({ offset: v > 0 ? String(v) : "" });
  const clearAllFilters    = () => { router.replace("?", { scroll: false }); setSearch(""); };

  // ── State ──────────────────────────────────────────────────────────────────
  const [summary, setSummary]             = useState<RadarV2SummaryResponse | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [signals, setSignals]             = useState<RadarV2SignalItem[]>([]);
  const [cases, setCases]                 = useState<RadarV2CaseItem[]>([]);
  const [total, setTotal]                 = useState(0);
  const [loading, setLoading]             = useState(true);
  const [error, setError]                 = useState<string | null>(null);

  const [previewOpen, setPreviewOpen]     = useState(false);
  const [previewType, setPreviewType]     = useState<"signal" | "case" | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError]   = useState<string | null>(null);
  const [signalPreview, setSignalPreview] = useState<RadarV2SignalPreviewResponse | null>(null);
  const [casePreview, setCasePreview]     = useState<RadarV2CasePreviewResponse | null>(null);

  const [coverageOpen, setCoverageOpen]   = useState(false);
  const [coverageLoading, setCoverageLoading] = useState(false);
  const [coverageError, setCoverageError] = useState<string | null>(null);
  const [coverage, setCoverage]           = useState<RadarV2CoverageResponse | null>(null);

  // ── Data loading ───────────────────────────────────────────────────────────
  useEffect(() => {
    setSummaryLoading(true);
    getRadarV2Summary({
      typology: typology || undefined,
      severity: severity || undefined,
      period_from: periodFrom || undefined,
      period_to: periodTo || undefined,
      corruption_type: corruptionType || undefined,
      sphere: sphere || undefined,
    })
      .then(setSummary)
      .catch(() => setSummary(null))
      .finally(() => setSummaryLoading(false));
  }, [typology, severity, periodFrom, periodTo, corruptionType, sphere]);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const common = {
      offset: offsetParam,
      limit: PAGE_SIZE,
      typology: typology || undefined,
      severity: severity || undefined,
      period_from: periodFrom || undefined,
      period_to: periodTo || undefined,
      corruption_type: corruptionType || undefined,
      sphere: sphere || undefined,
    };
    const task = view === "signals"
      ? getRadarV2Signals({ ...common, sort })
      : getRadarV2Cases(common);
    task
      .then((data) => {
        setTotal(data.total);
        if (view === "signals") { setSignals(data.items as RadarV2SignalItem[]); setCases([]); }
        else { setCases(data.items as RadarV2CaseItem[]); setSignals([]); }
      })
      .catch(() => setError("Erro ao carregar dados do Radar. Verifique a API e tente novamente."))
      .finally(() => setLoading(false));
  }, [view, offsetParam, typology, severity, sort, periodFrom, periodTo, corruptionType, sphere]);

  // ── Preview handlers ───────────────────────────────────────────────────────
  const openSignalPreview = (signalId: string) => {
    setPreviewOpen(true); setPreviewType("signal"); setPreviewLoading(true);
    setPreviewError(null); setSignalPreview(null); setCasePreview(null);
    getRadarV2SignalPreview(signalId, { limit: 10 })
      .then(setSignalPreview)
      .catch(() => setPreviewError("Não foi possível carregar a prévia do sinal"))
      .finally(() => setPreviewLoading(false));
  };

  const openCasePreview = (caseId: string) => {
    setPreviewOpen(true); setPreviewType("case"); setPreviewLoading(true);
    setPreviewError(null); setSignalPreview(null); setCasePreview(null);
    getRadarV2CasePreview(caseId)
      .then(setCasePreview)
      .catch(() => setPreviewError("Não foi possível carregar a prévia do caso"))
      .finally(() => setPreviewLoading(false));
  };

  const openCoverage = () => {
    setCoverageOpen(true);
    if (coverage || coverageLoading) return;
    setCoverageLoading(true); setCoverageError(null);
    getRadarV2Coverage()
      .then(setCoverage)
      .catch(() => setCoverageError("Não foi possível carregar a cobertura analítica"))
      .finally(() => setCoverageLoading(false));
  };

  // ── Derived state ──────────────────────────────────────────────────────────
  const activeFilters = useMemo(
    () => [typology, severity, periodFrom, periodTo, corruptionType, sphere].filter(Boolean).length,
    [typology, severity, periodFrom, periodTo, corruptionType, sphere],
  );

  const filteredSignals = useMemo(() => {
    if (!search.trim()) return signals;
    const q = search.toLowerCase();
    return signals.filter((s) => s.title.toLowerCase().includes(q) || s.typology_name.toLowerCase().includes(q));
  }, [signals, search]);

  const filteredCases = useMemo(() => {
    if (!search.trim()) return cases;
    const q = search.toLowerCase();
    return cases.filter((c) => c.title.toLowerCase().includes(q));
  }, [cases, search]);

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(offsetParam / PAGE_SIZE) + 1;
  const items = view === "signals" ? filteredSignals : filteredCases;

  return (
    <div className="flex min-h-screen flex-col">

      {/* ── Page header ────────────────────────────────────────── */}
      <div className="border-b border-border bg-surface-card">
        <div className="mx-auto max-w-[1280px] px-4 py-8 sm:px-6">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-accent-subtle border border-accent/20">
                <Radar className="h-6 w-6 text-accent" />
              </div>
              <div>
                <h1 className="font-display text-2xl font-bold tracking-tight text-primary sm:text-3xl">Radar de Riscos</h1>
                <p className="mt-1.5 text-sm text-secondary leading-relaxed">Monitoramento de sinais e casos de risco em dados públicos federais</p>
              </div>
            </div>
            <Button variant="secondary" size="sm" onClick={openCoverage} className="shrink-0 mt-1">
              <ShieldCheck className="h-3.5 w-3.5" />
              Confiabilidade
            </Button>
          </div>

          {/* KPI strip */}
          <div className="mt-6">
            <KpiStrip summary={summary} loading={summaryLoading} />
          </div>
        </div>
      </div>

      {/* ── Body ───────────────────────────────────────────────── */}
      <div className="flex-1 mx-auto w-full max-w-[1280px] px-4 py-6 sm:px-6">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start">

          {/* ── Left: filters + typology breakdown ─────────────── */}
          <div className="w-full lg:w-72 lg:shrink-0 space-y-4">
            <RadarFilterPanel
              view={view}
              typology={typology}
              severity={severity}
              periodFrom={periodFrom}
              periodTo={periodTo}
              corruptionType={corruptionType}
              sphere={sphere}
              onTypologyChange={setTypology}
              onSeverityChange={setSeverity}
              onPeriodFromChange={setPeriodFrom}
              onPeriodToChange={setPeriodTo}
              onCorruptionTypeChange={setCorruptionType}
              onSphereChange={setSphere}
              onClearAll={clearAllFilters}
            />
            {!summaryLoading && <TypologyBreakdown summary={summary} />}
          </div>

          {/* ── Right: content area ─────────────────────────────── */}
          <div className="flex-1 min-w-0 space-y-4">

            {/* Toolbar */}
            <div className="flex flex-wrap items-center gap-3">
              {/* View tabs */}
              <div className="flex rounded-lg border border-border bg-surface-card overflow-hidden">
                {(["signals", "cases"] as RadarViewMode[]).map((v) => (
                  <button
                    key={v}
                    onClick={() => setView(v)}
                    className={`px-4 py-2 text-xs font-semibold transition-colors ${
                      view === v
                        ? "bg-accent text-white"
                        : "text-secondary hover:text-primary hover:bg-surface-subtle"
                    }`}
                  >
                    {v === "signals" ? "Sinais" : "Casos"}
                  </button>
                ))}
              </div>

              {activeFilters > 0 && (
                <span className="rounded-full bg-accent text-white px-2 py-0.5 text-[10px] font-bold">
                  {activeFilters} filtro{activeFilters > 1 ? "s" : ""}
                </span>
              )}

              <div className="ml-auto flex items-center gap-2">
                {/* Search */}
                <label className="flex items-center gap-2 rounded-lg border border-border bg-surface-card px-3 py-1.5">
                  <Search className="h-3.5 w-3.5 shrink-0 text-muted" />
                  <input
                    type="text"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Buscar..."
                    className="w-36 bg-transparent text-xs text-primary outline-none placeholder:text-placeholder"
                  />
                </label>

                {/* Sort (signals only) */}
                {view === "signals" && (
                  <label className="flex items-center gap-2 rounded-lg border border-border bg-surface-card px-3 py-1.5">
                    <ArrowUpDown className="h-3.5 w-3.5 shrink-0 text-muted" />
                    <select
                      value={sort}
                      onChange={(e) => setSort(e.target.value)}
                      className="bg-transparent text-xs text-primary outline-none"
                    >
                      <option value="analysis_date">Data de análise</option>
                      <option value="ingestion_date">Data de ingestão</option>
                    </select>
                  </label>
                )}
              </div>
            </div>

            {/* Result count */}
            {!loading && !error && (
              <p className="font-mono text-[11px] tabular-nums text-muted">
                {formatNumber(total)} {view === "signals" ? "sinais" : "casos"} encontrados
                {search.trim() && ` · ${items.length} visíveis (filtro local)`}
              </p>
            )}

            {/* Content */}
            {loading ? (
              <TableSkeleton rows={6} />
            ) : error ? (
              <div className="flex flex-col items-center justify-center rounded-xl border border-error/20 bg-error-subtle py-12 gap-3">
                <AlertTriangle className="h-8 w-8 text-error" />
                <p className="text-sm text-error">{error}</p>
              </div>
            ) : items.length === 0 ? (
              <div className="flex flex-col items-center justify-center rounded-xl border border-border bg-surface-card py-16 gap-3">
                <AlertTriangle className="h-8 w-8 text-muted" />
                <div className="text-center">
                  <p className="text-sm font-semibold text-primary">
                    Nenhum {view === "signals" ? "sinal" : "caso"} encontrado
                  </p>
                  <p className="text-xs text-muted mt-1">Ajuste os filtros para ampliar a busca investigativa.</p>
                </div>
                {activeFilters > 0 && (
                  <Button variant="secondary" size="sm" onClick={clearAllFilters}>
                    Limpar filtros
                  </Button>
                )}
              </div>
            ) : (
              <div className="space-y-2">
                {view === "signals"
                  ? filteredSignals.map((item) => (
                      <SignalCard key={item.id} item={item} onPreview={openSignalPreview} />
                    ))
                  : filteredCases.map((item) => (
                      <CaseCard key={item.id} item={item} onPreview={openCasePreview} />
                    ))}
              </div>
            )}

            {/* Pagination */}
            {!loading && !error && total > PAGE_SIZE && (
              <div className="flex items-center justify-between border-t border-border pt-4">
                <p className="font-mono text-xs tabular-nums text-muted">
                  {offsetParam + 1}–{Math.min(offsetParam + PAGE_SIZE, total)} de {formatNumber(total)}
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="secondary" size="sm"
                    disabled={offsetParam === 0}
                    onClick={() => setOffset(Math.max(0, offsetParam - PAGE_SIZE))}
                  >
                    <ChevronLeft className="h-3.5 w-3.5" />
                    Anterior
                  </Button>
                  <span className="text-xs text-muted font-mono tabular-nums">
                    {currentPage}/{totalPages}
                  </span>
                  <Button
                    variant="secondary" size="sm"
                    disabled={offsetParam + PAGE_SIZE >= total}
                    onClick={() => setOffset(offsetParam + PAGE_SIZE)}
                  >
                    Próxima
                    <ChevronRight className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Drawers ─────────────────────────────────────────────── */}
      <RadarPreviewDrawer
        open={previewOpen}
        type={previewType}
        loading={previewLoading}
        error={previewError}
        signalPreview={signalPreview}
        casePreview={casePreview}
        onClose={() => {
          setPreviewOpen(false); setPreviewType(null);
          setPreviewError(null); setSignalPreview(null); setCasePreview(null);
        }}
      />

      <RadarCoveragePanel
        open={coverageOpen}
        loading={coverageLoading}
        error={coverageError}
        data={coverage}
        onClose={() => setCoverageOpen(false)}
      />
    </div>
  );
}

export default function RadarPage() {
  return (
    <Suspense fallback={<TableSkeleton rows={8} />}>
      <RadarPageInner />
    </Suspense>
  );
}
