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
    <div className="ow-content flex min-h-screen items-center justify-center">
      <div
        className="w-full max-w-lg rounded-xl border p-6"
        style={{
          background: "var(--color-critical-bg)",
          borderColor: "var(--color-critical-border)",
        }}
      >
        <div className="flex items-start gap-3">
          <AlertTriangle
            className="mt-0.5 h-5 w-5 flex-shrink-0"
            style={{ color: "var(--color-critical)" }}
            aria-hidden="true"
          />
          <div className="min-w-0">
            <h1
              className="font-display text-lg font-semibold"
              style={{ color: "var(--color-critical-text)" }}
            >
              Erro inesperado na aplicação
            </h1>
            <p
              className="mt-1 text-sm leading-relaxed"
              style={{ color: "var(--color-critical-text)", opacity: 0.8 }}
            >
              Encontramos uma falha em tempo de execução. O front manteve uma
              rota segura para você retomar o uso sem tela quebrada.
            </p>

            <div className="mt-5 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => reset()}
                className="ow-btn ow-btn-sm gap-1.5"
                style={{
                  background: "var(--color-critical-bg)",
                  borderColor: "var(--color-critical-border)",
                  color: "var(--color-critical-text)",
                }}
              >
                <RefreshCw className="h-4 w-4" aria-hidden="true" />
                Tentar novamente
              </button>

              <Link
                href="/api-health"
                className="ow-btn ow-btn-sm ow-btn-ghost"
                style={{ color: "var(--color-brand-light)" }}
              >
                Ver Saúde da API
              </Link>

              <Link href="/radar" className="ow-btn ow-btn-sm ow-btn-ghost">
                Voltar ao Radar
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
