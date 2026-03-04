import Link from "next/link";
import { DATA_SOURCES, TYPOLOGY_LABELS } from "@/lib/constants";
import {
  Radar,
  Database,
  BookOpen,
  Activity,
  Shield,
  ArrowRight,
  GitBranch,
  Layers,
  Target,
  Scale,
  Code,
  FileText,
  Globe,
} from "lucide-react";

export default function HomePage() {
  const typologyCount = Object.keys(TYPOLOGY_LABELS).length;
  const sourceCount = DATA_SOURCES.length;

  return (
    <div className="min-h-screen flex flex-col">

      {/* ── Hero / System Identity ─────────────────────────────────── */}
      <div className="border-b border-border bg-surface-card">
        <div className="mx-auto max-w-[1280px] px-4 py-8 sm:px-6">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-accent-subtle border border-accent/20">
              <Shield className="h-6 w-6 text-accent" />
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="font-display text-2xl font-bold tracking-tight text-primary sm:text-3xl">
                  AuditorIA
                </h1>
                <span className="rounded-md border border-border bg-surface-base px-2 py-0.5 font-mono text-xs font-medium text-muted">
                  GOV · v2
                </span>
                <span className="rounded-md border border-success/30 bg-success/10 px-2 py-0.5 font-mono text-xs font-semibold text-success">
                  ATIVO
                </span>
              </div>
              <p className="mt-1.5 max-w-2xl text-sm text-secondary leading-relaxed">
                Sistema de inteligência investigativa sobre dados públicos federais.
                Sinais determinísticos, evidências rastreáveis, hipóteses auditáveis.
              </p>
            </div>
          </div>

          {/* Operational metrics strip */}
          <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { icon: Target, value: typologyCount, label: "Tipologias ativas", mono: true },
              { icon: Database, value: sourceCount, label: "Fontes públicas", mono: true },
              { icon: Layers, value: "3", label: "Eixos de score", mono: true },
              { icon: GitBranch, value: "5", label: "Etapas do pipeline", mono: true },
            ].map((item) => (
              <div
                key={item.label}
                className="flex items-center gap-3 rounded-lg border border-border bg-surface-base px-3 py-2.5"
              >
                <item.icon className="h-4 w-4 shrink-0 text-accent" />
                <div>
                  <p className="font-mono tabular-nums text-lg font-bold text-primary leading-none">
                    {item.value}
                  </p>
                  <p className="mt-0.5 text-[11px] text-muted">{item.label}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Institutional positioning ──────────────────────────────── */}
      <div className="border-b border-border bg-surface-base/50">
        <div className="mx-auto max-w-[1280px] px-4 py-6 sm:px-6">
          <div className="flex items-center justify-between mb-4">
            <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-muted">
              Posicionamento Institucional
            </p>
            <Link
              href="/compliance"
              className="inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline"
            >
              Ver detalhes de compliance
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {[
              {
                icon: Code,
                title: "Tecnologicamente Robusto",
                sub: "Whitelist gov, código aberto, proveniência auditável",
                badge: "TÉCNICO",
              },
              {
                icon: FileText,
                title: "Metodologicamente Defensável",
                sub: "Tipologias com base legal, scoring determinístico",
                badge: "MÉTODO",
              },
              {
                icon: Scale,
                title: "Juridicamente Responsável",
                sub: "LAI + CF/88 + LGPD + Lei Anticorrupção",
                badge: "JURÍDICO",
              },
              {
                icon: Globe,
                title: "Publicamente Auditável",
                sub: "Open source, fontes públicas, GET /public/sources",
                badge: "ABERTO",
              },
            ].map((item) => (
              <div
                key={item.title}
                className="flex items-start gap-3 rounded-lg border border-border bg-surface-card px-4 py-3"
              >
                <item.icon className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-primary leading-snug">{item.title}</p>
                  <p className="mt-0.5 text-[11px] text-muted leading-relaxed">{item.sub}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Mission navigation ─────────────────────────────────────── */}
      <div className="flex-1 mx-auto w-full max-w-[1280px] px-4 py-8 sm:px-6 space-y-8">

        <section>
          <p className="mb-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-muted">
            Central de Investigação
          </p>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {[
              {
                href: "/radar",
                icon: Radar,
                title: "Radar de Riscos",
                desc: "Sinais e casos classificados por tipologia, severidade e período. Ponto de entrada para investigações cidadãs.",
                tag: "PRINCIPAL",
                tagClass: "bg-accent text-white",
              },
              {
                href: "/coverage",
                icon: Database,
                title: "Cobertura de Dados",
                desc: "Estado operacional das fontes e conectores. Monitoramento do pipeline de ingestão e qualidade dos dados.",
                tag: "OPERACIONAL",
                tagClass: "border border-border text-muted",
              },
              {
                href: "/methodology",
                icon: BookOpen,
                title: "Metodologia",
                desc: "Fundamentos técnicos e legais das tipologias, fatores de risco e critérios de classificação de evidência.",
                tag: "REFERÊNCIA",
                tagClass: "border border-border text-muted",
              },
            ].map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="group relative flex flex-col gap-3 rounded-xl border border-border bg-surface-card p-5 transition-all hover:border-accent/40 hover:bg-accent-subtle/10"
              >
                <div className="flex items-start justify-between">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent-subtle border border-accent/20">
                    <item.icon className="h-4 w-4 text-accent" />
                  </div>
                  <span className={`rounded-md px-1.5 py-0.5 text-[10px] font-semibold tracking-wide ${item.tagClass}`}>
                    {item.tag}
                  </span>
                </div>
                <div>
                  <h2 className="font-display text-sm font-bold text-primary">{item.title}</h2>
                  <p className="mt-1 text-xs text-secondary leading-relaxed">{item.desc}</p>
                </div>
                <div className="flex items-center gap-1 text-xs font-medium text-muted transition-colors group-hover:text-accent">
                  Acessar
                  <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
                </div>
              </Link>
            ))}
          </div>
        </section>

        {/* ── System links ─────────────────────────────────────────── */}
        <section>
          <p className="mb-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-muted">
            Sistema & Conformidade
          </p>
          <div className="flex flex-wrap gap-2">
            <Link
              href="/api-health"
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-card px-3 py-2 text-xs font-medium text-secondary transition hover:border-accent/30 hover:text-primary"
            >
              <Activity className="h-3.5 w-3.5" />
              Saúde da API
            </Link>
            <Link
              href="/compliance"
              className="inline-flex items-center gap-1.5 rounded-lg border border-accent/30 bg-accent-subtle/20 px-3 py-2 text-xs font-medium text-accent transition hover:border-accent/50 hover:bg-accent-subtle/30"
            >
              <Scale className="h-3.5 w-3.5" />
              Conformidade Legal
            </Link>
            <Link
              href="/methodology#base-legal"
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-card px-3 py-2 text-xs font-medium text-secondary transition hover:border-accent/30 hover:text-primary"
            >
              <FileText className="h-3.5 w-3.5" />
              Base Legal
            </Link>
            <Link
              href="/methodology#escopo"
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-card px-3 py-2 text-xs font-medium text-secondary transition hover:border-accent/30 hover:text-primary"
            >
              <Shield className="h-3.5 w-3.5" />
              Escopo & LGPD
            </Link>
          </div>
        </section>

        {/* ── Legal footer ─────────────────────────────────────────── */}
        <footer className="rounded-xl border border-border bg-surface-base p-4">
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
