"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getSignal, getSignalEvidence } from "@/lib/api";
import { Markdown } from "@/components/Markdown";
import { Breadcrumb } from "@/components/Breadcrumb";
import { DetailSkeleton } from "@/components/Skeleton";
import { EmptyState } from "@/components/EmptyState";
import { severityColor, formatDate, formatBRL, normalizeUnknownDisplay } from "@/lib/utils";
import { SEVERITY_LABELS, TYPOLOGY_LABELS } from "@/lib/constants";
import type { SignalDetail, SignalEvidencePage, FactorMeta } from "@/lib/types";
import {
  FileSearch,
  AlertTriangle,
  Info,
  AlertCircle,
  ShieldAlert,
  Calendar,
  Briefcase,
  Network,
  ExternalLink,
  RefreshCw,
  Layers,
  Building2,
  User,
  CheckCircle2,
  XCircle,
  FileText,
  HelpCircle,
  Scale,
} from "lucide-react";

const SEVERITY_ICONS = {
  low: Info,
  medium: AlertCircle,
  high: AlertTriangle,
  critical: ShieldAlert,
} as const;

const ENTITY_TYPE_ICONS: Record<string, typeof Building2> = {
  company: Building2,
  person: User,
  org: Building2,
};

const REF_TYPE_LABELS: Record<string, { label: string; icon: typeof FileText }> = {
  event: { label: "Evento (contrato/licitacao)", icon: FileText },
  baseline: { label: "Linha de base estatistica", icon: Layers },
  entity: { label: "Entidade", icon: Building2 },
  external_url: { label: "Fonte externa", icon: ExternalLink },
  raw_source: { label: "Registro bruto", icon: FileSearch },
};

function formatFactorValue(value: unknown, meta?: FactorMeta): string {
  if (value === null || value === undefined) return "—";

  if (meta?.unit === "boolean" || typeof value === "boolean") {
    return ""; // handled by icon rendering
  }
  if (meta?.unit === "brl" && typeof value === "number") {
    return formatBRL(value);
  }
  if (meta?.unit === "percent" && typeof value === "number") {
    return `${(value * (value > 1 ? 1 : 100)).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
  }
  if (meta?.unit === "days" && typeof value === "number") {
    return `${Math.round(value)} dias`;
  }
  if (typeof value === "number") {
    return value.toLocaleString("pt-BR", { maximumFractionDigits: 4 });
  }
  return normalizeUnknownDisplay(value);
}

function sanitizeText(value: string): string {
  return value
    .replace(/\bunknown\b/gi, "Nao informado pela fonte")
    .replace(/sem classificacao/gi, "Nao informado pela fonte")
    .replace(/sem classificação/gi, "Nao informado pela fonte");
}

const WHAT_CROSSED_LABELS: Record<string, string> = {
  orgao_comprador: "Orgao comprador",
  modalidade_dispensa: "Modalidade de compra direta (dispensa)",
  grupo_catmat: "Classificacao do item (CATMAT/CATSER)",
  janela_temporal: "Janela temporal das compras",
  entidades: "Entidades envolvidas",
  eventos: "Eventos publicos vinculados",
  fatores_quantitativos: "Indicadores quantitativos da tipologia",
};

const EVIDENCE_PAGE_SIZE = 10;

function toNumberOrNull(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const normalized = value.replace(/\./g, "").replace(",", ".").trim();
    const parsed = Number(normalized);
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

export default function SignalDetailPage() {
  const params = useParams();
  const [signal, setSignal] = useState<SignalDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [evidenceOffset, setEvidenceOffset] = useState(0);
  const [evidencePage, setEvidencePage] = useState<SignalEvidencePage | null>(null);
  const [evidenceLoading, setEvidenceLoading] = useState(false);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);

  const fetchSignal = () => {
    if (!params.id) return;
    setLoading(true);
    setError(null);
    getSignal(params.id as string)
      .then(setSignal)
      .catch(() => setError("Erro ao carregar sinal"))
      .finally(() => setLoading(false));
  };

  useEffect(fetchSignal, [params.id]);

  useEffect(() => {
    setEvidenceOffset(0);
  }, [params.id]);

  useEffect(() => {
    if (!params.id) return;
    setEvidenceLoading(true);
    setEvidenceError(null);
    getSignalEvidence(params.id as string, {
      offset: evidenceOffset,
      limit: EVIDENCE_PAGE_SIZE,
      sort: "occurred_at_desc",
    })
      .then(setEvidencePage)
      .catch(() => setEvidenceError("Erro ao carregar evidencias"))
      .finally(() => setEvidenceLoading(false));
  }, [params.id, evidenceOffset]);

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <DetailSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-12">
        <EmptyState
          icon={AlertTriangle}
          title="Erro ao carregar sinal"
          description={error}
        />
        <div className="mt-4 text-center">
          <button
            onClick={fetchSignal}
            className="inline-flex items-center gap-1.5 rounded-lg bg-gov-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-gov-blue-700"
          >
            <RefreshCw className="h-4 w-4" />
            Tentar novamente
          </button>
        </div>
      </div>
    );
  }

  if (!signal) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-12">
        <EmptyState
          icon={FileSearch}
          title="Sinal nao encontrado"
          description="O sinal solicitado nao existe ou foi removido"
        />
      </div>
    );
  }

  const SevIcon = SEVERITY_ICONS[signal.severity];
  const confidence = Math.round(signal.confidence * 100);
  const factorDescriptions = signal.factor_descriptions || {};
  const entities = signal.entities || [];
  const fallbackInvestigation = signal.typology_code === "T03"
    ? {
        what_crossed: [
          "orgao_comprador",
          "modalidade_dispensa",
          "grupo_catmat",
          "janela_temporal",
        ],
        period_start: signal.period_start ?? null,
        period_end: signal.period_end ?? null,
        observed_total_brl: toNumberOrNull(signal.factors?.total_value_brl),
        legal_threshold_brl: toNumberOrNull(signal.factors?.threshold_brl),
        ratio_over_threshold: toNumberOrNull(signal.factors?.ratio),
        legal_reference: "Lei 14.133/2021",
      }
    : null;
  const investigation = signal.investigation_summary ?? fallbackInvestigation;
  const totalEvidence = evidencePage?.total ?? signal.evidence_stats?.total_events ?? signal.evidence_refs.length;
  const evidenceItems = evidencePage?.items ?? [];

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <Breadcrumb
        items={[
          { label: "Radar", href: "/radar" },
          { label: sanitizeText(signal.title) },
        ]}
      />

      {/* Header */}
      <div className="mt-4 flex items-start justify-between">
        <div className="flex items-start gap-3">
          <div
            className={`mt-1 flex h-10 w-10 items-center justify-center rounded-full ${severityColor(signal.severity)}`}
          >
            <SevIcon className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gov-gray-900">
              {sanitizeText(signal.title)}
            </h1>
            <div className="mt-1 flex flex-wrap items-center gap-3 text-sm text-gov-gray-500">
              <span className="inline-flex items-center gap-1 rounded-full bg-gov-blue-100 px-2 py-0.5 font-mono text-xs font-semibold text-gov-blue-700">
                {signal.typology_code}
              </span>
              <span>
                {TYPOLOGY_LABELS[signal.typology_code] ?? signal.typology_name}
              </span>
              {signal.created_at && (
                <span className="inline-flex items-center gap-1">
                  <Calendar className="h-3.5 w-3.5" />
                  {formatDate(signal.created_at)}
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          <span
            className={`rounded-full px-3 py-1 text-xs font-medium ${severityColor(signal.severity)}`}
          >
            {SEVERITY_LABELS[signal.severity]}
          </span>
          <div className="flex items-center gap-2">
            <div className="h-2 w-20 rounded-full bg-gov-gray-200">
              <div
                className="h-2 rounded-full bg-gov-blue-600"
                style={{ width: `${confidence}%` }}
              />
            </div>
            <span className="text-xs font-medium text-gov-gray-500">
              {confidence}% confianca
            </span>
          </div>
        </div>
      </div>

      {/* Links */}
      <div className="mt-4 flex flex-wrap gap-2">
        {signal.case_id && (
          <Link
            href={`/case/${signal.case_id}`}
            className="inline-flex items-center gap-1.5 rounded-lg bg-gov-blue-600 px-3 py-1.5 text-xs font-medium text-white shadow-sm transition hover:bg-gov-blue-700"
          >
            <Briefcase className="h-4 w-4" />
            Ver caso: {signal.case_title}
          </Link>
        )}
        {signal.event_ids.length > 0 && (
          <Link
            href={`/signal/${signal.id}/graph`}
            className="inline-flex items-center gap-1.5 rounded-lg bg-gov-blue-600 px-3 py-1.5 text-xs font-medium text-white shadow-sm transition hover:bg-gov-blue-700"
          >
            <Network className="h-4 w-4" />
            Ver teia do sinal
          </Link>
        )}
        {signal.entity_ids.length > 0 && signal.case_id && (
          <Link
            href={`/investigation/${signal.case_id}?signal_id=${signal.id}`}
            className="inline-flex items-center gap-1.5 rounded-lg border border-gov-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gov-gray-700 shadow-sm transition hover:bg-gov-gray-50"
          >
            <Network className="h-4 w-4" />
            Investigar no Grafo
          </Link>
        )}
      </div>

      {/* Summary */}
      {signal.summary && (
        <div className="mt-6 rounded-lg border border-gov-gray-200 bg-white p-4">
          <p className="text-sm text-gov-gray-700">{sanitizeText(signal.summary)}</p>
        </div>
      )}

      {investigation && (
        <div className="mt-6 rounded-lg border border-gov-blue-100 bg-gov-blue-50/40 p-4">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-gov-gray-900">
            <Scale className="h-5 w-5 text-gov-blue-600" />
            Por que este sinal existe?
          </h2>
          <p className="mt-2 text-sm text-gov-gray-700">
            O motor cruzou dados publicos para identificar um padrao atipico nesta tipologia.
          </p>
          <p className="mt-1 text-xs text-gov-gray-500">
            Termo tecnico: cluster temporal de compras diretas com somatorio acima do limite legal.
          </p>
          <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
            <div className="rounded-md bg-white px-3 py-2">
              <p className="text-xs font-semibold text-gov-gray-600">Valor observado</p>
              <p className="text-sm text-gov-gray-900">
                {typeof investigation.observed_total_brl === "number"
                  ? formatBRL(investigation.observed_total_brl)
                  : "Nao informado"}
              </p>
            </div>
            <div className="rounded-md bg-white px-3 py-2">
              <p className="text-xs font-semibold text-gov-gray-600">Limite de referencia</p>
              <p className="text-sm text-gov-gray-900">
                {typeof investigation.legal_threshold_brl === "number"
                  ? formatBRL(investigation.legal_threshold_brl)
                  : "Nao informado"}
              </p>
            </div>
            <div className="rounded-md bg-white px-3 py-2">
              <p className="text-xs font-semibold text-gov-gray-600">Razao sobre limite</p>
              <p className="text-sm text-gov-gray-900">
                {typeof investigation.ratio_over_threshold === "number"
                  ? `${investigation.ratio_over_threshold.toLocaleString("pt-BR", {
                      maximumFractionDigits: 2,
                    })}x`
                  : "Nao informado"}
              </p>
            </div>
            <div className="rounded-md bg-white px-3 py-2">
              <p className="text-xs font-semibold text-gov-gray-600">Base legal</p>
              <p className="text-sm text-gov-gray-900">
                {investigation.legal_reference || "Nao informado"}
              </p>
            </div>
          </div>
          {investigation.what_crossed.length > 0 && (
            <div className="mt-3">
              <p className="text-xs font-semibold text-gov-gray-600">Dados cruzados</p>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {investigation.what_crossed.map((item) => (
                  <span
                    key={item}
                    className="rounded-full bg-white px-2 py-0.5 text-xs text-gov-gray-700"
                  >
                    {WHAT_CROSSED_LABELS[item] || item}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Explanation (markdown) */}
      {signal.explanation_md && (
        <div className="mt-6">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-gov-gray-900">
            <FileSearch className="h-5 w-5 text-gov-blue-600" />
            Explicacao e Cruzamento
          </h2>
          <div className="mt-3 rounded-lg border border-gov-gray-200 bg-white p-4">
            <Markdown content={signal.explanation_md} />
          </div>
        </div>
      )}

      {/* Analysis Period — always shown prominently */}
      <div className="mt-6">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-gov-gray-900">
          <Calendar className="h-5 w-5 text-gov-blue-600" />
          Periodo de analise
        </h2>
        <div className="mt-3 rounded-lg border border-gov-gray-200 bg-white p-4">
          <p className="text-sm text-gov-gray-700">
            {signal.period_start ? formatDate(signal.period_start) : "---"}
            {" → "}
            {signal.period_end ? formatDate(signal.period_end) : "---"}
          </p>
          <p className="mt-2 text-xs text-gov-gray-500">
            Janela temporal dos dados analisados pela tipologia. Eventos fora deste periodo nao foram considerados.
          </p>
        </div>
      </div>

      {/* Factors — with labels and descriptions */}
      {signal.factors && Object.keys(signal.factors).length > 0 && (
        <div className="mt-6">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-gov-gray-900">
            <Layers className="h-5 w-5 text-gov-blue-600" />
            Fatores
          </h2>
          <p className="mt-1 text-xs text-gov-gray-500">
            Indicadores quantitativos calculados pela tipologia {signal.typology_code} — {TYPOLOGY_LABELS[signal.typology_code] ?? signal.typology_name}. Cada fator contribui para a pontuacao de risco.
          </p>
          <div className="mt-3 rounded-lg border border-gov-gray-200 bg-white p-4">
            <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {Object.entries(signal.factors).map(([key, value]) => {
                const meta = factorDescriptions[key];
                const isBoolean = meta?.unit === "boolean" || typeof value === "boolean";
                const boolVal = isBoolean ? Boolean(value) : null;
                return (
                  <div key={key} className="rounded-md bg-gov-gray-50 px-3 py-2.5">
                    <dt className="flex items-center gap-1.5 text-xs font-semibold text-gov-gray-700">
                      {meta?.label || key}
                      {meta?.description && (
                        <span className="group relative">
                          <HelpCircle className="h-3.5 w-3.5 text-gov-gray-400" />
                          <span className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-1 hidden w-56 -translate-x-1/2 rounded-lg bg-gov-gray-900 px-3 py-2 text-xs font-normal text-white shadow-lg group-hover:block">
                            {meta.description}
                          </span>
                        </span>
                      )}
                    </dt>
                    <dd className="mt-1 flex items-center gap-1.5 font-mono text-sm font-medium text-gov-gray-900">
                      {isBoolean ? (
                        <>
                          {boolVal ? (
                            <CheckCircle2 className="h-4 w-4 text-green-600" />
                          ) : (
                            <XCircle className="h-4 w-4 text-gov-gray-400" />
                          )}
                          <span>{boolVal ? "Sim" : "Nao"}</span>
                        </>
                      ) : (
                        formatFactorValue(value, meta)
                      )}
                    </dd>
                  </div>
                );
              })}
            </dl>
          </div>
        </div>
      )}

      {/* Evidence References — complete list with pagination */}
      {(totalEvidence > 0 || evidenceLoading) && (
        <div className="mt-6">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-gov-gray-900">
            <ExternalLink className="h-5 w-5 text-gov-blue-600" />
            Evidencias ({totalEvidence})
          </h2>
          <p className="mt-1 text-xs text-gov-gray-500">
            Evidencias sao os registros publicos que fundamentam este sinal. Cada item explica por que entrou no conjunto de evidencias.
          </p>
          {signal.evidence_stats && signal.evidence_stats.omitted_refs > 0 && (
            <p className="mt-1 text-xs text-amber-700">
              {signal.evidence_stats.listed_refs} referencias sinteticas no sinal original, com{" "}
              {signal.evidence_stats.omitted_refs} evento(s) adicionais listados abaixo.
            </p>
          )}
          {evidenceError && (
            <p className="mt-2 text-xs text-red-600">{evidenceError}</p>
          )}
          <div className="mt-3 space-y-2">
            {evidenceLoading && evidenceItems.length === 0 && (
              <div className="rounded-lg border border-gov-gray-200 bg-white p-3 text-sm text-gov-gray-500">
                Carregando evidencias...
              </div>
            )}
            {!evidenceLoading && evidenceItems.length === 0 && signal.evidence_refs.length > 0 && (
              <>
                {signal.evidence_refs.map((ref, idx) => {
                  const refMeta = REF_TYPE_LABELS[ref.ref_type] || { label: ref.ref_type, icon: FileText };
                  const RefIcon = refMeta.icon;
                  return (
                    <div
                      key={idx}
                      className="rounded-lg border border-gov-gray-200 bg-white p-3"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-start gap-2">
                          <RefIcon className="mt-0.5 h-4 w-4 shrink-0 text-gov-blue-500" />
                          <p className="text-sm text-gov-gray-700">
                            {sanitizeText(ref.description)}
                          </p>
                        </div>
                        <span className="shrink-0 rounded bg-gov-gray-100 px-1.5 py-0.5 text-xs text-gov-gray-500">
                          {refMeta.label}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </>
            )}
            {evidenceItems.map((item) => (
              <div
                key={item.event_id}
                className="rounded-lg border border-gov-gray-200 bg-white p-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-gov-gray-900">
                      {sanitizeText(item.description)}
                    </p>
                    <p className="mt-1 text-xs text-gov-gray-500">
                      {item.occurred_at ? formatDate(item.occurred_at) : "Data nao informada"}
                      {typeof item.value_brl === "number" && (
                        <>
                          {" • "}
                          {formatBRL(item.value_brl)}
                        </>
                      )}
                      {" • "}
                      {normalizeUnknownDisplay(item.modality)}
                    </p>
                  </div>
                  <span className="rounded bg-gov-gray-100 px-1.5 py-0.5 text-xs text-gov-gray-600">
                    Evento
                  </span>
                </div>
                <div className="mt-2 grid grid-cols-1 gap-1 text-xs text-gov-gray-600 sm:grid-cols-2">
                  <p>
                    <span className="font-semibold">CATMAT:</span>{" "}
                    {normalizeUnknownDisplay(item.catmat_group)}
                  </p>
                  <p>
                    <span className="font-semibold">Fonte:</span>{" "}
                    {item.source_connector} / {item.source_id}
                  </p>
                  <p className="font-mono sm:col-span-2">
                    <span className="font-semibold font-sans">Event ID:</span>{" "}
                    {item.event_id}
                  </p>
                  <p className="sm:col-span-2">
                    <span className="font-semibold">Porque e evidencia:</span>{" "}
                    {item.evidence_reason}
                  </p>
                </div>
              </div>
            ))}
          </div>
          {evidencePage && evidencePage.total > evidencePage.limit && (
            <div className="mt-3 flex items-center justify-between text-xs">
              <button
                type="button"
                disabled={evidenceOffset === 0}
                onClick={() => setEvidenceOffset((prev) => Math.max(0, prev - EVIDENCE_PAGE_SIZE))}
                className="rounded border border-gov-gray-300 bg-white px-2.5 py-1 text-gov-gray-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Anterior
              </button>
              <span className="text-gov-gray-500">
                {evidenceOffset + 1}-
                {Math.min(evidenceOffset + EVIDENCE_PAGE_SIZE, evidencePage.total)} de {evidencePage.total}
              </span>
              <button
                type="button"
                disabled={evidenceOffset + EVIDENCE_PAGE_SIZE >= evidencePage.total}
                onClick={() => setEvidenceOffset((prev) => prev + EVIDENCE_PAGE_SIZE)}
                className="rounded border border-gov-gray-300 bg-white px-2.5 py-1 text-gov-gray-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Proxima
              </button>
            </div>
          )}
        </div>
      )}

      {/* Entities — resolved with names, types, identifiers, roles */}
      {entities.length > 0 ? (
        <div className="mt-6">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-gov-gray-900">
            <Building2 className="h-5 w-5 text-gov-blue-600" />
            Entidades envolvidas ({entities.length})
          </h2>
          <p className="mt-1 text-xs text-gov-gray-500">
            Entidades identificadas como participantes diretas nos eventos que geraram este sinal de risco.
          </p>
          <div className="mt-3 space-y-2">
            {entities.map((entity) => {
              const EntityIcon = ENTITY_TYPE_ICONS[entity.type] || Building2;
              const identifierEntries = Object.entries(entity.identifiers);
              return (
                <Link
                  key={entity.id}
                  href={`/entity/${entity.id}`}
                  className="flex items-start gap-3 rounded-lg border border-gov-gray-200 bg-white p-3 transition hover:border-gov-blue-200 hover:bg-gov-blue-50"
                >
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gov-blue-100">
                    <EntityIcon className="h-4 w-4 text-gov-blue-700" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-gov-gray-900">{entity.name}</p>
                    <div className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-gov-gray-500">
                      <span className="capitalize rounded bg-gov-gray-100 px-1.5 py-0.5">
                        {normalizeUnknownDisplay(entity.type)}
                      </span>
                      {identifierEntries.map(([k, v]) => (
                        <span key={k} className="font-mono">
                          {k.toUpperCase()}: {v}
                        </span>
                      ))}
                    </div>
                    {(entity.roles_detailed && entity.roles_detailed.length > 0) ? (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {entity.roles_detailed.map((role) => (
                          <span
                            key={role.code}
                            className="rounded-full bg-gov-blue-50 px-2 py-0.5 text-xs font-medium text-gov-blue-700"
                          >
                            {role.label} ({role.code}) em {role.count_in_signal}
                          </span>
                        ))}
                      </div>
                    ) : entity.roles.length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {entity.roles.map((role) => (
                          <span
                            key={role}
                            className="rounded-full bg-gov-blue-50 px-2 py-0.5 text-xs font-medium text-gov-blue-700"
                          >
                            {normalizeUnknownDisplay(role)}
                          </span>
                        ))}
                      </div>
                    )}
                    {entity.role_explanation && (
                      <p className="mt-1 text-xs text-gov-gray-500">
                        {sanitizeText(entity.role_explanation)}
                      </p>
                    )}
                  </div>
                  <ExternalLink className="mt-1 h-4 w-4 shrink-0 text-gov-gray-300" />
                </Link>
              );
            })}
          </div>
        </div>
      ) : signal.entity_ids.length > 0 ? (
        /* Fallback: show raw entity IDs if entities not resolved */
        <div className="mt-6">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-gov-gray-900">
            <Building2 className="h-5 w-5 text-gov-blue-600" />
            Entidades envolvidas ({signal.entity_ids.length})
          </h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {signal.entity_ids.map((eid) => (
              <Link
                key={eid}
                href={`/entity/${eid}`}
                className="inline-flex items-center gap-1 rounded-md border border-gov-gray-200 bg-white px-2.5 py-1 font-mono text-xs text-gov-blue-600 transition hover:bg-gov-blue-50"
              >
                {eid.slice(0, 8)}...
                <ExternalLink className="h-3 w-3" />
              </Link>
            ))}
          </div>
        </div>
      ) : null}

      {/* Legal disclaimer */}
      <div className="mt-6 rounded-lg border border-gov-gray-100 bg-gov-gray-50 p-3">
        <p className="text-xs text-gov-gray-500">
          <strong>Aviso legal:</strong> Este sinal constitui uma <em>hipotese investigativa</em> baseada em cruzamento automatico de dados publicos.
          Nao equivale a acusacao, condenacao ou juizo de culpa. A decisao final pertence aos orgaos competentes
          (controle interno, auditoria, corregedoria, Ministerio Publico e Judiciario).
        </p>
      </div>

      {/* Completeness */}
      <div className="mt-6 rounded-lg border border-gov-gray-200 bg-white p-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gov-gray-700">
            Completude da evidencia
          </span>
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${
              signal.completeness_status === "sufficient"
                ? "bg-green-100 text-green-800"
                : "bg-amber-100 text-amber-800"
            }`}
          >
            {signal.completeness_status === "sufficient"
              ? "Suficiente"
              : "Insuficiente"}
          </span>
        </div>
        <div className="mt-2 h-2 w-full rounded-full bg-gov-gray-200">
          <div
            className="h-2 rounded-full bg-gov-blue-600 transition-all"
            style={{
              width: `${Math.round(signal.completeness_score * 100)}%`,
            }}
          />
        </div>
        <p className="mt-1 text-right text-xs text-gov-gray-500">
          {Math.round(signal.completeness_score * 100)}%
        </p>
      </div>
    </div>
  );
}
