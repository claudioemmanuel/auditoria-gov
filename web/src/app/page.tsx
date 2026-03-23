import Link from "next/link";
import { DATA_SOURCES, TYPOLOGY_LABELS } from "@/lib/constants";
import {
  Radar,
  Database,
  BookOpen,
  Activity,
  Shield,
  GitBranch,
  Layers,
  Target,
  Scale,
  Code,
  FileText,
} from "lucide-react";

export default function HomePage() {
  const typologyCount = Object.keys(TYPOLOGY_LABELS).length;
  const sourceCount = DATA_SOURCES.length;

  return (
    <div className="min-h-screen flex flex-col">

      {/* ── Masthead ─────────────────────────────────────────────────── */}
      <div className="border-b border-border bg-surface-card scanline-texture">
        <div className="mx-auto max-w-[1280px] px-4 py-12 sm:px-8 sm:py-16">
          <div className="border-l-4 border-accent pl-6">
            <p className="section-kicker mb-4 text-accent/70">
              Plataforma de Auditoria Cidadã · Dados Federais · Brasil
            </p>
            <h1 className="font-display text-6xl font-black tracking-[-0.03em] text-primary sm:text-7xl mb-4 leading-none">
              OpenWatch
            </h1>
            <p
              className="max-w-xl text-base text-secondary leading-relaxed mb-6"
              style={{ fontFamily: "var(--font-serif)" }}
            >
              Sistema de inteligência investigativa sobre contratos, licitações e
              transferências do governo federal. Sinais determinísticos, evidências
              rastreáveis, hipóteses auditáveis.
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <span className="audit-stamp border border-border text-muted bg-surface-subtle">
                GOV · v2
              </span>
              <span className="audit-stamp border border-success/40 bg-success/8 text-success">
                ● ATIVO
              </span>
              <span className="audit-stamp border border-border text-muted bg-surface-subtle">
                LGPD · LAI · CF/88
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Live Statistics ──────────────────────────────────────────── */}
      <div className="border-b border-border bg-surface-base">
        <div className="mx-auto max-w-[1280px] px-4 sm:px-8">
          <div className="grid grid-cols-2 divide-x divide-border sm:grid-cols-4">
            {[
              { icon: Target,    value: typologyCount, label: "Tipologias ativas" },
              { icon: Database,  value: sourceCount,   label: "Fontes públicas"   },
              { icon: Layers,    value: "3",           label: "Eixos de score"    },
              { icon: GitBranch, value: "5",           label: "Etapas do pipeline"},
            ].map((item) => (
              <div key={item.label} className="flex flex-col gap-2 px-6 py-7 first:pl-0 last:pr-0">
                <p className="data-num text-5xl text-primary leading-none">
                  {item.value}
                </p>
                <div className="flex items-center gap-1.5">
                  <item.icon className="h-3.5 w-3.5 text-muted shrink-0" />
                  <p className="section-kicker">{item.label}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Institutional Framework ───────────────────────────────────── */}
      <div className="border-b border-border bg-border">
        <div className="mx-auto max-w-[1280px]">
          <div className="grid grid-cols-1 gap-px sm:grid-cols-2 lg:grid-cols-4">
            {[
              {
                icon: Code,
                title: "Tecnologicamente Robusto",
                sub: "Whitelist gov, código aberto, proveniência auditável",
                badge: "TÉCNICO",
                color: "text-accent",
              },
              {
                icon: FileText,
                title: "Metodologicamente Defensável",
                sub: "Tipologias com base legal, scoring determinístico",
                badge: "MÉTODO",
                color: "text-muted",
              },
              {
                icon: Scale,
                title: "Juridicamente Responsável",
                sub: "LAI + CF/88 + LGPD + Lei Anticorrupção",
                badge: "JURÍDICO",
                color: "text-muted",
              },
              {
                icon: Shield,
                title: "Publicamente Auditável",
                sub: "Open source, fontes públicas, GET /public/sources",
                badge: "ABERTO",
                color: "text-success",
              },
            ].map((item) => (
              <div
                key={item.title}
                className="flex items-start gap-3 bg-surface-card p-5"
              >
                <span className={`audit-stamp border border-border shrink-0 mt-0.5 ${item.color}`}>
                  {item.badge}
                </span>
                <div>
                  <p className="text-xs font-semibold text-primary leading-snug">{item.title}</p>
                  <p className="mt-1 text-[11px] text-muted leading-relaxed">{item.sub}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Navigation Cards ─────────────────────────────────────────── */}
      <div className="flex-1 mx-auto w-full max-w-[1280px] px-4 py-10 sm:px-8 space-y-10">

        <section>
          <p className="section-kicker mb-5">Central de Investigação</p>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {[
              {
                href: "/radar",
                icon: Radar,
                title: "Radar de Riscos",
                desc: "Sinais e casos classificados por tipologia, severidade e período. Ponto de entrada para investigações cidadãs.",
                tag: "PRINCIPAL",
                tagColor: "text-accent border-accent/30 bg-accent/5",
              },
              {
                href: "/coverage",
                icon: Database,
                title: "Cobertura de Dados",
                desc: "Estado operacional das fontes e conectores. Monitoramento do pipeline de ingestão e qualidade dos dados.",
                tag: "OPERACIONAL",
                tagColor: "text-amber border-amber/30 bg-amber/5",
              },
              {
                href: "/methodology",
                icon: BookOpen,
                title: "Metodologia",
                desc: "Fundamentos técnicos e legais das tipologias, fatores de risco e critérios de classificação de evidência.",
                tag: "REFERÊNCIA",
                tagColor: "text-muted border-border bg-surface-subtle",
              },
            ].map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="group card-interactive relative flex flex-col gap-3 rounded-[10px] border border-border bg-surface-card p-6 hover:border-accent/50"
              >
                <span className={`audit-stamp self-start border ${item.tagColor}`}>
                  {item.tag}
                </span>
                <h2 className="font-display text-lg font-bold text-primary leading-snug">{item.title}</h2>
                <p className="text-xs text-secondary leading-relaxed flex-1">{item.desc}</p>
                <div className="flex items-center gap-1 font-mono text-[11px] font-medium text-accent mt-1">
                  ACESSAR
                  <span className="transition-transform duration-150 group-hover:translate-x-1">→</span>
                </div>
              </Link>
            ))}
          </div>
        </section>

        {/* ── System links ─────────────────────────────────────────────── */}
        <section>
          <p className="section-kicker mb-3">Sistema & Conformidade</p>
          <div className="flex flex-wrap gap-2">
            <Link
              href="/api-health"
              className="inline-flex items-center gap-1.5 rounded-[6px] border border-border bg-surface-card px-3 py-2 font-mono text-[10px] font-medium text-secondary transition-colors duration-100 hover:border-accent/30 hover:text-primary"
            >
              <Activity className="h-3.5 w-3.5" />
              Saúde da API
            </Link>
            <Link
              href="/compliance"
              className="inline-flex items-center gap-1.5 rounded-[6px] border border-accent/30 bg-accent/5 px-3 py-2 font-mono text-[10px] font-medium text-accent transition-colors duration-100 hover:border-accent/50 hover:bg-accent/10"
            >
              <Scale className="h-3.5 w-3.5" />
              Conformidade Legal
            </Link>
            <Link
              href="/methodology#base-legal"
              className="inline-flex items-center gap-1.5 rounded-[6px] border border-border bg-surface-card px-3 py-2 font-mono text-[10px] font-medium text-secondary transition-colors duration-100 hover:border-accent/30 hover:text-primary"
            >
              <FileText className="h-3.5 w-3.5" />
              Base Legal
            </Link>
            <Link
              href="/methodology#escopo"
              className="inline-flex items-center gap-1.5 rounded-[6px] border border-border bg-surface-card px-3 py-2 font-mono text-[10px] font-medium text-secondary transition-colors duration-100 hover:border-accent/30 hover:text-primary"
            >
              <Shield className="h-3.5 w-3.5" />
              Escopo & LGPD
            </Link>
          </div>
        </section>

        {/* ── Legal footer ─────────────────────────────────────────────── */}
        <footer className="evidence-block rounded-[10px] border border-border bg-surface-card p-5">
          <div className="flex items-start gap-3">
            <Scale className="mt-0.5 h-4 w-4 shrink-0 text-muted" />
            <p className="text-xs text-muted leading-relaxed">
              <strong className="font-semibold text-secondary">Aviso legal:</strong>{" "}
              Esta plataforma é um instrumento de triagem para controle social e auditoria cidadã.
              Os resultados representam hipóteses investigáveis baseadas em dados públicos e{" "}
              <strong className="font-medium text-secondary">
                não configuram acusação, prova definitiva ou juízo de culpa
              </strong>
              . Tratamento de dados conforme LGPD (Lei 13.709/2018), art. 7, VII.
              Dados pessoais são anonimizados conforme art. 12.
            </p>
          </div>
        </footer>
      </div>
    </div>
  );
}
