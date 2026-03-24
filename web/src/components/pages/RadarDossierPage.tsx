"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import type { ElementType } from "react";
import {
  ArrowLeft, ShoppingCart, FileText, ShieldOff, ArrowRightLeft,
  Landmark, AlertTriangle, X, Building2, User, Calendar,
  Link2, Hash, DollarSign, Scale, Database, ChevronDown, ChevronUp,
} from "lucide-react";
import { useDossieBook } from "@/components/dossie/DossieBookContext";
import type {
  TimelineEntityDTO,
  TimelineEventDTO,
  TimelineEventSignalDTO,
  TimelineSignalDTO,
} from "@/lib/types";
import { cn, formatBRL, formatDate } from "@/lib/utils";

// ── Config ───────────────────────────────────────────────────────────────────

const EVENT_META: Record<string, { Icon: ElementType; color: string; label: string }> = {
  licitacao:     { Icon: ShoppingCart,   color: "#4A82D4", label: "Licitação"     },
  contrato:      { Icon: FileText,       color: "#8A63E8", label: "Contrato"      },
  sancao:        { Icon: ShieldOff,      color: "#E05050", label: "Sanção"        },
  transferencia: { Icon: ArrowRightLeft, color: "#D46020", label: "Transferência" },
  emenda:        { Icon: Landmark,       color: "#30A060", label: "Emenda"        },
};

const SEV = {
  critical: { label: "Crítico", bg: "bg-severity-critical-bg", text: "text-severity-critical", border: "border-severity-critical/30", dot: "bg-severity-critical"   },
  high:     { label: "Alto",    bg: "bg-severity-high-bg",     text: "text-severity-high",     border: "border-severity-high/30",     dot: "bg-severity-high"      },
  medium:   { label: "Médio",   bg: "bg-severity-medium-bg",   text: "text-severity-medium",   border: "border-severity-medium/30",   dot: "bg-severity-medium"    },
  low:      { label: "Baixo",   bg: "bg-severity-low-bg",      text: "text-severity-low",      border: "border-severity-low/30",      dot: "bg-severity-low"       },
} as const;

type SevKey = keyof typeof SEV;

function getSev(severity: string) {
  return SEV[(severity as SevKey) in SEV ? (severity as SevKey) : "low"];
}

const ENTITY_COL: Record<string, string> = {
  org:     "#3A90A0",
  company: "#4A82D4",
  person:  "#7C6AE0",
};
const ENTITY_ICON: Record<string, ElementType> = { org: Building2, company: Building2, person: User };
const ENTITY_LABEL: Record<string, string> = { org: "Órgão Público", company: "Empresa", person: "Pessoa Física" };

function initials(name: string) {
  const p = name.trim().split(/\s+/);
  return ((p[0]?.[0] ?? "") + (p.length > 1 ? (p[p.length - 1]?.[0] ?? "") : "")).toUpperCase();
}

function confidenceColor(pct: number) {
  if (pct >= 80) return "bg-success";
  if (pct >= 50) return "bg-amber";
  return "bg-error";
}

// ── Signal Modal ─────────────────────────────────────────────────────────────

function SignalModal({
  signal,
  fullSignal,
  caseId,
  onClose,
}: {
  signal: TimelineEventSignalDTO | null;
  fullSignal: TimelineSignalDTO | null;
  caseId: string;
  onClose: () => void;
}) {
  if (!signal) return null;
  const s = getSev(signal.severity);
  const pct = Math.round(signal.confidence * 100);
  const pctColor = confidenceColor(pct);
  const factorDescriptions = fullSignal?.factor_descriptions;
  const evidenceCount = fullSignal?.event_count ?? 0;
  const isPulsing = signal.severity === "critical" || signal.severity === "high";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />
      <div
        className={cn(
          "relative w-full max-w-lg rounded-2xl border p-6 shadow-2xl overflow-y-auto max-h-[90vh]",
          s.bg, s.border, s.text,
        )}
      >
        <button
          onClick={onClose}
          className="absolute right-4 top-4 rounded-lg p-1.5 opacity-50 hover:opacity-100"
        >
          <X className="h-4 w-4" />
        </button>

        {/* Header */}
        <div className="mb-3 flex items-center gap-2">
          <span className={cn("h-2.5 w-2.5 rounded-full", s.dot, isPulsing && "animate-pulse")} />
          <span className="font-mono text-xs font-bold">{signal.typology_code} · {s.label}</span>
        </div>
        <h3 className="font-display text-lg font-bold mb-1">{signal.typology_name}</h3>
        <p className="mb-3 text-sm opacity-85 leading-relaxed">{signal.title}</p>
        <p className="mb-4 font-mono text-xs opacity-60">
          {formatDate(signal.period_start)} — {formatDate(signal.period_end)}
        </p>

        {/* Confidence bar */}
        <div className="mb-4">
          <div className="mb-1.5 flex items-center justify-between">
            <span className="font-mono text-[10px] uppercase tracking-widest opacity-70">Confiança</span>
            <span className="font-mono text-sm font-bold">{pct}%</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-black/20">
            <div className={cn("h-full transition-all", pctColor)} style={{ width: `${pct}%` }} />
          </div>
        </div>

        {/* Factor descriptions */}
        {factorDescriptions && Object.keys(factorDescriptions).length > 0 && (
          <div className="mb-4">
            <p className="mb-2 font-mono text-[10px] uppercase tracking-widest opacity-70">
              Fatores de Detecção
            </p>
            <div className="space-y-2">
              {Object.entries(factorDescriptions).map(([key, meta]) => (
                <div key={key} className="rounded-lg border border-current/20 bg-black/20 p-2.5">
                  <p className="font-semibold text-sm">{meta.label}</p>
                  <p className="mt-0.5 text-xs opacity-70 leading-relaxed">{meta.description}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Evidence count */}
        {evidenceCount > 0 && (
          <div className="mb-4 flex items-center gap-2">
            <Database className="h-3.5 w-3.5 opacity-70" />
            <span className="font-mono text-xs opacity-70">
              {evidenceCount} evidência{evidenceCount !== 1 ? "s" : ""}
            </span>
          </div>
        )}

        {/* Full page link */}
        <Link
          href={`/radar/dossie/${caseId}/sinal/${signal.id}`}
          className="inline-flex items-center gap-1.5 rounded-xl border border-current/30 bg-black/20 px-4 py-2 font-mono text-xs font-bold transition-all hover:bg-black/40"
        >
          Ver página completa →
        </Link>

        <div className="mt-4 rounded-xl border border-current/20 bg-black/30 p-3 text-[11px] opacity-60 leading-relaxed">
          Análise estatística determinística. Requer confirmação documental e contraditório.
        </div>
      </div>
    </div>
  );
}

// ── Matrix table (extracted to keep DRY for mobile/desktop) ──────────────────

function MatrixTable({
  entities,
  events,
  entityMap,
}: {
  entities: TimelineEntityDTO[];
  events: TimelineEventDTO[];
  entityMap: Map<string, TimelineEntityDTO>;
}) {
  return (
    <table className="w-full border-collapse text-xs">
      <thead className="sticky top-0 z-10">
        <tr className="border-b border-border bg-surface-subtle">
          <th className="sticky left-0 z-20 bg-surface-subtle px-4 py-3 text-left font-mono text-[10px] uppercase tracking-widest text-muted min-w-[140px]">
            Ator
          </th>
          {events.map((e, i) => {
            const m = EVENT_META[e.type] ?? { color: "#a78bfa", label: e.type };
            return (
              <th
                key={e.id}
                className="px-3 py-3 text-center font-mono text-[10px] text-muted"
                title={e.description}
              >
                <div className="flex flex-col items-center gap-0.5">
                  <div className="h-2 w-2 rounded-full" style={{ backgroundColor: m.color }} />
                  <span>E{i + 1}</span>
                </div>
              </th>
            );
          })}
        </tr>
      </thead>
      <tbody>
        {entities.map((ent, ri) => {
          const col = ENTITY_COL[ent.type] ?? "#a78bfa";
          const rowBg = ri % 2 === 0 ? "bg-surface-card" : "bg-surface-subtle";
          return (
            <tr key={ent.id} className={rowBg}>
              <td className={cn("sticky left-0 z-10 px-4 py-2", rowBg)}>
                <div className="flex items-center gap-2">
                  <div
                    className="h-5 w-5 shrink-0 rounded-full flex items-center justify-center text-[7px] font-bold text-white"
                    style={{ backgroundColor: col }}
                  >
                    {initials(ent.name)}
                  </div>
                  <span className="text-xs text-secondary truncate max-w-[110px]">{ent.name}</span>
                </div>
              </td>
              {events.map((e) => {
                const participants = e.participants.filter((p) => p.entity_id === ent.id);
                const roleCount = participants.length;
                const roleTitle = participants.map((p) => p.role_label).join(", ");
                return (
                  <td key={e.id} className="px-3 py-2 text-center">
                    {roleCount > 0 ? (
                      <div
                        className={cn("flex flex-col items-center gap-0.5", roleCount === 1 ? "opacity-60" : "opacity-100")}
                        title={roleTitle}
                      >
                        <div className="h-3 w-3 rounded-sm" style={{ backgroundColor: col }} />
                        <span className="font-mono text-[7px] text-muted">
                          {participants[0]?.role_label.slice(0, 3)}
                        </span>
                      </div>
                    ) : (
                      <span className="text-border">—</span>
                    )}
                  </td>
                );
              })}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────


export default function DossierPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const { data, loading, error } = useDossieBook();

  const [openSignal, setOpenSignal] = useState<TimelineEventSignalDTO | null>(null);
  const [expandedSignals, setExpandedSignals] = useState<Set<string>>(new Set());

  function toggleExpand(id: string) {
    setExpandedSignals((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  // ── Loading ─────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-screen bg-surface-base">
        <div className="border-b border-border bg-surface-card">
          <div className="mx-auto max-w-6xl px-6 py-6">
            <div className="h-8 w-48 rounded-lg bg-surface-subtle animate-pulse" />
          </div>
        </div>
        <div className="mx-auto max-w-6xl px-6 py-10 space-y-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 rounded-2xl border border-border bg-surface-card animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  // ── Error ───────────────────────────────────────────────────────────────
  if (error || !data) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center p-6">
        <div className="rounded-2xl border border-severity-critical/30 bg-severity-critical-bg p-8 text-center max-w-md">
          <AlertTriangle className="h-8 w-8 text-severity-critical mx-auto mb-3" />
          <p className="text-sm text-severity-critical mb-4">
            {error ?? "Dossiê não encontrado."}
          </p>
          <Link
            href="/radar"
            className="inline-flex items-center gap-1.5 text-xs text-accent hover:underline"
          >
            <ArrowLeft className="h-3 w-3" />Voltar ao Radar
          </Link>
        </div>
      </div>
    );
  }

  const { case: caseData, entities, events, signals: allSignals, legal_hypotheses, related_cases } = data;
  const sevData = getSev(caseData.severity);
  const isPulsing = caseData.severity === "critical" || caseData.severity === "high";
  const sortedEvents = [...events].sort((a, b) => a.occurred_at.localeCompare(b.occurred_at));
  const entityMap = new Map(entities.map((e) => [e.id, e]));
  const signalMap = new Map(allSignals.map((s) => [s.id, s]));

  const totalValue = events.reduce((sum, e) => sum + (e.value_brl ?? 0), 0);
  const eventYears = events.map((e) => new Date(e.occurred_at).getFullYear());
  const periodStr = eventYears.length > 0
    ? `${Math.min(...eventYears)}–${Math.max(...eventYears)}`
    : "—";

  // Entity × event stats
  const entityMatrix = entities.map((ent) => ({
    entity: ent,
    eventCount: sortedEvents.filter((e) => e.participants.some((p) => p.entity_id === ent.id)).length,
    roles: [...new Set(
      sortedEvents.flatMap((e) =>
        e.participants.filter((p) => p.entity_id === ent.id).map((p) => p.role_label)
      )
    )],
    signalCount: [...new Set(
      sortedEvents
        .filter((e) => e.participants.some((p) => p.entity_id === ent.id))
        .flatMap((e) => e.signals.map((s) => s.id))
    )].length,
  }));

  // Unique signals across all events (for analysis section)
  const uniqueEventSignals = Array.from(
    new Map(sortedEvents.flatMap((e) => e.signals).map((s) => [s.id, s])).values()
  );

  const fullSignalForModal = openSignal ? (signalMap.get(openSignal.id) ?? null) : null;

  return (
    <div className="ledger-page min-h-screen bg-surface-base">
      {/* ── Hero severity banner ──────────────────────────────────── */}
      <div className={cn("border-b", sevData.bg, sevData.border)}>
        <div className="mx-auto max-w-6xl px-6 py-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/radar" className={cn("transition-opacity hover:opacity-70", sevData.text)}>
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <div className={cn(
              "flex items-center gap-2 rounded-full border px-3 py-1 font-mono text-xs font-bold",
              sevData.border, sevData.text,
            )}>
              <span className={cn("h-2 w-2 rounded-full", sevData.dot, isPulsing && "animate-pulse")} />
              {sevData.label} — Dossiê {caseData.id}
            </div>
          </div>
          <span className="font-mono text-[10px] uppercase tracking-widest opacity-50">
            Sala de Guerra
          </span>
        </div>
      </div>

      {/* ── Case header ──────────────────────────────────────────── */}
      <div className="border-b border-border bg-surface-card">
        <div className="mx-auto max-w-6xl px-6 py-8">
          <h1 className="font-display text-3xl font-black text-primary mb-2">{caseData.title}</h1>
          {caseData.summary && (
            <p className="text-secondary leading-relaxed max-w-3xl mb-6">{caseData.summary}</p>
          )}

          {/* Stats grid */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
            {[
              { Icon: Calendar,      label: "Período",     val: periodStr },
              { Icon: Hash,          label: "Eventos",     val: String(events.length) },
              { Icon: User,          label: "Atores",      val: String(entities.length) },
              { Icon: AlertTriangle, label: "Sinais",      val: String(allSignals.length) },
              { Icon: DollarSign,    label: "Valor Total", val: totalValue > 0 ? formatBRL(totalValue) : "—" },
            ].map(({ Icon, label, val }) => (
              <div key={label} className="rounded-xl border border-border bg-surface-subtle p-4">
                <Icon className="h-4 w-4 text-muted mb-2" />
                <p className="font-mono text-xs text-muted mb-0.5">{label}</p>
                <p className="font-mono font-bold text-primary tabular-nums">{val}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Body ─────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-6xl px-6 py-10 space-y-14">

        {/* ── Atores Identificados ─────────────────────────────── */}
        <section id="atores">
          <div className="mb-4 flex items-center gap-2">
            <User className="h-4 w-4 text-accent" />
            <h2 className="font-mono text-xs font-bold uppercase tracking-widest text-accent">
              Atores Identificados
            </h2>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {entityMatrix.map(({ entity, eventCount, roles, signalCount }) => {
              const col = ENTITY_COL[entity.type] ?? "#a78bfa";
              const photoUrl = typeof entity.attrs.photo_url === "string" ? entity.attrs.photo_url : null;
              const party = typeof entity.attrs.party === "string" ? entity.attrs.party : null;
              const sphere = typeof entity.attrs.sphere === "string" ? entity.attrs.sphere : null;
              const parliament = typeof entity.attrs.parliament === "string" ? entity.attrs.parliament : null;
              const mandateStart = entity.attrs.mandate_start != null ? String(entity.attrs.mandate_start) : null;
              const mandateEnd = entity.attrs.mandate_end != null ? String(entity.attrs.mandate_end) : null;
              const cnpj = entity.identifiers.cnpj;
              const cpf = entity.identifiers.cpf;

              return (
                <div key={entity.id} className="rounded-2xl border border-border bg-surface-card p-5">
                  <div className="mb-3 flex items-start gap-3">
                    {/* Photo or initials avatar */}
                    {photoUrl ? (
                      <img
                        src={photoUrl}
                        alt={entity.name}
                        className="h-10 w-10 shrink-0 rounded-xl object-cover"
                      />
                    ) : (
                      <div
                        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-sm font-bold text-white"
                        style={{ backgroundColor: col }}
                      >
                        {initials(entity.name)}
                      </div>
                    )}
                    <div className="min-w-0">
                      <p className="font-semibold text-primary leading-tight line-clamp-2">{entity.name}</p>
                      <span className="font-mono text-[9px] font-bold uppercase" style={{ color: col }}>
                        {ENTITY_LABEL[entity.type] ?? entity.type}
                      </span>
                    </div>
                  </div>

                  {/* Identifiers — unmasked */}
                  {cnpj && <p className="mb-1 font-mono text-[10px] text-muted">CNPJ {cnpj}</p>}
                  {cpf && <p className="mb-1 font-mono text-[10px] text-muted">CPF {cpf}</p>}

                  {/* Attribute badges */}
                  {(party || sphere || parliament) && (
                    <div className="mb-2 flex flex-wrap gap-1">
                      {party && (
                        <span className="rounded-full border border-accent/30 bg-accent/10 px-2 py-0.5 font-mono text-[9px] font-bold text-accent">
                          {party}
                        </span>
                      )}
                      {sphere && (
                        <span className="rounded-full border border-border bg-surface-subtle px-2 py-0.5 font-mono text-[9px] text-muted">
                          {sphere}
                        </span>
                      )}
                      {parliament && (
                        <span className="rounded-full border border-border bg-surface-subtle px-2 py-0.5 font-mono text-[9px] text-muted">
                          {parliament}
                        </span>
                      )}
                    </div>
                  )}

                  {/* Mandate */}
                  {(mandateStart || mandateEnd) && (
                    <p className="mb-2 font-mono text-[10px] text-muted">
                      Mandato: {mandateStart ? String(mandateStart).slice(0, 4) : "?"}
                      {mandateEnd ? `–${String(mandateEnd).slice(0, 4)}` : "–?"}
                    </p>
                  )}

                  {/* Event / signal stats */}
                  <div className="mt-3 grid grid-cols-2 gap-2 border-t border-border pt-3">
                    <div>
                      <p className="font-mono text-xl font-black text-primary">{eventCount}</p>
                      <p className="font-mono text-[9px] text-muted">eventos</p>
                    </div>
                    <div>
                      <p className={cn("font-mono text-xl font-black", signalCount > 0 ? "text-severity-high" : "text-muted")}>
                        {signalCount}
                      </p>
                      <p className="font-mono text-[9px] text-muted">sinais</p>
                    </div>
                  </div>

                  {/* Roles */}
                  {roles.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1">
                      {roles.map((r) => (
                        <span key={r} className="rounded-full border border-border bg-surface-subtle px-2 py-0.5 font-mono text-[9px] text-muted">
                          {r}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        {/* ── Linha do Tempo de Eventos ────────────────────────── */}
        <section id="timeline">
          <div className="mb-4 flex items-center gap-2">
            <Calendar className="h-4 w-4 text-accent" />
            <h2 className="font-mono text-xs font-bold uppercase tracking-widest text-accent">
              Linha do Tempo de Eventos
            </h2>
          </div>
          <div className="space-y-4">
            {sortedEvents.map((evt, idx) => {
              const meta = EVENT_META[evt.type] ?? { Icon: FileText, color: "#a78bfa", label: evt.type };
              const uniqueEvtSignals = Array.from(
                new Map(evt.signals.map((s) => [s.id, s])).values()
              );
              const valueBrlStr = evt.value_brl != null ? formatBRL(evt.value_brl) : null;
              // Skip rendering value if description already contains it
              const showValue = valueBrlStr != null &&
                !evt.description.includes(valueBrlStr.replace(/\u00a0/g, " "));
              const obs = typeof evt.attrs.obs === "string" ? evt.attrs.obs : null;
              const justificativa = typeof evt.attrs.justificativa === "string" ? evt.attrs.justificativa : null;

              return (
                <div
                  key={evt.id}
                  className="relative rounded-2xl border border-border bg-surface-card overflow-hidden"
                  style={{ borderLeftWidth: 3, borderLeftColor: meta.color }}
                >
                  <div className="absolute right-4 top-4 font-mono text-[10px] text-muted">
                    #{String(idx + 1).padStart(2, "0")}
                  </div>
                  <div className="p-5">
                    {/* Header */}
                    <div className="flex items-start gap-3 mb-3">
                      <div
                        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg"
                        style={{ backgroundColor: `${meta.color}1A`, color: meta.color }}
                      >
                        <meta.Icon className="h-4 w-4" />
                      </div>
                      <div>
                        <div className="flex flex-wrap items-center gap-2 mb-0.5">
                          <span className="font-mono text-xs font-bold" style={{ color: meta.color }}>
                            {meta.label}
                          </span>
                          <span className="font-mono text-xs text-muted">{formatDate(evt.occurred_at)}</span>
                          <span className="rounded border border-border px-1.5 py-0.5 font-mono text-[9px] uppercase text-muted">
                            {evt.source_connector}
                          </span>
                        </div>
                        <p className="text-sm text-secondary leading-relaxed">{evt.description}</p>
                        {showValue && (
                          <p className="mt-1 font-mono text-lg font-bold tabular-nums text-primary">
                            {valueBrlStr}
                          </p>
                        )}
                      </div>
                    </div>

                    {/* obs / justificativa blockquote */}
                    {(obs || justificativa) && (
                      <blockquote className="mb-3 rounded-r-lg border-l-2 border-accent/40 bg-accent/5 px-4 py-2.5">
                        <p className="text-sm italic leading-relaxed text-secondary">
                          {obs ?? justificativa}
                        </p>
                      </blockquote>
                    )}

                    {/* Participants */}
                    {evt.participants.length > 0 && (
                      <div className="mb-3">
                        <p className="mb-1.5 font-mono text-[9px] uppercase tracking-widest text-muted">
                          Participantes
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {evt.participants.map((p, i) => {
                            const ent = entityMap.get(p.entity_id);
                            const col = ENTITY_COL[ent?.type ?? "org"] ?? "#a78bfa";
                            return (
                              <span
                                key={i}
                                className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs"
                                style={{ borderColor: `${col}30`, backgroundColor: `${col}0D`, color: col }}
                              >
                                <span className="opacity-60">{p.role_label}</span>
                                <span>·</span>
                                <span className="font-semibold">{ent?.name ?? p.entity_id}</span>
                              </span>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Signal pills */}
                    {uniqueEvtSignals.length > 0 && (
                      <div>
                        <p className="mb-1.5 font-mono text-[9px] uppercase tracking-widest text-muted">
                          Alertas de Risco
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {uniqueEvtSignals.map((sig) => {
                            const ss = getSev(sig.severity);
                            return (
                              <button
                                key={sig.id}
                                onClick={() => setOpenSignal(sig)}
                                className={cn(
                                  "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 font-mono text-xs font-bold transition-all hover:opacity-80",
                                  ss.bg, ss.border, ss.text,
                                )}
                              >
                                <AlertTriangle className="h-3 w-3" />
                                {sig.typology_code} · {ss.label}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* ── Análise Detalhada dos Sinais ─────────────────────── */}
        {uniqueEventSignals.length > 0 && (
          <section id="sinais">
            <div className="mb-4 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-accent" />
              <h2 className="font-mono text-xs font-bold uppercase tracking-widest text-accent">
                Análise Detalhada dos Sinais
              </h2>
            </div>
            <div className="space-y-4">
              {uniqueEventSignals.map((sig) => {
                const s = getSev(sig.severity);
                const fullSig = signalMap.get(sig.id);
                const pct = Math.round(sig.confidence * 100);
                const pctColor = confidenceColor(pct);
                const relatedEvts = sortedEvents.filter((e) =>
                  e.signals.some((rs) => rs.id === sig.id)
                );
                const factorDescs = fullSig?.factor_descriptions;
                const factorKeys = factorDescs
                  ? Object.keys(factorDescs)
                  : sig.factors;
                const isExpanded = expandedSignals.has(sig.id);
                const visibleFactors = isExpanded ? factorKeys : factorKeys.slice(0, 5);
                const hasMore = factorKeys.length > 5;
                const evidenceCount = fullSig?.event_count ?? 0;

                return (
                  <div
                    key={sig.id}
                    className={cn("relative rounded-2xl border overflow-hidden bg-surface-card", s.border)}
                  >
                    {/* Severity stripe */}
                    <div className={cn("absolute left-0 top-0 bottom-0 w-1", s.dot)} />

                    <div className="pl-5 pr-6 py-6">
                      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <div className="mb-1 flex flex-wrap items-center gap-2">
                            <span className={cn("font-mono text-xs font-bold", s.text)}>
                              {sig.typology_code}
                            </span>
                            <span className={cn("rounded-full border px-2 py-0.5 font-mono text-[10px] font-bold", s.border, s.text)}>
                              {s.label}
                            </span>
                            {evidenceCount > 0 && (
                              <span className={cn("flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-[10px] opacity-70", s.border, s.text)}>
                                <Database className="h-2.5 w-2.5" />
                                {evidenceCount} ev.
                              </span>
                            )}
                          </div>
                          <h3 className={cn("font-display text-lg font-bold", s.text)}>
                            {sig.typology_name}
                          </h3>
                          <p className={cn("mt-0.5 text-sm opacity-80", s.text)}>{sig.title}</p>
                        </div>
                        <div className="text-right shrink-0">
                          <p className="font-mono text-[9px] uppercase tracking-widest opacity-60">Período</p>
                          <p className={cn("font-mono text-xs font-bold", s.text)}>
                            {sig.period_start ? formatDate(sig.period_start) : "—"}
                            {" — "}
                            {sig.period_end ? formatDate(sig.period_end) : "—"}
                          </p>
                        </div>
                      </div>

                      {/* Confidence bar */}
                      <div className="mb-4">
                        <div className="mb-1 flex items-center justify-between">
                          <span className={cn("font-mono text-[10px] opacity-70", s.text)}>
                            Confiança
                          </span>
                          <span className={cn("font-mono text-xs font-bold", s.text)}>{pct}%</span>
                        </div>
                        <div className="h-2 w-full overflow-hidden rounded-full bg-black/20">
                          <div
                            className={cn("h-full transition-all", pctColor)}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>

                      <div className="grid gap-4 md:grid-cols-2">
                        {/* Factors as pills */}
                        <div>
                          <p className={cn("mb-2 font-mono text-[9px] uppercase tracking-widest opacity-60", s.text)}>
                            Fatores
                          </p>
                          <div className="flex flex-wrap gap-1.5">
                            {visibleFactors.map((f) => {
                              const label = factorDescs?.[f]?.label ?? f;
                              return (
                                <span
                                  key={f}
                                  className={cn(
                                    "rounded-full border px-2.5 py-1 font-mono text-[10px] bg-black/10 opacity-80",
                                    s.border, s.text,
                                  )}
                                >
                                  {label}
                                </span>
                              );
                            })}
                            {hasMore && (
                              <button
                                onClick={() => toggleExpand(sig.id)}
                                className={cn(
                                  "inline-flex items-center gap-1 rounded-full border px-2.5 py-1 font-mono text-[10px] opacity-60 transition-all hover:opacity-80",
                                  s.border, s.text,
                                )}
                              >
                                {isExpanded ? (
                                  <><ChevronUp className="h-3 w-3" />Recolher</>
                                ) : (
                                  <><ChevronDown className="h-3 w-3" />Ver todos ({factorKeys.length})</>
                                )}
                              </button>
                            )}
                          </div>
                        </div>

                        {/* Related events */}
                        {relatedEvts.length > 0 && (
                          <div>
                            <p className={cn("mb-2 font-mono text-[9px] uppercase tracking-widest opacity-60", s.text)}>
                              Eventos Relacionados
                            </p>
                            <div className="space-y-1">
                              {relatedEvts.map((e) => {
                                const m = EVENT_META[e.type] ?? { color: "#a78bfa", label: e.type };
                                return (
                                  <div key={e.id} className="flex items-center gap-2 text-xs">
                                    <div className="h-1.5 w-1.5 rounded-full shrink-0" style={{ backgroundColor: m.color }} />
                                    <span className={cn("font-mono opacity-70", s.text)}>
                                      {formatDate(e.occurred_at)}
                                    </span>
                                    <span className={cn("opacity-80", s.text)}>{m.label}</span>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* ── Matriz de Cruzamento ─────────────────────────────── */}
        <section id="matriz">
          <div className="mb-4 flex items-center gap-2">
            <Link2 className="h-4 w-4 text-accent" />
            <h2 className="font-mono text-xs font-bold uppercase tracking-widest text-accent">
              Matriz de Cruzamento — Atores × Eventos
            </h2>
          </div>

          {/* Mobile: hidden behind <details> */}
          <details className="md:hidden mb-2">
            <summary className="cursor-pointer rounded-xl border border-border bg-surface-card px-4 py-3 font-mono text-xs text-muted hover:border-accent/40 select-none">
              Mostrar matriz de cruzamento
            </summary>
            <div className="mt-2 overflow-x-auto rounded-xl border border-border">
              <MatrixTable entities={entities} events={sortedEvents} entityMap={entityMap} />
            </div>
          </details>

          {/* Desktop: always visible */}
          <div className="hidden md:block overflow-x-auto rounded-xl border border-border">
            <MatrixTable entities={entities} events={sortedEvents} entityMap={entityMap} />
          </div>

          <p className="mt-2 font-mono text-[9px] text-muted">
            E1–E{sortedEvents.length} = eventos em ordem cronológica
          </p>
        </section>

        {/* ── Hipóteses Jurídicas ──────────────────────────────── */}
        {legal_hypotheses.length > 0 && (
          <section id="juridico">
            <div className="mb-4 flex items-center gap-2">
              <Scale className="h-4 w-4 text-accent" />
              <h2 className="font-mono text-xs font-bold uppercase tracking-widest text-accent">
                Hipóteses Jurídicas
              </h2>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              {legal_hypotheses.map((lh, i) => (
                <div key={i} className="rounded-xl border border-accent/20 bg-accent/5 p-5">
                  <div className="mb-2 flex items-center gap-2">
                    <Scale className="h-3.5 w-3.5 text-accent" />
                    <span className="font-mono text-xs font-bold text-accent">
                      {lh.law} — Art. {lh.article}
                    </span>
                  </div>
                  <p className="mb-2 font-semibold text-primary">{lh.violation_type}</p>
                  <p className="text-sm text-muted leading-relaxed">{lh.description}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* ── Fontes de Dados ──────────────────────────────────── */}
        <section>
          <div className="mb-4 flex items-center gap-2">
            <Database className="h-4 w-4 text-accent" />
            <h2 className="font-mono text-xs font-bold uppercase tracking-widest text-accent">
              Fontes de Dados
            </h2>
          </div>
          <div className="flex flex-wrap gap-2">
            {[...new Set(events.map((e) => e.source_connector))].map((src) => (
              <span
                key={src}
                className="rounded-full border border-border bg-surface-card px-3 py-1.5 font-mono text-xs text-secondary"
              >
                {src}
              </span>
            ))}
          </div>
          <p className="mt-3 text-xs text-muted leading-relaxed">
            Todos os dados provêm de fontes públicas oficiais do governo federal brasileiro.
            Análise gerada automaticamente por OpenWatch. Requer investigação adicional e contraditório.
          </p>
        </section>

        {/* ── Casos Relacionados ───────────────────────────────── */}
        {related_cases.length > 0 && (
          <section>
            <div className="mb-4 flex items-center gap-2">
              <Link2 className="h-4 w-4 text-accent" />
              <h2 className="font-mono text-xs font-bold uppercase tracking-widest text-accent">
                Casos Relacionados
              </h2>
            </div>
            <div className="space-y-2">
              {related_cases.map((rc) => {
                const rcs = getSev(rc.severity);
                return (
                  <Link key={rc.id} href={`/radar/dossie/${rc.id}`} className="block">
                    <div className="flex items-center gap-3 rounded-lg border border-border bg-surface-card p-3 hover:border-accent/40 transition-colors">
                      <span className={cn("h-2 w-2 shrink-0 rounded-full", rcs.dot)} />
                      <p className="flex-1 truncate text-sm text-primary">{rc.title}</p>
                    </div>
                  </Link>
                );
              })}
            </div>
          </section>
        )}
      </div>

      {/* ── Signal Modal ─────────────────────────────────────────── */}
      <SignalModal
        signal={openSignal}
        fullSignal={fullSignalForModal}
        caseId={caseId}
        onClose={() => setOpenSignal(null)}
      />
    </div>
  );
}
