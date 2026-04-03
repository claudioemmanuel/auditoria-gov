import Link from "next/link";
import { Radar, ArrowLeft, Search } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex min-h-[calc(100vh-48px)] flex-col items-center justify-center bg-[var(--color-surface-base)] px-4 py-20 text-center">
      {/* Icon */}
      <div
        className="mb-6 flex h-20 w-20 items-center justify-center rounded-full"
        style={{
          background: "rgba(220,38,38,0.08)",
          border: "2px solid rgba(220,38,38,0.20)",
        }}
        aria-hidden="true"
      >
        <Search className="h-9 w-9 text-[var(--color-error)]" />
      </div>

      {/* Status */}
      <p className="mb-2 font-mono text-[11px] font-bold uppercase tracking-[0.15em] text-[var(--color-text-muted)]">
        Erro 404
      </p>

      {/* Headline */}
      <h1 className="mb-3 font-[var(--font-display)] text-3xl font-bold text-[var(--color-text-primary)] md:text-4xl">
        Página não encontrada
      </h1>

      {/* Description */}
      <p className="mb-8 max-w-md text-base leading-relaxed text-[var(--color-text-secondary)]">
        A URL solicitada não existe nesta plataforma. Verifique o endereço ou
        retorne à página inicial para continuar sua investigação.
      </p>

      {/* Actions */}
      <div className="flex flex-wrap items-center justify-center gap-3">
        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-[var(--radius-sm)] bg-[var(--color-primary-dark)] px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-all duration-150 hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus)] focus-visible:ring-offset-2"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Ir para o início
        </Link>

        <Link
          href="/radar"
          className="inline-flex items-center gap-2 rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-surface-card)] px-5 py-2.5 text-sm font-semibold text-[var(--color-text-primary)] shadow-sm transition-all duration-150 hover:bg-[var(--color-surface-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus)] focus-visible:ring-offset-2"
        >
          <Radar className="h-4 w-4 text-[var(--color-accent)]" aria-hidden="true" />
          Abrir o Radar
        </Link>
      </div>
    </div>
  );
}
