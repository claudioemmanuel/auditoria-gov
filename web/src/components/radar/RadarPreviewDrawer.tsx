"use client";

import Link from "next/link";
import type { RadarV2CasePreviewResponse, RadarV2SignalPreviewResponse } from "@/lib/types";
import { formatBRL, formatDate, normalizeUnknownDisplay } from "@/lib/utils";
import { SEVERITY_LABELS } from "@/lib/constants";
import { Badge } from "@/components/ui/Badge";
import { X } from "lucide-react";

interface RadarPreviewDrawerProps {
  open: boolean;
  type: "signal" | "case" | null;
  loading: boolean;
  error: string | null;
  signalPreview: RadarV2SignalPreviewResponse | null;
  casePreview: RadarV2CasePreviewResponse | null;
  onClose: () => void;
}

export function RadarPreviewDrawer({
  open,
  type,
  loading,
  error,
  signalPreview,
  casePreview,
  onClose,
}: RadarPreviewDrawerProps) {
  if (!open) return null;

  const signal = type === "signal" ? signalPreview : null;
  const caseData = type === "case" ? casePreview : null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30">
      <div className="h-full w-full max-w-2xl overflow-y-auto bg-white p-4 shadow-2xl">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 border-b border-gov-gray-200 pb-3">
          <div>
            <h3 className="text-lg font-semibold text-gov-gray-900">
              {type === "signal" ? "Previa do sinal" : "Previa do caso"}
            </h3>
            <p className="text-xs text-gov-gray-400">Entenda o padrão sem sair do Radar.</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 text-gov-gray-400 hover:bg-gov-gray-50"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {loading && (
          <p className="mt-4 text-sm text-gov-gray-600">Carregando previa...</p>
        )}
        {error && (
          <p className="mt-4 text-sm text-red-600">{error}</p>
        )}

        {/* Signal preview */}
        {signal && (
          <div className="mt-4 space-y-4">
            <div className="rounded-lg border border-gov-gray-200 bg-white p-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-base font-semibold text-gov-gray-900">{signal.signal.title}</p>
                  <p className="text-xs text-gov-gray-600">
                    {signal.signal.typology_code} — {signal.signal.typology_name}
                  </p>
                </div>
                <Badge severity={signal.signal.severity} dot />
              </div>
              {signal.signal.investigation_summary && (
                <p className="mt-2 text-sm text-gov-gray-600">
                  Razao sobre limite:{" "}
                  {signal.signal.investigation_summary.ratio_over_threshold != null
                    ? `${Number(signal.signal.investigation_summary.ratio_over_threshold).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}x`
                    : "Nao informado"}
                  {" | "}
                  Base legal: {signal.signal.investigation_summary.legal_reference || "Nao informada"}
                </p>
              )}
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-gov-gray-200 bg-gov-blue-50 p-3">
                <p className="text-xs font-semibold uppercase text-gov-blue-700">Onde começou</p>
                <p className="mt-1 text-sm text-gov-gray-900">
                  {signal.graph.pattern_story.started_at
                    ? formatDate(signal.graph.pattern_story.started_at)
                    : "Data nao informada"}
                </p>
              </div>
              <div className="rounded-lg border border-gov-gray-200 bg-gov-blue-50 p-3">
                <p className="text-xs font-semibold uppercase text-gov-blue-700">Para onde foi</p>
                <p className="mt-1 text-sm text-gov-gray-900">
                  {signal.graph.pattern_story.ended_at
                    ? formatDate(signal.graph.pattern_story.ended_at)
                    : "Data nao informada"}
                </p>
              </div>
            </div>

            <div className="rounded-lg border border-gov-gray-200 p-3">
              <p className="text-xs font-semibold uppercase text-gov-gray-400">
                Evidências ({signal.evidence.total})
              </p>
              <div className="mt-2 space-y-2">
                {signal.evidence.items.map((item) => (
                  <div key={item.event_id} className="rounded-md bg-gov-gray-50 p-2">
                    <p className="text-sm font-medium text-gov-gray-900">{item.description}</p>
                    <p className="mt-1 text-xs text-gov-gray-600">
                      {item.occurred_at ? formatDate(item.occurred_at) : "Sem data"}{" "}
                      {typeof item.value_brl === "number" ? `| ${formatBRL(item.value_brl)}` : ""}
                      {" | "}CATMAT: {normalizeUnknownDisplay(item.catmat_group)}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <Link
                href={`/signal/${signal.signal.id}`}
                className="rounded-md border border-gov-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gov-gray-600 hover:bg-gov-gray-50"
              >
                Abrir detalhe
              </Link>
              <Link
                href={`/signal/${signal.signal.id}/graph`}
                className="rounded-md border border-gov-gray-200 bg-gov-blue-50 px-3 py-1.5 text-xs font-medium text-gov-blue-700 hover:bg-gov-blue-50/80"
              >
                Ver teia
              </Link>
            </div>
          </div>
        )}

        {/* Case preview */}
        {caseData && (
          <div className="mt-4 space-y-4">
            <div className="rounded-lg border border-gov-gray-200 bg-white p-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-base font-semibold text-gov-gray-900">{caseData.case.title}</p>
                  <p className="text-xs text-gov-gray-600">
                    {caseData.case.signal_count} sinais conectados
                  </p>
                </div>
                <Badge severity={caseData.case.severity} dot />
              </div>
              {caseData.case.summary && (
                <p className="mt-2 text-sm text-gov-gray-600">{caseData.case.summary}</p>
              )}
            </div>

            <div className="rounded-lg border border-gov-gray-200 p-3">
              <p className="text-xs font-semibold uppercase text-gov-gray-400">Sinais associados</p>
              <div className="mt-2 space-y-2">
                {caseData.top_signals.map((sig) => (
                  <div key={sig.id} className="rounded-md bg-gov-gray-50 p-2">
                    <p className="text-sm font-medium text-gov-gray-900">{sig.title}</p>
                    <p className="mt-1 text-xs text-gov-gray-600">
                      {sig.typology_code} — {sig.typology_name} |{" "}
                      <span className="font-mono tabular-nums">{Math.round(sig.confidence * 100)}%</span>
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-lg border border-gov-gray-200 p-3 text-xs text-gov-gray-600">
              Teia do caso: <span className="font-mono tabular-nums">{caseData.graph.nodes.length}</span> entidades e{" "}
              <span className="font-mono tabular-nums">{caseData.graph.edges.length}</span> conexões.
            </div>

            <div className="flex flex-wrap gap-2">
              <Link
                href={`/case/${caseData.case.id}`}
                className="rounded-md border border-gov-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gov-gray-600 hover:bg-gov-gray-50"
              >
                Abrir detalhe
              </Link>
              <Link
                href={`/investigation/${caseData.case.id}`}
                className="rounded-md border border-gov-gray-200 bg-gov-blue-50 px-3 py-1.5 text-xs font-medium text-gov-blue-700 hover:bg-gov-blue-50/80"
              >
                Abrir investigacao
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
