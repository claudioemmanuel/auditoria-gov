"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getCase } from "@/lib/api";
import { Markdown } from "@/components/Markdown";
import { Breadcrumb } from "@/components/Breadcrumb";
import { DetailSkeleton } from "@/components/Skeleton";
import { EmptyState } from "@/components/EmptyState";
import { severityColor, formatDate, formatBRL, normalizeUnknownDisplay } from "@/lib/utils";
import { SEVERITY_LABELS, TYPOLOGY_LABELS } from "@/lib/constants";
import type { CaseDetail, FactorMeta } from "@/lib/types";
import {
  FileSearch,
  AlertTriangle,
  Info,
  AlertCircle,
  ShieldAlert,
  TrendingUp,
  Briefcase,
  Network,
  RefreshCw,
  Building2,
  ChevronDown,
  ChevronUp,
  Calendar,
  DollarSign,
  Users,
  HelpCircle,
} from "lucide-react";

const SEVERITY_ICONS = {
  low: Info,
  medium: AlertCircle,
  high: AlertTriangle,
  critical: ShieldAlert,
} as const;

const FACTOR_LABEL_OVERRIDES: Record<string, string> = {
  n_purchases: "Compras no cluster",
  total_value_brl: "Valor total",
  threshold_brl: "Limite legal",
  avg_value_brl: "Valor medio por compra",
  span_days: "Duracao da janela",
  n_contracts: "Contratos",
  n_factors: "Fatores detectados",
  amendment_pct: "Acrescimo por aditivos",
};

function humanizeFactorKey(key: string): string {
  if (FACTOR_LABEL_OVERRIDES[key]) return FACTOR_LABEL_OVERRIDES[key];
  return key
    .replace(/_/g, " ")
    .replace(/\bbrl\b/gi, "BRL")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatCaseFactorValue(value: unknown, key: string, meta?: FactorMeta): string {
  if (value === null || value === undefined) return "Nao informado";
  if (meta?.unit === "boolean" || typeof value === "boolean") {
    return value ? "Sim" : "Nao";
  }
  if (typeof value === "number") {
    if (meta?.unit === "brl" || key.includes("value_brl") || key.includes("threshold_brl")) {
      return formatBRL(value);
    }
    if (meta?.unit === "days" || key.includes("span_days") || key.includes("overlap_days")) {
      return `${Math.round(value)} dias`;
    }
    if (meta?.unit === "percent" || key.includes("_pct")) {
      return `${value.toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%`;
    }
    if (meta?.unit === "ratio" || key.includes("ratio")) {
      return `${value.toLocaleString("pt-BR", { maximumFractionDigits: 2 })}x`;
    }
    return value.toLocaleString("pt-BR", { maximumFractionDigits: 4 });
  }
  return normalizeUnknownDisplay(value);
}

function pluralize(value: number, singular: string, plural: string): string {
  return value === 1 ? singular : plural;
}

export default function CaseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [caseData, setCaseData] = useState<CaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [faqOpen, setFaqOpen] = useState(true);

  const fetchCase = () => {
    if (!params.id) return;
    setLoading(true);
    setError(null);
    getCase(params.id as string)
      .then(setCaseData)
      .catch((err) => {
        if (err instanceof Error && err.message.includes("404")) {
          setError("Caso nao encontrado. Verifique o link ou volte ao Radar.");
        } else {
          setError("Erro de conexao ao carregar caso. Tente novamente.");
        }
      })
      .finally(() => setLoading(false));
  };

  useEffect(fetchCase, [params.id]);

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
          title="Erro ao carregar caso"
          description={error}
        />
        <div className="mt-4 text-center">
          <button
            onClick={fetchCase}
            className="inline-flex items-center gap-1.5 rounded-lg bg-gov-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-gov-blue-700"
          >
            <RefreshCw className="h-4 w-4" />
            Tentar novamente
          </button>
        </div>
      </div>
    );
  }

  if (!caseData) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-12">
        <EmptyState
          icon={FileSearch}
          title="Caso nao encontrado"
          description="O caso solicitado nao existe ou foi removido"
        />
      </div>
    );
  }

  const SevIcon = SEVERITY_ICONS[caseData.severity];
  const entityNames = caseData.entity_names || [];
  const typologyLabels = Array.from(
    new Set(
      caseData.signals.map((signal) => TYPOLOGY_LABELS[signal.typology_code] ?? signal.typology_name),
    ),
  );
  const highCriticalCount = caseData.signals.filter((signal) => signal.severity === "high" || signal.severity === "critical").length;
  const totalEvidence = caseData.signals.reduce((acc, signal) => acc + (signal.evidence_count ?? 0), 0);
  const periodLabel = (caseData.period_start || caseData.period_end)
    ? `${caseData.period_start ? formatDate(caseData.period_start) : "---"} → ${caseData.period_end ? formatDate(caseData.period_end) : "---"}`
    : "Periodo nao informado";
  const topEntitiesLabel = entityNames.slice(0, 3).join(", ");

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <Breadcrumb
        items={[
          { label: "Radar", href: "/radar" },
          { label: caseData.title },
        ]}
      />

      <div className="mt-4 flex items-start justify-between">
        <div className="flex items-start gap-3">
          <div className={`mt-1 flex h-10 w-10 items-center justify-center rounded-full ${severityColor(caseData.severity)}`}>
            <SevIcon className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gov-gray-900">
              {caseData.title}
            </h1>
            <div className="mt-1 flex items-center gap-3 text-sm text-gov-gray-500">
              <span className="capitalize">Status: {caseData.status}</span>
              {caseData.created_at && (
                <span>Criado em {formatDate(caseData.created_at)}</span>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href={`/investigation/${caseData.id}`}
            className="inline-flex items-center gap-1.5 rounded-lg bg-gov-blue-600 px-3 py-1.5 text-xs font-medium text-white shadow-sm transition hover:bg-gov-blue-700"
          >
            <Network className="h-4 w-4" />
            Investigar no Grafo
          </Link>
          <span
            className={`rounded-full px-3 py-1 text-xs font-medium ${severityColor(caseData.severity)}`}
          >
            {SEVERITY_LABELS[caseData.severity]}
          </span>
        </div>
      </div>

      {/* Explanatory box */}
      {caseData.explanation && (
        <div className="mt-6 rounded-lg border border-gov-blue-200 bg-gov-blue-50 p-4">
          <div className="flex items-start gap-2">
            <Info className="mt-0.5 h-4 w-4 shrink-0 text-gov-blue-600" />
            <p className="text-sm text-gov-blue-800">
              {caseData.explanation}
            </p>
          </div>
        </div>
      )}

      {/* Aggregated metrics */}
      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-lg border border-gov-gray-200 bg-white p-3">
          <div className="flex items-center gap-1.5 text-xs text-gov-gray-500">
            <TrendingUp className="h-3.5 w-3.5" />
            Sinais
          </div>
          <p className="mt-1 text-lg font-semibold text-gov-gray-900">
            {caseData.signals.length}
          </p>
        </div>
        <div className="rounded-lg border border-gov-gray-200 bg-white p-3">
          <div className="flex items-center gap-1.5 text-xs text-gov-gray-500">
            <Users className="h-3.5 w-3.5" />
            Entidades
          </div>
          <p className="mt-1 text-lg font-semibold text-gov-gray-900">
            {entityNames.length}
          </p>
        </div>
        {caseData.total_value_brl != null && caseData.total_value_brl > 0 && (
          <div className="rounded-lg border border-gov-gray-200 bg-white p-3">
            <div className="flex items-center gap-1.5 text-xs text-gov-gray-500">
              <DollarSign className="h-3.5 w-3.5" />
              Valor total
            </div>
            <p className="mt-1 text-lg font-semibold text-gov-gray-900">
              {formatBRL(caseData.total_value_brl)}
            </p>
          </div>
        )}
        {(caseData.period_start || caseData.period_end) && (
          <div className="rounded-lg border border-gov-gray-200 bg-white p-3">
            <div className="flex items-center gap-1.5 text-xs text-gov-gray-500">
              <Calendar className="h-3.5 w-3.5" />
              Periodo
            </div>
            <p className="mt-1 text-xs font-medium text-gov-gray-900">
              {caseData.period_start ? formatDate(caseData.period_start) : "---"}
              {" → "}
              {caseData.period_end ? formatDate(caseData.period_end) : "---"}
            </p>
          </div>
        )}
      </div>

      {/* Entity list */}
      {entityNames.length > 0 && (
        <div className="mt-6">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-gov-gray-900">
            <Building2 className="h-5 w-5 text-gov-blue-600" />
            Entidades envolvidas ({entityNames.length})
          </h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {entityNames.map((name, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1.5 rounded-lg border border-gov-gray-200 bg-white px-3 py-1.5 text-sm text-gov-gray-700"
              >
                <Building2 className="h-3.5 w-3.5 text-gov-gray-400" />
                {name}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="mt-6 rounded-lg border border-gov-gray-200 bg-white p-4">
        <p className="text-sm font-semibold text-gov-gray-900">
          Este caso consolida {caseData.signals.length} {pluralize(caseData.signals.length, "sinal", "sinais")} de risco em {typologyLabels.length} {pluralize(typologyLabels.length, "tipologia", "tipologias")}.
        </p>
        <p className="mt-1 text-sm text-gov-gray-700">
          Prioridade {SEVERITY_LABELS[caseData.severity].toLowerCase()} porque {highCriticalCount} {pluralize(highCriticalCount, "sinal esta", "sinais estao")} em nivel alto/critico. Janela analisada: {periodLabel}.
        </p>
        <div className="mt-2 flex flex-wrap gap-2 text-xs text-gov-gray-600">
          <span className="rounded-full bg-gov-gray-100 px-2 py-0.5">
            Tipologias: {typologyLabels.join(", ") || "Nao informado"}
          </span>
          {topEntitiesLabel && (
            <span className="rounded-full bg-gov-gray-100 px-2 py-0.5">
              Entidades-chave: {topEntitiesLabel}{entityNames.length > 3 ? ` e mais ${entityNames.length - 3}` : ""}
            </span>
          )}
          <span className="rounded-full bg-gov-gray-100 px-2 py-0.5">
            Evidencias vinculadas: {totalEvidence}
          </span>
        </div>
      </div>

      {caseData.summary && (
        <details className="mt-3 rounded-lg border border-gov-gray-200 bg-white">
          <summary className="cursor-pointer px-4 py-2 text-xs font-medium text-gov-gray-600">
            Resumo tecnico do agrupamento
          </summary>
          <div className="border-t border-gov-gray-100 px-4 py-3 text-sm text-gov-gray-700">
            <Markdown content={caseData.summary} />
          </div>
        </details>
      )}

      {/* "O que e um caso?" collapsible */}
      <div className="mt-6 rounded-lg border border-gov-gray-200 bg-white">
        <button
          onClick={() => setFaqOpen(!faqOpen)}
          aria-expanded={faqOpen}
          className="flex w-full items-center justify-between px-4 py-3 text-left"
        >
          <span className="flex items-center gap-2 text-sm font-medium text-gov-gray-700">
            <HelpCircle className="h-4 w-4 text-gov-blue-600" />
            O que e um caso consolidado?
          </span>
          {faqOpen ? (
            <ChevronUp className="h-4 w-4 text-gov-gray-400" />
          ) : (
            <ChevronDown className="h-4 w-4 text-gov-gray-400" />
          )}
        </button>
        {faqOpen && (
          <div className="border-t border-gov-gray-100 px-4 py-3">
            <div className="space-y-2 text-sm text-gov-gray-600">
              <p>
                Um <strong>caso consolidado</strong> agrupa sinais de risco que compartilham as mesmas entidades envolvidas.
                O sistema identifica automaticamente quando multiplos sinais de diferentes tipologias apontam para as mesmas
                empresas ou pessoas, sugerindo um padrao de irregularidade mais amplo.
              </p>
              <p>
                <strong>Criterios de agrupamento:</strong>
              </p>
              <ul className="ml-4 list-disc space-y-1">
                <li>Entidades em comum (mesmo CNPJ, CPF ou cluster de resolucao de entidades)</li>
                <li>Proximidade temporal (sinais detectados em janelas de ate 90 dias)</li>
                <li>Minimo de 2 sinais para formar um caso</li>
              </ul>
              <p>
                A <strong>severidade do caso</strong> e definida pelo sinal mais grave dentro do grupo.
                Auditorias podem considerar a severidade do caso como indicador de prioridade para investigacao.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Legal disclaimer */}
      <div className="mt-6 rounded-lg border border-gov-gray-100 bg-gov-gray-50 p-3">
        <p className="text-xs text-gov-gray-500">
          <strong>Aviso legal:</strong> Os sinais neste caso constituem <em>hipoteses investigativas</em> baseadas em cruzamento automatico de dados publicos.
          Nao equivalem a acusacao ou juizo de culpa. A decisao final pertence aos orgaos competentes.
        </p>
      </div>

      <h2 className="mt-8 flex items-center gap-2 text-lg font-semibold text-gov-gray-900">
        <TrendingUp className="h-5 w-5 text-gov-blue-600" />
        Sinais associados ({caseData.signals.length})
      </h2>
      <div className="mt-4 space-y-4">
        {caseData.signals.map((signal) => {
          const ItemSevIcon = SEVERITY_ICONS[signal.severity];
          const signalFactors = Object.entries(signal.factors || {});
          const visibleFactors = signalFactors.slice(0, 6);
          return (
            <Link
              key={signal.id}
              href={`/signal/${signal.id}`}
              className="block rounded-lg border border-gov-gray-200 bg-white p-4 transition hover:border-gov-blue-200 hover:shadow-sm"
            >
              <div className="flex items-center justify-between">
                <h3 className="font-medium text-gov-gray-900">{signal.title}</h3>
                <span
                  className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${severityColor(signal.severity)}`}
                >
                  <ItemSevIcon className="h-3 w-3" />
                  {SEVERITY_LABELS[signal.severity]}
                </span>
              </div>
              <p className="mt-1 text-sm text-gov-gray-500">
                <span className="font-mono text-xs">{signal.typology_code}</span>
                {" — "}
                {TYPOLOGY_LABELS[signal.typology_code] ?? signal.typology_name}
              </p>
              {signal.summary && (
                <p className="mt-2 text-sm text-gov-gray-700">{signal.summary}</p>
              )}
              {signal.confidence != null && (
                <div className="mt-2 flex items-center gap-2">
                  <div className="h-1.5 w-24 rounded-full bg-gov-gray-200">
                    <div
                      className="h-1.5 rounded-full bg-gov-blue-600"
                      style={{ width: `${signal.confidence * 100}%` }}
                    />
                  </div>
                  <span className="text-xs text-gov-gray-500">
                    {Math.round(signal.confidence * 100)}% confianca
                  </span>
                </div>
              )}
              <div className="mt-2 flex flex-wrap gap-1.5 text-xs text-gov-gray-600">
                <span className="rounded-full bg-gov-blue-50 px-2 py-0.5 text-gov-blue-700">
                  Compartilha entidades e janela temporal com outros sinais do caso
                </span>
                {signal.evidence_count != null && (
                  <span className="rounded-full bg-gov-gray-100 px-2 py-0.5">
                    Evidencias: {signal.evidence_count}
                  </span>
                )}
                {signal.entity_count != null && (
                  <span className="rounded-full bg-gov-gray-100 px-2 py-0.5">
                    Entidades: {signal.entity_count}
                  </span>
                )}
                {(signal.period_start || signal.period_end) && (
                  <span className="rounded-full bg-gov-gray-100 px-2 py-0.5">
                    Periodo: {signal.period_start ? formatDate(signal.period_start) : "---"} → {signal.period_end ? formatDate(signal.period_end) : "---"}
                  </span>
                )}
              </div>
              {signal.factors && Object.keys(signal.factors).length > 0 && (
                <div className="mt-3 border-t border-gov-gray-100 pt-3">
                  <h4 className="text-xs font-semibold uppercase text-gov-gray-500">
                    Indicadores que sustentam o sinal
                  </h4>
                  <dl className="mt-1 grid grid-cols-2 gap-2 sm:grid-cols-3">
                    {visibleFactors.map(([key, value]) => {
                      const meta = signal.factor_descriptions?.[key];
                      return (
                      <div key={key} className="rounded bg-gov-gray-50 px-2 py-1">
                        <dt className="text-xs text-gov-gray-500" title={meta?.description || ""}>
                          {meta?.label || humanizeFactorKey(key)}
                        </dt>
                        <dd className="font-mono text-xs font-medium text-gov-gray-900">
                          {formatCaseFactorValue(value, key, meta)}
                        </dd>
                      </div>
                    );
                    })}
                  </dl>
                  {signalFactors.length > visibleFactors.length && (
                    <p className="mt-2 text-xs text-gov-gray-500">
                      +{signalFactors.length - visibleFactors.length} indicador(es) disponivel(is) no detalhe do sinal.
                    </p>
                  )}
                </div>
              )}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
