import Link from "next/link";
import { DATA_SOURCES, TYPOLOGY_LABELS } from "@/lib/constants";
import { Scale, Shield, Code, FileText, Activity } from "lucide-react";

export default function HomePage() {
  const typologyCount = Object.keys(TYPOLOGY_LABELS).length;
  const sourceCount = DATA_SOURCES.length;

  const today = new Date().toLocaleDateString("pt-BR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  return (
    <div className="ledger-page min-h-screen flex flex-col">
      {/* ── Edition strip ─────────────────────────────────────── */}
      <div className="edition-strip bg-newsprint">
        <div className="mx-auto max-w-[1280px] px-4 sm:px-8 flex items-center justify-between">
          <span>OpenWatch · Edição Gov · v2</span>
          <span className="hidden sm:block">{today}</span>
          <span>LGPD · LAI · CF/88</span>
        </div>
      </div>

      {/* ── Masthead ──────────────────────────────────────────── */}
      <div className="bg-newsprint px-4 sm:px-8 pt-8 pb-6">
        <div className="mx-auto max-w-[1280px]">
          {/* Double rule above */}
          <div className="masthead-rule mb-6" />

          {/* Logotype */}
          <div className="text-center mb-4">
            <h1
              className="font-black uppercase leading-none tracking-[0.18em] sm:tracking-[0.25em]"
              style={{ fontSize: "clamp(2.5rem, 10vw, 7rem)" }}
            >
              OpenWatch
            </h1>
            <p
              className="mt-3 text-base leading-relaxed"
              style={{ color: "var(--color-muted)" }}
            >
              Sistema de Inteligência Investigativa sobre o Governo Federal Brasileiro
            </p>
          </div>

          {/* Double rule below */}
          <div className="masthead-rule mt-6" />

          {/* Stats byline — única linha mono */}
          <div className="text-center py-2 text-sm" style={{ fontFamily: "var(--font-mono)", color: "var(--color-muted)" }}>
            {typologyCount} tipologias ativas
            &nbsp;·&nbsp; {sourceCount} fontes públicas
            &nbsp;·&nbsp; 3 eixos de score
            &nbsp;·&nbsp; 5 etapas no pipeline
            &nbsp;·&nbsp;{" "}
            <span className="text-masthead font-bold">ATIVO</span>
          </div>

          {/* Bottom rule */}
          <div className="h-px bg-border mt-2" />
        </div>
      </div>

      {/* ── Navigation Cards — broadsheet 3 colunas ───────────── */}
      <div className="mx-auto w-full max-w-[1280px] px-4 sm:px-8 py-0">
        {/* Section label */}
        <div className="flex items-center gap-3 py-3 border-b border-border">
          <span className="section-flag">Central de Investigação</span>
        </div>

        {/* 3-column grid with column rules */}
        <div className="grid grid-cols-1 sm:grid-cols-3 border-b border-border">
          {[
            {
              href: "/radar",
              title: "Radar de Riscos",
              desc: "Sinais e casos classificados por tipologia, severidade e período. Ponto de entrada para investigações cidadãs sobre contratos e licitações federais.",
              tag: "PRINCIPAL",
              tagClass: "bg-masthead text-newsprint",
            },
            {
              href: "/coverage",
              title: "Cobertura de Dados",
              desc: "Estado operacional das fontes e conectores. Monitoramento do pipeline de ingestão, normalização e qualidade dos dados públicos.",
              tag: "OPERACIONAL",
              tagClass: "bg-ink-secondary text-newsprint",
            },
            {
              href: "/methodology",
              title: "Metodologia",
              desc: "Fundamentos técnicos e legais das tipologias, fatores de risco e critérios de classificação de evidência para auditoria cidadã.",
              tag: "REFERÊNCIA",
              tagClass: "bg-ink-muted text-newsprint",
            },
          ].map((item, i) => (
            <Link
              key={item.href}
              href={item.href}
              className={`nav-ledger-card relative group flex flex-col gap-3 p-6 transition-colors duration-100 hover:bg-newsprint-hover ${
                i < 2 ? "sm:col-rule" : ""
              }`}
            >
              <span
                className={`self-start font-mono text-[9px] font-bold tracking-[0.2em] uppercase px-2 py-1 ${item.tagClass}`}
              >
                {item.tag}
              </span>
              <h2 className="font-bold leading-snug text-xl">
                {item.title}
              </h2>
              <p className="text-[13px] leading-relaxed flex-1" style={{ color: "var(--color-muted)" }}>
                {item.desc}
              </p>
              <div className="byline text-masthead transition-colors group-hover:text-masthead-hover">
                ACESSAR →
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* ── Marco Institucional ───────────────────────────────── */}
      <div className="mx-auto w-full max-w-[1280px] px-4 sm:px-8">
        <div className="flex items-center gap-3 py-3 border-b border-border">
          <span className="section-flag">Marco Institucional</span>
          <Link
            href="/compliance"
            className="byline text-masthead hover:text-masthead-hover ml-auto"
          >
            VER COMPLIANCE →
          </Link>
        </div>

        {/* 4-column institutional grid with col rules */}
        <div className="grid grid-cols-1 gap-px bg-border sm:grid-cols-2 lg:grid-cols-4 border-b border-border">
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
              icon: Shield,
              title: "Publicamente Auditável",
              sub: "Open source, fontes públicas, GET /public/sources",
              badge: "ABERTO",
            },
          ].map((item) => (
            <div
              key={item.title}
              className="flex items-start gap-3 bg-newsprint p-5"
            >
              <span className="section-flag shrink-0 mt-0.5">{item.badge}</span>
              <div>
                <p
                  className="text-xs font-semibold text-ink leading-snug"
                  style={{ fontFamily: "var(--font-ibm-plex-serif, Georgia, serif)" }}
                >
                  {item.title}
                </p>
                <p className="mt-1 text-[11px] text-ink-muted leading-relaxed">
                  {item.sub}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Sistema & Conformidade ────────────────────────────── */}
      <div className="mx-auto w-full max-w-[1280px] px-4 sm:px-8 py-6 space-y-6">
        <div>
          <p className="byline mb-3">Sistema & Conformidade</p>
          <div className="flex flex-wrap gap-2">
            {[
              { href: "/api-health",           icon: Activity, label: "Saúde da API"       },
              { href: "/compliance",           icon: Scale,    label: "Conformidade Legal" },
              { href: "/methodology#base-legal",icon: FileText, label: "Base Legal"        },
              { href: "/methodology#escopo",   icon: Shield,   label: "Escopo & LGPD"     },
            ].map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="inline-flex items-center gap-1.5 border border-border bg-newsprint-card px-3 py-2 font-mono text-[10px] font-medium text-ink-secondary transition-colors duration-100 hover:border-ink hover:text-ink"
              >
                <link.icon className="h-3.5 w-3.5" />
                {link.label}
              </Link>
            ))}
          </div>
        </div>

        {/* ── Legal footer ─────────────────────────────────── */}
        <footer className="evidence-block border border-border bg-newsprint-card p-5">
          <div className="flex items-start gap-3">
            <Scale className="mt-0.5 h-4 w-4 shrink-0 text-ink-muted" />
            <p
              className="text-xs text-ink-muted leading-relaxed"
              style={{ fontFamily: "var(--font-ibm-plex-serif, Georgia, serif)" }}
            >
              <strong className="font-semibold text-ink-secondary">Aviso legal:</strong>{" "}
              Esta plataforma é um instrumento de triagem para controle social e auditoria cidadã.
              Os resultados representam hipóteses investigáveis baseadas em dados públicos e{" "}
              <strong className="font-medium text-ink-secondary">
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
