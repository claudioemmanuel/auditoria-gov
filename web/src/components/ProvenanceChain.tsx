"use client";

import { useState } from "react";
import { AlertTriangle, ChevronDown, ChevronRight, Database, FileJson, Loader2 } from "lucide-react";
import { CONNECTOR_COLORS, CONNECTOR_LABELS } from "@/lib/constants";
import { formatBRL, formatDate } from "@/lib/utils";
import type { SignalProvenanceResponse, RawSourceItem } from "@/lib/types";

interface ProvenanceChainProps {
  data: SignalProvenanceResponse | null;
  loading?: boolean;
  error?: string | null;
  onViewRawSource?: (rawSources: RawSourceItem[]) => void;
}

export default function ProvenanceChain({ data, loading, error, onViewRawSource }: ProvenanceChainProps) {
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(new Set());

  const toggleEvent = (eventId: string) => {
    setExpandedEvents((prev) => {
      const next = new Set(prev);
      if (next.has(eventId)) next.delete(eventId);
      else next.add(eventId);
      return next;
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-gov-blue-400" />
        <span className="ml-2 text-sm text-gov-gray-500">Carregando cadeia de evidencia...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 rounded-lg bg-red-50 text-red-800 text-sm flex items-center gap-2">
        <AlertTriangle className="w-4 h-4" />
        {error}
      </div>
    );
  }

  if (!data || data.events.length === 0) {
    return (
      <div className="p-4 rounded-lg bg-gov-gray-50 text-gov-gray-500 text-sm flex items-center gap-2">
        <Database className="w-4 h-4 opacity-40" />
        Dados de proveniencia indisponiveis para este sinal.
      </div>
    );
  }

  return (
    <div className="space-y-0">
      {/* Signal root */}
      <div className="flex items-start gap-3 pb-2">
        <div className="flex flex-col items-center">
          <div className="w-3 h-3 rounded-full bg-gov-blue-500 ring-4 ring-gov-blue-100 mt-1" />
          <div className="w-0.5 flex-1 bg-gov-gray-200 mt-1" />
        </div>
        <div>
          <p className="text-sm font-semibold text-gov-gray-900">{data.title}</p>
          {data.typology_code && (
            <span className="inline-block mt-0.5 px-1.5 py-0.5 rounded text-xs font-medium bg-gov-blue-50 text-gov-blue-700">
              {data.typology_code}
            </span>
          )}
        </div>
      </div>

      {/* Events */}
      {data.events.map((event, eventIdx) => {
        const isExpanded = expandedEvents.has(event.event_id);
        const isLast = eventIdx === data.events.length - 1;

        return (
          <div key={event.event_id} className="flex items-start gap-3">
            <div className="flex flex-col items-center">
              <div className="w-0.5 h-3 bg-gov-gray-200" />
              <div className="w-2.5 h-2.5 rounded-full bg-amber-400 ring-2 ring-amber-100" />
              {(!isLast || (isExpanded && event.raw_sources.length > 0)) && (
                <div className="w-0.5 flex-1 bg-gov-gray-200 mt-1" />
              )}
            </div>
            <div className="flex-1 pb-3">
              <button
                onClick={() => toggleEvent(event.event_id)}
                className="flex items-center gap-1 text-sm font-medium text-gov-gray-800 hover:text-gov-blue-700 transition-colors"
              >
                {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                Evento {event.event_id.slice(0, 8)}...
              </button>

              {/* Raw sources (expanded) */}
              {isExpanded && event.raw_sources.length > 0 && (
                <div className="mt-2 ml-5 space-y-2">
                  {event.raw_sources.map((src) => {
                    const colors = CONNECTOR_COLORS[src.connector];
                    const label = CONNECTOR_LABELS[src.connector] || src.connector;
                    return (
                      <div
                        key={src.id}
                        className="flex items-start gap-3 pl-4 border-l-2 border-gov-gray-200"
                      >
                        <div className="w-2 h-2 rounded-full bg-gov-gray-300 ring-2 ring-gov-gray-100 mt-1.5 -ml-[21px]" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${colors?.bg || "bg-gov-gray-100"} ${colors?.text || "text-gov-gray-800"}`}>
                              {label}
                            </span>
                            <code className="text-xs text-gov-gray-500 font-mono truncate">
                              {src.raw_id}
                            </code>
                          </div>
                          {src.created_at && (
                            <p className="text-xs text-gov-gray-400 mt-0.5">
                              Capturado: {formatDate(src.created_at)}
                            </p>
                          )}
                          {onViewRawSource && (
                            <button
                              onClick={() => onViewRawSource(event.raw_sources)}
                              className="mt-1 flex items-center gap-1 text-xs text-gov-blue-600 hover:text-gov-blue-800 transition-colors"
                            >
                              <FileJson className="w-3 h-3" />
                              Ver JSON bruto
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {isExpanded && event.raw_sources.length === 0 && (
                <p className="mt-1 ml-5 text-xs text-gov-gray-400 italic">
                  Sem dados brutos vinculados
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
