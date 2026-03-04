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
      className={`fixed top-0 right-0 h-full w-full sm:w-[480px] z-50 bg-surface-card border-l border-border transition-transform duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] ${
        open ? "translate-x-0" : "translate-x-full"
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border bg-surface-base">
        <div className="flex items-center gap-3">
          <FileJson className="w-5 h-5 text-accent" />
          <h2 className="font-semibold text-primary">Dados Brutos</h2>
          {colors && (
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${colors.bg} ${colors.text}`}>
              {label}
            </span>
          )}
        </div>
        <button onClick={onClose} className="p-1.5 rounded-md hover:bg-surface-hover text-muted">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div className="h-[calc(100%-65px)] overflow-y-auto">
        {loading && (
          <div className="flex items-center justify-center h-40">
            <div className="w-6 h-6 border-2 border-accent/20 border-t-accent rounded-full animate-spin" />
          </div>
        )}

        {error && (
          <div className="p-5">
            <div className="p-4 rounded-lg bg-error-subtle text-error text-sm">
              Erro ao carregar dados brutos: {error}
            </div>
          </div>
        )}

        {!loading && !error && sources.length === 0 && (
          <div className="flex flex-col items-center justify-center h-40 text-muted">
            <Database className="w-8 h-8 mb-2 opacity-40" />
            <p className="text-sm">Dados de proveniencia indisponiveis</p>
            <p className="text-xs mt-1 text-muted">Este evento foi criado antes do rastreamento de proveniencia</p>
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
                          ? `${srcColors?.bg || "bg-surface-subtle"} ${srcColors?.text || "text-primary"} ring-1 ${srcColors?.ring || "ring-border"}`
                          : "bg-surface-base text-secondary hover:bg-surface-subtle"
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
                    <Database className="w-3.5 h-3.5 text-muted" />
                    <span className="text-secondary">raw_id:</span>
                    <code className="text-xs bg-surface-subtle px-1.5 py-0.5 rounded font-mono text-primary">
                      {activeSource.raw_id}
                    </code>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-secondary ml-5.5">job:</span>
                    <code className="text-xs bg-surface-subtle px-1.5 py-0.5 rounded font-mono text-primary">
                      {activeSource.job}
                    </code>
                  </div>
                  {activeSource.created_at && (
                    <div className="flex items-center gap-2 text-sm">
                      <Clock className="w-3.5 h-3.5 text-muted" />
                      <span className="text-secondary">Capturado em:</span>
                      <span className="text-primary">{formatDateTime(activeSource.created_at)}</span>
                    </div>
                  )}
                </div>

                {/* JSON viewer */}
                <JsonViewer data={activeSource.raw_data} defaultExpand={2} />

                {/* Actions */}
                <div className="flex gap-2 pt-2">
                  <button
                    onClick={handleExport}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-accent-subtle text-accent hover:bg-accent-subtle transition-colors"
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
