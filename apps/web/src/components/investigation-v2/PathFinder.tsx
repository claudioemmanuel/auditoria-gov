"use client";

import { useState, useCallback } from "react";
import { ArrowRight, Loader2 } from "lucide-react";
import { getGraphPath } from "@/lib/api";
import type { EntityPathResponse } from "@/lib/types";
import { Button } from "@/components/Button";
import { cn } from "@/lib/utils";

interface PathFinderProps {
  initialSourceId?: string;
}

export function PathFinder({ initialSourceId = "" }: PathFinderProps) {
  const [sourceId, setSourceId] = useState(initialSourceId);
  const [targetId, setTargetId] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<EntityPathResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const findPath = useCallback(async () => {
    if (!sourceId.trim() || !targetId.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await getGraphPath(sourceId.trim(), targetId.trim());
      setResult(data);
      if (!data.found) {
        setError("Nenhum caminho encontrado entre as entidades.");
      }
    } catch {
      setError("Erro ao buscar caminho. Verifique os IDs das entidades.");
    } finally {
      setLoading(false);
    }
  }, [sourceId, targetId]);

  return (
    <div className="space-y-3">
      <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
        Caminho entre Entidades
      </p>

      <div className="flex flex-wrap items-end gap-2">
        <div className="flex-1 min-w-[200px]">
          <label className="text-xs text-muted mb-1 block">Origem (Entity ID)</label>
          <input
            type="text"
            value={sourceId}
            onChange={(e) => setSourceId(e.target.value)}
            placeholder="ID da entidade origem"
            className="w-full rounded-lg border border-border bg-surface-card px-3 py-2 text-xs text-primary placeholder:text-placeholder outline-none focus:border-accent/50"
          />
        </div>
        <div className="flex-1 min-w-[200px]">
          <label className="text-xs text-muted mb-1 block">Destino (Entity ID)</label>
          <input
            type="text"
            value={targetId}
            onChange={(e) => setTargetId(e.target.value)}
            placeholder="ID da entidade destino"
            className="w-full rounded-lg border border-border bg-surface-card px-3 py-2 text-xs text-primary placeholder:text-placeholder outline-none focus:border-accent/50"
          />
        </div>
        <Button
          variant="primary"
          size="sm"
          onClick={findPath}
          disabled={loading || !sourceId.trim() || !targetId.trim()}
        >
          {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Encontrar Caminho"}
        </Button>
      </div>

      {error && (
        <div className="rounded-lg border border-error/20 bg-error/5 px-3 py-2 text-xs text-error">
          {error}
        </div>
      )}

      {result?.found && result.path.length > 0 && (
        <div className="rounded-xl border border-border bg-surface-card p-4">
          <p className="text-xs text-muted mb-3">
            {result.hops} salto{result.hops !== 1 ? "s" : ""} encontrado{result.hops !== 1 ? "s" : ""}
          </p>
          <div className="flex flex-wrap items-center gap-1">
            {result.path.map((node, i) => (
              <div key={node.entity_id} className="flex items-center gap-1">
                <span
                  className={cn(
                    "rounded-lg px-2.5 py-1 text-xs font-medium",
                    i === 0 || i === result.path.length - 1
                      ? "bg-accent/10 text-accent border border-accent/20"
                      : "bg-surface-subtle text-secondary",
                  )}
                >
                  {node.label}
                </span>
                {i < result.path.length - 1 && (
                  <div className="flex items-center gap-0.5 text-muted">
                    <div className="h-px w-4 bg-border" />
                    {result.edges[i] && (
                      <span className="text-[9px] text-muted">{result.edges[i].edge_type}</span>
                    )}
                    <ArrowRight className="h-3 w-3" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
