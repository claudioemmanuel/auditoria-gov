"use client";

import Link from "next/link";
import { severityColor } from "@/lib/utils";
import { SEVERITY_LABELS, TYPOLOGY_LABELS } from "@/lib/constants";
import type { CaseSignalBrief, SignalSeverity } from "@/lib/types";
import type { GNode } from "@/hooks/useCaseGraph";
import { X, User, Building2, Landmark, ExternalLink, ShieldAlert, Network } from "lucide-react";
import { cn } from "@/lib/utils";

const TYPE_CONFIG: Record<
  string,
  { Icon: typeof User; label: string; accent: string; iconBg: string; headerBar: string }
> = {
  person: {
    Icon: User,
    label: "Pessoa",
    accent: "text-blue-700",
    iconBg: "bg-blue-100",
    headerBar: "bg-blue-500",
  },
  company: {
    Icon: Building2,
    label: "Empresa",
    accent: "text-emerald-700",
    iconBg: "bg-emerald-100",
    headerBar: "bg-emerald-500",
  },
  org: {
    Icon: Landmark,
    label: "Órgão Público",
    accent: "text-violet-700",
    iconBg: "bg-violet-100",
    headerBar: "bg-violet-500",
  },
};

interface InvestigationSidebarProps {
  node: GNode | null;
  nodeAttrs: Record<string, unknown>;
  signals: CaseSignalBrief[];
  entitySeverityMap: Record<string, SignalSeverity>;
  open: boolean;
  onClose: () => void;
}

export function InvestigationSidebar({
  node,
  nodeAttrs,
  signals,
  onClose,
}: InvestigationSidebarProps) {
  // Always render the panel — show empty state when no node selected
  if (!node) {
    return (
      <div className="flex w-80 shrink-0 flex-col border-l border-[var(--color-border-light)] bg-[var(--color-surface-card)]">
        <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6 py-10 text-center">
          <Network className="h-9 w-9 text-[var(--color-text-muted)]" />
          <div>
            <p className="text-base font-semibold text-[var(--color-text-primary)] mb-2">Selecione um node</p>
            <p className="text-sm text-[var(--color-text-secondary)]">
              Clique em uma entidade no grafo para ver seus detalhes e sinais associados.
            </p>
          </div>
          <div className="mt-4 p-3 rounded-lg bg-[var(--color-surface-hover)] border border-[var(--color-border-light)]">
            <p className="text-xs text-[var(--color-text-muted)] mb-2">Atalhos de teclado:</p>
            <div className="space-y-1 text-xs">
              <div className="flex items-center gap-2">
                <kbd className="rounded bg-[var(--color-surface-card)] px-2 py-1 font-mono text-[10px] border border-[var(--color-border-light)]">Espaço</kbd>
                <span className="text-[var(--color-text-secondary)]">Ajustar vista</span>
              </div>
              <div className="flex items-center gap-2">
                <kbd className="rounded bg-[var(--color-surface-card)] px-2 py-1 font-mono text-[10px] border border-[var(--color-border-light)]">E</kbd>
                <span className="text-[var(--color-text-secondary)]">Expandir node</span>
              </div>
              <div className="flex items-center gap-2">
                <kbd className="rounded bg-[var(--color-surface-card)] px-2 py-1 font-mono text-[10px] border border-[var(--color-border-light)]">Esc</kbd>
                <span className="text-[var(--color-text-secondary)]">Limpar</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const config = TYPE_CONFIG[node.node_type] ?? TYPE_CONFIG.person;
  const { Icon } = config;

  const relatedSignals = signals.filter((s) =>
    s.entity_ids.includes(node.entity_id),
  );

  const nestedIdentifiers =
    (nodeAttrs.identifiers as Record<string, unknown> | undefined) ??
    (nodeAttrs.attrs as { identifiers?: Record<string, unknown> } | undefined)?.identifiers ??
    {};
  const directIdentifiers = Object.fromEntries(
    Object.entries(nodeAttrs).filter(([k, v]) =>
      typeof v === "string" && ["cnpj", "cpf", "uasg", "cod_ibge"].includes(k),
    ),
  );
  const identifiers = Object.entries({
    ...directIdentifiers,
    ...nestedIdentifiers,
  }).filter(([, v]) => typeof v === "string" && (v as string).trim()) as [string, string][];

  const rawAttrs =
    (nodeAttrs.attrs as Record<string, unknown> | undefined) ??
    {};
  const photoUrl = (
    (nodeAttrs.url_foto as string | undefined)
    || (nodeAttrs.urlFoto as string | undefined)
    || (nodeAttrs.photo_url as string | undefined)
    || (rawAttrs.url_foto as string | undefined)
    || (rawAttrs.urlFoto as string | undefined)
    || null
  );
  const attrsToShow = Object.entries(rawAttrs)
    .filter(([key, value]) =>
      ["cargo", "partido", "uf", "sigla_uf", "sigla_partido", "orgao", "cluster_id", "photo_source"].includes(key)
      && value != null
      && String(value).trim() !== "",
    )
    .slice(0, 8);

  const typologies = Array.from(new Set(relatedSignals.map((sig) => sig.typology_code)));
  const whyLinked = relatedSignals.length > 0
    ? `Esta entidade participa de ${relatedSignals.length} sinal(is) neste caso (${typologies.join(", ")}), por isso aparece na teia investigativa.`
    : "A entidade foi carregada no grafo, mas ainda sem sinais diretamente vinculados no caso.";

  return (
    <div className="flex w-80 shrink-0 flex-col overflow-hidden border-l border-[var(--color-border-light)] bg-[var(--color-surface-card)]">
      {/* Colored top accent bar */}
      <div className={cn("h-2 w-full shrink-0", config.headerBar)} />

      {/* Header — modernized */}
      <div className="flex items-start justify-between gap-3 border-b border-[var(--color-border-light)] px-4 py-4">
        <div className="flex min-w-0 items-start gap-3">
          {photoUrl ? (
            <img
              src={photoUrl}
              alt={`Foto de ${node.label}`}
              className="h-10 w-10 shrink-0 rounded-lg object-cover"
            />
          ) : (
            <div className={cn("flex h-10 w-10 shrink-0 items-center justify-center rounded-lg", config.iconBg)}>
              <Icon className={cn("h-5 w-5", config.accent)} strokeWidth={2} />
            </div>
          )}
          <div className="min-w-0 flex-1">
            <h3 className="truncate text-base font-bold font-[var(--font-display)] text-[var(--color-text-primary)] leading-tight">
              {node.label}
            </h3>
            <span className={cn("text-xs font-semibold uppercase tracking-widest", config.accent)}>
              {config.label}
            </span>
          </div>
        </div>
        <button
          onClick={onClose}
          title="Limpar seleção (Esc)"
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-[var(--color-text-secondary)] transition hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {/* Identifiers — improved with new tokens */}
        {identifiers.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {identifiers.map(([key, val]) => (
              <span
                key={key}
                className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--color-border-light)] bg-[var(--color-surface-hover)] px-2.5 py-1 text-xs font-mono"
              >
                <span className="font-semibold text-[var(--color-text-secondary)]">{key}:</span>
                <span className="tabular-nums text-[var(--color-text-primary)]">{val}</span>
              </span>
            ))}
          </div>
        )}

        {/* Link to entity — modern button style */}
        <Link
          href={`/entity/${node.entity_id}`}
          className="inline-flex items-center justify-center gap-2 w-full rounded-lg bg-[var(--color-secondary)] text-white px-3 py-2 text-sm font-semibold transition hover:shadow-md hover:shadow-[var(--color-secondary)]/30"
        >
          Ver Detalhes da Entidade
          <ExternalLink className="h-4 w-4" />
        </Link>

        {/* Why linked section — modernized with new design tokens */}
        <div className="rounded-lg border border-[var(--color-medium)]/30 bg-[#FEF9E7] p-3">
          <p className="text-xs font-bold uppercase tracking-widest text-[var(--color-medium)] mb-2">
            Por que está ligada
          </p>
          <p className="text-sm leading-relaxed text-[var(--color-text-secondary)]">
            {whyLinked}
          </p>
        </div>

        {/* Public profile attributes */}
        {attrsToShow.length > 0 && (
          <div className="rounded-lg border border-[var(--color-border-light)] bg-[var(--color-surface-hover)] p-3">
            <p className="text-xs font-bold uppercase tracking-widest text-[var(--color-text-secondary)] mb-2">
              Perfil Público
            </p>
            <div className="space-y-2">
              {attrsToShow.map(([key, value]) => (
                <div key={key} className="flex items-start justify-between bg-white rounded px-2.5 py-1.5 text-xs border border-[var(--color-border-light)]">
                  <span className="text-[10px] font-medium text-muted">{key}</span>
                  <span className="ml-2 text-[10px] font-semibold text-secondary">{String(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Related signals header */}
        <div className="mt-4 flex items-center gap-2">
          <ShieldAlert className="h-3.5 w-3.5 text-muted" />
          <h4 className="text-[11px] font-semibold uppercase tracking-wider text-muted">
            Sinais associados
          </h4>
          {relatedSignals.length > 0 && (
            <span className="flex h-4 min-w-4 items-center justify-center rounded-full bg-severity-critical-bg px-1 text-[10px] font-bold text-severity-critical">
              {relatedSignals.length}
            </span>
          )}
        </div>

        {relatedSignals.length === 0 ? (
          <p className="mt-2 text-xs text-muted">
            Nenhum sinal diretamente associado a esta entidade.
          </p>
        ) : (
          <div className="mt-2 space-y-2">
            {relatedSignals.map((sig) => (
              <div
                key={sig.id}
                className="rounded-lg border border-border bg-surface-subtle p-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <h5 className="text-[13px] font-medium leading-snug text-primary">
                    {sig.title}
                  </h5>
                  <span
                    className={cn("shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold", severityColor(sig.severity))}
                  >
                    {SEVERITY_LABELS[sig.severity]}
                  </span>
                </div>

                <p className="mt-1 text-[11px] text-muted">
                  <span className="font-mono tabular-nums text-muted">{sig.typology_code}</span>
                  {" — "}
                  {TYPOLOGY_LABELS[sig.typology_code] ?? sig.typology_name}
                </p>

                {/* Confidence */}
                <div className="mt-2 flex items-center gap-2">
                  <span className="text-[10px] font-medium text-muted">Confianca</span>
                  <div className="h-1.5 flex-1 rounded-full bg-border">
                    <div
                      className="h-1.5 rounded-full bg-accent transition-all"
                      style={{ width: `${sig.confidence * 100}%` }}
                    />
                  </div>
                  <span className="text-[10px] font-semibold tabular-nums text-secondary">
                    {Math.round(sig.confidence * 100)}%
                  </span>
                </div>

                {sig.summary && (
                  <p className="mt-2 text-[11px] leading-relaxed text-muted">
                    {sig.summary}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
