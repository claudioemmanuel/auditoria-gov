import Link from "next/link";
import { Breadcrumb } from "@/components/Breadcrumb";
import { DATA_SOURCES } from "@/lib/constants";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  BookOpen,
  Brain,
  CheckCircle2,
  Clock3,
  Database,
  FileCheck2,
  Layers,
  Map,
  Network,
  Radar,
  Scale,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Users,
  Workflow,
} from "lucide-react";

const PRINCIPLES = [
  {
    title: "Sinal de Risco != Prova",
    desc: "A plataforma prioriza hipoteses investigaveis para triagem tecnica e controle social.",
    icon: ShieldAlert,
  },
  {
    title: "Evidencia Reproduzivel",
    desc: "Cada sinal deve manter fatores numericos, contexto e referencias de origem auditaveis.",
    icon: FileCheck2,
  },
  {
    title: "LGPD-by-Design",
    desc: "Tratamento orientado por finalidade publica, minimizacao de dados e boa pratica de governanca.",
    icon: ShieldCheck,
  },
];

const SCORE_DIMENSIONS = [
  {
    name: "Severidade",
    icon: AlertTriangle,
    tone: "text-red-600",
    desc: "Mede impacto potencial e magnitude do desvio observado.",
    bullets: [
      "Baseada em desvio estatistico e relevancia financeira/operacional.",
      "Classificada em Baixo, Medio, Alto e Critico.",
      "Nao define culpabilidade, apenas prioridade de analise.",
    ],
  },
  {
    name: "Confianca",
    icon: Scale,
    tone: "text-gov-blue-700",
    desc: "Mede o quanto o padrao observado e consistente nos dados disponiveis.",
    bullets: [
      "Considera volume amostral, estabilidade e coerencia entre fatores.",
      "Baselines e estratificacoes reduzem ruído e falso positivo.",
      "Confianca baixa exige verificacao adicional antes de escalar o caso.",
    ],
  },
  {
    name: "Completude",
    icon: CheckCircle2,
    tone: "text-emerald-700",
    desc: "Mede qualidade e disponibilidade de evidencia para sustentar a leitura.",
    bullets: [
      "Avalia quantidade e qualidade das fontes vinculadas ao sinal.",
      "Sinais com baixa completude devem ser tratados como observacao.",
      "A cobertura da fonte impacta diretamente esse eixo.",
    ],
  },
];

const PIPELINE_STEPS = [
  {
    step: "1",
    title: "Ingestao e Catalogacao",
    desc: "Coleta automatica em fontes publicas com metadados de recencia e status por job.",
    icon: Database,
  },
  {
    step: "2",
    title: "Normalizacao Canonica",
    desc: "Padronizacao de contratos, participantes, valores, periodos e identificadores.",
    icon: Layers,
  },
  {
    step: "3",
    title: "Resolucao de Entidades",
    desc: "Matching deterministico e probabilistico para consolidar pessoas, empresas e orgaos.",
    icon: Users,
  },
  {
    step: "4",
    title: "Baselines e Scores",
    desc: "Calculo de distribuicoes historicas, percentis e thresholds com fallback de escopo.",
    icon: BarChart3,
  },
  {
    step: "5",
    title: "Deteccao e Explicacao",
    desc: "Aplicacao das tipologias com registro de execucao (candidatos, criados, deduplicados, bloqueados), classificacao de risco e producao de explicacao interpretavel.",
    icon: Sparkles,
  },
];

const TYPOLOGIES = [
  { code: "T01", name: "Concentracao em Fornecedor", family: "Mercado", evidence: "indirect" as const },
  { code: "T02", name: "Baixa Competicao", family: "Mercado", evidence: "indirect" as const },
  { code: "T03", name: "Fracionamento de Despesa", family: "Comportamento", evidence: "direct" as const },
  { code: "T04", name: "Aditivo Outlier", family: "Comportamento", evidence: "indirect" as const },
  { code: "T05", name: "Preco Outlier", family: "Preco", evidence: "direct" as const },
  { code: "T06", name: "Proxy de Empresa de Fachada", family: "Integridade", evidence: "proxy" as const },
  { code: "T07", name: "Rede de Cartel", family: "Rede", evidence: "indirect" as const },
  { code: "T08", name: "Sancao x Contrato", family: "Integridade", evidence: "direct" as const },
  { code: "T09", name: "Proxy de Folha Fantasma", family: "Pessoal", evidence: "proxy" as const },
  { code: "T10", name: "Terceirizacao Paralela", family: "Pessoal", evidence: "indirect" as const },
];

const EVIDENCE_LEVEL_LABELS: Record<string, { label: string; color: string; desc: string }> = {
  direct: {
    label: "Direto",
    color: "bg-green-100 text-green-700 border-green-200",
    desc: "Padrao viola diretamente uma regra legal especifica",
  },
  indirect: {
    label: "Indireto",
    color: "bg-yellow-100 text-yellow-700 border-yellow-200",
    desc: "Anomalia estatistica consistente com o padrao de corrupcao",
  },
  proxy: {
    label: "Proxy",
    color: "bg-orange-100 text-orange-700 border-orange-200",
    desc: "Indicador associado ao veiculo de risco, nao ao ato em si",
  },
};

const LIMITATIONS = [
  "A qualidade do resultado depende da completude e recencia das fontes publicas disponiveis.",
  "Modelos estatisticos e heuristicas de rede podem gerar falsos positivos e falsos negativos.",
  "Resolucao de entidades e probabilistica em parte dos cenarios e exige revisao humana em casos sensiveis.",
  "Ausencia de dado em uma fonte nao comprova inexistencia do fato; pode ser lacuna de cobertura. Consulte o painel de Confiabilidade no Radar para verificar se a tipologia foi executada com sucesso.",
  "A plataforma nao substitui auditoria oficial, controle interno, investigacao ou decisao judicial.",
];

export default function MethodologyPage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <Breadcrumb items={[{ label: "Metodologia" }]} />

      <section className="mt-4 rounded-2xl border border-gov-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-start gap-3">
          <div className="rounded-xl bg-gov-blue-50 p-2.5">
            <BookOpen className="h-6 w-6 text-gov-blue-600" />
          </div>
          <div className="min-w-0">
            <h1 className="text-3xl font-bold tracking-tight text-gov-gray-900">
              Metodologia e Governanca Tecnica
            </h1>
            <p className="mt-2 max-w-4xl text-sm text-gov-gray-600">
              Esta pagina descreve como o AuditorIA Gov transforma dados publicos em sinais de risco,
              como os scores devem ser interpretados e quais limites devem ser considerados na leitura.
            </p>
          </div>
        </div>

        <div className="mt-4 rounded-xl border border-yellow-200 bg-yellow-50 p-4 text-sm text-yellow-900">
          <strong>Leitura obrigatoria:</strong> o sistema indica risco tecnico para priorizacao de
          analise. Nao produz acusacao, prova definitiva ou decisao administrativa/judicial.
        </div>
      </section>

      <section className="mt-8">
        <div className="mb-3 flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-gov-gray-500" />
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gov-gray-600">
            Principios Institucionais
          </h2>
        </div>
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
          {PRINCIPLES.map((item) => (
            <article
              key={item.title}
              className="rounded-xl border border-gov-gray-200 bg-white p-5 shadow-sm"
            >
              <item.icon className="h-5 w-5 text-gov-blue-600" />
              <h3 className="mt-3 text-sm font-semibold text-gov-gray-900">{item.title}</h3>
              <p className="mt-1 text-sm text-gov-gray-600">{item.desc}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="mt-8 rounded-xl border border-gov-gray-200 bg-white p-6 shadow-sm">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-gov-gray-900">
          <Scale className="h-5 w-5 text-gov-blue-600" />
          Como Interpretar um Sinal
        </h2>
        <p className="mt-2 text-sm text-gov-gray-600">
          A leitura correta exige considerar os tres eixos abaixo em conjunto. Severidade alta sem
          completude adequada, por exemplo, indica prioridade de verificacao e nao conclusao final.
        </p>

        <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-3">
          {SCORE_DIMENSIONS.map((item) => (
            <article key={item.name} className="rounded-lg border border-gov-gray-200 bg-gov-gray-50 p-4">
              <div className="flex items-center gap-2">
                <item.icon className={`h-4 w-4 ${item.tone}`} />
                <h3 className="text-sm font-semibold text-gov-gray-900">{item.name}</h3>
              </div>
              <p className="mt-2 text-sm text-gov-gray-600">{item.desc}</p>
              <ul className="mt-3 space-y-1.5">
                {item.bullets.map((bullet) => (
                  <li key={bullet} className="text-xs text-gov-gray-600">
                    • {bullet}
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="mt-8">
        <div className="mb-3 flex items-center gap-2">
          <Workflow className="h-4 w-4 text-gov-gray-500" />
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gov-gray-600">
            Pipeline de Processamento
          </h2>
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5">
          {PIPELINE_STEPS.map((item) => (
            <article
              key={item.step}
              className="rounded-xl border border-gov-gray-200 bg-white p-4 shadow-sm"
            >
              <div className="flex items-center justify-between">
                <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-gov-blue-600 text-xs font-bold text-white">
                  {item.step}
                </span>
                <item.icon className="h-4 w-4 text-gov-blue-600" />
              </div>
              <h3 className="mt-3 text-sm font-semibold text-gov-gray-900">{item.title}</h3>
              <p className="mt-1 text-sm text-gov-gray-600">{item.desc}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="mt-8 rounded-xl border border-gov-gray-200 bg-white p-6 shadow-sm">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-gov-gray-900">
          <Scale className="h-5 w-5 text-gov-blue-600" />
          Classificacao Legal e Esferas
        </h2>
        <p className="mt-2 text-sm text-gov-gray-600">
          Cada tipologia mapeia para tipos de corrupcao (com artigos legais) e esferas de atuacao.
          Esses filtros estao disponiveis no Radar para busca por categoria juridica.
        </p>
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-gov-gray-500">Tipos de Corrupcao</p>
            <ul className="mt-2 space-y-1">
              {[
                ["Fraude em Licitacao", "Lei 14.133/2021"],
                ["Corrupcao Passiva", "art. 317 CP"],
                ["Corrupcao Ativa", "art. 333 CP"],
                ["Peculato", "art. 312 CP"],
                ["Lavagem de Dinheiro", "Lei 9.613/98"],
                ["Prevaricacao", "art. 319 CP"],
                ["Concussao", "art. 316 CP"],
                ["Nepotismo/Clientelismo", "Decreto 7.203/2010"],
              ].map(([name, ref]) => (
                <li key={name} className="flex items-center justify-between text-xs text-gov-gray-700">
                  <span>{name}</span>
                  <span className="font-mono text-gov-gray-400">{ref}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-gov-gray-500">Esferas</p>
            <ul className="mt-2 space-y-1">
              {[
                ["Administrativa/Burocratica", "Desvios dentro da maquina publica"],
                ["Privada", "Atores privados envolvidos em desvios"],
                ["Politica", "Nivel macro de decisao e influencia"],
                ["Sistemica", "Redes coordenadas multi-ator"],
              ].map(([name, desc]) => (
                <li key={name} className="text-xs text-gov-gray-700">
                  <span className="font-medium">{name}</span>
                  <span className="text-gov-gray-400"> — {desc}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <section className="mt-8 grid grid-cols-1 gap-6 xl:grid-cols-2">
        <article className="rounded-xl border border-gov-gray-200 bg-white p-6 shadow-sm">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-gov-gray-900">
            <Radar className="h-5 w-5 text-gov-blue-600" />
            Catalogo de Tipologias
          </h2>
          <p className="mt-2 text-sm text-gov-gray-600">
            O motor aplica 10 tipologias com thresholds especificos por contexto e baseline.
          </p>
          <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
            {TYPOLOGIES.map((item) => {
              const ev = EVIDENCE_LEVEL_LABELS[item.evidence];
              return (
                <div
                  key={item.code}
                  className="rounded-lg border border-gov-gray-200 bg-gov-gray-50 px-3 py-2"
                >
                  <div className="flex items-center justify-between">
                    <p className="font-mono text-xs font-semibold text-gov-blue-700">{item.code}</p>
                    <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${ev.color}`}>
                      {ev.label}
                    </span>
                  </div>
                  <p className="mt-0.5 text-sm font-medium text-gov-gray-900">{item.name}</p>
                  <p className="mt-0.5 text-xs text-gov-gray-500">Familia: {item.family}</p>
                </div>
              );
            })}
          </div>

          <div className="mt-4 rounded-lg border border-gov-gray-200 bg-gov-gray-50 p-3">
            <p className="text-xs font-semibold text-gov-gray-700">Nivel de Evidencia</p>
            <div className="mt-2 space-y-1">
              {Object.entries(EVIDENCE_LEVEL_LABELS).map(([key, ev]) => (
                <div key={key} className="flex items-center gap-2">
                  <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${ev.color}`}>
                    {ev.label}
                  </span>
                  <span className="text-xs text-gov-gray-600">{ev.desc}</span>
                </div>
              ))}
            </div>
          </div>
        </article>

        <article className="rounded-xl border border-gov-gray-200 bg-white p-6 shadow-sm">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-gov-gray-900">
            <Database className="h-5 w-5 text-gov-blue-600" />
            Fontes e Cobertura
          </h2>
          <p className="mt-2 text-sm text-gov-gray-600">
            Integracao com fontes publicas e abertas, com monitoramento de recencia e disponibilidade.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            {DATA_SOURCES.map((source) => (
              <span
                key={source}
                className="rounded-full border border-gov-blue-200 bg-gov-blue-50 px-3 py-1 text-xs font-medium text-gov-blue-700"
              >
                {source}
              </span>
            ))}
          </div>

          <div className="mt-5 rounded-lg border border-gov-gray-200 bg-gov-gray-50 p-3 text-sm text-gov-gray-600">
            <p className="flex items-center gap-2 font-medium text-gov-gray-800">
              <Clock3 className="h-4 w-4 text-gov-blue-600" />
              Cobertura e recencia influenciam diretamente a completude dos sinais.
            </p>
            <p className="mt-1">
              Consulte a aba de cobertura para avaliar disponibilidade por fonte, status de jobs e atrasos de ingestao.
            </p>
            <p className="mt-2">
              No Radar, o painel de Confiabilidade da Analise mostra o status de execucao de cada tipologia:
              quando executou pela ultima vez, quantos candidatos avaliou e se produziu sinais.
              Isso permite distinguir &quot;a tipologia rodou e nao encontrou nada&quot; de &quot;a tipologia nao pode rodar porque faltam dados.&quot;
            </p>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            <Link
              href="/coverage"
              className="inline-flex items-center gap-1 rounded-md bg-gov-blue-700 px-3 py-2 text-xs font-medium text-white transition hover:bg-gov-blue-800"
            >
              Ver Cobertura
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
            <Link
              href="/radar"
              className="inline-flex items-center gap-1 rounded-md border border-gov-gray-300 bg-white px-3 py-2 text-xs font-medium text-gov-gray-700 transition hover:bg-gov-gray-50"
            >
              Ir para o Radar
            </Link>
          </div>
        </article>
      </section>

      <section className="mt-8 rounded-xl border border-yellow-200 bg-yellow-50 p-6">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-gov-gray-900">
          <AlertCircle className="h-5 w-5 text-yellow-700" />
          Limitacoes e Boas Praticas de Uso
        </h2>
        <ul className="mt-3 space-y-2">
          {LIMITATIONS.map((item) => (
            <li key={item} className="flex items-start gap-2 text-sm text-gov-gray-700">
              <span className="mt-1.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-yellow-700" />
              {item}
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-6 rounded-xl border border-gov-gray-200 bg-white p-5 text-sm text-gov-gray-600 shadow-sm">
        <p className="flex items-start gap-2">
          <Map className="mt-0.5 h-4 w-4 shrink-0 text-gov-blue-600" />
          A metodologia evolui conforme expansao de cobertura nacional e melhoria de evidencia por UF/municipio.
          Ajustes de threshold, score e tipologias sao versionados para rastreabilidade tecnica.
        </p>
      </section>
    </div>
  );
}
