"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import type { ElementType } from "react";
import {
  ArrowLeft, AlertTriangle, Building2, User, Calendar,
  Hash, DollarSign, TrendingUp, ArrowRight,
} from "lucide-react";
import { useDossieBook } from "@/components/dossie/DossieBookContext";
import type { TimelineEntityDTO, TimelineSignalDTO } from "@/lib/types";
import { cn, formatBRL, formatDate } from "@/lib/utils";
import { TYPOLOGY_LABELS } from "@/lib/constants";

// ── Config ───────────────────────────────────────────────────────────────────

/** Read CSS variable at runtime */
function getCSSToken(varName: string): string {
  if (typeof document === "undefined") return "";
  return getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
}

/** Entity type color tokens */
function getEntityColor(entityType: string): string {
  const tokenMap: Record<string, string> = {
    org:     "--color-entity-org",
    company: "--color-entity-company",
    person:  "--color-entity-person",
  };
  const token = tokenMap[entityType];
  return token ? getCSSToken(token) : getCSSToken("--color-muted");
}

const SEV = {
  critical: { label: "Crítico", bg: "bg-severity-critical-bg", text: "text-severity-critical", border: "border-severity-critical/30", dot: "bg-severity-critical" },
  high:     { label: "Alto",    bg: "bg-severity-high-bg",     text: "text-severity-high",     border: "border-severity-high/30",     dot: "bg-severity-high"     },
  medium:   { label: "Médio",   bg: "bg-severity-medium-bg",   text: "text-severity-medium",   border: "border-severity-medium/30",   dot: "bg-severity-medium"   },
  low:      { label: "Baixo",   bg: "bg-severity-low-bg",      text: "text-severity-low",      border: "border-severity-low/30",      dot: "bg-severity-low"      },
} as const;

type SevKey = keyof typeof SEV;
function getSev(sv: string) { return SEV[(sv as SevKey) in SEV ? (sv as SevKey) : "low"]; }

const ENTITY_ICON: Record<string, ElementType> = { org: Building2, company: Building2, person: User };
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

// ── Entity mini-card ─────────────────────────────────────────────────────────

function EntityMiniCard({ entity }: { entity: TimelineEntityDTO }) {
  const col = getEntityColor(entity.type);
  const photoUrl = typeof entity.attrs.photo_url === "string" ? entity.attrs.photo_url : null;
  const cnpj = entity.identifiers.cnpj;
  const cpf  = entity.identifiers.cpf;

  return (
    <div className="rounded-xl border border-border bg-surface-card p-4">
      <div className="mb-2 flex items-center gap-3">
        {photoUrl ? (
          <img src={photoUrl} alt={entity.name} className="h-8 w-8 shrink-0 rounded-lg object-cover" />
        ) : (
          <div
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-xs font-bold text-white"
            style={{ backgroundColor: col }}
          >
            {initials(entity.name)}
          </div>
        )}
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-primary leading-tight">{entity.name}</p>
          <span className="font-mono text-[9px] font-bold uppercase" style={{ color: col }}>
            {ENTITY_LABEL_MAP[entity.type] ?? entity.type}
          </span>
        </div>
      </div>
      {cnpj && <p className="font-mono text-[10px] text-muted">CNPJ {cnpj}</p>}
      {cpf  && <p className="font-mono text-[10px] text-muted">CPF {cpf}</p>}
    </div>
  );
}

// ── Signal card ──────────────────────────────────────────────────────────────

function SignalCard({
  signal,
  entities,
  caseId,
}: {
  signal: TimelineSignalDTO;
  entities: TimelineEntityDTO[];
  caseId: string;
}) {
  const s = getSev(signal.severity);
  const pct = Math.round(signal.confidence * 100);
  const pctColor = confidenceColor(pct);
  const factorKeys = signal.factor_descriptions
    ? Object.keys(signal.factor_descriptions)
    : Object.keys(signal.factors);
  const previewFactors = factorKeys.slice(0, 3);
  const remaining = factorKeys.length - previewFactors.length;

  return (
    <div className={cn("relative rounded-2xl border overflow-hidden bg-surface-card", s.border)}>
      <div className={cn("absolute left-0 top-0 bottom-0 w-1", s.dot)} />
      <div className="pl-5 pr-6 py-5">

        {/* Header */}
        <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
          <div>
            <div className="mb-1 flex items-center gap-2">
              <span className={cn("font-mono text-xs font-bold", s.text)}>{signal.typology_code}</span>
              <span className={cn("rounded-full border px-2 py-0.5 font-mono text-[10px] font-bold", s.border, s.text)}>
                {s.label}
              </span>
            </div>
            <h3 className={cn("text-base font-bold leading-snug", s.text)}>{signal.title}</h3>
          </div>
          <span className={cn("shrink-0 font-mono text-xs opacity-70", s.text)}>
            {signal.period_start ? formatDate(signal.period_start) : "—"}
            {signal.period_end ? ` — ${formatDate(signal.period_end)}` : ""}
          </span>
        </div>

        {/* Confidence bar */}
        <div className="mb-3">
          <div className="mb-1 flex items-center justify-between">
            <span className={cn("font-mono text-[10px] opacity-70", s.text)}>Confiança</span>
            <span className={cn("font-mono text-xs font-bold", s.text)}>{pct}%</span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-black/20">
            <div className={cn("h-full transition-all", pctColor)} style={{ width: `${pct}%` }} />
          </div>
        </div>

        {/* Entities */}
        {entities.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-1.5">
            {entities.slice(0, 4).map((ent) => {
              const col = ENTITY_COL[ent.type] ?? "#a78bfa";
              return (
                <span
                  key={ent.id}
                  className="inline-flex items-center rounded-full border px-2.5 py-0.5 font-mono text-[10px]"
                  style={{ borderColor: `${col}30`, backgroundColor: `${col}0D`, color: col }}
                >
                  {ent.name.split(" ")[0]}
                </span>
              );
            })}
            {entities.length > 4 && (
              <span className={cn("rounded-full border px-2 py-0.5 font-mono text-[10px] opacity-60", s.border, s.text)}>
                +{entities.length - 4}
              </span>
            )}
          </div>
        )}

        {/* Factor pills */}
        {previewFactors.length > 0 && (
          <div className="mb-4 flex flex-wrap gap-1">
            {previewFactors.map((key) => {
              const label = signal.factor_descriptions?.[key]?.label ?? key;
              return (
                <span
                  key={key}
                  className={cn("rounded-full border px-2.5 py-1 font-mono text-[10px] bg-black/10 opacity-80", s.border, s.text)}
                >
                  {label}
                </span>
              );
            })}
            {remaining > 0 && (
              <span className={cn("rounded-full border px-2.5 py-1 font-mono text-[10px] opacity-50", s.border, s.text)}>
                e mais {remaining}
              </span>
            )}
          </div>
        )}

        <Link
          href={`/radar/dossie/${caseId}/sinal/${signal.id}`}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-xl border px-4 py-2 font-mono text-xs font-bold transition-all hover:opacity-80",
            s.border, s.text, "bg-black/10",
          )}
        >
          Ver sinal completo <ArrowRight className="h-3 w-3" />
        </Link>
      </div>
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────


export default function CapituloPage() {
  const { caseId, typologyCode } = useParams<{ caseId: string; typologyCode: string }>();
  const { data, loading, error } = useDossieBook();

  if (loading) {
    return (
      <div className="min-h-screen bg-surface-base">
        <div className="mx-auto max-w-6xl px-6 py-8 space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-40 rounded-2xl border border-border bg-surface-card animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center p-6">
        <div className="rounded-2xl border border-severity-critical/30 bg-severity-critical-bg p-8 text-center max-w-md">
          <AlertTriangle className="h-8 w-8 text-severity-critical mx-auto mb-3" />
          <p className="text-sm text-severity-critical mb-4">{error ?? "Dossiê não encontrado."}</p>
          <Link href={`/radar/dossie/${caseId}`} className="text-xs text-accent hover:underline">
            Voltar ao dossiê
          </Link>
        </div>
      </div>
    );
  }

  const chapterSignals = data.signals.filter((s) => s.typology_code === typologyCode);

  if (chapterSignals.length === 0) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center p-6">
        <div className="rounded-2xl border border-border bg-surface-card p-8 text-center">
          <p className="text-sm text-muted mb-4">Capítulo {typologyCode} não encontrado.</p>
          <Link href={`/radar/dossie/${caseId}`} className="text-xs text-accent hover:underline">
            Voltar ao dossiê
          </Link>
        </div>
      </div>
    );
  }

  const typologyName = TYPOLOGY_LABELS[typologyCode] ?? chapterSignals[0]?.typology_name ?? typologyCode;
  const sevOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
  const maxSeverity = chapterSignals.reduce(
    (max, sig) => (sevOrder[sig.severity] ?? 3) < (sevOrder[max] ?? 3) ? sig.severity : max,
    "low" as string,
  );
  const s = getSev(maxSeverity);
  const isPulsing = maxSeverity === "critical" || maxSeverity === "high";

  const avgConfidence = Math.round(
    (chapterSignals.reduce((sum, sig) => sum + sig.confidence, 0) / chapterSignals.length) * 100,
  );
  const chapterSignalIds = new Set(chapterSignals.map((sig) => sig.id));
  const chapterEvents = data.events.filter((evt) =>
    evt.signals.some((es) => chapterSignalIds.has(es.id)),
  );
  const totalValue = chapterEvents.reduce((sum, evt) => sum + (evt.value_brl ?? 0), 0);
  const periods = chapterSignals
    .flatMap((sig) => [sig.period_start, sig.period_end])
    .filter((d): d is string => d != null)
    .sort();
  const periodStr =
    periods.length > 0
      ? `${formatDate(periods[0]!)} — ${formatDate(periods[periods.length - 1]!)}`
      : "—";

  const entityMap = new Map(data.entities.map((e) => [e.id, e]));
  const chapterEntityIds = new Set<string>();
  for (const evt of chapterEvents) {
    for (const p of evt.participants) chapterEntityIds.add(p.entity_id);
  }
  const chapterEntities = [...chapterEntityIds]
    .map((id) => entityMap.get(id))
    .filter((e): e is TimelineEntityDTO => e != null);

  function signalEntities(signalId: string): TimelineEntityDTO[] {
    const ids = new Set<string>();
    for (const evt of data!.events) {
      if (evt.signals.some((es) => es.id === signalId)) {
        for (const p of evt.participants) ids.add(p.entity_id);
      }
    }
    return [...ids].map((id) => entityMap.get(id)).filter((e): e is TimelineEntityDTO => e != null);
  }

  return (
    <div className="ledger-page min-h-screen bg-surface-base">

      {/* Hero banner */}
      <div className={cn("border-b", s.bg, s.border)}>
        <div className="mx-auto max-w-6xl px-6 py-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href={`/radar/dossie/${caseId}`} className={cn("transition-opacity hover:opacity-70", s.text)}>
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <div className={cn("flex items-center gap-2 rounded-full border px-3 py-1 font-mono text-xs font-bold", s.border, s.text)}>
              <span className={cn("h-2 w-2 rounded-full", s.dot, isPulsing && "animate-pulse")} />
              {s.label} — Capítulo {typologyCode}
            </div>
          </div>
          <span className="hidden font-mono text-[10px] uppercase tracking-widest opacity-50 sm:block">
            {typologyName}
          </span>
        </div>
      </div>

      {/* Chapter header */}
      <div className="border-b border-border bg-surface-card">
        <div className="mx-auto max-w-6xl px-6 py-8">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="rounded bg-accent/10 px-1.5 py-0.5 font-mono text-xs font-bold text-accent">
              {typologyCode}
            </span>
            <h1 className="font-display text-2xl font-black text-primary">{typologyName}</h1>
          </div>

          <div className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              { Icon: Hash,       label: "Total Sinais",    val: String(chapterSignals.length) },
              { Icon: TrendingUp, label: "Confiança Média", val: `${avgConfidence}%` },
              { Icon: Calendar,   label: "Período",         val: periodStr },
              { Icon: DollarSign, label: "Valor Total",     val: totalValue > 0 ? formatBRL(totalValue) : "—" },
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

      {/* Body */}
      <div className="mx-auto max-w-6xl px-6 py-10 space-y-12">

        {/* Sinais */}
        <section>
          <div className="mb-4 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-accent" />
            <h2 className="font-mono text-xs font-bold uppercase tracking-widest text-accent">
              Sinais do Capítulo
            </h2>
          </div>
          <div className="space-y-4">
            {chapterSignals.map((sig) => (
              <SignalCard
                key={sig.id}
                signal={sig}
                entities={signalEntities(sig.id)}
                caseId={caseId}
              />
            ))}
          </div>
        </section>

        {/* Entities */}
        {chapterEntities.length > 0 && (
          <section>
            <div className="mb-4 flex items-center gap-2">
              <User className="h-4 w-4 text-accent" />
              <h2 className="font-mono text-xs font-bold uppercase tracking-widest text-accent">
                Entidades deste Capítulo
              </h2>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {chapterEntities.map((entity) => (
                <EntityMiniCard key={entity.id} entity={entity} />
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
