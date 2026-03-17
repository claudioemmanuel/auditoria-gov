"use client";

import { useState, useCallback, useEffect } from "react";
import { Network } from "lucide-react";
import { getGraphNeighborhood } from "@/lib/api";
import { PathFinder } from "./PathFinder";
import { EntityNetworkGraph } from "@/components/EntityNetworkGraph";
import { TableSkeleton } from "@/components/Skeleton";

interface NetworkSectionProps {
  initialEntityId?: string;
}

export function NetworkSection({ initialEntityId }: NetworkSectionProps) {
  const [entityId, setEntityId] = useState<string | null>(initialEntityId ?? null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadNeighborhood = useCallback(async (id: string) => {
    setEntityId(id);
    setLoading(true);
    setError(null);
    try {
      await getGraphNeighborhood(id, 2);
    } catch {
      setError("Erro ao carregar grafo de vizinhanca.");
    } finally {
      setLoading(false);
    }
  }, []);

  // Auto-load when initialEntityId changes
  useEffect(() => {
    if (initialEntityId && initialEntityId !== entityId) {
      setEntityId(initialEntityId);
    }
  }, [initialEntityId]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex flex-1 mx-auto w-full max-w-[1280px] relative">
      <div className="flex-1 min-w-0 px-4 py-6 sm:px-6 space-y-8">
      {/* Entity selector */}
      <div>
        <p className="font-mono text-[10px] uppercase tracking-widest text-muted">Grafo de Rede</p>
        <p className="text-xs text-secondary mt-0.5 mb-3">
          Insira o ID de uma entidade para visualizar suas conexoes no grafo
        </p>
        <div>
          <label className="text-xs text-muted mb-1 block">Entity ID (UUID)</label>
          <input
            type="text"
            placeholder="Ex: 3fa85f64-5717-4562-b3fc-2c963f66afa6"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                const val = (e.target as HTMLInputElement).value.trim();
                if (val) loadNeighborhood(val);
              }
            }}
            className="w-full rounded-xl border border-border bg-surface-card py-2.5 px-3 text-sm text-primary placeholder:text-placeholder outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/30 font-mono"
          />
          <p className="mt-1 text-[10px] text-muted">Pressione Enter para carregar o grafo</p>
        </div>
      </div>

      {/* Neighborhood graph */}
      {loading && <TableSkeleton rows={6} />}

      {error && (
        <div className="rounded-xl border border-error/20 bg-error/5 p-6 text-center">
          <p className="text-sm text-error">{error}</p>
        </div>
      )}

      {!loading && !error && entityId && (
        <div className="rounded-xl border border-border bg-surface-card p-4">
          <EntityNetworkGraph entityId={entityId} />
        </div>
      )}

      {!loading && !error && !entityId && (
        <div className="rounded-xl border border-dashed border-border bg-surface-card p-16 text-center">
          <Network className="h-8 w-8 text-muted mx-auto mb-3 opacity-40" />
          <p className="text-sm font-medium text-secondary">Visualizador de rede</p>
          <p className="mt-1 text-xs text-muted max-w-sm mx-auto">
            Insira o ID de uma entidade para explorar o grafo de conexoes e co-participacoes.
          </p>
        </div>
      )}

      {/* Path finder */}
      <div className="border-t border-border pt-6">
        <PathFinder initialSourceId={entityId ?? ""} />
      </div>
      </div>
    </div>
  );
}
