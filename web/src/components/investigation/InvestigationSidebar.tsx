"use client";

import Link from "next/link";
import { severityColor } from "@/lib/utils";
import { SEVERITY_LABELS, TYPOLOGY_LABELS } from "@/lib/constants";
import type { CaseSignalBrief, SignalSeverity } from "@/lib/types";
import type { GNode } from "@/hooks/useCaseGraph";
import { X, User, Building2, Landmark, ExternalLink, ShieldAlert } from "lucide-react";

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
    label: "Orgao Publico",
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
  open,
  onClose,
}: InvestigationSidebarProps) {
  if (!node) return null;

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
  }).filter(([, v]) => typeof v === "string" && v.trim()) as [string, string][];

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
    <div
      className={`investigation-sidebar absolute top-0 right-0 z-30 flex h-full w-[380px] flex-col overflow-hidden bg-white shadow-2xl ${
        open ? "translate-x-0" : "translate-x-full"
      }`}
    >
      {/* Colored top accent bar */}
      <div className={`h-1 w-full shrink-0 ${config.headerBar}`} />

      {/* Header */}
      <div className="flex items-start justify-between gap-3 border-b border-gray-100 px-5 py-4">
        <div className="flex items-start gap-3 min-w-0">
          {photoUrl ? (
            <img
              src={photoUrl}
              alt={`Foto de ${node.label}`}
              className="h-9 w-9 shrink-0 rounded-lg object-cover"
            />
          ) : (
            <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${config.iconBg}`}>
              <Icon className={`h-4.5 w-4.5 ${config.accent}`} strokeWidth={2} />
            </div>
          )}
          <div className="min-w-0">
            <h3 className="truncate text-base font-semibold text-gray-900 leading-tight">
              {node.label}
            </h3>
            <span className={`text-xs font-medium ${config.accent} opacity-75`}>
              {config.label}
            </span>
          </div>
        </div>
        <button
          onClick={onClose}
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-gray-400 transition hover:bg-gray-100 hover:text-gray-600"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-5 py-4">
        {/* Identifiers */}
        {identifiers.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {identifiers.map(([key, val]) => (
              <span
                key={key}
                className="inline-flex items-center gap-1 rounded-md border border-gray-100 bg-gray-50 px-2 py-1 text-[11px]"
              >
                <span className="font-medium text-gray-400">{key}</span>
                <span className="font-mono text-gray-600">{val}</span>
              </span>
            ))}
          </div>
        )}

        {/* Link to entity */}
        <Link
          href={`/entity/${node.entity_id}`}
          className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-gov-blue-200 bg-gov-blue-50 px-2.5 py-1.5 text-[11px] font-medium text-gov-blue-700 transition hover:bg-gov-blue-100"
        >
          Ver detalhes da entidade
          <ExternalLink className="h-3 w-3" />
        </Link>

        {/* Divider */}
        <div className="my-5 h-px bg-gray-100" />

        <div className="rounded-lg border border-amber-200 bg-amber-50 p-2.5">
          <p className="text-[11px] font-semibold text-amber-800">
            Por que esta entidade esta ligada ao padrao
          </p>
          <p className="mt-1 text-[11px] leading-relaxed text-amber-700">
            {whyLinked}
          </p>
        </div>

        {attrsToShow.length > 0 && (
          <div className="mt-3 rounded-lg border border-gray-100 bg-gray-50 p-2.5">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-500">
              Perfil publico
            </p>
            <div className="mt-1.5 grid grid-cols-1 gap-1.5">
              {attrsToShow.map(([key, value]) => (
                <div key={key} className="flex items-center justify-between rounded bg-white px-2 py-1">
                  <span className="text-[10px] font-medium text-gray-500">{key}</span>
                  <span className="ml-2 text-[10px] font-semibold text-gray-700">{String(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Related signals */}
        <div className="flex items-center gap-2">
          <ShieldAlert className="h-3.5 w-3.5 text-gray-400" />
          <h4 className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">
            Sinais associados
          </h4>
          {relatedSignals.length > 0 && (
            <span className="flex h-4.5 min-w-4.5 items-center justify-center rounded-full bg-red-50 px-1 text-[10px] font-bold text-red-600">
              {relatedSignals.length}
            </span>
          )}
        </div>

        {relatedSignals.length === 0 ? (
          <p className="mt-3 text-xs text-gray-400">
            Nenhum sinal diretamente associado a esta entidade.
          </p>
        ) : (
          <div className="mt-3 space-y-2.5">
            {relatedSignals.map((sig) => (
              <div
                key={sig.id}
                className="rounded-lg border border-gray-100 bg-gray-50/50 p-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <h5 className="text-[13px] font-medium leading-snug text-gray-800">
                    {sig.title}
                  </h5>
                  <span
                    className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold ${severityColor(sig.severity)}`}
                  >
                    {SEVERITY_LABELS[sig.severity]}
                  </span>
                </div>

                <p className="mt-1 text-[11px] text-gray-500">
                  <span className="font-mono text-gray-400">{sig.typology_code}</span>
                  {" — "}
                  {TYPOLOGY_LABELS[sig.typology_code] ?? sig.typology_name}
                </p>

                {/* Confidence */}
                <div className="mt-2.5 flex items-center gap-2">
                  <span className="text-[10px] font-medium text-gray-400">Confianca</span>
                  <div className="h-1.5 flex-1 rounded-full bg-gray-200">
                    <div
                      className="h-1.5 rounded-full bg-gov-blue-500 transition-all"
                      style={{ width: `${sig.confidence * 100}%` }}
                    />
                  </div>
                  <span className="text-[10px] font-semibold tabular-nums text-gray-500">
                    {Math.round(sig.confidence * 100)}%
                  </span>
                </div>

                {sig.summary && (
                  <p className="mt-2 text-[11px] leading-relaxed text-gray-500">
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
