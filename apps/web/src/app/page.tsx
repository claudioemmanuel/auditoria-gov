// apps/web/src/app/page.tsx
import Link from "next/link";
import { CaseCard, Section } from "@/components/watchdog";
import type { CaseCardProps } from "@/components/watchdog";
import { TYPOLOGY_LABELS, DATA_SOURCES } from "@/lib/constants";

// Static placeholder cases — replace with API fetch when data layer is ready.
// These represent the "what we found today" feed on the home page.
const SAMPLE_CASES: CaseCardProps[] = [
  {
    id: "caso-001",
    riskLevel: "ALTO",
    title: "Contrato de R$ 12,4M com licitante único",
    company: "FORNECEDORA ÚNICA LTDA",
    agency: "Ministério da Gestão e da Inovação",
    signals: ["Licitante único", "Vencedor recorrente"],
    explanation:
      "Apenas uma empresa participou da licitação, reduzindo a competição e elevando o risco de sobrepreço.",
    flaggedAt: "há 2 horas",
  },
  {
    id: "caso-002",
    riskLevel: "CRÍTICO",
    title: "Fornecedor venceu 9 contratos do mesmo órgão em 90 dias",
    company: "PRESTADORA GERAL S/A",
    agency: "Secretaria de Infraestrutura do Estado",
    signals: ["Concentração de fornecedor", "Dispensa suspeita"],
    explanation:
      "O mesmo fornecedor ganhou contratos consecutivos do mesmo órgão sem alternância de concorrentes.",
    flaggedAt: "há 5 horas",
  },
];

// Static fallback stats — replace with API fetch when data layer is ready.
const STUB_FLAGGED_TODAY = 7;
const STUB_ANALYZED_24H = 128;

export default function HomePage() {
  const typologyCount = Object.keys(TYPOLOGY_LABELS).length;
  const sourceCount = DATA_SOURCES.length;

  return (
    <div className="max-w-5xl mx-auto px-6 py-10 space-y-14">

      {/* ── Header ───────────────────────────────────────────────────── */}
      <header className="space-y-3">
        <h1 className="text-2xl font-semibold text-[var(--color-text)]">
          OpenWatch
        </h1>
        <p className="text-sm text-[var(--color-text-3)]">
          Dinheiro público, sob escrutínio.
        </p>

        <div className="flex gap-6 text-sm text-[var(--color-text-2)]">
          <span>
            <strong
              className="tabular-nums"
              style={{ color: "var(--color-critical)" }}
            >
              {STUB_FLAGGED_TODAY}
            </strong>{" "}
            casos sinalizados hoje
          </span>
          <span>
            <strong className="tabular-nums">{STUB_ANALYZED_24H}</strong> analisados nas
            últimas 24h
          </span>
        </div>
      </header>

      {/* ── Primary action — one per screen ──────────────────────────── */}
      <div>
        <Link
          href="/radar"
          className="inline-flex items-center gap-2 bg-[var(--color-brand)] text-[var(--color-bg)] px-5 py-2.5 rounded-md text-sm font-semibold hover:bg-[var(--color-brand-light)] transition-colors"
        >
          Ver casos sinalizados
        </Link>
      </div>

      {/* ── Live cases ───────────────────────────────────────────────── */}
      <Section
        title="O que encontramos hoje"
        action={
          <Link
            href="/radar"
            className="text-xs text-[var(--color-text-3)] hover:text-[var(--color-brand-light)] transition-colors"
          >
            Ver todos →
          </Link>
        }
      >
        {/* Intentionally 2 cards, not 3 — avoids perfect symmetry */}
        <div className="grid md:grid-cols-2 gap-5">
          {SAMPLE_CASES.map((c) => (
            <CaseCard key={c.id} {...c} />
          ))}
        </div>
      </Section>

      {/* ── How it works ─────────────────────────────────────────────── */}
      <Section title="Como funciona">
        <p className="text-sm text-[var(--color-text-3)] max-w-xl">
          Analisamos dados federais públicos e destacamos padrões que podem
          indicar risco. Não acusamos — apontamos o que merece atenção.
        </p>

        <ol className="space-y-2 text-sm text-[var(--color-text-2)] list-decimal list-inside">
          <li>
            Coletamos dados de fontes governamentais oficiais (PNCP,
            ComprasGov, TCU)
          </li>
          <li>
            Detectamos padrões incomuns usando{" "}
            <strong>{typologyCount} tipologias</strong> pré-definidas
          </li>
          <li>
            Expomos os achados para escrutínio público —{" "}
            <strong>{sourceCount} fontes</strong> monitoradas
          </li>
        </ol>
      </Section>

      {/* Disclaimer — raw section intentional, no title needed */}
      <section className="text-xs text-[var(--color-text-3)] border-t border-[var(--color-border)] pt-6 max-w-xl">
        OpenWatch não acusa irregularidades. Destacamos padrões para que
        possam ser investigados. Os dados são extraídos de fontes oficiais do
        governo federal brasileiro.
      </section>
    </div>
  );
}
