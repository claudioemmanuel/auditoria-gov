"use client";

import type { CoverageItem, IngestRun } from "@/lib/types";
import {
  Download,
  Users,
  BarChart3,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Loader2,
  Radar,
} from "lucide-react";

interface ProcessingStatusProps {
  coverage: CoverageItem[];
  recentRuns: IngestRun[];
  signalCount: number;
  loading: boolean;
}

interface PipelineStage {
  label: string;
  description: string;
  icon: React.ElementType;
  status: "done" | "processing" | "pending" | "warning" | "error";
}

function isStuckRun(run: IngestRun): boolean {
  if (run.status !== "running" || !run.started_at) return false;
  const startedAt = new Date(run.started_at).getTime();
  if (Number.isNaN(startedAt)) return false;
  const elapsedMs = Date.now() - startedAt;
  return elapsedMs > 20 * 60 * 1000;
}

export function ProcessingStatus({
  coverage,
  recentRuns,
  signalCount,
  loading,
}: ProcessingStatusProps) {
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-gov-gray-200 bg-white py-16">
        <Loader2 className="h-8 w-8 animate-spin text-gov-blue-600" />
        <p className="mt-3 text-sm text-gov-gray-500">Verificando status do pipeline...</p>
      </div>
    );
  }

  const totalItems = coverage.reduce((sum, c) => sum + c.total_items, 0);
  const okSources = coverage.filter((c) => c.status === "ok").length;
  const warningSources = coverage.filter((c) => c.status === "warning").length;
  const pendingSources = coverage.filter((c) => c.status === "pending").length;
  const errorSources = coverage.filter((c) => c.status === "error").length;
  const staleSources = coverage.filter((c) => c.status === "stale").length;

  const enabledJobs = new Set(
    coverage.filter((c) => c.enabled_in_mvp).map((c) => `${c.connector}:${c.job}`),
  );

  const latestRunsByJob = new Map<string, IngestRun>();
  for (const run of recentRuns) {
    const key = `${run.connector}:${run.job}`;
    if (!latestRunsByJob.has(key)) {
      latestRunsByJob.set(key, run);
    }
  }
  const latestRuns = Array.from(latestRunsByJob.values());
  const runningRuns = latestRuns.filter((r) => r.status === "running");
  const stuckRuns = runningRuns.filter(isStuckRun);
  // Only count errors from enabled connectors — disabled ones failing is expected
  const runtimeErrorRuns = latestRuns.filter(
    (r) => r.status === "error" && enabledJobs.has(`${r.connector}:${r.job}`),
  );
  const enabledErrorSources = coverage.filter(
    (c) => c.status === "error" && c.enabled_in_mvp,
  ).length;

  const hasData = totalItems > 0;
  const allPending = coverage.length === 0 || pendingSources === coverage.length;
  const hasBlockingIngestIssue = stuckRuns.length > 0 || runtimeErrorRuns.length > 0 || enabledErrorSources > 0;

  const stages: PipelineStage[] = [
    {
      label: "Ingestao de Dados",
      description:
        stuckRuns.length > 0
          ? `${stuckRuns.length} job(ns) travado(s) ha mais de 20 min`
          : runningRuns.length > 0
            ? `${runningRuns.length} job(ns) em execucao agora`
            : runtimeErrorRuns.length > 0
              ? `${runtimeErrorRuns.length} fonte(s) habilitada(s) com erro`
              : hasData
                ? `${totalItems.toLocaleString("pt-BR")} itens de ${okSources + warningSources + staleSources} fonte(s)`
                : allPending
                  ? "Nenhuma fonte de dados ingerida ainda"
                  : `${enabledErrorSources} fonte(s) com erro`,
      icon: Download,
      status:
        stuckRuns.length > 0
          ? "error"
          : runningRuns.length > 0
            ? "processing"
            : runtimeErrorRuns.length > 0
              ? "warning"
              : hasData
                ? "done"
                : allPending
                  ? "pending"
                  : "error",
    },
    {
      label: "Resolucao de Entidades",
      description: hasData
        ? "Vinculacao de CNPJs, CPFs e nomes entre fontes"
        : "Aguardando dados para iniciar vinculacao",
      icon: Users,
      status: hasData && !hasBlockingIngestIssue ? "done" : hasData ? "warning" : "pending",
    },
    {
      label: "Calculo de Baselines",
      description: hasData
        ? "Distribuicoes estatisticas de precos, participantes, aditivos"
        : "Aguardando dados para calcular baselines",
      icon: BarChart3,
      status: hasData && !hasBlockingIngestIssue ? "done" : hasData ? "warning" : "pending",
    },
    {
      label: "Deteccao de Sinais",
      description: signalCount > 0
        ? `${signalCount} sinal(is) identificado(s)`
        : stuckRuns.length > 0
          ? "Travado: existe job de ingestao sem concluir"
          : runtimeErrorRuns.length > 0
            ? "Ultima execucao terminou com erro; ver detalhes por fonte"
            : runningRuns.length > 0
              ? "Analise em andamento — ingestao/normalizacao ainda executando"
              : hasData
                ? "Sem sinais no momento; aguardando proxima rodada de deteccao"
                : "Aguardando baselines para iniciar deteccao",
      icon: AlertTriangle,
      status: signalCount > 0 ? "done" : stuckRuns.length > 0 ? "error" : runningRuns.length > 0 ? "processing" : runtimeErrorRuns.length > 0 ? "warning" : hasData ? "pending" : "pending",
    },
  ];

  return (
    <div className="rounded-lg border border-gov-gray-200 bg-white">
      <div className="border-b border-gov-gray-200 px-6 py-4">
        <div className="flex items-center gap-2">
          <Radar className="h-5 w-5 text-gov-blue-600" />
          <h3 className="font-semibold text-gov-gray-900">Status do Pipeline</h3>
        </div>
        <p className="mt-1 text-sm text-gov-gray-500">
          {stuckRuns.length > 0
            ? "Foram detectados jobs travados. Abra os itens abaixo para ver erro, horario e ultimo estado."
            : runtimeErrorRuns.length > 0
              ? "Ha erros recentes de ingestao. Os detalhes estao disponiveis clicando em cada item."
              : signalCount > 0
                ? "O pipeline esta operacional e sinais foram detectados."
                : hasData
                  ? "Dados ingeridos com sucesso. Se nao houver sinais, aguarde a proxima rodada de deteccao."
                  : "O radar precisa de dados para funcionar. Execute a ingestao de dados para comecar."}
        </p>
      </div>

      <div className="divide-y divide-gov-gray-100">
        {stages.map((stage, i) => {
          const StatusIcon = stage.status === "done"
            ? CheckCircle2
            : stage.status === "processing"
              ? Loader2
              : stage.status === "warning"
                ? AlertTriangle
              : stage.status === "error"
                ? AlertTriangle
                : Clock;

          const statusColor = stage.status === "done"
            ? "text-green-600"
            : stage.status === "processing"
              ? "text-gov-blue-600"
              : stage.status === "warning"
                ? "text-amber-500"
              : stage.status === "error"
                ? "text-red-500"
                : "text-gov-gray-400";

          return (
            <div key={i} className="flex items-center gap-4 px-6 py-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gov-gray-100">
                <stage.icon className="h-5 w-5 text-gov-gray-600" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-gov-gray-900">{stage.label}</p>
                <p className="text-xs text-gov-gray-500">{stage.description}</p>
              </div>
              <StatusIcon
                className={`h-5 w-5 shrink-0 ${statusColor} ${stage.status === "processing" ? "animate-spin" : ""}`}
              />
            </div>
          );
        })}
      </div>

      {coverage.length > 0 && (
        <div className="border-t border-gov-gray-200 px-6 py-3">
          <div className="flex flex-wrap gap-3 text-xs text-gov-gray-500">
            {okSources > 0 && (
              <span className="inline-flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-green-500" />
                {okSources} fonte(s) atualizada(s)
              </span>
            )}
            {warningSources > 0 && (
              <span className="inline-flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-amber-500" />
                {warningSources} fonte(s) em alerta
              </span>
            )}
            {staleSources > 0 && (
              <span className="inline-flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-yellow-500" />
                {staleSources} fonte(s) desatualizada(s)
              </span>
            )}
            {pendingSources > 0 && (
              <span className="inline-flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-gray-400" />
                {pendingSources} fonte(s) pendente(s)
              </span>
            )}
            {errorSources > 0 && (
              <span className="inline-flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-red-500" />
                {errorSources} fonte(s) com erro
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
