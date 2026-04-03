import Link from "next/link";
import {
  Radar, Activity, BookOpen, ArrowRight, Shield, Code,
  FileText, Scale, TrendingUp, Database, Zap
} from "lucide-react";
import { OpenWatchLogoMark } from "@/components/OpenWatchLogo";
import { TYPOLOGY_LABELS, DATA_SOURCES } from "@/lib/constants";

const TYPOLOGY_SAMPLE = [
  { code: "T01", name: "Concentração de Fornecedores", severity: "high" },
  { code: "T06", name: "Empresa de Fachada", severity: "critical" },
  { code: "T07", name: "Rede de Cartel", severity: "critical" },
  { code: "T22", name: "Favorecimento Político", severity: "high" },
  { code: "T03", name: "Dispensa Irregular", severity: "medium" },
  { code: "T05", name: "Preço Superfaturado", severity: "high" },
];

const SEVERITY_COLORS: Record<string, string> = {
  critical: "var(--color-critical)",
  high: "var(--color-high)",
  medium: "var(--color-medium)",
  low: "var(--color-low)",
};

const PILLARS = [
  {
    icon: Code,
    title: "Tecnicamente Robusto",
    desc: "APIs governamentais em whitelist, código aberto, proveniência de dados auditável.",
  },
  {
    icon: FileText,
    title: "Metodologicamente Sólido",
    desc: "Tipologias com base legal, pontuação determinística, resultados reproduzíveis.",
  },
  {
    icon: Scale,
    title: "Juridicamente Responsável",
    desc: "Conformidade com LAI · Constituição · LGPD · Lei Anticorrupção.",
  },
  {
    icon: Shield,
    title: "Publicamente Auditável",
    desc: "Repositório open source, fontes de dados públicas, APIs transparentes.",
  },
];

export default function HomePage() {
  const typologyCount = Object.keys(TYPOLOGY_LABELS).length;
  const sourceCount = DATA_SOURCES.length;

  return (
    <div className="min-h-screen">
      {/* ── Hero ──────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden border-b border-[var(--color-border)]">
        {/* Background grid */}
        <div
          className="absolute inset-0 opacity-[0.04] pointer-events-none"
          style={{
            backgroundImage: `
              linear-gradient(var(--color-border) 1px, transparent 1px),
              linear-gradient(90deg, var(--color-border) 1px, transparent 1px)
            `,
            backgroundSize: "40px 40px",
          }}
        />

        {/* Amber glow */}
        <div
          className="absolute top-0 left-0 w-96 h-96 opacity-10 pointer-events-none"
          style={{
            background: "radial-gradient(circle at 30% 30%, var(--color-amber) 0%, transparent 70%)",
          }}
        />

        <div className="max-w-7xl mx-auto px-6 py-20 md:py-28 relative">
          <div className="max-w-3xl">
            {/* Eyebrow */}
            <div className="flex items-center gap-2 mb-6">
              <OpenWatchLogoMark size="sm" />
              <span className="text-label text-[var(--color-amber)]">
                Plataforma de Auditoria Cidadã
              </span>
            </div>

            <h1 className="text-display-2xl text-[var(--color-text)] mb-6">
              Inteligência investigativa sobre{" "}
              <span style={{ color: "var(--color-amber)" }}>
                dados federais
              </span>
            </h1>

            <p className="text-body-lg text-[var(--color-text-2)] mb-10 max-w-xl leading-relaxed">
              Sinais de risco de corrupção baseados em evidências extraídas de dados
              públicos. Determinístico, auditável, reproduzível. Open source,
              em conformidade com a LGPD.
            </p>

            <div className="flex flex-wrap gap-3">
              <Link
                href="/radar"
                className="ow-btn ow-btn-primary ow-btn-lg gap-2"
              >
                <Radar size={18} />
                Explorar Sinais
                <ArrowRight size={16} />
              </Link>
              <Link
                href="/methodology"
                className="ow-btn ow-btn-outline ow-btn-lg"
              >
                Ver Metodologia
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ── Stat Strip ───────────────────────────────────────────────── */}
      <section className="border-b border-[var(--color-border)] bg-[var(--color-surface-2)]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 divide-x divide-y md:divide-y-0 divide-[var(--color-border)]">
            {[
              { value: typologyCount, label: "Tipologias Ativas",  icon: TrendingUp, color: "var(--color-amber)" },
              { value: sourceCount,   label: "Fontes de Dados",    icon: Database,   color: "var(--color-trust)" },
              { value: "5",           label: "Etapas de Pipeline", icon: Zap,        color: "var(--color-info)" },
              { value: "100%",        label: "Reprodutível",       icon: Shield,     color: "var(--color-low)" },
            ].map((stat) => (
              <div key={stat.label} className="flex items-center gap-4 p-5 md:p-6">
                <div
                  className="w-8 h-8 rounded flex-center flex-shrink-0"
                  style={{ background: `${stat.color}18`, color: stat.color }}
                >
                  <stat.icon size={16} />
                </div>
                <div>
                  <div
                    className="font-display text-2xl font-bold tabular-nums"
                    style={{ color: stat.color, fontFamily: "var(--font-display)" }}
                  >
                    {stat.value}
                  </div>
                  <div className="text-caption text-[var(--color-text-3)] uppercase tracking-wider font-medium">
                    {stat.label}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Navigation Cards ─────────────────────────────────────────── */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-6">
          <div className="mb-10">
            <p className="text-label text-[var(--color-amber)] mb-2">Ponto de Entrada</p>
            <h2
              className="text-display-lg text-[var(--color-text)] mb-3"
            >
              Três caminhos para investigar
            </h2>
            <p className="text-body text-[var(--color-text-2)] max-w-lg">
              Do sinal ao caso, da fonte ao relatório — uma plataforma integrada
              para auditoria cidadã.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              {
                href: "/radar",
                icon: Radar,
                iconColor: "var(--color-amber)",
                iconBg: "var(--color-amber-dim)",
                label: "Investigação",
                title: "Radar de Risco",
                desc: "Sinais e casos classificados por tipologia, severidade e período. Ponto de partida para investigações cidadãs.",
                cta: "Explorar Sinais",
                delay: "0ms",
              },
              {
                href: "/coverage",
                icon: Activity,
                iconColor: "var(--color-trust)",
                iconBg: "#031218",
                label: "Monitoramento",
                title: "Cobertura de Dados",
                desc: "Status operacional de fontes e conectores. Monitore ingestão de pipeline, normalização e qualidade.",
                cta: "Ver Cobertura",
                delay: "50ms",
              },
              {
                href: "/methodology",
                icon: BookOpen,
                iconColor: "var(--color-info)",
                iconBg: "var(--color-info-bg)",
                label: "Referência",
                title: "Metodologia",
                desc: "Fundamentos técnicos e jurídicos das tipologias, fatores de risco e critérios de classificação de evidências.",
                cta: "Ler Metodologia",
                delay: "100ms",
              },
            ].map((card) => (
              <Link
                key={card.href}
                href={card.href}
                className="ow-card ow-card-hover group flex flex-col animate-slide-up"
                style={{ animationDelay: card.delay }}
              >
                <div className="ow-card-section flex-1">
                  <div className="flex items-start justify-between mb-4">
                    <div
                      className="w-9 h-9 rounded-lg flex-center"
                      style={{ background: card.iconBg, color: card.iconColor }}
                    >
                      <card.icon size={18} />
                    </div>
                    <ArrowRight
                      size={16}
                      className="text-[var(--color-text-3)] group-hover:text-[var(--color-amber)] transition-colors mt-1"
                    />
                  </div>

                  <div className="text-label mb-2" style={{ color: card.iconColor }}>
                    {card.label}
                  </div>
                  <h3
                    className="text-display-sm text-[var(--color-text)] mb-2 group-hover:text-[var(--color-amber)] transition-colors"
                  >
                    {card.title}
                  </h3>
                  <p className="text-body text-[var(--color-text-2)]">{card.desc}</p>
                </div>

                <div
                  className="ow-card-section border-t border-[var(--color-border)] flex items-center gap-1 text-sm font-medium transition-colors"
                  style={{ color: card.iconColor }}
                >
                  {card.cta}
                  <ArrowRight size={14} />
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ── Typologies Overview ───────────────────────────────────────── */}
      <section className="py-16 border-t border-[var(--color-border)] bg-[var(--color-surface-2)]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex-between mb-8 gap-4 flex-wrap">
            <div>
              <p className="text-label text-[var(--color-amber)] mb-2">Detecção</p>
              <h2 className="text-display-lg text-[var(--color-text)]">
                Tipologias de Risco
              </h2>
            </div>
            <Link
              href="/methodology"
              className="ow-btn ow-btn-outline ow-btn-sm gap-1.5"
            >
              Ver todas ({typologyCount})
              <ArrowRight size={14} />
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {TYPOLOGY_SAMPLE.map((t, i) => (
              <div
                key={t.code}
                className="ow-card flex items-start gap-3 p-4 animate-slide-up"
                style={{ animationDelay: `${i * 40}ms` }}
              >
                <div
                  className="w-1 self-stretch rounded-full flex-shrink-0"
                  style={{ background: SEVERITY_COLORS[t.severity] }}
                />
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-mono-sm text-[var(--color-text-3)]">{t.code}</span>
                    <span
                      className="ow-badge text-[10px]"
                      style={{
                        background: `${SEVERITY_COLORS[t.severity]}18`,
                        color: SEVERITY_COLORS[t.severity],
                        borderColor: `${SEVERITY_COLORS[t.severity]}40`,
                      }}
                    >
                      {t.severity}
                    </span>
                  </div>
                  <p className="text-body-sm text-[var(--color-text-2)] font-medium">
                    {t.name}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pillars ──────────────────────────────────────────────────── */}
      <section className="py-16 border-t border-[var(--color-border)]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="mb-10">
            <p className="text-label text-[var(--color-amber)] mb-2">Fundações</p>
            <h2 className="text-display-lg text-[var(--color-text)]">
              Construído para Confiança
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {PILLARS.map((p, i) => (
              <div
                key={p.title}
                className="ow-card p-5 animate-slide-up"
                style={{ animationDelay: `${i * 60}ms` }}
              >
                <div className="w-8 h-8 rounded-md bg-[var(--color-surface-3)] flex-center mb-4 text-[var(--color-amber)]">
                  <p.icon size={16} />
                </div>
                <h3 className="text-body font-semibold text-[var(--color-text)] mb-2">
                  {p.title}
                </h3>
                <p className="text-body-sm text-[var(--color-text-2)]">{p.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA strip ────────────────────────────────────────────────── */}
      <section
        className="border-t border-[var(--color-amber-border)] py-12"
        style={{ background: "var(--color-amber-dim)" }}
      >
        <div className="max-w-7xl mx-auto px-6 flex-between gap-6 flex-wrap">
          <div>
            <h2 className="text-display-md text-[var(--color-text)] mb-1">
              Pronto para investigar?
            </h2>
            <p className="text-body text-[var(--color-text-2)]">
              Explore {typologyCount} tipologias de risco e dados de {sourceCount} fontes governamentais.
            </p>
          </div>
          <Link href="/radar" className="ow-btn ow-btn-primary ow-btn-lg gap-2 flex-shrink-0">
            <Radar size={18} />
            Abrir Radar
            <ArrowRight size={16} />
          </Link>
        </div>
      </section>
    </div>
  );
}
