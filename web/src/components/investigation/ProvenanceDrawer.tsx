"use client";

import { useEffect, useState, useCallback } from "react";
import { X, Download, Database, Clock, FileJson } from "lucide-react";
import { CONNECTOR_COLORS, CONNECTOR_LABELS } from "@/lib/constants";
import { getEventRawSources } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";
import JsonViewer from "@/components/JsonViewer";
import type { RawSourceItem } from "@/lib/types";

interface ProvenanceDrawerProps {
  open: boolean;
  onClose: () => void;
  eventId: string | null;
  rawSources?: RawSourceItem[];
}

export default function ProvenanceDrawer({
  open,
  onClose,
  eventId,
  rawSources: prefetched,
}: ProvenanceDrawerProps) {
  const [sources, setSources] = useState<RawSourceItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState(0);

  useEffect(() => {
    if (prefetched && prefetched.length > 0) {
      setSources(prefetched);
      setActiveTab(0);
      return;
    }

    if (!eventId || !open) return;

    setLoading(true);
    setError(null);
    getEventRawSources(eventId)
      .then((res) => {
        setSources(res.raw_sources || []);
        setActiveTab(0);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [eventId, open, prefetched]);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && open) onClose();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  const handleExport = useCallback(() => {
    const source = sources[activeTab];
    if (!source) return;
    const blob = new Blob([JSON.stringify(source.raw_data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `raw-source-${source.connector}-${source.raw_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [sources, activeTab]);

  const activeSource = sources[activeTab];
  const colors = activeSource ? CONNECTOR_COLORS[activeSource.connector] : null;
  const label = activeSource ? (CONNECTOR_LABELS[activeSource.connector] || activeSource.connector) : "";

  return (
    <div
      className={`fixed top-0 right-0 h-full w-full sm:w-[480px] z-50 bg-white shadow-2xl border-l border-gov-gray-200 transition-transform duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] ${
        open ? "translate-x-0" : "translate-x-full"
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-gov-gray-200 bg-gov-gray-50">
        <div className="flex items-center gap-3">
          <FileJson className="w-5 h-5 text-gov-blue-600" />
          <h2 className="font-semibold text-gov-gray-900">Dados Brutos</h2>
          {colors && (
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${colors.bg} ${colors.text}`}>
              {label}
            </span>
          )}
        </div>
        <button onClick={onClose} className="p-1.5 rounded-md hover:bg-gov-gray-200 text-gov-gray-500">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div className="h-[calc(100%-65px)] overflow-y-auto">
        {loading && (
          <div className="flex items-center justify-center h-40">
            <div className="w-6 h-6 border-2 border-gov-blue-200 border-t-gov-blue-600 rounded-full animate-spin" />
          </div>
        )}

        {error && (
          <div className="p-5">
            <div className="p-4 rounded-lg bg-red-50 text-red-800 text-sm">
              Erro ao carregar dados brutos: {error}
            </div>
          </div>
        )}

        {!loading && !error && sources.length === 0 && (
          <div className="flex flex-col items-center justify-center h-40 text-gov-gray-500">
            <Database className="w-8 h-8 mb-2 opacity-40" />
            <p className="text-sm">Dados de proveniencia indisponiveis</p>
            <p className="text-xs mt-1 text-gov-gray-400">Este evento foi criado antes do rastreamento de proveniencia</p>
          </div>
        )}

        {!loading && !error && sources.length > 0 && (
          <div className="p-5 space-y-4">
            {/* Source tabs (if multiple) */}
            {sources.length > 1 && (
              <div className="flex gap-1 overflow-x-auto pb-1">
                {sources.map((src, i) => {
                  const srcColors = CONNECTOR_COLORS[src.connector];
                  const srcLabel = CONNECTOR_LABELS[src.connector] || src.connector;
                  return (
                    <button
                      key={src.id}
                      onClick={() => setActiveTab(i)}
                      className={`flex-shrink-0 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                        i === activeTab
                          ? `${srcColors?.bg || "bg-gov-gray-100"} ${srcColors?.text || "text-gov-gray-800"} ring-1 ${srcColors?.ring || "ring-gov-gray-300"}`
                          : "bg-gov-gray-50 text-gov-gray-600 hover:bg-gov-gray-100"
                      }`}
                    >
                      {srcLabel}
                    </button>
                  );
                })}
              </div>
            )}

            {activeSource && (
              <>
                {/* Metadata */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    <Database className="w-3.5 h-3.5 text-gov-gray-400" />
                    <span className="text-gov-gray-600">raw_id:</span>
                    <code className="text-xs bg-gov-gray-100 px-1.5 py-0.5 rounded font-mono text-gov-gray-800">
                      {activeSource.raw_id}
                    </code>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-gov-gray-600 ml-5.5">job:</span>
                    <code className="text-xs bg-gov-gray-100 px-1.5 py-0.5 rounded font-mono text-gov-gray-800">
                      {activeSource.job}
                    </code>
                  </div>
                  {activeSource.created_at && (
                    <div className="flex items-center gap-2 text-sm">
                      <Clock className="w-3.5 h-3.5 text-gov-gray-400" />
                      <span className="text-gov-gray-600">Capturado em:</span>
                      <span className="text-gov-gray-800">{formatDateTime(activeSource.created_at)}</span>
                    </div>
                  )}
                </div>

                {/* JSON viewer */}
                <JsonViewer data={activeSource.raw_data} defaultExpand={2} />

                {/* Actions */}
                <div className="flex gap-2 pt-2">
                  <button
                    onClick={handleExport}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-gov-blue-50 text-gov-blue-700 hover:bg-gov-blue-100 transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Exportar JSON
                  </button>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
