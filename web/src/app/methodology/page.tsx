import { TYPOLOGY_LABELS, DATA_SOURCES } from "@/lib/constants";
import { TableOfContents } from "./TableOfContents";

// ── Local data maps ────────────────────────────────────────────────────────────

const TYPOLOGY_DESCRIPTIONS: Record<string, string> = {
  T01: "Órgão direciona parcela desproporcional do gasto a um único fornecedor ao longo do período analisado.",
  T02: "Licitações com número de participantes abaixo do esperado para o segmento e faixa de valor.",
  T03: "Despesas particionadas sistematicamente abaixo de limiares legais de modalidade licitatória.",
  T04: "Aditivos contratuais com valor ou extensão fora do intervalo histórico para o tipo de contrato.",
  T05: "Preço unitário contratado desvia significativamente da mediana de mercado para o mesmo item/serviço.",
  T06: "Empresa apresenta indicadores associados a sociedade de fachada: capital mínimo, CNAE inconsistente, endereço compartilhado.",
  T07: "Conjunto de empresas apresenta padrão de propostas coordenadas compatível com cartel em múltiplas licitações.",
  T08: "Fornecedor com contrato ativo consta em cadastro de sancionados (CEIS, CNEP, CEPIM) vigente.",
  T09: "Servidores com vínculo ativo não localizáveis na folha de pagamento do período ou com remuneração inconsistente.",
  T10: "Contratação terceirizada paralela a quadro próprio com sobreposição de função e órgão.",
};

const TYPOLOGY_SOURCES: Record<string, string[]> = {
  T01: ["PNCP", "Compras.gov.br"],
  T02: ["PNCP", "Compras.gov.br"],
  T03: ["PNCP", "ComprasNet Contratos"],
  T04: ["PNCP", "ComprasNet Contratos"],
  T05: ["PNCP", "Compras.gov.br"],
  T06: ["Receita Federal (CNPJ)"],
  T07: ["PNCP", "Compras.gov.br", "ComprasNet Contratos"],
  T08: ["Portal da Transparência", "PNCP"],
  T09: ["Portal da Transparência"],
  T10: ["Portal da Transparência", "Compras.gov.br"],
};

// ── Static content ─────────────────────────────────────────────────────────────

const PRINCIPLES = [
  {
    title: "Sinal de Risco != Prova",
    body: "A plataforma produz hipóteses investigáveis para triagem técnica e controle social, não conclusões definitivas. Severidade alta indica prioridade de análise, não culpabilidade.",
  },
  {
    title: "Evidência Reproduzível",
    body: "Cada sinal registra os fatores numéricos, contexto de execução e referências de origem. Qualquer auditor pode replicar o cálculo a partir das fontes públicas citadas.",
  },
  {
    title: "Transparência de Cobertura",
    body: "O painel de Confiabilidade no Radar informa quando cada tipologia executou, quantos candidatos avaliou e se produziu sinais — distinguindo 'não encontrou' de 'não pode rodar'.",
  },
  {
    title: "LGPD-by-Design",
    body: "Tratamento orientado por finalidade pública, minimização de dados pessoais e boa prática de governança. CPFs são hasheados e nunca persistidos em claro.",
  },
];

const PIPELINE_STEPS = [
  {
    n: 1,
    title: "Ingestão e Catalogação",
    desc: "Coleta automática em fontes públicas com metadados de recência e status por job.",
  },
  {
    n: 2,
    title: "Normalização Canônica",
    desc: "Padronização de contratos, participantes, valores, períodos e identificadores.",
  },
  {
    n: 3,
    title: "Resolução de Entidades",
    desc: "Matching determinístico e probabilístico para consolidar pessoas, empresas e órgãos.",
  },
  {
    n: 4,
    title: "Baselines e Scores",
    desc: "Cálculo de distribuições históricas, percentis e thresholds com fallback de escopo.",
  },
  {
    n: 5,
    title: "Detecção e Explicação",
    desc: "Aplicação das tipologias com registro de execução (candidatos, criados, deduplicados, bloqueados), classificação de risco e produção de explicação interpretável.",
  },
];

const SCORE_DIMENSIONS = [
  {
    name: "Severidade",
    desc: "Mede impacto potencial e magnitude do desvio observado. Baseada em desvio estatístico e relevância financeira/operacional. Classificada em Baixo, Médio, Alto e Crítico. Não define culpabilidade, apenas prioridade de análise.",
  },
  {
    name: "Confiança",
    desc: "Mede o quanto o padrão observado é consistente nos dados disponíveis. Considera volume amostral, estabilidade e coerência entre fatores. Confiança baixa exige verificação adicional antes de escalar o caso.",
  },
  {
    name: "Completude",
    desc: "Mede qualidade e disponibilidade de evidência para sustentar a leitura. Avalia quantidade e qualidade das fontes vinculadas ao sinal. Sinais com baixa completude devem ser tratados como observação preliminar.",
  },
];

const SCOPE_CURRENT = [
  "União Federal (orçamento federal direto)",
  "Contratos e licitações via PNCP e ComprasNet",
  "Folha de pagamento do Executivo Federal",
  "Empresas com CNPJ ativo na Receita Federal",
  "Sancionados nos cadastros CEIS, CNEP e CEPIM",
];

const SCOPE_ROADMAP = [
  "Estados e municípios com maior volume de contratação",
  "Transferências voluntárias via Transfere.gov",
  "Dados do TSE para cruzamento político-contratual",
  "Diários oficiais via Querido Diário (OCR)",
  "Histórico de preços de referência por categoria CATMAT/CATSER",
];

const LEGAL_REFS = [
  ["Fraude em Licitação", "Lei 14.133/2021"],
  ["Corrupção Passiva", "art. 317 CP"],
  ["Corrupção Ativa", "art. 333 CP"],
  ["Peculato", "art. 312 CP"],
  ["Lavagem de Dinheiro", "Lei 9.613/98"],
  ["Prevaricação", "art. 319 CP"],
  ["Concussão", "art. 316 CP"],
  ["Nepotismo/Clientelismo", "Decreto 7.203/2010"],
];

// ── Section heading ────────────────────────────────────────────────────────────

function SectionHeading({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <h2
      id={id}
      className="text-xl font-semibold text-gov-gray-900 mb-4 mt-10 pb-2 border-b border-gov-gray-200 scroll-mt-8"
    >
      {children}
    </h2>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function MethodologyPage() {
  return (
    <div>
      <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6">
        {/* Page title */}
        <h1 className="text-2xl font-bold text-gov-gray-900 tracking-tight">
          Metodologia AuditorIA Gov
        </h1>
        <p className="mt-2 text-sm text-gov-gray-600 leading-relaxed max-w-2xl">
          Como o sistema transforma dados públicos em sinais de risco, como interpretar os scores
          e quais limites considerar na leitura.
        </p>
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 max-w-2xl">
          <strong>Leitura obrigatória:</strong> sinais indicam risco técnico para priorização de
          análise. Não constituem acusação, prova definitiva ou decisão administrativa/judicial.
        </div>

        {/* Two-column layout */}
        <div className="mt-10 flex gap-12">
          {/* TOC — hidden on mobile */}
          <div className="hidden lg:block">
            <TableOfContents />
          </div>

          {/* Main content */}
          <div className="min-w-0 flex-1 max-w-2xl">

            {/* ── Princípios ── */}
            <SectionHeading id="principios">Princípios</SectionHeading>
            <div className="space-y-4">
              {PRINCIPLES.map((p) => (
                <div key={p.title}>
                  <h3 className="text-base font-semibold text-gov-gray-900 mb-1">{p.title}</h3>
                  <p className="text-sm text-gov-gray-600 leading-relaxed">{p.body}</p>
                </div>
              ))}
            </div>

            {/* ── Pipeline ── */}
            <SectionHeading id="pipeline">Pipeline</SectionHeading>
            <ol className="space-y-4">
              {PIPELINE_STEPS.map((step) => (
                <li key={step.n} className="flex gap-4">
                  <span className="font-mono tabular-nums text-sm font-bold text-gov-blue-700 shrink-0 w-6 pt-0.5">
                    {step.n}.
                  </span>
                  <div>
                    <h3 className="text-base font-semibold text-gov-gray-900 mb-1">{step.title}</h3>
                    <p className="text-sm text-gov-gray-600 leading-relaxed">{step.desc}</p>
                  </div>
                </li>
              ))}
            </ol>

            {/* ── Tipologias ── */}
            <SectionHeading id="tipologias">Tipologias</SectionHeading>
            <p className="text-sm text-gov-gray-600 leading-relaxed mb-6">
              O motor aplica 10 tipologias com thresholds específicos por contexto e baseline.
              A leitura de cada código deve considerar o nível de evidência: direto (viola regra
              legal específica), indireto (anomalia estatística) ou proxy (indicador associado ao
              veículo de risco).
            </p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {Object.entries(TYPOLOGY_LABELS).map(([code, name]) => {
                const sources = TYPOLOGY_SOURCES[code] ?? [];
                const desc = TYPOLOGY_DESCRIPTIONS[code] ?? "";
                return (
                  <div
                    key={code}
                    className="border border-gov-gray-200 rounded-lg p-4 bg-white"
                  >
                    <div className="flex items-baseline gap-2 mb-1">
                      <span className="font-mono font-bold text-gov-blue-700 text-sm">{code}</span>
                      <span className="text-sm font-semibold text-gov-gray-900">{name}</span>
                    </div>
                    {desc && (
                      <p className="text-xs text-gov-gray-600 leading-relaxed mb-3">{desc}</p>
                    )}
                    {sources.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {sources.map((src) => (
                          <span
                            key={src}
                            className="rounded-full bg-gov-blue-50 px-2 py-0.5 text-[10px] font-medium text-gov-blue-700"
                          >
                            {src}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Fontes de dados */}
            <h3 className="text-base font-semibold text-gov-gray-900 mt-8 mb-3">Fontes de Dados</h3>
            <div className="flex flex-wrap gap-2">
              {DATA_SOURCES.map((src) => (
                <span
                  key={src}
                  className="rounded-full border border-gov-gray-200 bg-gov-gray-50 px-3 py-1 text-xs font-medium text-gov-gray-600"
                >
                  {src}
                </span>
              ))}
            </div>

            {/* ── Scores ── */}
            <SectionHeading id="scores">Scores de Avaliação</SectionHeading>
            <p className="text-sm text-gov-gray-600 leading-relaxed mb-6">
              A leitura correta exige considerar os três eixos em conjunto. Severidade alta sem
              completude adequada indica prioridade de verificação, não conclusão final.
            </p>
            <div className="space-y-3">
              {SCORE_DIMENSIONS.map((dim) => (
                <div
                  key={dim.name}
                  className="border border-gov-gray-200 rounded-lg p-4 bg-white"
                >
                  <h3 className="text-base font-semibold text-gov-gray-900 mb-1">{dim.name}</h3>
                  <p className="text-sm text-gov-gray-600 leading-relaxed">{dim.desc}</p>
                </div>
              ))}
            </div>

            {/* ── Escopo ── */}
            <SectionHeading id="escopo">Escopo</SectionHeading>
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
              <div>
                <h3 className="text-base font-semibold text-gov-gray-900 mb-3">Cobertura atual</h3>
                <ul className="space-y-2">
                  {SCOPE_CURRENT.map((item) => (
                    <li key={item} className="flex items-start gap-2 text-sm text-gov-gray-600">
                      <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-gov-gray-600" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h3 className="text-base font-semibold text-gov-gray-900 mb-3">Roadmap</h3>
                <ul className="space-y-2">
                  {SCOPE_ROADMAP.map((item) => (
                    <li key={item} className="flex items-start gap-2 text-sm text-gov-gray-400">
                      <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-gov-gray-400" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* ── Base Legal ── */}
            <SectionHeading id="base-legal">Base Legal</SectionHeading>
            <p className="text-sm text-gov-gray-600 leading-relaxed mb-6">
              Cada tipologia mapeia para tipos de corrupção com artigos legais específicos e esferas
              de atuação. Esses filtros estão disponíveis no Radar para busca por categoria jurídica.
            </p>
            <div className="border border-gov-gray-200 rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gov-gray-50 border-b border-gov-gray-200">
                    <th className="text-left px-4 py-2 text-xs font-semibold uppercase tracking-wide text-gov-gray-400">
                      Tipo
                    </th>
                    <th className="text-left px-4 py-2 text-xs font-semibold uppercase tracking-wide text-gov-gray-400">
                      Referência
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gov-gray-200">
                  {LEGAL_REFS.map(([name, ref]) => (
                    <tr key={name} className="bg-white">
                      <td className="px-4 py-2.5 text-sm text-gov-gray-900">{name}</td>
                      <td className="px-4 py-2.5 font-mono text-xs text-gov-gray-400">{ref}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-6 text-xs text-gov-gray-400 leading-relaxed">
              A metodologia evolui conforme expansão de cobertura nacional e melhoria de evidência
              por UF/município. Ajustes de threshold, score e tipologias são versionados para
              rastreabilidade técnica.
            </p>

          </div>
        </div>
      </div>
    </div>
  );
}
