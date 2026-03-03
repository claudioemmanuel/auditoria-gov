"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getRadar, getAnalyticalCoverage } from "@/lib/api";
import { Filters } from "@/components/Filters";
import { SignalTable } from "@/components/SignalTable";
import { TableSkeleton } from "@/components/Skeleton";
import { Breadcrumb } from "@/components/Breadcrumb";
import type { RiskSignal, AnalyticalCoverageItem } from "@/lib/types";
import { SEVERITY_LABELS, CORRUPTION_TYPE_LABELS, SPHERE_LABELS } from "@/lib/constants";
import {
  Radar,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
  ShieldAlert,
  Info,
  AlertCircle,
  ListFilter,
  Activity,
  Workflow,
  ArrowUpDown,
  CalendarRange,
  ShieldCheck,
  AlertOctagon,
  CheckCircle2,
  XCircle,
  Clock,
  Scale,
  Globe,
  Minus,
} from "lucide-react";

const SEVERITY_ICONS = {
  low: Info,
  medium: AlertCircle,
  high: AlertTriangle,
  critical: ShieldAlert,
} as const;

export default function RadarPage() {
  const [signals, setSignals] = useState<RiskSignal[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [typology, setTypology] = useState("");
  const [severity, setSeverity] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sort, setSort] = useState<"analysis_date" | "ingestion_date">("analysis_date");
  const [periodFrom, setPeriodFrom] = useState("");
  const [periodTo, setPeriodTo] = useState("");
  const [analytics, setAnalytics] = useState<AnalyticalCoverageItem[]>([]);
  const [corruptionType, setCorruptionType] = useState("");
  const [sphere, setSphere] = useState("");

  const [severityCounts, setSeverityCounts] = useState<Record<string, number>>({
    low: 0,
    medium: 0,
    high: 0,
    critical: 0,
  });

  useEffect(() => {
    setLoading(true);
    setError(null);
    getRadar({
      offset,
      limit: 20,
      typology,
      severity,
      sort,
      period_from: periodFrom || undefined,
      period_to: periodTo || undefined,
      corruption_type: corruptionType || undefined,
      sphere: sphere || undefined,
    })
      .then((data) => {
        setSignals(data.items);
        setTotal(data.total);
      })
      .catch(() => setError("Erro ao carregar sinais de risco"))
      .finally(() => setLoading(false));
  }, [offset, typology, severity, sort, periodFrom, periodTo, corruptionType, sphere]);

  useEffect(() => {
    if (!typology && !severity) {
      Promise.all([
        getRadar({ limit: 1, severity: "critical" }),
        getRadar({ limit: 1, severity: "high" }),
        getRadar({ limit: 1, severity: "medium" }),
        getRadar({ limit: 1, severity: "low" }),
      ])
        .then(([crit, high, med, low]) => {
          setSeverityCounts({
            critical: crit.total,
            high: high.total,
            medium: med.total,
            low: low.total,
          });
        })
        .catch(() => {});
    }
  }, [typology, severity]);

  useEffect(() => {
    getAnalyticalCoverage().then(setAnalytics).catch(() => {});
  }, []);

  const aptCount = analytics.filter((a) => a.apt).length;
  const withSignals = analytics.filter((a) => a.signals_30d > 0).length;
  const blockedTypologies = analytics.filter((a) => !a.apt);

  const totalSignals =
    severityCounts.critical +
    severityCounts.high +
    severityCounts.medium +
    severityCounts.low;
  const hasFilters = Boolean(typology || severity || periodFrom || periodTo || corruptionType || sphere);

  const statCards = useMemo(
    () => [
      {
        label: "Total de Sinais",
        value: totalSignals,
        icon: Activity,
      },
      {
        label: "Retornados na Consulta",
        value: total,
        icon: Workflow,
      },
      {
        label: "Filtros Ativos",
        value: Number(Boolean(typology)) + Number(Boolean(severity)) + Number(Boolean(periodFrom || periodTo)) + Number(Boolean(corruptionType)) + Number(Boolean(sphere)),
        icon: ListFilter,
      },
    ],
    [totalSignals, total, typology, severity, periodFrom, periodTo, corruptionType, sphere],
  );

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <Breadcrumb items={[{ label: "Radar" }]} />

      <div className="mt-4 flex items-center gap-3">
        <div className="rounded-xl bg-gov-blue-50 p-2.5">
          <Radar className="h-6 w-6 text-gov-blue-600" />
        </div>
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-gov-gray-900">
            Central de Riscos
          </h1>
          <p className="text-sm text-gov-gray-500">
            Sinais identificados automaticamente a partir de dados publicos federais
          </p>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {loading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <div
              key={`radar-stat-skeleton-${i}`}
              className="h-24 animate-pulse rounded-xl border border-gov-gray-200 bg-white"
            />
          ))
        ) : (
          statCards.map((card) => (
            <div
              key={card.label}
              className="rounded-xl border border-gov-gray-200 bg-white p-4 shadow-sm"
            >
              <div className="flex items-center justify-between">
                <p className="text-xs font-medium uppercase tracking-wide text-gov-gray-500">
                  {card.label}
                </p>
                <card.icon className="h-4 w-4 text-gov-blue-600" />
              </div>
              <p className="mt-2 text-2xl font-semibold text-gov-gray-900">
                {card.value}
              </p>
            </div>
          ))
        )}
      </div>

      {totalSignals > 0 && (
        <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {(["critical", "high", "medium", "low"] as const).map((sev) => {
            const SevIcon = SEVERITY_ICONS[sev];
            const count = severityCounts[sev];
            const isActive = severity === sev;

            return (
              <button
                key={sev}
                onClick={() => {
                  setSeverity(isActive ? "" : sev);
                  setOffset(0);
                }}
                className={`rounded-xl border p-4 text-left transition ${
                  isActive
                    ? "border-gov-blue-300 bg-gov-blue-50 shadow-sm"
                    : "border-gov-gray-200 bg-white hover:border-gov-blue-200 hover:shadow-sm"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wide text-gov-gray-500">
                    {SEVERITY_LABELS[sev]}
                  </span>
                  <SevIcon
                    className={`h-4 w-4 ${
                      sev === "critical"
                        ? "text-red-500"
                        : sev === "high"
                          ? "text-orange-500"
                          : sev === "medium"
                            ? "text-yellow-500"
                            : "text-blue-500"
                    }`}
                  />
                </div>
                <p className="mt-2 text-2xl font-semibold text-gov-gray-900">{count}</p>
              </button>
            );
          })}
        </div>
      )}

      {/* Analytical Coverage Card */}
      {analytics.length > 0 && (
        <div className="mt-6 rounded-xl border border-gov-gray-200 bg-white p-4 shadow-sm">
          <div className="mb-3 flex items-center gap-1.5 text-sm text-gov-gray-700">
            <ShieldCheck className="h-4 w-4 text-gov-blue-600" />
            <span className="font-medium">Confiabilidade da Analise</span>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="rounded-lg bg-gov-gray-50 px-3 py-2">
              <p className="text-xs text-gov-gray-500">Tipologias aptas</p>
              <p className="mt-0.5 text-lg font-semibold text-gov-gray-900">
                {aptCount}/{analytics.length}
              </p>
              <p className="text-xs text-gov-gray-400">
                dominios necessarios disponiveis
              </p>
            </div>
            <div className="rounded-lg bg-gov-gray-50 px-3 py-2">
              <p className="text-xs text-gov-gray-500">Tipologias com sinais (30d)</p>
              <p className="mt-0.5 text-lg font-semibold text-gov-gray-900">
                {withSignals}/{analytics.length}
              </p>
              <p className="text-xs text-gov-gray-400">
                produziram sinais recentemente
              </p>
            </div>
            <div className="rounded-lg bg-gov-gray-50 px-3 py-2">
              <p className="text-xs text-gov-gray-500">Bloqueadas por dominio</p>
              <p className="mt-0.5 text-lg font-semibold text-gov-gray-900">
                {blockedTypologies.length}
              </p>
              {blockedTypologies.length > 0 && (
                <p className="text-xs text-amber-600">
                  Faltam: {[...new Set(blockedTypologies.flatMap((t) => t.domains_missing))].join(", ")}
                </p>
              )}
            </div>
          </div>

          {/* Per-typology execution status */}
          <div className="mt-4 border-t border-gov-gray-100 pt-3">
            <p className="mb-2 text-xs font-medium text-gov-gray-500">Status de execucao por tipologia</p>
            <div className="space-y-1.5">
              {analytics.map((t) => {
                const RunIcon = t.last_run_status === "success"
                  ? CheckCircle2
                  : t.last_run_status === "error"
                    ? XCircle
                    : t.last_run_status === "running"
                      ? Clock
                      : Minus;
                const iconColor = t.last_run_status === "success"
                  ? "text-green-500"
                  : t.last_run_status === "error"
                    ? "text-red-500"
                    : t.last_run_status === "running"
                      ? "text-blue-500"
                      : "text-gov-gray-300";
                const runDate = t.last_run_at
                  ? new Date(t.last_run_at).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })
                  : null;
                const tooltip = t.last_run_at
                  ? `Ultima execucao: ${runDate} — ${(t.last_run_candidates ?? 0).toLocaleString("pt-BR")} candidatos avaliados, ${t.last_run_signals_created ?? 0} sinais novos`
                  : "Nenhuma execucao registrada";

                return (
                  <div
                    key={t.typology_code}
                    className="flex items-center gap-2 rounded-md px-2 py-1 text-xs hover:bg-gov-gray-50"
                    title={tooltip}
                  >
                    <RunIcon className={`h-3.5 w-3.5 shrink-0 ${iconColor}`} />
                    <span className="w-8 font-mono font-semibold text-gov-gray-600">{t.typology_code}</span>
                    <span className="flex-1 text-gov-gray-700">{t.typology_name}</span>
                    {runDate && (
                      <span className="text-gov-gray-400">{runDate}</span>
                    )}
                    {!t.apt && (
                      <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700">
                        sem dados
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {blockedTypologies.length > 0 && (
            <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
              <div className="flex items-start gap-2">
                <AlertOctagon className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                <div>
                  <p className="text-xs font-medium text-amber-800">
                    Tipologias indisponiveis por falta de dados:
                  </p>
                  <ul className="mt-1 space-y-0.5">
                    {blockedTypologies.map((t) => (
                      <li key={t.typology_code} className="text-xs text-amber-700">
                        <span className="font-mono font-semibold">{t.typology_code}</span> {t.typology_name}
                        {" — faltam: "}
                        {t.domains_missing.join(", ")}
                      </li>
                    ))}
                  </ul>
                  <p className="mt-1 text-xs text-amber-600">
                    Ausencia de sinal nestas tipologias nao indica ausencia de risco — indica apenas que os dados necessarios nao estao disponiveis.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      <div className="mt-6 rounded-xl border border-gov-gray-200 bg-white p-4 shadow-sm">
        <div className="mb-3 flex items-center gap-1.5 text-sm text-gov-gray-500">
          <ListFilter className="h-4 w-4" />
          <span>Filtros do Radar</span>
        </div>
        <Filters
          typology={typology}
          severity={severity}
          onTypologyChange={(value) => {
            setTypology(value);
            setOffset(0);
          }}
          onSeverityChange={(value) => {
            setSeverity(value);
            setOffset(0);
          }}
        />

        {/* Sort toggle */}
        <div className="mt-4 flex flex-wrap items-center gap-4 border-t border-gov-gray-100 pt-4">
          <div className="flex items-center gap-2">
            <ArrowUpDown className="h-4 w-4 text-gov-gray-400" />
            <span className="text-xs font-medium text-gov-gray-500">Ordenar por:</span>
            <div className="flex rounded-lg border border-gov-gray-200">
              <button
                onClick={() => { setSort("analysis_date"); setOffset(0); }}
                className={`px-3 py-1.5 text-xs font-medium transition ${
                  sort === "analysis_date"
                    ? "bg-gov-blue-600 text-white"
                    : "text-gov-gray-600 hover:bg-gov-gray-50"
                } rounded-l-lg`}
              >
                Data de analise
              </button>
              <button
                onClick={() => { setSort("ingestion_date"); setOffset(0); }}
                className={`px-3 py-1.5 text-xs font-medium transition ${
                  sort === "ingestion_date"
                    ? "bg-gov-blue-600 text-white"
                    : "text-gov-gray-600 hover:bg-gov-gray-50"
                } rounded-r-lg`}
              >
                Data de ingestao
              </button>
            </div>
          </div>

          {/* Period date range filter */}
          <div className="flex items-center gap-2">
            <CalendarRange className="h-4 w-4 text-gov-gray-400" />
            <span className="text-xs font-medium text-gov-gray-500">Periodo:</span>
            <input
              type="date"
              value={periodFrom}
              onChange={(e) => { setPeriodFrom(e.target.value); setOffset(0); }}
              className="rounded-md border border-gov-gray-200 px-2 py-1 text-xs text-gov-gray-700"
              placeholder="De"
            />
            <span className="text-xs text-gov-gray-400">ate</span>
            <input
              type="date"
              value={periodTo}
              onChange={(e) => { setPeriodTo(e.target.value); setOffset(0); }}
              className="rounded-md border border-gov-gray-200 px-2 py-1 text-xs text-gov-gray-700"
              placeholder="Ate"
            />
            {(periodFrom || periodTo) && (
              <button
                onClick={() => { setPeriodFrom(""); setPeriodTo(""); setOffset(0); }}
                className="text-xs text-gov-blue-600 hover:underline"
              >
                Limpar
              </button>
            )}
          </div>
        </div>

        {/* Legal classification filters */}
        <div className="mt-4 flex flex-wrap items-center gap-4 border-t border-gov-gray-100 pt-4">
          <div className="flex items-center gap-2">
            <Scale className="h-4 w-4 text-gov-gray-400" />
            <span className="text-xs font-medium text-gov-gray-500">Tipo de Corrupcao:</span>
            <select
              value={corruptionType}
              onChange={(e) => { setCorruptionType(e.target.value); setOffset(0); }}
              className="rounded-md border border-gov-gray-200 px-2 py-1.5 text-xs text-gov-gray-700"
            >
              <option value="">Todos</option>
              {Object.entries(CORRUPTION_TYPE_LABELS).map(([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <Globe className="h-4 w-4 text-gov-gray-400" />
            <span className="text-xs font-medium text-gov-gray-500">Esfera:</span>
            <select
              value={sphere}
              onChange={(e) => { setSphere(e.target.value); setOffset(0); }}
              className="rounded-md border border-gov-gray-200 px-2 py-1.5 text-xs text-gov-gray-700"
            >
              <option value="">Todas</option>
              {Object.entries(SPHERE_LABELS).map(([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
          </div>
          {(corruptionType || sphere) && (
            <button
              onClick={() => { setCorruptionType(""); setSphere(""); setOffset(0); }}
              className="text-xs text-gov-blue-600 hover:underline"
            >
              Limpar filtros legais
            </button>
          )}
        </div>
      </div>

      <div className="mt-6">
        {loading ? (
          <TableSkeleton rows={6} />
        ) : error ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-red-200 bg-red-50 py-12">
            <AlertTriangle className="h-8 w-8 text-red-400" />
            <p className="mt-2 text-sm text-red-600">{error}</p>
            <button
              onClick={() => {
                setError(null);
                setOffset(offset);
              }}
              className="mt-3 rounded-md bg-red-100 px-4 py-1.5 text-sm text-red-700 transition hover:bg-red-200"
            >
              Tentar novamente
            </button>
          </div>
        ) : signals.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-gov-gray-200 bg-white py-16">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gov-gray-100">
              <Radar className="h-7 w-7 text-gov-gray-400" />
            </div>
            <h3 className="mt-4 text-sm font-semibold text-gov-gray-900">
              {hasFilters
                ? "Nenhum sinal encontrado com os filtros aplicados"
                : "Nenhum sinal de risco disponivel no momento"}
            </h3>
            <p className="mt-1 max-w-md text-center text-sm text-gov-gray-500">
              {hasFilters
                ? "Ajuste os filtros de tipologia ou severidade para ampliar a busca."
                : "O status da pipeline e da ingestao de dados esta disponivel na aba Cobertura."}
            </p>
            {!hasFilters && (
              <div className="mt-4 flex gap-2">
                <Link
                  href="/coverage"
                  className="rounded-md bg-gov-blue-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-gov-blue-800"
                >
                  Ver Cobertura
                </Link>
                <Link
                  href="/methodology"
                  className="rounded-md border border-gov-gray-300 bg-white px-4 py-2 text-sm font-medium text-gov-gray-700 transition hover:bg-gov-gray-50"
                >
                  Ver Metodologia
                </Link>
              </div>
            )}
          </div>
        ) : (
          <SignalTable signals={signals} />
        )}
      </div>

      {!loading && !error && total > 20 && (
        <div className="mt-4 flex items-center justify-between">
          <p className="text-sm text-gov-gray-500">
            Mostrando {offset + 1}–{Math.min(offset + 20, total)} de {total}
          </p>
          <div className="flex gap-2">
            <button
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - 20))}
              className="inline-flex items-center gap-1 rounded-md border border-gov-gray-300 bg-white px-3 py-1.5 text-sm transition hover:bg-gov-gray-50 disabled:opacity-50"
            >
              <ChevronLeft className="h-4 w-4" />
              Anterior
            </button>
            <button
              disabled={offset + 20 >= total}
              onClick={() => setOffset(offset + 20)}
              className="inline-flex items-center gap-1 rounded-md border border-gov-gray-300 bg-white px-3 py-1.5 text-sm transition hover:bg-gov-gray-50 disabled:opacity-50"
            >
              Proximo
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
