"use client";

import Link from "next/link";
import { AlertTriangle, RefreshCw } from "lucide-react";

export default function ApiHealthError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <div className="rounded-2xl border border-red-200 bg-red-50 p-6 shadow-sm">
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-0.5 h-5 w-5 text-red-600" />
          <div>
            <h1 className="text-lg font-semibold text-red-800">Falha ao carregar Saude da API</h1>
            <p className="mt-1 text-sm text-red-700">
              O monitor encontrou um erro inesperado. Isso pode indicar indisponibilidade parcial
              da API ou instabilidade temporaria.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => reset()}
                className="inline-flex items-center gap-1 rounded-md border border-red-300 bg-white px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-100"
              >
                <RefreshCw className="h-4 w-4" />
                Tentar novamente
              </button>
              <Link
                href="/coverage"
                className="inline-flex items-center rounded-md border border-accent/20 bg-accent-subtle px-3 py-1.5 text-sm font-medium text-accent hover:bg-accent-subtle"
              >
                Ir para Cobertura
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
