"use client";

import { useMemo } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  Scale,
  FileText,
  BookOpen,
  AlertTriangle,
  CheckCircle2,
  ArrowLeft,
  Home,
  ChevronRight,
  Shield,
  BarChart3,
} from "lucide-react";
import { useDossieBook } from "@/components/dossie/DossieBookContext";
import type { LegalHypothesisDTO, TimelineSignalDTO } from "@/lib/types";
import { cn } from "@/lib/utils";

const SEV = {
  critical: {
    label: "Critico",
    bg: "bg-severity-critical-bg",
    text: "text-severity-critical",
    border: "border-severity-critical/30",
    dot: "bg-severity-critical",
  },
  high: {
    label: "Alto",
    bg: "bg-severity-high-bg",
    text: "text-severity-high",
    border: "border-severity-high/30",
    dot: "bg-severity-high",
  },
  medium: {
    label: "Medio",
    bg: "bg-severity-medium-bg",
    text: "text-severity-medium",
    border: "border-severity-medium/30",
    dot: "bg-severity-medium",
  },
  low: {
    label: "Baixo",
    bg: "bg-severity-low-bg",
    text: "text-severity-low",
    border: "border-severity-low/30",
    dot: "bg-severity-low",
  },
} as const;

const VIOLATION_LABELS: Record<string, string> = {
  fraude_licitatoria: "Fraude Licitatoria",
  corrupcao_passiva: "Corrupcao Passiva",
  corrupcao_ativa: "Corrupcao Ativa",
  lavagem: "Lavagem de Dinheiro",
  peculato: "Peculato",
  nepotismo_clientelismo: "Nepotismo / Clientelismo",
};

const TYPOLOGY_NAMES: Record<string, string> = {
  T01: "Concentracao de Contratos",
  T02: "Baixa Competicao",
  T03: "Fracionamento de Despesas",
  T04: "Aditivo Outlier",
  T05: "Preco Outlier",
  T06: "Empresa de Fachada",
  T07: "Rede de Cartel",
  T08: "Sancao vs Contrato",
  T09: "Folha Fantasma",
  T10: "Terceirizacao Irregular",
  T11: "Jogo de Planilha",
  T12: "Edital Direcionado",
  T13: "Conflito de Interesse",
  T14: "Favorecimento Composto",
  T15: "Inexigibilidade Indevida",
  T16: "Clientelismo Orcamentario",
  T17: "Lavagem Societaria",
  T18: "Acumulo de Cargos",
  T19: "Rodizio de Vencedores",
  T20: "Licitante Fantasma",
  T21: "Cluster Colusivo",
  T22: "Favorecimento Politico",
};

/** Build a human-readable legal rationale for a hypothesis based on the signals in this case. */
function buildRationale(
  lh: LegalHypothesisDTO,
  signalsByTypology: Map<string, TimelineSignalDTO[]>,
  entityNames: string[],
): string {
  const cluster = lh.signal_cluster ?? [];
  const parts: string[] = [];

  // Opening: what article and why
  parts.push(
    `A hipotese de enquadramento no ${lh.law} (${lh.article}) decorre da convergencia de evidencias detectadas neste dossie.`,
  );

  // Detail per typology in the signal_cluster
  if (cluster.length > 0) {
    parts.push(
      `Os seguintes padroes de risco fundamentam esta hipotese:`,
    );

    for (const code of cluster) {
      const typName = TYPOLOGY_NAMES[code] ?? code;
      const signals = signalsByTypology.get(code) ?? [];

      if (signals.length === 0) {
        parts.push(`- ${code} (${typName}): tipologia ativa no caso.`);
        continue;
      }

      const totalEvents = signals.reduce((sum, s) => sum + s.event_count, 0);
      const totalEntities = signals.reduce((sum, s) => sum + s.entity_count, 0);
      const maxConf = Math.max(...signals.map((s) => s.confidence));

      let detail = `- ${code} (${typName}): ${signals.length} sinal(is) detectado(s)`;
      detail += `, envolvendo ${totalEntities} entidade(s) e ${totalEvents} evento(s)`;
      detail += ` (confianca maxima: ${(maxConf * 100).toFixed(0)}%).`;

      // Add the most relevant signal's title
      const best = signals.reduce((a, b) =>
        b.confidence > a.confidence ? b : a,
      );
      if (best.title) {
        detail += ` Principal achado: "${best.title}".`;
      }

      parts.push(detail);
    }
  }

  // Entities involved
  if (entityNames.length > 0) {
    const namesStr =
      entityNames.length <= 3
        ? entityNames.join(", ")
        : entityNames.slice(0, 3).join(", ") +
          ` e mais ${entityNames.length - 3}`;
    parts.push(
      `Entidades envolvidas: ${namesStr}.`,
    );
  }

  // Violation type rationale
  const violLabel = VIOLATION_LABELS[lh.violation_type] ?? lh.violation_type;
  parts.push(
    `O conjunto de evidencias configura indicios de ${violLabel.toLowerCase()}, conforme tipificado no ${lh.article} da ${lh.law}.`,
  );

  return parts.join("\n\n");
}

export default function DossieJuridicoPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const { data, loading, error } = useDossieBook();

  // Build signal lookup by typology code
  const signalsByTypology = useMemo(() => {
    if (!data) return new Map<string, TimelineSignalDTO[]>();
    const map = new Map<string, TimelineSignalDTO[]>();
    for (const sig of data.signals) {
      if (!sig.typology_code) continue;
      const list = map.get(sig.typology_code);
      if (list) list.push(sig);
      else map.set(sig.typology_code, [sig]);
    }
    return map;
  }, [data]);

  const entityNames = useMemo(
    () => (data?.entities ?? []).map((e) => e.name),
    [data],
  );

  // ── Loading ───────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-screen bg-surface-base">
        <div className="h-20 animate-pulse border-b border-border bg-surface-card" />
        <div className="mx-auto max-w-6xl px-6 py-10 space-y-4">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="h-32 rounded-xl border border-border bg-surface-card animate-pulse"
            />
          ))}
        </div>
      </div>
    );
  }

  // ── Error ─────────────────────────────────────────────────────────────────────
  if (error || !data) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center">
        <div className="text-center">
          <p className="text-sm text-error">
            {error ?? "Erro ao carregar dados do caso."}
          </p>
          <Link
            href={`/radar/dossie/${caseId}`}
            className="mt-3 inline-block text-sm text-accent hover:underline"
          >
            Voltar ao dossie
          </Link>
        </div>
      </div>
    );
  }

  const sevData =
    SEV[data.case.severity as keyof typeof SEV] ?? SEV.low;
  const hypotheses = data.legal_hypotheses;
  const uniqueLaws = new Set(hypotheses.map((h) => h.law)).size;
  const activeTypologies = new Set(
    data.signals.map((s) => s.typology_code).filter(Boolean),
  ).size;

  // Build a set of typology codes for chapter link support
  const typologyCodes = new Set(
    data.signals.map((s) => s.typology_code).filter(Boolean),
  );

  function findChapterHref(
    signalCluster: string[],
    violationType: string,
  ): string | null {
    // Try signal cluster codes first
    for (const code of signalCluster) {
      if (typologyCodes.has(code)) {
        return `/radar/dossie/${caseId}/capitulo/${code}`;
      }
    }
    // Fallback: match from violation_type
    const match = violationType.match(/\bT\d{2}\b/);
    if (match && typologyCodes.has(match[0])) {
      return `/radar/dossie/${caseId}/capitulo/${match[0]}`;
    }
    return null;
  }

  return (
    <div className="min-h-screen bg-surface-base">

      {/* ── Hero Banner ──────────────────────────────────────────────────────── */}
      <div className={cn("border-b", sevData.bg, sevData.border)}>
        <div className="mx-auto max-w-6xl px-6 py-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                "flex items-center gap-2 rounded-full border px-3 py-1 font-mono text-xs font-bold",
                sevData.border,
                sevData.text,
              )}
            >
              <span className={cn("h-2 w-2 rounded-full", sevData.dot)} />
              Hipoteses Juridicas — {data.case.id}
            </div>
            <span
              className={cn(
                "rounded-full border px-2.5 py-0.5 font-mono text-[10px] font-bold uppercase",
                sevData.border,
                sevData.text,
              )}
            >
              {sevData.label}
            </span>
          </div>
          <Scale className={cn("h-4 w-4 opacity-60", sevData.text)} />
        </div>
      </div>

      {/* ── Stats Grid ───────────────────────────────────────────────────────── */}
      <div className="border-b border-border bg-surface-card">
        <div className="mx-auto max-w-6xl px-6 py-6">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              { label: "Total Hipoteses", val: hypotheses.length, color: "#a78bfa" },
              { label: "Leis Referenciadas", val: uniqueLaws, color: "#34D399" },
              { label: "Tipologias Ativas", val: activeTypologies, color: "#FB923C" },
              { label: "Sinais no Caso", val: data.signals.length, color: "#60A5FA" },
            ].map(({ label, val, color }) => (
              <div
                key={label}
                className="rounded-xl border border-border bg-surface-subtle p-4"
              >
                <p className="font-mono text-xs text-muted mb-1">{label}</p>
                <p
                  className="font-mono text-2xl font-black tabular-nums"
                  style={{ color }}
                >
                  {val}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-6 py-10 space-y-10">

        {/* ── Hypothesis Cards ───────────────────────────────────────────────── */}
        <section>
          <div className="mb-4 flex items-center gap-2">
            <Scale className="h-4 w-4 text-accent" />
            <h2 className="font-mono text-xs font-bold uppercase tracking-widest text-accent">
              Hipoteses Juridicas
            </h2>
          </div>

          {hypotheses.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border bg-surface-card p-12 text-center">
              <BookOpen className="h-8 w-8 text-muted mx-auto mb-3 opacity-40" />
              <p className="text-sm font-medium text-secondary">
                Nenhuma hipotese juridica identificada neste caso.
              </p>
              <p className="mt-1 text-xs text-muted">
                Hipoteses sao geradas automaticamente a partir dos sinais de risco detectados.
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {hypotheses.map((lh, i) => {
                const cluster = lh.signal_cluster ?? [];
                const chapterHref = findChapterHref(cluster, lh.violation_type);
                const confidence = lh.confidence ?? 0;
                const violLabel = VIOLATION_LABELS[lh.violation_type] ?? lh.violation_type?.replace(/_/g, " ");
                const rationale = buildRationale(lh, signalsByTypology, entityNames);

                // Gather related signals from the cluster
                const relatedSignals = cluster.flatMap(
                  (code) => signalsByTypology.get(code) ?? [],
                );

                return (
                  <div
                    key={i}
                    className="rounded-xl border border-border bg-surface-card overflow-hidden"
                  >
                    {/* Header */}
                    <div className="border-b border-border bg-accent/5 px-6 py-4">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <Scale className="h-4 w-4 text-accent shrink-0" />
                            <span className="font-mono text-sm font-bold text-accent">
                              {lh.law} — {lh.article}
                            </span>
                          </div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="inline-flex items-center rounded-full border border-accent/30 bg-accent/10 px-2.5 py-0.5 font-mono text-xs font-bold text-accent">
                              {violLabel}
                            </span>
                            {cluster.map((code) => (
                              <span
                                key={code}
                                className="inline-flex items-center rounded-full border border-border bg-surface-subtle px-2 py-0.5 font-mono text-[10px] font-bold text-secondary"
                              >
                                {code}
                              </span>
                            ))}
                          </div>
                        </div>
                        {confidence > 0 && (
                          <div className="flex items-center gap-1.5 shrink-0">
                            <BarChart3 className="h-3.5 w-3.5 text-muted" />
                            <div className="text-right">
                              <p className="font-mono text-lg font-black tabular-nums text-primary">
                                {(confidence * 100).toFixed(0)}%
                              </p>
                              <p className="font-mono text-[9px] text-muted">confianca</p>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Rationale */}
                    <div className="px-6 py-5">
                      <div className="mb-3 flex items-center gap-2">
                        <Shield className="h-3.5 w-3.5 text-accent" />
                        <h3 className="font-mono text-[10px] font-bold uppercase tracking-widest text-accent">
                          Fundamentacao
                        </h3>
                      </div>
                      <div className="space-y-3 text-sm leading-relaxed text-secondary">
                        {rationale.split("\n\n").map((paragraph, pi) => (
                          <p key={pi} className={paragraph.startsWith("- ") ? "pl-4 text-[13px]" : ""}>
                            {paragraph}
                          </p>
                        ))}
                      </div>
                    </div>

                    {/* Related signals */}
                    {relatedSignals.length > 0 && (
                      <div className="border-t border-border px-6 py-4 bg-surface-subtle/50">
                        <p className="mb-2 font-mono text-[10px] font-bold uppercase tracking-widest text-muted">
                          Sinais Fundamentadores
                        </p>
                        <div className="space-y-2">
                          {relatedSignals.slice(0, 5).map((sig) => (
                            <Link
                              key={sig.id}
                              href={`/radar/dossie/${caseId}/sinal/${sig.id}`}
                              className="flex items-center gap-3 rounded-lg border border-border bg-surface-card px-3 py-2 transition-colors hover:border-accent/40"
                            >
                              <span
                                className={cn(
                                  "h-2 w-2 rounded-full shrink-0",
                                  sig.severity === "critical"
                                    ? "bg-severity-critical"
                                    : sig.severity === "high"
                                      ? "bg-severity-high"
                                      : sig.severity === "medium"
                                        ? "bg-severity-medium"
                                        : "bg-severity-low",
                                )}
                              />
                              <div className="min-w-0 flex-1">
                                <p className="text-xs font-medium text-primary truncate">
                                  {sig.title}
                                </p>
                                <p className="font-mono text-[10px] text-muted">
                                  {sig.typology_code} · {sig.entity_count} entidades · {sig.event_count} eventos · {(sig.confidence * 100).toFixed(0)}% confianca
                                </p>
                              </div>
                              <ChevronRight className="h-3 w-3 text-muted shrink-0" />
                            </Link>
                          ))}
                          {relatedSignals.length > 5 && (
                            <p className="font-mono text-[10px] text-muted pl-1">
                              + {relatedSignals.length - 5} sinais adicionais
                            </p>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Chapter link */}
                    {chapterHref && (
                      <div className="border-t border-border px-6 py-3">
                        <Link
                          href={chapterHref}
                          className="inline-flex items-center gap-1.5 font-mono text-[10px] text-accent hover:underline"
                        >
                          <BookOpen className="h-3 w-3" />
                          Ver capitulo correspondente →
                        </Link>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* ── Legal Disclaimer ─────────────────────────────────────────────── */}
        <section>
          <div className="rounded-xl border border-border bg-surface-base p-5">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-muted" />
              <div className="space-y-2 text-xs leading-relaxed text-muted">
                <p>
                  <strong className="font-semibold text-secondary">
                    Aviso legal:
                  </strong>{" "}
                  As hipoteses juridicas apresentadas sao inferencias automaticas
                  baseadas em cruzamento de dados publicos e{" "}
                  <strong className="font-medium text-secondary">
                    nao constituem acusacao, imputacao criminal ou juizo definitivo
                    de culpa
                  </strong>
                  .
                </p>
                <p>
                  A analise e de natureza estatistica e deterministica, devendo
                  ser complementada por investigacao documental, contraditorio e
                  avaliacao juridica especializada antes de qualquer uso formal.
                </p>
                <p>
                  Todos os dados provem de fontes publicas oficiais do governo
                  federal brasileiro. OpenWatch e um instrumento de triagem
                  para controle social cidadao.
                </p>
              </div>
            </div>
            <div className="mt-4 flex items-center gap-2 border-t border-border pt-3">
              <FileText className="h-3 w-3 text-muted" />
              <p className="font-mono text-[10px] text-muted">
                Legislacao de referencia: Lei 8.666/93, Lei 14.133/21, Lei 8.429/92, Lei 12.846/13, Lei 9.613/98, Lei 12.529/11
              </p>
            </div>
          </div>
        </section>

        {/* ── End of Dossie Banner ─────────────────────────────────────────── */}
        <section>
          <div className="rounded-2xl border-2 border-dashed border-accent/30 bg-accent/5 p-8 text-center">
            <CheckCircle2 className="h-10 w-10 text-accent mx-auto mb-4 opacity-80" />
            <h3 className="text-lg font-bold text-primary mb-2">
              Fim do Dossie
            </h3>
            <p className="text-sm text-secondary mb-6 max-w-md mx-auto">
              Voce revisou todas as paginas deste dossie: visao geral, capitulos de tipologia,
              sinais de risco, rede de conexoes e hipoteses juridicas.
            </p>
            <div className="flex items-center justify-center gap-3">
              <Link
                href={`/radar/dossie/${caseId}`}
                className="inline-flex items-center gap-2 rounded-lg border border-accent/30 bg-accent/10 px-4 py-2.5 font-mono text-xs font-bold text-accent transition-colors hover:bg-accent/20"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                Inicio do Dossie
              </Link>
              <Link
                href="/radar"
                className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface-card px-4 py-2.5 font-mono text-xs font-bold text-secondary transition-colors hover:bg-surface-subtle"
              >
                <Home className="h-3.5 w-3.5" />
                Painel Radar
              </Link>
            </div>
          </div>
        </section>

      </div>
    </div>
  );
}
