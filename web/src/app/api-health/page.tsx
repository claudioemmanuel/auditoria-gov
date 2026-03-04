"use client";

import { useEffect, useMemo, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/Button";
import { getApiHeartbeat, getCoverageV2Summary } from "@/lib/api";
import type { CoverageV2SummaryResponse } from "@/lib/types";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  DatabaseZap,
  RefreshCw,
  ServerCrash,
  Workflow,
} from "lucide-react";

type HealthTone = "healthy" | "attention" | "blocked";
type CheckStatus = "ok" | "attention" | "error";

interface ServiceCheck {
  id: string;
  name: string;
  endpoint: string;
  status: CheckStatus;
  detail: string;
}

function statusBadge(tone: HealthTone) {
  if (tone === "healthy") {
    return {
      label: "Saudavel",
      cls: "status-ok",
      Icon: CheckCircle2,
    };
  }
  if (tone === "blocked") {
    return {
      label: "Bloqueado",
      cls: "status-error",
      Icon: ServerCrash,
    };
  }
  return {
    label: "Atencao",
    cls: "status-warning",
    Icon: AlertTriangle,
  };
}

function checkBadge(status: CheckStatus) {
  if (status === "ok") return "status-ok";
  if (status === "attention") return "status-warning";
  return "status-error";
}

function overallFromChecks(checks: ServiceCheck[]): HealthTone {
  if (checks.some((check) => check.status === "error")) return "blocked";
  if (checks.some((check) => check.status === "attention")) return "attention";
  return "healthy";
}

export default function ApiHealthPage() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [checkedAt, setCheckedAt] = useState<string | null>(null);

  const [heartbeatOk, setHeartbeatOk] = useState(false);
  const [coverageSummary, setCoverageSummary] = useState<CoverageV2SummaryResponse | null>(null);

  const [heartbeatError, setHeartbeatError] = useState<string | null>(null);
  const [coverageError, setCoverageError] = useState<string | null>(null);

  async function loadHealth() {
    setRefreshing(true);
    setHeartbeatError(null);
    setCoverageError(null);
    try {
      const [heartbeatResult, coverageResult] = await Promise.allSettled([
        getApiHeartbeat(),
        getCoverageV2Summary(),
      ]);

      if (heartbeatResult.status === "fulfilled") {
        setHeartbeatOk(heartbeatResult.value.status === "ok");
      } else {
        setHeartbeatOk(false);
        setHeartbeatError("Sem resposta do container da API.");
      }

      if (coverageResult.status === "fulfilled") {
        setCoverageSummary(coverageResult.value);
      } else {
        setCoverageSummary(null);
        setCoverageError("Nao foi possivel consultar o estado operacional do pipeline.");
      }
    } catch {
      setHeartbeatOk(false);
      setCoverageSummary(null);
      setHeartbeatError("Falha inesperada ao consultar saude da API.");
      setCoverageError("Falha inesperada ao consultar saude do pipeline.");
    } finally {
      setCheckedAt(new Date().toISOString());
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    void loadHealth();
  }, []);

  const checks = useMemo<ServiceCheck[]>(() => {
    const apiCheck: ServiceCheck = {
      id: "api",
      name: "Container API",
      endpoint: "/health",
      status: heartbeatOk ? "ok" : "error",
      detail: heartbeatOk
        ? "API respondendo normalmente."
        : heartbeatError || "API sem resposta no heartbeat.",
    };

    const pipelineCheck: ServiceCheck = {
      id: "pipeline",
      name: "Pipeline de dados",
      endpoint: "/public/coverage/v2/summary",
      status:
        coverageSummary == null
          ? "error"
          : coverageSummary.pipeline.overall_status === "healthy"
            ? "ok"
            : coverageSummary.pipeline.overall_status === "attention"
              ? "attention"
              : "error",
      detail:
        coverageSummary == null
          ? coverageError || "Sem dados operacionais do pipeline."
          : `Estado atual: ${coverageSummary.pipeline.overall_status}.`,
    };

    const workersCheck: ServiceCheck = {
      id: "workers",
      name: "Workers de processamento",
      endpoint: "/public/coverage/v2/summary",
      status:
        coverageSummary == null
          ? "error"
          : coverageSummary.totals.runtime.failed_or_stuck > 0
            ? "error"
            : "ok",
      detail:
        coverageSummary == null
          ? "Nao foi possivel validar workers."
          : coverageSummary.totals.runtime.failed_or_stuck > 0
            ? `${coverageSummary.totals.runtime.failed_or_stuck} execucao(oes) com falha/travamento.`
            : coverageSummary.totals.runtime.running > 0
              ? `${coverageSummary.totals.runtime.running} worker(s) em execucao normal.`
              : "Sem execucoes ativas no momento (estado normal).",
    };

    return [apiCheck, pipelineCheck, workersCheck];
  }, [heartbeatOk, heartbeatError, coverageSummary, coverageError]);

  const overallTone = overallFromChecks(checks);
  const badge = statusBadge(overallTone);
  const BadgeIcon = badge.Icon;

  return (
    <div className="page-wrap">
      <PageHeader
        title="Saude da Plataforma"
        subtitle="Monitor rapido de disponibilidade tecnica dos servicos essenciais."
        breadcrumbs={[{ label: "Saude API" }]}
        actions={
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-sm font-semibold ${badge.cls}`}>
              <BadgeIcon className="h-4 w-4" />
              {badge.label}
            </span>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => void loadHealth()}
              disabled={refreshing}
              loading={refreshing}
            >
              <RefreshCw className="h-4 w-4" />
              Atualizar
            </Button>
          </div>
        }
      />

      <p className="text-xs text-muted">
        Ultima verificacao: {checkedAt ? new Date(checkedAt).toLocaleString("pt-BR") : "Aguardando"}
      </p>

      <section className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-3">
        <article className="metric-card">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-accent" />
            <p className="font-display text-xs font-medium uppercase tracking-wide text-muted">API</p>
          </div>
          <p className="mt-2 font-mono tabular-nums text-3xl font-bold text-primary">{checks[0]?.status === "ok" ? "OK" : "Falha"}</p>
          <p className="mt-1 text-xs text-muted">{checks[0]?.endpoint}</p>
        </article>

        <article className="metric-card">
          <div className="flex items-center gap-2">
            <Workflow className="h-4 w-4 text-accent" />
            <p className="font-display text-xs font-medium uppercase tracking-wide text-muted">Pipeline</p>
          </div>
          <p className="mt-2 font-mono tabular-nums text-3xl font-bold text-primary">
            {coverageSummary?.pipeline.overall_status || "indisponivel"}
          </p>
          <p className="mt-1 text-xs text-muted">Estado operacional geral</p>
        </article>

        <article className="metric-card">
          <div className="flex items-center gap-2">
            <Cpu className="h-4 w-4 text-accent" />
            <p className="font-display text-xs font-medium uppercase tracking-wide text-muted">Workers</p>
          </div>
          <p className="mt-2 font-mono tabular-nums text-3xl font-bold text-primary">
            {coverageSummary?.totals.runtime.failed_or_stuck ?? "-"}
          </p>
          <p className="mt-1 text-xs text-muted">falha/travamento</p>
        </article>
      </section>

      <section className="surface-card mt-6 p-4">
        <h2 className="font-display flex items-center gap-2 text-base font-semibold text-primary">
          <DatabaseZap className="h-4 w-4 text-accent" />
          Checklist tecnico
        </h2>

        {loading ? (
          <div className="mt-3 h-24 animate-pulse rounded-lg bg-surface-subtle" />
        ) : (
          <div className="mt-3 space-y-2">
            {checks.map((check) => (
              <article key={check.id} className="rounded-lg border border-border p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold text-primary">{check.name}</p>
                    <p className="text-xs text-muted">{check.endpoint}</p>
                  </div>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${checkBadge(check.status)}`}>
                    {check.status}
                  </span>
                </div>
                <p className="mt-2 text-sm text-secondary">{check.detail}</p>
              </article>
            ))}
          </div>
        )}
      </section>

      {overallTone !== "healthy" && (
        <section className="mt-6 rounded-[10px] border border-amber/20 bg-amber-subtle p-4 text-sm">
          <p className="font-display font-semibold text-primary">Acoes recomendadas</p>
          <ul className="mt-2 list-disc space-y-1 pl-4 text-secondary">
            <li>Verifique se os containers `api`, `worker` e `beat` estao ativos.</li>
            <li>Valide conexao com Redis/Postgres e logs de inicializacao.</li>
            <li>Reexecute a verificacao apos estabilizar os servicos.</li>
          </ul>
        </section>
      )}
    </div>
  );
}
