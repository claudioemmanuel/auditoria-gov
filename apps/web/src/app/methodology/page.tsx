import Link from "next/link";
import { TYPOLOGY_LABELS, DATA_SOURCES } from "@/lib/constants";
import { BookOpen, CheckCircle2, ExternalLink, ArrowRight, Scale } from "lucide-react";
import { fetchTipologiaList } from "@/lib/api";
import type { TypologyLegalBasis } from "@/lib/types";
import { PageHeader } from "@/components/PageHeader";

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
  T19: "Mesmo conjunto restrito de fornecedores vence contratos alternadamente em licitacoes do mesmo orgao — padrao indicativo de rodizio combinado para aparentar competitividade.",
  T20: "Empresa vencedora nao localizavel em registros comerciais ativos, com CNPJ cancelado/suspenso ou endereco fantasma confirmado na Receita Federal.",
  T21: "Grupo de empresas formalmente distintas apresenta comportamento licitatório homogeneo (precos, datas, documentos) sugerindo controle comum oculto.",
  T22: "Contratacoes concentradas em periodos eleitorais ou cujo beneficiario apresenta vinculo com agente politico responsavel pela autorizacao.",
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
  T19: ["PNCP", "ComprasNet Contratos"],
  T20: ["Receita Federal (CNPJ)", "PNCP"],
  T21: ["PNCP", "Receita Federal (CNPJ)", "Compras.gov.br"],
  T22: ["Portal da Transparencia", "PNCP"],
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

const LEGAL_REFS: [string, string, string][] = [
  ["Fraude em Licitacao", "Lei 14.133/2021", "https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/L14133.htm"],
  ["Corrupcao Passiva", "art. 317 CP", "https://www.planalto.gov.br/ccivil_03/decreto-lei/del2848compilado.htm"],
  ["Corrupcao Ativa", "art. 333 CP", "https://www.planalto.gov.br/ccivil_03/decreto-lei/del2848compilado.htm"],
  ["Peculato", "art. 312 CP", "https://www.planalto.gov.br/ccivil_03/decreto-lei/del2848compilado.htm"],
  ["Lavagem de Dinheiro", "Lei 9.613/98", "https://www.planalto.gov.br/ccivil_03/leis/l9613.htm"],
  ["Prevaricacao", "art. 319 CP", "https://www.planalto.gov.br/ccivil_03/decreto-lei/del2848compilado.htm"],
  ["Concussao", "art. 316 CP", "https://www.planalto.gov.br/ccivil_03/decreto-lei/del2848compilado.htm"],
  ["Nepotismo/Clientelismo", "Decreto 7.203/2010", "https://www.planalto.gov.br/ccivil_03/_ato2007-2010/2010/decreto/d7203.htm"],
];

function Divider() {
  return <div className="ow-divider" />;
}

export default async function MethodologyPage() {
  const legalBasisList: TypologyLegalBasis[] = await fetchTipologiaList().catch(() => []);

  const typologyCount = Object.keys(TYPOLOGY_LABELS).length;
  const uniqueSources = new Set(Object.values(TYPOLOGY_SOURCES).flat()).size;
  const legalBases = LEGAL_REFS.length;

  // Build lookup for legal basis per typology code from API data
  const legalByCode = new Map<string, TypologyLegalBasis>(
    legalBasisList.map((b) => [b.code, b])
  );

  return (
    <div className="min-h-screen" style={{ background: "var(--color-surface-2)" }}>

      {/* ── Page Header ─────────────────────────────────────────── */}
      <PageHeader
        eyebrow="METODOLOGIA"
        title="Tipologias de Risco"
        description="Fundamentos técnicos e legais das 22 tipologias de detecção. Motor determinístico, scoring reproduzível, auditável por design."
        variant="hero"
        icon={<Scale className="h-5 w-5" />}
        stats={[
          { label: "Tipologias", value: typologyCount, mono: true, tone: "brand" },
          { label: "Fontes públicas", value: uniqueSources, mono: true },
          { label: "Bases legais", value: legalBases, mono: true },
          { label: "Dimensões de score", value: 3, mono: true },
        ]}
      />

      <div className="mx-auto max-w-[1280px] px-4 py-8 sm:px-6 space-y-10 animate-fade-in">

        {/* ── Principles ──────────────────────────────────────── */}
        <section>
          <p className="text-mono-xs uppercase tracking-widest mb-4" style={{ color: "var(--color-text-3)" }}>
            Princípios
          </p>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {PRINCIPLES.map((p) => (
              <div key={p.title} className="ow-card p-4">
                <div className="flex items-start gap-3">
                  <CheckCircle2
                    className="mt-0.5 h-4 w-4 shrink-0"
                    style={{ color: "var(--color-low-text)" }}
                  />
                  <div>
                    <h3 className="text-label font-bold mb-1" style={{ color: "var(--color-text)" }}>
                      {p.title}
                    </h3>
                    <p className="text-caption leading-relaxed" style={{ color: "var(--color-text-2)" }}>
                      {p.body}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        <Divider />

        {/* ── Typologies grid ─────────────────────────────────── */}
        <section>
          <div className="flex flex-wrap items-end justify-between gap-3 mb-4">
            <div>
              <p className="text-mono-xs uppercase tracking-widest mb-1" style={{ color: "var(--color-text-3)" }}>
                Tipologias de Detecção
              </p>
              <p className="text-caption" style={{ color: "var(--color-text-2)" }}>
                Motor aplica {typologyCount} tipologias com thresholds específicos por contexto e baseline.
                Leitura de cada código deve considerar o nível de evidência: direto, indireto ou proxy.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {Object.entries(TYPOLOGY_LABELS).map(([code, name]) => {
              const sources = TYPOLOGY_SOURCES[code] ?? [];
              const desc = TYPOLOGY_DESCRIPTIONS[code] ?? "";
              const legal = legalByCode.get(code);
              const firstArticle = legal?.law_articles?.[0];
              const legalText = firstArticle
                ? `${firstArticle.law_name} — ${firstArticle.article}`
                : legal?.description_legal ?? null;

              return (
                <div key={code} className="ow-card ow-card-hover p-4 space-y-2.5">
                  {/* Code + title */}
                  <div className="flex items-start gap-2 flex-wrap">
                    <span className="ow-badge ow-badge-neutral text-mono-xs font-bold">{code}</span>
                    <span className="text-label font-semibold leading-snug" style={{ color: "var(--color-text)" }}>
                      {name}
                    </span>
                  </div>

                  {/* Description */}
                  {desc && (
                    <p className="text-caption leading-relaxed" style={{ color: "var(--color-text-2)" }}>
                      {desc}
                    </p>
                  )}

                  {/* Legal basis */}
                  {legalText && (
                    <div className="flex items-center gap-1.5 pt-0.5">
                      <Scale className="h-3 w-3 shrink-0" style={{ color: "var(--color-text-3)" }} />
                      <span className="text-mono-xs" style={{ color: "var(--color-text-3)" }}>
                        {legalText}
                      </span>
                    </div>
                  )}

                  {/* Data sources */}
                  {sources.length > 0 && (
                    <div className="flex flex-wrap gap-1 pt-0.5">
                      {sources.map((src) => (
                        <span key={src} className="ow-badge ow-badge-info text-mono-xs">
                          {src}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        <Divider />

        {/* ── Legal basis from API ────────────────────────────── */}
        {legalBasisList.length > 0 && (
          <section>
            <p className="text-mono-xs uppercase tracking-widest mb-4" style={{ color: "var(--color-text-3)" }}>
              Base Legal por Tipologia
            </p>
            <p className="text-caption mb-4" style={{ color: "var(--color-text-2)" }}>
              Mapeamento dos artigos legais associados a cada tipologia detectada pelo motor de análise.
            </p>
            <div className="ow-table-wrapper">
              <table className="ow-table">
                <thead>
                  <tr>
                    <th>Código</th>
                    <th>Tipo de Corrupção</th>
                    <th>Base Legal</th>
                    <th>Evidência</th>
                  </tr>
                </thead>
                <tbody>
                  {legalBasisList.map((basis, i) => {
                    const firstArticle = basis.law_articles[0];
                    return (
                      <tr key={`${basis.code}-${i}`}>
                        <td>
                          <span className="ow-badge ow-badge-neutral text-mono-xs">{basis.code}</span>
                        </td>
                        <td className="text-caption" style={{ color: "var(--color-text-2)" }}>
                          {basis.corruption_types.join(", ")}
                        </td>
                        <td className="text-mono-xs" style={{ color: "var(--color-text)" }}>
                          {firstArticle
                            ? `${firstArticle.law_name} — ${firstArticle.article}`
                            : basis.description_legal || "—"}
                        </td>
                        <td>
                          <span className="ow-badge ow-badge-neutral text-mono-xs">
                            {basis.evidence_level}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* ── Score dimensions ────────────────────────────────── */}
        <section>
          <p className="text-mono-xs uppercase tracking-widest mb-4" style={{ color: "var(--color-text-3)" }}>
            Scores de Avaliação
          </p>
          <p className="text-caption mb-4" style={{ color: "var(--color-text-2)" }}>
            A leitura correta exige considerar os três eixos em conjunto. Severidade alta sem
            completude adequada indica prioridade de verificação, não conclusão final.
          </p>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {SCORE_DIMENSIONS.map((dim, i) => (
              <div key={dim.name} className="ow-card p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span
                    className="flex h-6 w-6 items-center justify-center rounded-full text-mono-xs font-bold"
                    style={{
                      background: "var(--color-amber-dim)",
                      color: "var(--color-amber-text)",
                      border: "1px solid var(--color-amber-border)",
                    }}
                  >
                    {i + 1}
                  </span>
                  <h3 className="text-label font-bold" style={{ color: "var(--color-text)" }}>
                    {dim.name}
                  </h3>
                </div>
                <p className="text-caption leading-relaxed" style={{ color: "var(--color-text-2)" }}>
                  {dim.desc}
                </p>
              </div>
            ))}
          </div>
        </section>

        <Divider />

        {/* ── Scope ───────────────────────────────────────────── */}
        <section>
          <p className="text-mono-xs uppercase tracking-widest mb-4" style={{ color: "var(--color-text-3)" }}>
            Escopo de Cobertura
          </p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="ow-card p-4">
              <p className="text-mono-xs uppercase tracking-widest mb-3 font-semibold" style={{ color: "var(--color-low-text)" }}>
                Cobertura Atual
              </p>
              <ul className="space-y-2">
                {SCOPE_CURRENT.map((item) => (
                  <li key={item} className="flex items-start gap-2 text-caption" style={{ color: "var(--color-text-2)" }}>
                    <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0" style={{ color: "var(--color-low-text)" }} />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <div className="ow-card p-4" style={{ background: "var(--color-surface-3)" }}>
              <p className="text-mono-xs uppercase tracking-widest mb-3 font-semibold" style={{ color: "var(--color-text-3)" }}>
                Roadmap
              </p>
              <ul className="space-y-2">
                {SCOPE_ROADMAP.map((item) => (
                  <li key={item} className="flex items-start gap-2 text-caption" style={{ color: "var(--color-text-3)" }}>
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: "var(--color-text-3)" }} />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        {/* ── Legal references ────────────────────────────────── */}
        <section>
          <p className="text-mono-xs uppercase tracking-widest mb-4" style={{ color: "var(--color-text-3)" }}>
            Base Legal &amp; Compliance
          </p>
          <p className="text-caption mb-4" style={{ color: "var(--color-text-2)" }}>
            Cada tipologia mapeia para tipos de corrupção com artigos legais específicos.
            A plataforma opera exclusivamente sobre dados de transparência ativa obrigatória (LAI art. 8º).
          </p>
          <div className="ow-table-wrapper">
            <table className="ow-table">
              <thead>
                <tr>
                  <th>Tipo</th>
                  <th>Norma / Artigo</th>
                </tr>
              </thead>
              <tbody>
                {LEGAL_REFS.map(([name, ref, url], i) => (
                  <tr key={`${name}-${i}`}>
                    <td style={{ color: "var(--color-text)" }}>{name}</td>
                    <td>
                      <a
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-mono-xs hover:underline"
                        style={{ color: "var(--color-amber-text)" }}
                      >
                        {ref}
                        <ExternalLink className="h-2.5 w-2.5" />
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <Divider />

        {/* ── Data sources ────────────────────────────────────── */}
        <section>
          <p className="text-mono-xs uppercase tracking-widest mb-4" style={{ color: "var(--color-text-3)" }}>
            Fontes de Dados
          </p>
          <div className="flex flex-wrap gap-2">
            {DATA_SOURCES.map((src) => (
              <span key={src} className="ow-badge ow-badge-neutral">
                {src}
              </span>
            ))}
          </div>
        </section>

        {/* ── Conformidade link ───────────────────────────────── */}
        <div
          className="ow-card p-4 flex items-center justify-between gap-4"
          style={{ borderColor: "var(--color-amber-border)", background: "var(--color-amber-dim)" }}
        >
          <div className="flex items-center gap-3">
            <Scale className="h-4 w-4 shrink-0" style={{ color: "var(--color-amber-text)" }} />
            <p className="text-caption" style={{ color: "var(--color-text-2)" }}>
              Veja o documento técnico-jurídico completo com respaldo legal detalhado.
            </p>
          </div>
          <Link
            href="/compliance"
            className="inline-flex items-center gap-1 text-caption font-medium shrink-0 hover:underline"
            style={{ color: "var(--color-amber-text)" }}
          >
            Compliance completo
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        <p className="text-caption pb-8" style={{ color: "var(--color-text-3)" }}>
          A metodologia evolui conforme expansão de cobertura nacional e melhoria de evidência
          por UF/município. Ajustes de threshold, score e tipologias são versionados para rastreabilidade técnica.
        </p>
      </div>
    </div>
  );
}
