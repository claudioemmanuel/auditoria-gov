"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { getRadarV2Signals, getRadarV2SignalPreview } from "@/lib/api";
import type { RadarV2SignalItem, RadarV2SignalPreviewResponse } from "@/lib/types";
import { SignalCard } from "./SignalCard";
import { SignalInlineFilters } from "./SignalInlineFilters";
import { RadarDetailPanel } from "@/components/radar/RadarDetailPanel";
import { TableSkeleton } from "@/components/Skeleton";
import { Button } from "@/components/Button";

const PAGE_SIZE = 20;

export function SignalsSection() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const sigTypology  = searchParams.get("sig_typology") || "";
  const sigSeverity  = searchParams.get("sig_severity") || "";
  const sigSort      = searchParams.get("sig_sort") || "";
  const sigFrom      = searchParams.get("sig_from") || "";
  const sigTo        = searchParams.get("sig_to") || "";
  const sigOffset    = Number(searchParams.get("sig_offset") || "0");

  const updateParam = useCallback(
    (updates: Record<string, string>) => {
      const params = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(updates)) {
        if (value) { params.set(key, value); } else { params.delete(key); }
      }
      router.replace(`?${params.toString()}`, { scroll: false });
    },
    [router, searchParams],
  );

  const [search, setSearch]     = useState("");
  const [signals, setSignals]   = useState<RadarV2SignalItem[]>([]);
  const [total, setTotal]       = useState(0);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);

  // Detail panel
  const [panelOpen, setPanelOpen]           = useState(false);
  const [panelLoading, setPanelLoading]     = useState(false);
  const [panelError, setPanelError]         = useState<string | null>(null);
  const [signalPreview, setSignalPreview]   = useState<RadarV2SignalPreviewResponse | null>(null);
  const [activeSignalId, setActiveSignalId] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getRadarV2Signals({
      offset: sigOffset,
      limit: PAGE_SIZE,
      typology: sigTypology || undefined,
      severity: sigSeverity || undefined,
      sort: (sigSort as "analysis_date" | "ingestion_date") || undefined,
      period_from: sigFrom || undefined,
      period_to: sigTo || undefined,
    })
      .then((data) => {
        setSignals(data.items);
        setTotal(data.total);
      })
      .catch(() => setError("Erro ao carregar sinais."))
      .finally(() => setLoading(false));
  }, [sigOffset, sigTypology, sigSeverity, sigSort, sigFrom, sigTo]);

  const filteredSignals = useMemo(() => {
    if (!search.trim()) return signals;
    const q = search.toLowerCase();
    return signals.filter((s) => s.title.toLowerCase().includes(q));
  }, [signals, search]);

  const openSignalPanel = useCallback((signalId: string) => {
    setActiveSignalId(signalId);
    setPanelOpen(true);
    setPanelLoading(true);
    setPanelError(null);
    setSignalPreview(null);
    getRadarV2SignalPreview(signalId, { limit: 10 })
      .then(setSignalPreview)
      .catch(() => setPanelError("Nao foi possivel carregar a previa do sinal"))
      .finally(() => setPanelLoading(false));
  }, []);

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(sigOffset / PAGE_SIZE) + 1;

  return (
    <div className="flex flex-1 mx-auto w-full max-w-[1280px] relative">
      <div className={`flex-1 min-w-0 overflow-y-auto px-4 py-6 sm:px-6 transition-all ${panelOpen ? "lg:mr-[480px]" : ""}`}>
        {/* Header + filters */}
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-widest text-muted">Sinais Detectados</p>
            <p className="text-sm font-semibold text-primary mt-0.5">
              {loading ? "—" : `${total.toLocaleString("pt-BR")} sinais`}
            </p>
            <p className="text-xs text-secondary mt-0.5">
              Sinais individuais de irregularidade detectados pelo motor de analise
            </p>
          </div>
          <SignalInlineFilters
            search={search}
            onSearchChange={setSearch}
            typology={sigTypology}
            severity={sigSeverity}
            sort={sigSort}
            periodFrom={sigFrom}
            periodTo={sigTo}
            onTypologyChange={(v) => updateParam({ sig_typology: v, sig_offset: "" })}
            onSeverityChange={(v) => updateParam({ sig_severity: v, sig_offset: "" })}
            onSortChange={(v) => updateParam({ sig_sort: v, sig_offset: "" })}
            onPeriodFromChange={(v) => updateParam({ sig_from: v, sig_offset: "" })}
            onPeriodToChange={(v) => updateParam({ sig_to: v, sig_offset: "" })}
            onClearAll={() => {
              updateParam({ sig_typology: "", sig_severity: "", sig_sort: "", sig_from: "", sig_to: "", sig_offset: "" });
              setSearch("");
            }}
          />
        </div>

        {/* Error */}
        {error && (
          <div className="rounded-xl border border-error/20 bg-error/5 p-6 text-center">
            <p className="text-sm text-error">{error}</p>
            <Button variant="secondary" size="sm" className="mt-3" onClick={() => window.location.reload()}>
              Tentar novamente
            </Button>
          </div>
        )}

        {/* Loading */}
        {loading && !error && <TableSkeleton rows={6} />}

        {/* Empty */}
        {!loading && !error && filteredSignals.length === 0 && (
          <div className="rounded-xl border border-border bg-surface-card p-12 text-center">
            <p className="text-sm font-medium text-secondary">Nenhum sinal encontrado</p>
            <p className="mt-1 text-xs text-muted">Ajuste os filtros ou aguarde novos dados do pipeline.</p>
          </div>
        )}

        {/* Signal list */}
        {!loading && !error && filteredSignals.length > 0 && (
          <div className="space-y-3">
            {filteredSignals.map((s) => (
              <SignalCard
                key={s.id}
                signal={s}
                onClick={openSignalPanel}
                active={s.id === activeSignalId}
              />
            ))}
          </div>
        )}

        {/* Pagination */}
        {!loading && totalPages > 1 && (
          <div className="mt-6 flex items-center justify-between border-t border-border pt-4">
            <span className="text-xs text-muted">
              Pagina {currentPage} de {totalPages} · {total} sinais
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                disabled={currentPage <= 1}
                onClick={() => updateParam({ sig_offset: String(Math.max(0, sigOffset - PAGE_SIZE)) })}
              >
                <ChevronLeft className="h-3.5 w-3.5" />
                Anterior
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={currentPage >= totalPages}
                onClick={() => updateParam({ sig_offset: String(sigOffset + PAGE_SIZE) })}
              >
                Proxima
                <ChevronRight className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Detail panel */}
      <RadarDetailPanel
        open={panelOpen}
        type="signal"
        loading={panelLoading}
        error={panelError}
        signalPreview={signalPreview}
        casePreview={null}
        onClose={() => { setPanelOpen(false); setActiveSignalId(null); }}
      />
    </div>
  );
}
