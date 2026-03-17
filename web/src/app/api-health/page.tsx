"use client";

import { useEffect, useMemo, useState } from "react";
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
  Clock,
  ShieldCheck,
  Circle,
} from "lucide-react";

type HealthTone = "healthy" | "attention" | "blocked";
type CheckStatus = "ok" | "attention" | "error";

interface ServiceCheck {
  id: string;
  name: string;
  endpoint: string;
  status: CheckStatus;
  detail: string;
  icon: typeof Activity;
}

function overallFromChecks(checks: ServiceCheck[]): HealthTone {
  if (checks.some((c) => c.status === "error")) return "blocked";
  if (checks.some((c) => c.status === "attention")) return "attention";
  return "healthy";
}

const TONE_CONFIG: Record<HealthTone, { label: string; cls: string; Icon: typeof CheckCircle2; dot: string }> = {
  healthy: { label: "Operacional", cls: "text-success", Icon: CheckCircle2, dot: "bg-success" },
  attention: { label: "Atenção", cls: "text-amber", Icon: AlertTriangle, dot: "bg-amber" },
  blocked: { label: "Bloqueado", cls: "text-error", Icon: ServerCrash, dot: "bg-error" },
};

const STATUS_CONFIG: Record<CheckStatus, { label: string; dot: string; text: string }> = {
  ok: { label: "ok", dot: "bg-success", text: "text-success" },
  attention: { label: "atenção", dot: "bg-amber", text: "text-amber" },
  error: { label: "erro", dot: "bg-error", text: "text-error" },
};

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

  useEffect(() => { void loadHealth(); }, []);

  const checks = useMemo<ServiceCheck[]>(() => [
    {
      id: "api",
      name: "Container API",
      endpoint: "/health",
      icon: Activity,
      status: heartbeatOk ? "ok" : "error",
      detail: heartbeatOk
        ? "API respondendo normalmente."
        : heartbeatError ?? "API sem resposta no heartbeat.",
    },
    {
      id: "pipeline",
      name: "Pipeline de dados",
      endpoint: "/public/coverage/v2/summary",
      icon: Workflow,
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
          ? coverageError ?? "Sem dados operacionais do pipeline."
          : `Estado atual: ${coverageSummary.pipeline.overall_status}.`,
    },
    {
      id: "workers",
      name: "Workers de processamento",
      endpoint: "/public/coverage/v2/summary",
      icon: Cpu,
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
    },
  ], [heartbeatOk, heartbeatError, coverageSummary, coverageError]);

  const tone = overallFromChecks(checks);
  const toneConfig = TONE_CONFIG[tone];
  const ToneIcon = toneConfig.Icon;

  return (
    <div className="min-h-screen">

      {/* ── Page Header ────────────────────────────────────────── */}
      <div className="border-b border-border bg-surface-card">
        <div className="mx-auto max-w-[1280px] px-4 py-8 sm:px-6">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-start gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-accent-subtle border border-accent/20">
                <ShieldCheck className="h-6 w-6 text-accent" />
              </div>
              <div>
                <h1 className="font-display text-2xl font-bold tracking-tight text-primary sm:text-3xl">Saúde da Plataforma</h1>
                <p className="mt-1.5 text-sm text-secondary leading-relaxed">Monitor de disponibilidade técnica dos serviços essenciais</p>
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-3">
              {!loading && (
                <div className={`flex items-center gap-1.5 text-sm font-semibold ${toneConfig.cls}`}>
                  <ToneIcon className="h-4 w-4" />
                  {toneConfig.label}
                </div>
              )}
              <Button
                variant="secondary"
                size="sm"
                onClick={() => void loadHealth()}
                disabled={refreshing}
                loading={refreshing}
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Atualizar
              </Button>
            </div>
          </div>

          {/* Last checked */}
          <div className="mt-3">
            <div className="rounded-lg border border-border bg-surface-base px-3 py-2 inline-flex flex-col">
              <p className="flex items-center gap-1 font-mono text-[10px] font-semibold uppercase tracking-wide text-muted">
                <Clock className="h-3 w-3" />
                Última verificação
              </p>
              <p className="mt-0.5 font-mono tabular-nums text-xs font-medium text-primary">
                {checkedAt ? new Date(checkedAt).toLocaleString("pt-BR") : "Aguardando…"}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-[1280px] px-4 py-8 sm:px-6 space-y-6">

        {/* ── Status board ─────────────────────────────────────── */}
        <section>
          <p className="mb-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-muted">
            Status dos Serviços
          </p>
          <div className="rounded-xl border border-border bg-surface-card overflow-hidden">
            {loading ? (
              <div className="space-y-px">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="flex items-center gap-4 px-5 py-4 border-b border-border last:border-0">
                    <div className="h-2 w-2 rounded-full bg-surface-subtle animate-pulse" />
                    <div className="flex-1 space-y-1.5">
                      <div className="h-3 w-40 rounded bg-surface-subtle animate-pulse" />
                      <div className="h-2.5 w-64 rounded bg-surface-subtle animate-pulse" />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div>
                {checks.map((check, i) => {
                  const st = STATUS_CONFIG[check.status];
                  const CheckIcon = check.icon;
                  return (
                    <div
                      key={check.id}
                      className={`flex items-start gap-4 px-5 py-4 ${i < checks.length - 1 ? "border-b border-border" : ""}`}
                    >
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-surface-base border border-border mt-0.5">
                        <CheckIcon className="h-4 w-4 text-muted" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-primary">{check.name}</span>
                          <span className="font-mono text-[10px] text-muted">{check.endpoint}</span>
                        </div>
                        <p className="mt-0.5 text-xs text-secondary">{check.detail}</p>
                      </div>
                      <div className="flex shrink-0 items-center gap-1.5">
                        <span className={`h-2 w-2 rounded-full ${st.dot}`} />
                        <span className={`font-mono text-xs font-semibold ${st.text}`}>{st.label}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </section>

        {/* ── Metric summary ────────────────────────────────────── */}
        {!loading && coverageSummary && (
          <section>
            <p className="mb-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-muted">
              Métricas Operacionais
            </p>
            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-lg border border-border bg-surface-card p-4 text-center">
                <p className="font-mono tabular-nums text-2xl font-bold text-primary">
                  {heartbeatOk ? "OK" : "—"}
                </p>
                <p className="mt-1 text-[11px] text-muted">API Container</p>
              </div>
              <div className="rounded-lg border border-border bg-surface-card p-4 text-center">
                <p className="font-mono tabular-nums text-2xl font-bold text-primary">
                  {coverageSummary.pipeline.overall_status}
                </p>
                <p className="mt-1 text-[11px] text-muted">Pipeline</p>
              </div>
              <div className="rounded-lg border border-border bg-surface-card p-4 text-center">
                <p className="font-mono tabular-nums text-2xl font-bold text-primary">
                  {coverageSummary.totals.runtime.failed_or_stuck}
                </p>
                <p className="mt-1 text-[11px] text-muted">Falhas/Travamentos</p>
              </div>
            </div>
          </section>
        )}

        {/* ── Recommendations ───────────────────────────────────── */}
        {!loading && tone !== "healthy" && (
          <section className="rounded-xl border border-amber/30 bg-amber-subtle/60 p-5">
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle className="h-4 w-4 text-amber" />
              <h2 className="font-display text-sm font-semibold text-primary">Ações recomendadas</h2>
            </div>
            <ul className="space-y-2">
              {[
                "Verifique se os containers `api`, `worker` e `beat` estão ativos.",
                "Valide a conexão com Redis/Postgres e logs de inicialização.",
                "Reexecute a verificação após estabilizar os serviços.",
              ].map((item) => (
                <li key={item} className="flex items-start gap-2 text-xs text-secondary">
                  <Circle className="mt-1 h-1.5 w-1.5 shrink-0 fill-current text-muted" />
                  {item}
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* ── Services legend ───────────────────────────────────── */}
        <section className="rounded-xl border border-border bg-surface-base p-4">
          <div className="flex items-center gap-2 mb-3">
            <DatabaseZap className="h-4 w-4 text-muted" />
            <h2 className="font-display text-xs font-semibold uppercase tracking-wide text-muted">
              O que é monitorado
            </h2>
          </div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3 text-xs text-secondary">
            <div>
              <p className="font-semibold text-primary mb-0.5">API Container</p>
              <p className="text-muted">Heartbeat HTTP via <code className="font-mono">/health</code>. Confirma que o servidor FastAPI está respondendo.</p>
            </div>
            <div>
              <p className="font-semibold text-primary mb-0.5">Pipeline de Dados</p>
              <p className="text-muted">Estado geral do pipeline de ingestão — fontes ativas, jobs habilitados e execuções recentes.</p>
            </div>
            <div>
              <p className="font-semibold text-primary mb-0.5">Workers</p>
              <p className="text-muted">Celery workers responsáveis pelo processamento assíncrono. Travamentos indicam necessidade de restart.</p>
            </div>
          </div>
        </section>

      </div>
    </div>
  );
}
