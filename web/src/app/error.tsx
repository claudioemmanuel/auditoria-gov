"use client";

import Link from "next/link";
import { AlertTriangle, RefreshCw } from "lucide-react";

export default function GlobalError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="pt-BR">
      <body className="min-h-screen bg-surface-base">
        <div className="mx-auto flex min-h-screen max-w-3xl items-center px-4 py-12">
          <div className="w-full rounded-2xl border border-error/20 bg-error-subtle p-6 shadow-sm">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 h-5 w-5 text-error" />
              <div>
                <h1 className="font-display text-lg font-semibold text-error">Erro inesperado na aplicacao</h1>
                <p className="mt-1 text-sm text-error/80">
                  Encontramos uma falha em tempo de execucao. O front manteve uma rota segura para
                  voce retomar o uso sem tela quebrada.
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
                    Ver Saude API
                  </Link>
                  <Link
                    href="/radar"
                    className="inline-flex items-center rounded-md border border-border bg-surface-card px-3 py-1.5 text-sm font-medium text-secondary hover:bg-surface-subtle"
                  >
                    Voltar ao Radar
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </body>
    </html>
  );
}
