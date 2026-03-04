import { TYPOLOGY_LABELS, DATA_SOURCES } from "@/lib/constants";
import { TableOfContents } from "./TableOfContents";
import { BookOpen, CheckCircle2 } from "lucide-react";

// ── Local data maps ────────────────────────────────────────────────────────────

const TYPOLOGY_DESCRIPTIONS: Record<string, string> = {
  T01: "Orgao direciona parcela desproporcional do gasto a um unico fornecedor ao longo do periodo analisado.",
  T02: "Licitacoes com numero de participantes abaixo do esperado para o segmento e faixa de valor.",
  T03: "Despesas particionadas sistematicamente abaixo de limiares legais de modalidade licitatoria.",
  T04: "Aditivos contratuais com valor ou extensao fora do intervalo historico para o tipo de contrato.",
  T05: "Preco unitario contratado desvia significativamente da mediana de mercado para o mesmo item/servico.",
  T06: "Empresa apresenta indicadores associados a sociedade de fachada: capital minimo, CNAE inconsistente, endereco compartilhado.",
  T07: "Conjunto de empresas apresenta padrao de propostas coordenadas compativel com cartel em multiplas licitacoes.",
  T08: "Fornecedor com contrato ativo consta em cadastro de sancionados (CEIS, CNEP, CEPIM) vigente.",
  T09: "Servidores com vinculo ativo nao localizaveis na folha de pagamento do periodo ou com remuneracao inconsistente.",
  T10: "Contratacao terceirizada paralela a quadro proprio com sobreposicao de funcao e orgao.",
  T11: "Itens com preco unitario inflado seguidos de aumento de quantidade via aditivo — padrao classico de jogo de planilha em obras publicas.",
  T12: "Edital com exigencias tecnicas, geograficas ou de qualificacao direcionadas a fornecedor especifico, restringindo a competitividade.",
  T13: "Agente publico responsavel pela contratacao compartilha vinculo familiar, societario ou financeiro com o fornecedor vencedor.",
  T14: "Fornecedor acumula multiplos sinais de favorecimento (concentracao, baixa competicao, aditivo outlier, preco outlier) de forma persistente e composta.",
  T15: "Contratacao declarada inexigivel quando existem fornecedores alternativos habilitados no mesmo segmento de mercado.",
  T16: "Emendas parlamentares ou transferencias especiais sem plano de trabalho registrado ou com valor desproporcional a capacidade administrativa do ente.",
  T17: "Fluxo financeiro circular entre empresas interligadas societariamente apos contrato publico, indicador de lavagem por camadas.",
  T18: "Servidor com vinculo ativo em dois orgaos simultaneamente ou expulso da administracao atuando como socio em empresa contratada.",
};

const TYPOLOGY_SOURCES: Record<string, string[]> = {
  T01: ["PNCP", "Compras.gov.br"],
  T02: ["PNCP", "Compras.gov.br"],
  T03: ["PNCP", "ComprasNet Contratos"],
  T04: ["PNCP", "ComprasNet Contratos"],
  T05: ["PNCP", "Compras.gov.br"],
  T06: ["Receita Federal (CNPJ)"],
  T07: ["PNCP", "Compras.gov.br", "ComprasNet Contratos"],
  T08: ["Portal da Transparencia", "PNCP"],
  T09: ["Portal da Transparencia"],
  T10: ["Portal da Transparencia", "Compras.gov.br"],
  T11: ["PNCP", "ComprasNet Contratos"],
  T12: ["PNCP", "Compras.gov.br"],
  T13: ["Receita Federal (CNPJ)", "Portal da Transparencia"],
  T14: ["PNCP", "Portal da Transparencia"],
  T15: ["PNCP", "Compras.gov.br"],
  T16: ["Portal da Transparencia", "Transfere.gov"],
  T17: ["Receita Federal (CNPJ)"],
  T18: ["Portal da Transparencia"],
};

const PRINCIPLES = [
  {
    title: "Sinal de Risco != Prova",
    body: "A plataforma produz hipoteses investigaveis para triagem tecnica e controle social, nao conclusoes definitivas. Severidade alta indica prioridade de analise, nao culpabilidade.",
  },
  {
    title: "Evidencia Reproduzivel",
    body: "Cada sinal registra os fatores numericos, contexto de execucao e referencias de origem. Qualquer auditor pode replicar o calculo a partir das fontes publicas citadas.",
  },
  {
    title: "Transparencia de Cobertura",
    body: "O painel de Confiabilidade no Radar informa quando cada tipologia executou, quantos candidatos avaliou e se produziu sinais — distinguindo 'nao encontrou' de 'nao pode rodar'.",
  },
  {
    title: "LGPD-by-Design",
    body: "Tratamento orientado por finalidade publica, minimizacao de dados pessoais e boa pratica de governanca. CPFs sao hasheados e nunca persistidos em claro.",
  },
];

const PIPELINE_STEPS = [
  { n: 1, title: "Ingestao e Catalogacao", desc: "Coleta automatica em fontes publicas com metadados de recencia e status por job." },
  { n: 2, title: "Normalizacao Canonica", desc: "Padronizacao de contratos, participantes, valores, periodos e identificadores." },
  { n: 3, title: "Resolucao de Entidades", desc: "Matching deterministico e probabilistico para consolidar pessoas, empresas e orgaos." },
  { n: 4, title: "Baselines e Scores", desc: "Calculo de distribuicoes historicas, percentis e thresholds com fallback de escopo." },
  { n: 5, title: "Deteccao e Explicacao", desc: "Aplicacao das tipologias com registro de execucao (candidatos, criados, deduplicados, bloqueados), classificacao de risco e producao de explicacao interpretavel." },
];

const SCORE_DIMENSIONS = [
  {
    name: "Severidade",
    desc: "Mede impacto potencial e magnitude do desvio observado. Baseada em desvio estatistico e relevancia financeira/operacional. Classificada em Baixo, Medio, Alto e Critico. Nao define culpabilidade, apenas prioridade de analise.",
  },
  {
    name: "Confianca",
    desc: "Mede o quanto o padrao observado e consistente nos dados disponiveis. Considera volume amostral, estabilidade e coerencia entre fatores. Confianca baixa exige verificacao adicional antes de escalar o caso.",
  },
  {
    name: "Completude",
    desc: "Mede qualidade e disponibilidade de evidencia para sustentar a leitura. Avalia quantidade e qualidade das fontes vinculadas ao sinal. Sinais com baixa completude devem ser tratados como observacao preliminar.",
  },
];

const SCOPE_CURRENT = [
  "Uniao Federal (orcamento federal direto)",
  "Contratos e licitacoes via PNCP e ComprasNet",
  "Folha de pagamento do Executivo Federal",
  "Empresas com CNPJ ativo na Receita Federal",
  "Sancionados nos cadastros CEIS, CNEP e CEPIM",
];

const SCOPE_ROADMAP = [
  "Estados e municipios com maior volume de contratacao",
  "Transferencias voluntarias via Transfere.gov",
  "Dados do TSE para cruzamento politico-contratual",
  "Diarios oficiais via Querido Diario (OCR)",
  "Historico de precos de referencia por categoria CATMAT/CATSER",
];

const LEGAL_REFS = [
  ["Fraude em Licitacao", "Lei 14.133/2021"],
  ["Corrupcao Passiva", "art. 317 CP"],
  ["Corrupcao Ativa", "art. 333 CP"],
  ["Peculato", "art. 312 CP"],
  ["Lavagem de Dinheiro", "Lei 9.613/98"],
  ["Prevaricacao", "art. 319 CP"],
  ["Concussao", "art. 316 CP"],
  ["Nepotismo/Clientelismo", "Decreto 7.203/2010"],
];

function SectionHeading({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <h2
      id={id}
      className="font-display text-lg font-bold text-primary mb-4 mt-10 pb-2 border-b border-border scroll-mt-24 first:mt-0"
    >
      {children}
    </h2>
  );
}

export default function MethodologyPage() {
  const aside = (
    <div className="rounded-xl border border-border bg-surface-card p-4">
      <div className="flex items-center gap-2 mb-4">
        <BookOpen className="h-4 w-4 text-accent" />
        <h2 className="font-display text-xs font-semibold uppercase tracking-wide text-muted">
          Conteúdo
        </h2>
      </div>
      <TableOfContents />
    </div>
  );

  const main = (
    <article className="prose-none">

      {/* ── Principios ─────────────────────────────────────────── */}
      <SectionHeading id="principios">Princípios</SectionHeading>
      <div className="space-y-3">
        {PRINCIPLES.map((p) => (
          <div key={p.title} className="rounded-lg border border-border bg-surface-card p-4">
            <div className="flex items-start gap-2">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
              <div>
                <h3 className="font-display text-sm font-bold text-primary mb-1">{p.title}</h3>
                <p className="text-sm text-secondary leading-relaxed">{p.body}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* ── Pipeline ───────────────────────────────────────────── */}
      <SectionHeading id="pipeline">Pipeline</SectionHeading>
      <div className="space-y-2">
        {PIPELINE_STEPS.map((step) => (
          <div key={step.n} className="flex gap-4 rounded-lg border border-border bg-surface-card p-4">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent-subtle border border-accent/20">
              <span className="font-mono text-xs font-bold text-accent">{step.n}</span>
            </div>
            <div>
              <h3 className="font-display text-sm font-bold text-primary mb-1">{step.title}</h3>
              <p className="text-sm text-secondary leading-relaxed">{step.desc}</p>
            </div>
          </div>
        ))}
      </div>

      {/* ── Tipologias ─────────────────────────────────────────── */}
      <SectionHeading id="tipologias">Tipologias</SectionHeading>
      <p className="mb-4 text-sm text-secondary leading-relaxed">
        O motor aplica {Object.keys(TYPOLOGY_LABELS).length} tipologias com thresholds específicos por contexto e baseline.
        A leitura de cada código deve considerar o nível de evidência: direto (viola regra legal específica),
        indireto (anomalia estatística) ou proxy (indicador associado ao veículo de risco).
      </p>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {Object.entries(TYPOLOGY_LABELS).map(([code, name]) => {
          const sources = TYPOLOGY_SOURCES[code] ?? [];
          const desc = TYPOLOGY_DESCRIPTIONS[code] ?? "";
          return (
            <div key={code} className="rounded-lg border border-border bg-surface-card p-3">
              <div className="flex items-baseline gap-2 mb-1.5">
                <span className="font-mono text-xs font-bold text-accent">{code}</span>
                <span className="text-xs font-semibold text-primary leading-snug">{name}</span>
              </div>
              {desc && <p className="text-xs text-secondary leading-relaxed mb-2">{desc}</p>}
              {sources.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {sources.map((src) => (
                    <span key={src} className="rounded-full bg-accent-subtle px-2 py-0.5 text-[10px] font-medium text-accent">
                      {src}
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <h3 className="font-display text-sm font-bold text-primary mt-6 mb-3">Fontes de Dados</h3>
      <div className="flex flex-wrap gap-2">
        {DATA_SOURCES.map((src) => (
          <span key={src} className="rounded-full border border-border bg-surface-subtle px-3 py-1 text-xs font-medium text-secondary">
            {src}
          </span>
        ))}
      </div>

      {/* ── Scores ─────────────────────────────────────────────── */}
      <SectionHeading id="scores">Scores de Avaliação</SectionHeading>
      <p className="mb-4 text-sm text-secondary leading-relaxed">
        A leitura correta exige considerar os três eixos em conjunto. Severidade alta sem
        completude adequada indica prioridade de verificação, não conclusão final.
      </p>
      <div className="space-y-2">
        {SCORE_DIMENSIONS.map((dim) => (
          <div key={dim.name} className="rounded-lg border border-border bg-surface-card p-4">
            <h3 className="font-display text-sm font-bold text-primary mb-1">{dim.name}</h3>
            <p className="text-sm text-secondary leading-relaxed">{dim.desc}</p>
          </div>
        ))}
      </div>

      {/* ── Escopo ─────────────────────────────────────────────── */}
      <SectionHeading id="escopo">Escopo</SectionHeading>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="rounded-lg border border-border bg-surface-card p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted mb-3">Cobertura atual</h3>
          <ul className="space-y-2">
            {SCOPE_CURRENT.map((item) => (
              <li key={item} className="flex items-start gap-2 text-xs text-secondary">
                <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-success" />
                {item}
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-lg border border-border bg-surface-base p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted mb-3">Roadmap</h3>
          <ul className="space-y-2">
            {SCOPE_ROADMAP.map((item) => (
              <li key={item} className="flex items-start gap-2 text-xs text-muted">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-muted" />
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* ── Base Legal ─────────────────────────────────────────── */}
      <SectionHeading id="base-legal">Base Legal</SectionHeading>
      <p className="mb-4 text-sm text-secondary leading-relaxed">
        Cada tipologia mapeia para tipos de corrupção com artigos legais específicos e esferas
        de atuação. Esses filtros estão disponíveis no Radar para busca por categoria jurídica.
      </p>
      <div className="rounded-lg border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-surface-base">
              <th className="text-left px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted">Tipo</th>
              <th className="text-left px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted">Referência</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border bg-surface-card">
            {LEGAL_REFS.map(([name, ref]) => (
              <tr key={name} className="hover:bg-surface-subtle transition-colors">
                <td className="px-4 py-2.5 text-sm text-primary">{name}</td>
                <td className="px-4 py-2.5 font-mono text-xs text-muted">{ref}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-6 text-xs text-muted leading-relaxed">
        A metodologia evolui conforme expansão de cobertura nacional e melhoria de evidência
        por UF/município. Ajustes de threshold, score e tipologias são versionados para
        rastreabilidade técnica.
      </p>
    </article>
  );

  return (
    <div className="min-h-screen">

      {/* ── Page header ────────────────────────────────────────── */}
      <div className="border-b border-border bg-surface-card">
        <div className="mx-auto max-w-[1280px] px-4 py-8 sm:px-6">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-accent-subtle border border-accent/20">
              <BookOpen className="h-6 w-6 text-accent" />
            </div>
            <div>
              <h1 className="font-display text-2xl font-bold tracking-tight text-primary sm:text-3xl">Metodologia</h1>
              <p className="mt-1.5 text-sm text-secondary leading-relaxed">Fundamentos técnicos e legais das tipologias, fatores de risco e critérios de classificação de evidência</p>
            </div>
          </div>
        </div>
      </div>

      {/* ── Body: TOC aside + content ───────────────────────────── */}
      <div className="mx-auto max-w-[1280px] px-4 py-8 sm:px-6">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
          <aside className="w-full lg:w-72 lg:shrink-0 lg:sticky lg:top-6">
            {aside}
          </aside>
          <div className="flex-1 min-w-0">
            {main}
          </div>
        </div>
      </div>
    </div>
  );
}
