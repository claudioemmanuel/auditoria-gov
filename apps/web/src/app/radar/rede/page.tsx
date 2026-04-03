"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Network, Search, Loader2 } from "lucide-react";
import { searchEntities } from "@/lib/api";
import type { EntitySearchResult } from "@/lib/types";
import { RadarBreadcrumb } from "@/components/radar/RadarBreadcrumb";

export default function NetworkSearchPage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<EntitySearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [manualId, setManualId] = useState("");

  const doSearch = useCallback(async () => {
    if (!query.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const data = await searchEntities(query.trim(), undefined, 20);
      setResults(data.items ?? []);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [query]);

  const handleManualNav = () => {
    const id = manualId.trim();
    if (id) router.push(`/radar/rede/${id}`);
  };

  return (
    <div className="mx-auto w-full max-w-[1280px] px-4 py-6 sm:px-6">
      <RadarBreadcrumb crumbs={[
        { label: "Radar", href: "/radar" },
        { label: "Rede" },
      ]} />

      <div className="mt-6 space-y-8">
        {/* Entity search */}
        <div>
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted">Explorador de Rede</p>
          <p className="text-sm text-secondary mt-1 mb-4">
            Busque uma entidade para visualizar suas conexoes no grafo de relacionamentos
          </p>

          <div className="flex gap-2">
            <label className="flex-1 flex items-center gap-2 rounded-xl border border-border bg-surface-card px-4 py-3">
              <Search className="h-4 w-4 text-muted shrink-0" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") doSearch(); }}
                placeholder="Buscar por nome, CNPJ, CPF..."
                className="flex-1 bg-transparent text-sm text-primary outline-none placeholder:text-placeholder"
              />
            </label>
            <button
              type="button"
              onClick={doSearch}
              disabled={loading || !query.trim()}
              className="inline-flex items-center gap-2 rounded-xl bg-accent px-5 py-3 text-sm font-semibold text-white hover:bg-accent/90 transition-colors disabled:opacity-50"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Buscar"}
            </button>
          </div>
        </div>

        {/* Search results */}
        {searched && !loading && results.length === 0 && (
          <div className="rounded-xl border border-border bg-surface-card p-8 text-center">
            <p className="text-sm text-secondary">Nenhuma entidade encontrada para &quot;{query}&quot;</p>
          </div>
        )}

        {results.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs text-muted">{results.length} resultado{results.length !== 1 ? "s" : ""}</p>
            {results.map((entity) => (
              <button
                key={entity.id}
                type="button"
                onClick={() => router.push(`/radar/rede/${entity.id}`)}
                className="group flex w-full items-center gap-3 rounded-xl border border-border bg-surface-card p-4 text-left transition-all hover:border-accent/40 hover:shadow-sm"
              >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent/10">
                  <Network className="h-4 w-4 text-accent" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-primary group-hover:text-accent transition-colors truncate">
                    {entity.name}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[10px] uppercase font-medium text-muted">{entity.type}</span>
                    {entity.identifiers && Object.entries(entity.identifiers).slice(0, 2).map(([k, v]) => (
                      <span key={k} className="font-mono text-[10px] text-muted">{v}</span>
                    ))}
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}

        {/* Manual UUID input */}
        <div className="border-t border-border pt-6">
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted mb-2">Acesso direto por ID</p>
          <div className="flex gap-2">
            <input
              type="text"
              value={manualId}
              onChange={(e) => setManualId(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") handleManualNav(); }}
              placeholder="Cole um Entity ID (UUID)..."
              className="flex-1 rounded-xl border border-border bg-surface-card px-4 py-2.5 text-sm text-primary placeholder:text-placeholder outline-none focus:border-accent/50 font-mono"
            />
            <button
              type="button"
              onClick={handleManualNav}
              disabled={!manualId.trim()}
              className="rounded-xl border border-border bg-surface-card px-4 py-2.5 text-sm font-medium text-secondary hover:border-accent/40 transition-colors disabled:opacity-50"
            >
              Ir
            </button>
          </div>
        </div>

        {/* Empty state */}
        {!searched && (
          <div className="rounded-xl border border-dashed border-border bg-surface-card p-16 text-center">
            <Network className="h-8 w-8 text-muted mx-auto mb-3 opacity-40" />
            <p className="text-sm font-medium text-secondary">Visualizador de rede</p>
            <p className="mt-1 text-xs text-muted max-w-sm mx-auto">
              Busque uma entidade ou cole um ID para explorar o grafo de conexoes e co-participacoes.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
