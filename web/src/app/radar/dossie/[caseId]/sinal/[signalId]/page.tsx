"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import type { ElementType } from "react";
import {
  ArrowLeft, AlertTriangle, Building2, User, Database,
  FileText, ChevronLeft, ChevronRight, Hash, TrendingUp,
  Calendar, GitBranch,
} from "lucide-react";
import { useDossieBook } from "@/components/dossie/DossieBookContext";
import { getSignalEvidence, getSignalProvenance } from "@/lib/api";
import type {
  TimelineEntityDTO,
  TimelineSignalDTO,
  SignalEvidencePage,
  SignalProvenanceResponse,
} from "@/lib/types";
import { cn, formatBRL, formatDate, normalizeUnknownDisplay, severityNumeric } from "@/lib/utils";
import { ScoreBar } from "@/components/ScoreBar";

const EVIDENCE_PAGE_SIZE = 10;

// ── Config ───────────────────────────────────────────────────────────────────

const SEV = {
  critical: { label: "Crítico", bg: "bg-severity-critical-bg", text: "text-severity-critical", border: "border-severity-critical/30", dot: "bg-severity-critical" },
  high:     { label: "Alto",    bg: "bg-severity-high-bg",     text: "text-severity-high",     border: "border-severity-high/30",     dot: "bg-severity-high"     },
  medium:   { label: "Médio",   bg: "bg-severity-medium-bg",   text: "text-severity-medium",   border: "border-severity-medium/30",   dot: "bg-severity-medium"   },
  low:      { label: "Baixo",   bg: "bg-severity-low-bg",      text: "text-severity-low",      border: "border-severity-low/30",      dot: "bg-severity-low"      },
} as const;

type SevKey = keyof typeof SEV;
function getSev(sv: string) { return SEV[(sv as SevKey) in SEV ? (sv as SevKey) : "low"]; }

const ENTITY_COL: Record<string, string>    = { org: "#a78bfa", company: "#34D399", person: "#60A5FA" };
const ENTITY_LABEL_MAP: Record<string, string> = { org: "Órgão Público", company: "Empresa", person: "Pessoa Física" };

function initials(name: string) {
  const p = name.trim().split(/\s+/);
  return ((p[0]?.[0] ?? "") + (p.length > 1 ? (p[p.length - 1]?.[0] ?? "") : "")).toUpperCase();
}

function confidenceColor(pct: number) {
  if (pct >= 80) return "bg-success";
  if (pct >= 50) return "bg-amber";
  return "bg-error";
}

// ── Entity card ──────────────────────────────────────────────────────────────

function EntityCard({ entity, caseId }: { entity: TimelineEntityDTO; caseId: string }) {
  const col = ENTITY_COL[entity.type] ?? "#a78bfa";
  const photoUrl = typeof entity.attrs.photo_url === "string" ? entity.attrs.photo_url : null;
  const cnpj = entity.identifiers.cnpj;
  const cpf  = entity.identifiers.cpf;

  return (
    <Link href={`/radar/dossie/${caseId}/rede`} className="block">
      <div className="rounded-xl border border-border bg-surface-card p-4 hover:border-accent/40 transition-colors">
        <div className="mb-2 flex items-center gap-3">
          {photoUrl ? (
            <img src={photoUrl} alt={entity.name} className="h-9 w-9 shrink-0 rounded-xl object-cover" />
          ) : (
            <div
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-sm font-bold text-white"
              style={{ backgroundColor: col }}
            >
              {initials(entity.name)}
            </div>
          )}
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-primary">{entity.name}</p>
            <span className="font-mono text-[9px] font-bold uppercase" style={{ color: col }}>
              {ENTITY_LABEL_MAP[entity.type] ?? entity.type}
            </span>
          </div>
        </div>
        {cnpj && <p className="font-mono text-[10px] text-muted">CNPJ {cnpj}</p>}
        {cpf  && <p className="font-mono text-[10px] text-muted">CPF {cpf}</p>}
      </div>
    </Link>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function SinalPage() {
  const { caseId, signalId } = useParams<{ caseId: string; signalId: string }>();
  const { data, loading: ctxLoading, error: ctxError } = useDossieBook();

  const [evidence, setEvidence] = useState<SignalEvidencePage | null>(null);
  const [evidencePage, setEvidencePage] = useState(1);
  const [evidenceLoading, setEvidenceLoading] = useState(false);
  const [provenance, setProvenance] = useState<SignalProvenanceResponse | null>(null);
  const [apiLoading, setApiLoading] = useState(true);

  const loadEvidencePage = useCallback(
    (page: number) => {
      setEvidenceLoading(true);
      getSignalEvidence(signalId, {
        offset: (page - 1) * EVIDENCE_PAGE_SIZE,
        limit: EVIDENCE_PAGE_SIZE,
      })
        .then((ev) => { setEvidence(ev); setEvidencePage(page); })
        .finally(() => setEvidenceLoading(false));
    },
    [signalId],
  );

  useEffect(() => {
    setApiLoading(true);
    Promise.all([
      getSignalEvidence(signalId, { offset: 0, limit: EVIDENCE_PAGE_SIZE }).catch(() => null),
      getSignalProvenance(signalId).catch(() => null),
    ])
      .then(([ev, prov]) => { setEvidence(ev); setProvenance(prov); })
      .finally(() => setApiLoading(false));
  }, [signalId]);

  // ── Loading ─────────────────────────────────────────────────────────────
  if (ctxLoading || apiLoading) {
    return (
      <div className="min-h-screen bg-surface-base">
        <div className="mx-auto max-w-6xl px-6 py-8 space-y-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-32 rounded-2xl border border-border bg-surface-card animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  // ── Error ───────────────────────────────────────────────────────────────
  if (ctxError || !data) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center p-6">
        <div className="rounded-2xl border border-severity-critical/30 bg-severity-critical-bg p-8 text-center max-w-md">
          <AlertTriangle className="h-8 w-8 text-severity-critical mx-auto mb-3" />
          <p className="text-sm text-severity-critical mb-4">{ctxError ?? "Dossiê não encontrado."}</p>
          <Link href={`/radar/dossie/${caseId}`} className="text-xs text-accent hover:underline">
            Voltar ao dossiê
          </Link>
        </div>
      </div>
    );
  }

  const signal: TimelineSignalDTO | undefined = data.signals.find((s) => s.id === signalId);

  if (!signal) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center p-6">
        <div className="rounded-2xl border border-border bg-surface-card p-8 text-center">
          <p className="text-sm text-muted mb-4">Sinal não encontrado.</p>
          <Link href={`/radar/dossie/${caseId}`} className="text-xs text-accent hover:underline">
            Voltar ao dossiê
          </Link>
        </div>
      </div>
    );
  }

  const s = getSev(signal.severity);
  const isPulsing = signal.severity === "critical" || signal.severity === "high";
  const pct = Math.round(signal.confidence * 100);
  const pctColor = confidenceColor(pct);

  // Entities from events that reference this signal
  const entityMap = new Map(data.entities.map((e) => [e.id, e]));
  const signalEntityIds = new Set<string>();
  for (const evt of data.events) {
    if (evt.signals.some((es) => es.id === signalId)) {
      for (const p of evt.participants) signalEntityIds.add(p.entity_id);
    }
  }
  const signalEntities = [...signalEntityIds]
    .map((id) => entityMap.get(id))
    .filter((e): e is TimelineEntityDTO => e != null);

  const evidenceTotal = evidence?.total ?? 0;
  const totalPages = Math.ceil(evidenceTotal / EVIDENCE_PAGE_SIZE);

  return (
    <div className="min-h-screen bg-surface-base">

      {/* Hero banner */}
      <div className={cn("border-b", s.bg, s.border)}>
        <div className="mx-auto max-w-6xl px-6 py-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              href={`/radar/dossie/${caseId}/capitulo/${signal.typology_code}`}
              className={cn("transition-opacity hover:opacity-70", s.text)}
            >
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <div className={cn("flex items-center gap-2 rounded-full border px-3 py-1 font-mono text-xs font-bold", s.border, s.text)}>
              <span className={cn("h-2 w-2 rounded-full", s.dot, isPulsing && "animate-pulse")} />
              {s.label} — {signal.typology_code}
            </div>
          </div>
          <span className="hidden font-mono text-[10px] uppercase tracking-widest opacity-50 sm:block">
            {signal.typology_name}
          </span>
        </div>
      </div>

      {/* Signal header */}
      <div className="border-b border-border bg-surface-card">
        <div className="mx-auto max-w-6xl px-6 py-8">
          <h1 className="font-display text-2xl font-black text-primary mb-1">{signal.title}</h1>
          {signal.summary && (
            <p className="text-secondary leading-relaxed max-w-3xl mb-6">{signal.summary}</p>
          )}

          {/* Stats grid — 5 cols */}
          <div className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-5">
            {[
              { Icon: TrendingUp, label: "Confiança",   val: `${pct}%` },
              { Icon: User,       label: "Entidades",   val: String(signalEntities.length || signal.entity_count) },
              { Icon: Hash,       label: "Eventos",     val: String(signal.event_count) },
              { Icon: Database,   label: "Evidências",  val: evidenceTotal > 0 ? String(evidenceTotal) : "—" },
              {
                Icon: Calendar,
                label: "Período",
                val: signal.period_start ? formatDate(signal.period_start) : "—",
              },
            ].map(({ Icon, label, val }) => (
              <div key={label} className="rounded-xl border border-border bg-surface-subtle p-4">
                <Icon className="h-4 w-4 text-muted mb-2" />
                <p className="font-mono text-xs text-muted mb-0.5">{label}</p>
                <p className="font-mono font-bold text-primary tabular-nums">{val}</p>
              </div>
            ))}
          </div>

          {/* Score bars */}
          <div className="mt-4 max-w-xs space-y-3">
            <ScoreBar
              label="Gravidade"
              value={severityNumeric(signal.severity)}
              color="red"
            />
            <ScoreBar
              label="Confiança dos dados"
              value={signal.signal_confidence_score ?? 100}
              color="blue"
            />
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="mx-auto max-w-6xl px-6 py-10 space-y-10">

        {/* Fatores de Detecção */}
        {signal.factor_descriptions && Object.keys(signal.factor_descriptions).length > 0 && (
          <section>
            <div className="mb-4 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-accent" />
              <h2 className="font-mono text-xs font-bold uppercase tracking-widest text-accent">
                Fatores de Detecção
              </h2>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {Object.entries(signal.factor_descriptions).map(([key, meta]) => {
                const raw = signal.factors[key];
                const detected = raw != null ? `${raw}` : "—";
                return (
                  <div key={key} className="rounded-xl border border-border bg-surface-card p-4">
                    <p className="font-semibold text-sm text-primary mb-1">{meta.label}</p>
                    <p className="text-xs text-muted leading-relaxed mb-3">{meta.description}</p>
                    <div className="flex items-baseline gap-1.5">
                      <span className="font-mono text-lg font-black text-primary tabular-nums">
                        {detected}
                      </span>
                      {meta.unit && (
                        <span className="font-mono text-[10px] text-muted">{meta.unit}</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Entidades Envolvidas */}
        {signalEntities.length > 0 && (
          <section>
            <div className="mb-4 flex items-center gap-2">
              <User className="h-4 w-4 text-accent" />
              <h2 className="font-mono text-xs font-bold uppercase tracking-widest text-accent">
                Entidades Envolvidas ({signalEntities.length})
              </h2>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {signalEntities.map((entity) => (
                <EntityCard key={entity.id} entity={entity} caseId={caseId} />
              ))}
            </div>
          </section>
        )}

        {/* Evidências */}
        {evidence && evidenceTotal > 0 && (
          <section>
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Database className="h-4 w-4 text-accent" />
                <h2 className="font-mono text-xs font-bold uppercase tracking-widest text-accent">
                  Evidências ({evidenceTotal})
                </h2>
              </div>
              {evidenceTotal > EVIDENCE_PAGE_SIZE && (
                <span className="font-mono text-xs text-muted">
                  {(evidencePage - 1) * EVIDENCE_PAGE_SIZE + 1}–
                  {Math.min(evidencePage * EVIDENCE_PAGE_SIZE, evidenceTotal)} de {evidenceTotal}
                </span>
              )}
            </div>

            <div className={cn("space-y-3 transition-opacity", evidenceLoading && "opacity-40 pointer-events-none")}>
              {evidence.items.map((item) => (
                <div
                  key={item.event_id}
                  className="rounded-xl border border-border bg-surface-card p-4 space-y-2"
                >
                  <p className="font-mono text-[10px] font-bold uppercase tracking-widest text-amber">
                    {item.evidence_reason}
                  </p>
                  <p className="text-sm font-medium text-primary">{item.description}</p>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-secondary">
                    <span>
                      <span className="text-muted">Data </span>
                      {item.occurred_at ? formatDate(item.occurred_at) : "—"}
                    </span>
                    {typeof item.value_brl === "number" && (
                      <span>
                        <span className="text-muted">Valor </span>
                        <span className="font-semibold text-primary">{formatBRL(item.value_brl)}</span>
                      </span>
                    )}
                    <span>
                      <span className="text-muted">Modalidade </span>
                      {normalizeUnknownDisplay(item.modality)}
                    </span>
                    <span className="font-mono">
                      <span className="text-muted">Fonte </span>
                      {item.source_connector}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            {evidenceTotal > EVIDENCE_PAGE_SIZE && (
              <div className="mt-4 flex items-center justify-between border-t border-border pt-3">
                <button
                  onClick={() => loadEvidencePage(evidencePage - 1)}
                  disabled={evidencePage === 1 || evidenceLoading}
                  className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-secondary transition-colors hover:bg-surface-subtle disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <ChevronLeft className="h-3.5 w-3.5" />Anterior
                </button>
                <span className="font-mono text-xs text-muted">
                  Página {evidencePage} de {totalPages}
                </span>
                <button
                  onClick={() => loadEvidencePage(evidencePage + 1)}
                  disabled={evidencePage >= totalPages || evidenceLoading}
                  className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-secondary transition-colors hover:bg-surface-subtle disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Próxima<ChevronRight className="h-3.5 w-3.5" />
                </button>
              </div>
            )}
          </section>
        )}

        {/* Cadeia de Proveniência */}
        {provenance && provenance.events.length > 0 && (
          <section>
            <div className="mb-4 flex items-center gap-2">
              <GitBranch className="h-4 w-4 text-accent" />
              <h2 className="font-mono text-xs font-bold uppercase tracking-widest text-accent">
                Cadeia de Proveniência
              </h2>
            </div>
            <div className="space-y-3">
              {provenance.events.slice(0, 10).map((ev, idx) => (
                <div key={ev.event_id} className="rounded-xl border border-border bg-surface-card p-4">
                  {/* Visual chain: Event → Connector → Job → Signal */}
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span className="flex items-center gap-1.5 rounded border border-border bg-surface-subtle px-2 py-1 font-mono text-muted">
                      <Hash className="h-3 w-3" />
                      E{idx + 1}
                    </span>
                    {ev.raw_sources.map((rs, ri) => (
                      <div key={rs.id} className="flex items-center gap-2">
                        <span className="text-border">→</span>
                        <span className="rounded border border-accent/30 bg-accent/10 px-2 py-1 font-mono text-xs font-bold text-accent">
                          {rs.connector}
                        </span>
                        <span className="text-border">→</span>
                        <span className="truncate max-w-[160px] rounded border border-border px-2 py-1 font-mono text-[10px] text-muted">
                          {rs.job}
                        </span>
                        {ri === ev.raw_sources.length - 1 && (
                          <>
                            <span className="text-border">→</span>
                            <span className={cn("rounded-full border px-2 py-0.5 font-mono text-[10px] font-bold", s.border, s.text)}>
                              Sinal
                            </span>
                          </>
                        )}
                      </div>
                    ))}
                    {ev.raw_sources.length === 0 && (
                      <span className="font-mono text-[10px] text-muted opacity-60 truncate max-w-[240px]">
                        {ev.event_id}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
