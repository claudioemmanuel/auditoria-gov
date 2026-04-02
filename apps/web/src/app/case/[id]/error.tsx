"use client";

import Link from "next/link";
import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";

export default function CaseError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[case page error]", error);
  }, [error]);

  return (
    <div className="mx-auto max-w-5xl px-4 py-20 sm:px-6 flex flex-col items-center gap-4 text-center">
      <AlertTriangle className="h-8 w-8 text-error" />
      <div>
        <p className="text-sm font-semibold text-primary">Erro ao carregar o caso</p>
        <p className="mt-1 text-xs text-muted">{error.message}</p>
      </div>
      <div className="flex items-center gap-2 mt-2">
        <button
          type="button"
          onClick={reset}
          className="rounded-md border border-border bg-surface-card px-3 py-1.5 text-xs font-medium text-secondary hover:bg-surface-subtle"
        >
          Tentar novamente
        </button>
        <Link
          href="/radar"
          className="rounded-md bg-accent px-3 py-1.5 text-xs font-medium text-white hover:opacity-90"
        >
          Voltar ao Radar
        </Link>
      </div>
    </div>
  );
}
