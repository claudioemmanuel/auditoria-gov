import Link from "next/link";
import { DATA_SOURCES, TYPOLOGY_LABELS } from "@/lib/constants";
import { Radar, Database, BookOpen, ArrowRight, Shield, Activity } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";

export default function HomePage() {
  const typologyCount = Object.keys(TYPOLOGY_LABELS).length;
  const sourceCount = DATA_SOURCES.length;

  return (
    <div>
      <PageHeader
        title="Inteligencia Investigativa"
        subtitle="Triagem automatizada de riscos em dados publicos federais. Sinais deterministicos, evidencias rastreáveis, investigacoes cidadas."
      />

      <div className="page-wrap pt-6">
        {/* KPIs operacionais */}
        <section className="mb-8">
          <h2 className="mb-3 font-display text-sm font-semibold uppercase tracking-wider text-muted">
            Visao Operacional
          </h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="surface-card px-4 py-3">
              <p className="font-mono tabular-nums text-2xl font-bold text-primary">{typologyCount}</p>
              <p className="text-xs text-secondary">Tipologias ativas</p>
            </div>
            <div className="surface-card px-4 py-3">
              <p className="font-mono tabular-nums text-2xl font-bold text-primary">{sourceCount}</p>
              <p className="text-xs text-secondary">Fontes publicas</p>
            </div>
            <div className="surface-card px-4 py-3">
              <p className="font-mono tabular-nums text-2xl font-bold text-primary">3</p>
              <p className="text-xs text-secondary">Eixos de score</p>
            </div>
            <div className="surface-card px-4 py-3">
              <p className="font-mono tabular-nums text-2xl font-bold text-primary">5</p>
              <p className="text-xs text-secondary">Etapas do pipeline</p>
            </div>
          </div>
        </section>

        {/* Atalhos investigativos */}
        <section className="mb-8">
          <h2 className="mb-3 font-display text-sm font-semibold uppercase tracking-wider text-muted">
            Atalhos Investigativos
          </h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {[
              {
                href: "/radar",
                title: "Central de Riscos",
                desc: "Sinais de risco classificados por tipologia, severidade e periodo. Ponto de entrada para investigacoes.",
                icon: Radar,
              },
              {
                href: "/coverage",
                title: "Cobertura de Dados",
                desc: "Status operacional das fontes e conectores. Monitoramento de ingestao e disponibilidade.",
                icon: Database,
              },
              {
                href: "/methodology",
                title: "Metodologia",
                desc: "Fundamentacao tecnica e legal das tipologias, fatores de risco e criterios de classificacao.",
                icon: BookOpen,
              },
            ].map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="surface-card group flex items-start gap-3 p-4 transition-colors duration-120 hover:border-accent/30"
              >
                <div className="rounded-[10px] bg-accent-subtle p-2">
                  <item.icon className="h-4 w-4 text-accent" />
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="font-display text-sm font-semibold text-primary">{item.title}</h3>
                  <p className="mt-0.5 text-xs leading-relaxed text-secondary">{item.desc}</p>
                </div>
                <ArrowRight className="mt-1 h-3.5 w-3.5 shrink-0 text-muted transition-colors group-hover:text-accent" />
              </Link>
            ))}
          </div>
        </section>

        {/* Acesso rapido */}
        <section className="mb-8 flex flex-wrap gap-2">
          <Link
            href="/api-health"
            className="inline-flex items-center gap-1.5 rounded-[10px] border border-border bg-surface-card px-3 py-1.5 text-xs font-medium text-secondary transition-colors hover:bg-surface-subtle hover:text-primary"
          >
            <Activity className="h-3.5 w-3.5" />
            Saude da API
          </Link>
          <Link
            href="/methodology"
            className="inline-flex items-center gap-1.5 rounded-[10px] border border-border bg-surface-card px-3 py-1.5 text-xs font-medium text-secondary transition-colors hover:bg-surface-subtle hover:text-primary"
          >
            <Shield className="h-3.5 w-3.5" />
            Transparencia e Conformidade
          </Link>
        </section>

        {/* Aviso legal */}
        <footer className="rounded-[10px] border border-amber/20 bg-amber-subtle px-4 py-3">
          <p className="text-xs leading-relaxed text-secondary">
            <strong className="font-semibold text-primary">Aviso legal:</strong> Esta plataforma e um
            instrumento de triagem para controle social e auditoria cidada. Os resultados representam
            hipoteses investigaveis baseadas em dados publicos e{" "}
            <strong className="font-semibold">
              nao configuram acusacao, prova definitiva ou juizo de culpa
            </strong>
            . Tratamento de dados conforme LGPD (Lei 13.709/2018), art. 7, VII — execucao de politicas
            publicas. Dados pessoais sao anonimizados conforme art. 12.
          </p>
        </footer>
      </div>
    </div>
  );
}
