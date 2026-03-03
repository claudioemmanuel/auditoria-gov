import Link from "next/link";
import { DATA_SOURCES, TYPOLOGY_LABELS } from "@/lib/constants";
import {
  Shield,
  Radar,
  Database,
  BookOpen,
  Search,
  Map,
  ShieldCheck,
  Scale,
  Workflow,
  FileCheck2,
  Clock3,
  Target,
  ArrowRight,
  AlertTriangle,
  Brain,
  Layers,
  BarChart3,
  CheckCircle2,
  Network,
  Users,
  Globe,
  Eye,
  Lock,
  Sparkles,
  Activity,
  Boxes,
  FileText,
} from "lucide-react";

/* ── Pipeline steps ────────────────────────────────────────────── */

const PIPELINE_STEPS = [
  {
    number: "1",
    title: "Ingestão de Dados",
    desc: "Conectores automatizados coletam dados de portais públicos federais (Compras.gov, PNCP, Portal da Transparência, entre outros). Cada registro é armazenado com hash de origem para rastreabilidade.",
    icon: Database,
  },
  {
    number: "2",
    title: "Normalização e Resolução",
    desc: "Os registros brutos são convertidos para um modelo canônico. Um motor de Entity Resolution conecta diferentes representações da mesma entidade (empresa, pessoa, órgão) em um grafo unificado.",
    icon: Network,
  },
  {
    number: "3",
    title: "Baselines Estatísticos",
    desc: "Calculamos referências como preço mediano por item (CATMAT), concentração de mercado (HHI) e frequência de aditivos. Esses baselines são a referência para definir o que é um desvio significativo.",
    icon: BarChart3,
  },
  {
    number: "4",
    title: "Detecção de Tipologias",
    desc: "10 detectores especializados rodam periodicamente, cruzando dados de múltiplas fontes para identificar padrões atípicos. Cada sinal gerado inclui fatores quantitativos, período de análise e referências.",
    icon: Brain,
  },
  {
    number: "5",
    title: "Triagem e Apresentação",
    desc: "Os sinais são classificados por severidade, confiança e completude. Sinais que compartilham entidades são agrupados em casos. Tudo é exposto para consulta pública com explicação e evidência.",
    icon: Eye,
  },
];

/* ── Principles ────────────────────────────────────────────────── */

const PRINCIPLES = [
  {
    title: "Sinal de Risco ≠ Prova",
    desc: "A plataforma identifica hipóteses investigáveis com base em padrões atípicos em dados públicos. Os sinais não configuram acusação, sanção ou juízo de culpa — a decisão final pertence aos órgãos competentes.",
    icon: AlertTriangle,
  },
  {
    title: "Evidência Reproduzível",
    desc: "Cada sinal mantém fatores numéricos, referências de origem com hash criptográfico e contexto auditável. Qualquer pessoa pode verificar as fontes e reproduzir a análise.",
    icon: FileCheck2,
  },
  {
    title: "Transparência de Cobertura",
    desc: "A plataforma expõe quais fontes estão ativas, quando cada tipologia executou, quantos candidatos avaliou e se a análise é limitada por dados indisponíveis.",
    icon: Activity,
  },
  {
    title: "LGPD-by-Design",
    desc: "Tratamento orientado por finalidade pública e interesse social (art. 7, VII). Minimização de dados pessoais, uso exclusivo de fontes públicas oficiais e governança técnica de acesso.",
    icon: Lock,
  },
];

/* ── Score dimensions ──────────────────────────────────────────── */

const SCORE_DIMENSIONS = [
  {
    name: "Severidade",
    tone: "bg-red-100 text-red-700",
    desc: "Impacto potencial e magnitude do desvio. Classificada em Baixo, Médio, Alto e Crítico com base em relevância financeira e operacional.",
    icon: AlertTriangle,
  },
  {
    name: "Confiança",
    tone: "bg-blue-100 text-blue-700",
    desc: "Consistência e solidez do padrão nos dados. Baselines estratificados e volume amostral reduzem falsos positivos.",
    icon: Scale,
  },
  {
    name: "Completude",
    tone: "bg-emerald-100 text-emerald-700",
    desc: "Qualidade e disponibilidade de evidência. Sinais com baixa completude são rebaixados de severidade automaticamente.",
    icon: CheckCircle2,
  },
];

/* ── Quick links ───────────────────────────────────────────────── */

const QUICK_LINKS = [
  {
    href: "/radar",
    title: "Central de Riscos",
    desc: "Sinais de risco com filtros por tipologia, severidade, tipo de corrupção e esfera jurídica",
    icon: Radar,
    cta: "Explorar sinais",
  },
  {
    href: "/coverage",
    title: "Cobertura de Dados",
    desc: "Status operacional, recência e disponibilidade das fontes com mapa de cobertura por UF",
    icon: Database,
    cta: "Ver cobertura",
  },
  {
    href: "/methodology",
    title: "Metodologia",
    desc: "Como os indicadores, limites, scores e classificações legais são calculados e aplicados",
    icon: BookOpen,
    cta: "Ler metodologia",
  },
];

/* ── Current scope ─────────────────────────────────────────────── */

const CURRENT_SCOPE = [
  {
    text: "Portal público de consulta com foco em sinais de risco, sem login ou cadastro.",
    icon: Globe,
  },
  {
    text: "Análise de dados públicos federais com trilha de evidências e explicabilidade por sinal.",
    icon: FileText,
  },
  {
    text: "Radar central para priorização de hipóteses com filtros por tipologia, severidade, corrupção e esfera.",
    icon: Radar,
  },
  {
    text: "Painel de cobertura com frescor por fonte, status de execução e mapa de cobertura.",
    icon: Activity,
  },
  {
    text: "10 tipologias de detecção cobrindo licitações, contratos, folha de pagamento e estruturas empresariais.",
    icon: Boxes,
  },
];

const ROADMAP_SCOPE = [
  {
    text: "Drill-down de cobertura por UF, município e órgão/UG/UASG.",
    icon: Map,
  },
  {
    text: "Fechamento do ciclo do dinheiro: repasse → contrato → execução → publicação.",
    icon: Workflow,
  },
  {
    text: "Redução de falsos positivos com baselines estratificados e qualidade de sinal.",
    icon: BarChart3,
  },
  {
    text: "Linha do tempo e checklist de limites por caso para apoiar triagem humana.",
    icon: Clock3,
  },
];

/* ── Page ──────────────────────────────────────────────────────── */

export default function HomePage() {
  const typologyCount = Object.keys(TYPOLOGY_LABELS).length;
  const sourceCount = DATA_SOURCES.length;

  return (
    <div>
      {/* ── Hero ───────────────────────────────────────────────── */}
      <section className="relative overflow-hidden bg-gradient-to-r from-gov-blue-900 to-gov-blue-800 py-20 text-white">
        <div className="absolute inset-0 opacity-[0.03]" style={{
          backgroundImage: "url(\"data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E\")",
        }} />
        <div className="relative mx-auto max-w-5xl px-4 text-center">
          <div className="mb-4 flex justify-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-white/10 backdrop-blur-sm">
              <Shield className="h-9 w-9 text-white" />
            </div>
          </div>
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">AuditorIA Gov</h1>
          <p className="mx-auto mt-4 max-w-2xl text-lg leading-relaxed text-gov-blue-100">
            Plataforma de auditoria cidadã para triagem de riscos em dados públicos federais.
            Controle social com evidência reproduzível, governança técnica e transparência completa de cobertura.
          </p>
          <div className="mt-8 flex flex-col justify-center gap-4 sm:flex-row">
            <Link
              href="/radar"
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-white px-6 py-3 font-semibold text-gov-blue-800 shadow-lg transition hover:bg-gov-blue-50 hover:shadow-xl"
            >
              <Search className="h-4 w-4" />
              Acessar a Central de Riscos
            </Link>
            <Link
              href="/methodology"
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/30 px-6 py-3 font-semibold text-white backdrop-blur-sm transition hover:bg-white/10"
            >
              <BookOpen className="h-4 w-4" />
              Ver Metodologia
            </Link>
          </div>

          {/* Stats strip */}
          <div className="mx-auto mt-10 flex max-w-lg flex-wrap justify-center gap-8">
            <div className="text-center">
              <p className="text-3xl font-bold">{typologyCount}</p>
              <p className="text-xs text-gov-blue-200">Tipologias de detecção</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold">{sourceCount}</p>
              <p className="text-xs text-gov-blue-200">Fontes públicas</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold">3</p>
              <p className="text-xs text-gov-blue-200">Eixos de score</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Principles ─────────────────────────────────────────── */}
      <section className="py-16">
        <div className="mx-auto max-w-6xl px-4">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-gov-gray-900">Princípios Fundamentais</h2>
            <p className="mx-auto mt-2 max-w-2xl text-sm text-gov-gray-500">
              Diretrizes que orientam cada decisão técnica e institucional da plataforma.
            </p>
          </div>
          <div className="mt-8 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {PRINCIPLES.map((item) => (
              <div
                key={item.title}
                className="rounded-lg border border-gov-gray-200 bg-white p-5 transition hover:shadow-sm"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gov-blue-100">
                  <item.icon className="h-5 w-5 text-gov-blue-700" />
                </div>
                <h3 className="mt-3 font-semibold text-gov-gray-900">{item.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-gov-gray-500">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pipeline ───────────────────────────────────────────── */}
      <section className="border-t border-gov-gray-200 bg-gov-gray-50 py-16">
        <div className="mx-auto max-w-6xl px-4">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-gov-gray-900">Como Funciona</h2>
            <p className="mx-auto mt-2 max-w-2xl text-sm text-gov-gray-500">
              O pipeline opera de forma automatizada e recorrente, desde a coleta de dados
              públicos até a apresentação dos sinais de risco para consulta cidadã.
            </p>
          </div>
          <div className="relative mt-10">
            {/* Connecting line (desktop) */}
            <div className="absolute left-[19px] top-0 hidden h-full w-0.5 bg-gov-gray-200 lg:left-1/2 lg:block lg:-translate-x-0.5" />

            <div className="space-y-6 lg:space-y-8">
              {PIPELINE_STEPS.map((step, idx) => (
                <div key={step.number} className="relative flex gap-4 lg:gap-0">
                  {/* Left side (desktop) */}
                  <div className={`hidden lg:flex lg:w-1/2 ${idx % 2 === 0 ? "lg:justify-end lg:pr-10" : "lg:order-2 lg:pl-10"}`}>
                    <div className="max-w-md rounded-lg border border-gov-gray-200 bg-white p-5 shadow-sm">
                      <div className="flex items-center gap-2">
                        <step.icon className="h-5 w-5 text-gov-blue-600" />
                        <h3 className="font-semibold text-gov-gray-900">{step.title}</h3>
                      </div>
                      <p className="mt-2 text-sm leading-relaxed text-gov-gray-600">{step.desc}</p>
                    </div>
                  </div>

                  {/* Center number (desktop) */}
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 border-gov-blue-600 bg-white text-sm font-bold text-gov-blue-700 lg:absolute lg:left-1/2 lg:top-4 lg:-translate-x-1/2 lg:z-10">
                    {step.number}
                  </div>

                  {/* Empty space for alternating layout (desktop) */}
                  <div className={`hidden lg:block lg:w-1/2 ${idx % 2 === 0 ? "lg:order-2" : ""}`} />

                  {/* Mobile card */}
                  <div className="flex-1 lg:hidden">
                    <div className="rounded-lg border border-gov-gray-200 bg-white p-4 shadow-sm">
                      <div className="flex items-center gap-2">
                        <step.icon className="h-5 w-5 text-gov-blue-600" />
                        <h3 className="font-semibold text-gov-gray-900">{step.title}</h3>
                      </div>
                      <p className="mt-2 text-sm leading-relaxed text-gov-gray-600">{step.desc}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Score Dimensions ───────────────────────────────────── */}
      <section className="border-t border-gov-gray-200 bg-white py-16">
        <div className="mx-auto max-w-5xl px-4">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-gov-gray-900">Três Eixos de Score</h2>
            <p className="mx-auto mt-2 max-w-2xl text-sm text-gov-gray-500">
              Cada sinal de risco é avaliado em três dimensões independentes.
              A separação evita que um único número simplifique uma avaliação complexa.
            </p>
          </div>
          <div className="mt-8 grid grid-cols-1 gap-5 sm:grid-cols-3">
            {SCORE_DIMENSIONS.map((dim) => (
              <div
                key={dim.name}
                className="rounded-lg border border-gov-gray-200 bg-white p-5 transition hover:shadow-sm"
              >
                <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${dim.tone}`}>
                  <dim.icon className="h-3.5 w-3.5" />
                  {dim.name}
                </span>
                <p className="mt-3 text-sm leading-relaxed text-gov-gray-600">{dim.desc}</p>
              </div>
            ))}
          </div>
          <p className="mt-4 text-center text-xs text-gov-gray-400">
            Detalhes completos na{" "}
            <Link href="/methodology" className="text-gov-blue-600 underline hover:text-gov-blue-700">
              página de Metodologia
            </Link>
            .
          </p>
        </div>
      </section>

      {/* ── Data sources ───────────────────────────────────────── */}
      <section className="border-t border-gov-gray-200 bg-gov-gray-50 py-16">
        <div className="mx-auto max-w-5xl px-4">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-gov-gray-900">Fontes de Dados Públicos</h2>
            <p className="mx-auto mt-2 max-w-2xl text-sm text-gov-gray-500">
              Todos os dados utilizados são de acesso público, obtidos exclusivamente de
              portais oficiais do governo federal. Nenhuma fonte privada é utilizada.
            </p>
          </div>
          <div className="mt-8 flex flex-wrap justify-center gap-2">
            {DATA_SOURCES.map((source) => (
              <span
                key={source}
                className="rounded-full border border-gov-gray-200 bg-white px-4 py-2 text-sm text-gov-gray-700 shadow-sm"
              >
                {source}
              </span>
            ))}
          </div>
          <p className="mt-4 text-center text-xs text-gov-gray-400">
            O status atualizado de cada fonte está disponível na{" "}
            <Link href="/coverage" className="text-gov-blue-600 underline hover:text-gov-blue-700">
              página de Cobertura
            </Link>
            .
          </p>
        </div>
      </section>

      {/* ── Typologies ─────────────────────────────────────────── */}
      <section className="border-t border-gov-gray-200 bg-white py-16">
        <div className="mx-auto max-w-5xl px-4">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-gov-gray-900">{typologyCount} Tipologias de Detecção</h2>
            <p className="mx-auto mt-2 max-w-2xl text-sm text-gov-gray-500">
              Cada tipologia é um detector especializado que busca um padrão específico de irregularidade
              em dados públicos. Todas operam sobre dados de licitações, contratos, folha de pagamento ou
              estruturas empresariais.
            </p>
          </div>
          <div className="mt-8 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(TYPOLOGY_LABELS).map(([code, name]) => (
              <div
                key={code}
                className="flex items-center gap-3 rounded-lg border border-gov-gray-200 bg-white px-4 py-3 transition hover:shadow-sm"
              >
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded bg-gov-blue-100 font-mono text-xs font-bold text-gov-blue-700">
                  {code}
                </span>
                <span className="text-sm text-gov-gray-700">{name}</span>
              </div>
            ))}
          </div>
          <p className="mt-4 text-center text-xs text-gov-gray-400">
            Detalhes de cada tipologia, classificação legal e nível de evidência na{" "}
            <Link href="/methodology" className="text-gov-blue-600 underline hover:text-gov-blue-700">
              Metodologia
            </Link>
            .
          </p>
        </div>
      </section>

      {/* ── Scope ──────────────────────────────────────────────── */}
      <section className="border-t border-gov-gray-200 bg-white py-16">
        <div className="mx-auto max-w-6xl px-4">
          <h2 className="text-2xl font-bold text-gov-gray-900">Escopo da Plataforma</h2>
          <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div className="rounded-lg border border-gov-gray-200 bg-white p-5">
              <h3 className="flex items-center gap-2 text-lg font-semibold text-gov-gray-900">
                <Target className="h-5 w-5 text-gov-blue-600" />
                Escopo Atual
              </h3>
              <ul className="mt-3 space-y-3">
                {CURRENT_SCOPE.map((item) => (
                  <li key={item.text} className="flex items-start gap-2 text-sm text-gov-gray-600">
                    <item.icon className="mt-0.5 h-4 w-4 shrink-0 text-gov-blue-500" />
                    {item.text}
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-lg border border-gov-gray-200 bg-gov-gray-50 p-5">
              <h3 className="flex items-center gap-2 text-lg font-semibold text-gov-gray-900">
                <Sparkles className="h-5 w-5 text-gov-blue-600" />
                Roadmap de Evolução
              </h3>
              <ul className="mt-3 space-y-3">
                {ROADMAP_SCOPE.map((item) => (
                  <li key={item.text} className="flex items-start gap-2 text-sm text-gov-gray-600">
                    <item.icon className="mt-0.5 h-4 w-4 shrink-0 text-gov-gray-400" />
                    {item.text}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* ── Explore ────────────────────────────────────────────── */}
      <section className="border-t border-gov-gray-200 bg-gov-gray-50 py-16">
        <div className="mx-auto max-w-5xl px-4">
          <h2 className="text-2xl font-bold text-gov-gray-900">Explorar a Plataforma</h2>
          <p className="mt-2 text-sm text-gov-gray-500">
            Acesse qualquer seção diretamente. Não é necessário cadastro ou login.
          </p>
          <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {QUICK_LINKS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="group rounded-lg border border-gov-gray-200 bg-white p-5 transition hover:border-gov-blue-300 hover:shadow-md"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gov-blue-100 transition group-hover:bg-gov-blue-200">
                  <item.icon className="h-5 w-5 text-gov-blue-700" />
                </div>
                <h3 className="mt-3 font-semibold text-gov-gray-900">{item.title}</h3>
                <p className="mt-1 text-sm text-gov-gray-500">{item.desc}</p>
                <span className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-gov-blue-600 transition group-hover:text-gov-blue-700">
                  {item.cta}
                  <ArrowRight className="h-3.5 w-3.5 transition group-hover:translate-x-0.5" />
                </span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ── Legal disclaimer ───────────────────────────────────── */}
      <section className="border-t border-gov-gray-200 bg-gov-gray-100 py-8">
        <div className="mx-auto max-w-4xl px-4 text-center">
          <p className="text-sm leading-relaxed text-gov-gray-500">
            <strong>Aviso legal:</strong> Esta plataforma é um instrumento de triagem para controle
            social e auditoria cidadã. Os resultados são hipóteses investigáveis baseadas em
            cruzamento automático de dados públicos e{" "}
            <strong>não configuram acusação, prova definitiva, sanção administrativa ou juízo de culpa</strong>.
            A decisão final pertence exclusivamente aos órgãos competentes (controle interno,
            auditoria, corregedoria, Ministério Público e Judiciário).
          </p>
          <p className="mt-2 text-xs text-gov-gray-400">
            Tratamento de dados conforme LGPD (Lei 13.709/2018), art. 7, VII —
            dados públicos com finalidade de controle social e interesse público.
          </p>
        </div>
      </section>
    </div>
  );
}
