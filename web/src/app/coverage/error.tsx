"use client";

import Link from "next/link";
import { AlertTriangle, RefreshCw } from "lucide-react";

export default function CoverageError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <div className="rounded-2xl border border-error/20 bg-error-subtle p-6">
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-0.5 h-5 w-5 text-error" />
          <div>
            <h1 className="font-display text-lg font-semibold text-error">Falha ao carregar Cobertura</h1>
            <p className="mt-1 text-sm text-error/80">
              Detectamos um problema na comunicação com a API. A tela não foi interrompida:
              tente novamente ou abra a Saúde da API para diagnóstico.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => reset()}
                className="inline-flex items-center gap-1 rounded-md border border-error/20 bg-surface-card px-3 py-1.5 text-sm font-medium text-error hover:bg-error-subtle"
              >
                <RefreshCw className="h-4 w-4" />
                Tentar novamente
              </button>
              <Link
                href="/api-health"
                className="inline-flex items-center rounded-md border border-accent/20 bg-accent-subtle px-3 py-1.5 text-sm font-medium text-accent hover:bg-accent-subtle"
              >
                Abrir Saúde API
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
