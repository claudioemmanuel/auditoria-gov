import Link from "next/link";
import { DATA_SOURCES, TYPOLOGY_LABELS } from "@/lib/constants";
import { Radar, Database, BookOpen, ArrowRight } from "lucide-react";

export default function HomePage() {
  const typologyCount = Object.keys(TYPOLOGY_LABELS).length;
  const sourceCount = DATA_SOURCES.length;

  return (
    <div className="page-wrap">
      {/* Page header */}
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-primary">AuditorIA Gov</h1>
        <p className="mt-1 text-sm text-secondary">
          Plataforma de auditoria cidada para triagem de riscos em dados publicos federais.
        </p>
      </div>

      {/* Quick stats */}
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="linear-card px-4 py-3">
          <p className="text-2xl font-semibold text-primary">{typologyCount}</p>
          <p className="text-xs text-muted">Tipologias</p>
        </div>
        <div className="linear-card px-4 py-3">
          <p className="text-2xl font-semibold text-primary">{sourceCount}</p>
          <p className="text-xs text-muted">Fontes publicas</p>
        </div>
        <div className="linear-card px-4 py-3">
          <p className="text-2xl font-semibold text-primary">3</p>
          <p className="text-xs text-muted">Eixos de score</p>
        </div>
        <div className="linear-card px-4 py-3">
          <p className="text-2xl font-semibold text-primary">5</p>
          <p className="text-xs text-muted">Etapas do pipeline</p>
        </div>
      </div>

      {/* Quick links */}
      <div className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
        {[
          { href: "/radar", title: "Central de Riscos", desc: "Sinais de risco com filtros por tipologia e severidade", icon: Radar },
          { href: "/coverage", title: "Cobertura de Dados", desc: "Status e disponibilidade das fontes de dados", icon: Database },
          { href: "/methodology", title: "Metodologia", desc: "Como os indicadores e classificacoes sao calculados", icon: BookOpen },
        ].map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="linear-card group flex items-start gap-3 p-4 transition hover:border-accent/30"
          >
            <div className="rounded-lg bg-accent-subtle p-2">
              <item.icon className="h-4 w-4 text-accent" />
            </div>
            <div className="min-w-0 flex-1">
              <h3 className="text-sm font-medium text-primary">{item.title}</h3>
              <p className="mt-0.5 text-xs text-muted">{item.desc}</p>
            </div>
            <ArrowRight className="mt-1 h-3.5 w-3.5 text-muted transition group-hover:text-accent" />
          </Link>
        ))}
      </div>

      {/* Legal disclaimer */}
      <p className="text-xs leading-relaxed text-muted">
        <strong className="text-secondary">Aviso legal:</strong> Esta plataforma e um instrumento de
        triagem para controle social e auditoria cidada. Os resultados sao hipoteses investigaveis e{" "}
        <strong>nao configuram acusacao, prova definitiva ou juizo de culpa</strong>. Tratamento de
        dados conforme LGPD (Lei 13.709/2018), art. 7, VII.
      </p>
    </div>
  );
}
