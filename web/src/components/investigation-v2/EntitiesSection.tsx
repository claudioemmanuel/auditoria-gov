"use client";

import { useState, useCallback } from "react";
import { Search } from "lucide-react";
import { searchEntities } from "@/lib/api";
import type { EntitySearchResult } from "@/lib/types";
import { EntitySearchBar } from "./EntitySearchBar";
import { EntityResultCard } from "./EntityResultCard";
import { TableSkeleton } from "@/components/Skeleton";

export function EntitiesSection() {
  const [results, setResults] = useState<EntitySearchResult[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = useCallback(async (query: string, type: string) => {
    setLoading(true);
    setError(null);
    setSearched(true);
    try {
      const data = await searchEntities(query, type || undefined, 20);
      setResults(data.items);
      setTotal(data.total);
    } catch {
      setError("Erro ao buscar entidades. Verifique a API.");
      setResults([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div className="flex flex-1 mx-auto w-full max-w-[1280px] relative">
      <div className="flex-1 min-w-0 px-4 py-6 sm:px-6">
      <div className="mb-6">
        <p className="font-mono text-[10px] uppercase tracking-widest text-muted">Busca de Entidades</p>
        <p className="text-xs text-secondary mt-0.5">
          Pesquise por nome, CNPJ ou identificador de entidades no sistema
        </p>
      </div>

      <EntitySearchBar onSearch={handleSearch} />

      <div className="mt-6">
        {loading && <TableSkeleton rows={4} />}

        {error && (
          <div className="rounded-xl border border-error/20 bg-error/5 p-6 text-center">
            <p className="text-sm text-error">{error}</p>
          </div>
        )}

        {!loading && !error && !searched && (
          <div className="rounded-xl border border-dashed border-border bg-surface-card p-16 text-center">
            <Search className="h-8 w-8 text-muted mx-auto mb-3 opacity-40" />
            <p className="text-sm font-medium text-secondary">Buscar entidades</p>
            <p className="mt-1 text-xs text-muted max-w-sm mx-auto">
              Digite o nome de uma empresa, pessoa ou orgao para explorar suas conexoes e sinais de risco.
            </p>
          </div>
        )}

        {!loading && !error && searched && results.length === 0 && (
          <div className="rounded-xl border border-border bg-surface-card p-12 text-center">
            <p className="text-sm font-medium text-secondary">Nenhuma entidade encontrada</p>
            <p className="mt-1 text-xs text-muted">Tente um termo diferente ou ajuste o filtro de tipo.</p>
          </div>
        )}

        {!loading && !error && results.length > 0 && (
          <>
            <p className="mb-3 text-xs text-muted">{total} resultado{total !== 1 ? "s" : ""}</p>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {results.map((entity) => (
                <EntityResultCard key={entity.id} entity={entity} />
              ))}
            </div>
          </>
        )}
      </div>
      </div>
    </div>
  );
}
