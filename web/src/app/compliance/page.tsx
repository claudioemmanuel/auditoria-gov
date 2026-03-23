import Link from "next/link";
import {
  Shield,
  Code,
  Scale,
  Globe,
  CheckCircle2,
  ArrowRight,
  ExternalLink,
  Lock,
  FileText,
  AlertTriangle,
} from "lucide-react";

const PILLARS = [
  {
    icon: Code,
    title: "Tecnologicamente Robusto",
    badge: "TÉCNICO",
    badgeClass: "bg-accent/10 text-accent border border-accent/20",
    items: [
      "Whitelist de domínios governamentais (.gov.br, .leg.br, .jus.br, .mil.br, .mp.br, .def.br) aplicada em nível de HTTP — domínios fora da lista são bloqueados automaticamente",
      "Score de veracidade por fonte (5 critérios: domínio governamental, autoridade legal, disponibilidade pública, API documentada, rastreabilidade de metadados)",
      "Código-fonte aberto sob licença AGPL-3.0 — qualquer técnico pode auditar a lógica de detecção",
      "Cadeia de proveniência completa: RiskSignal → SignalEvent → Event → RawSource (JSON bruto), exposta via GET /signal/{id}/provenance",
    ],
  },
  {
    icon: FileText,
    title: "Metodologicamente Defensável",
    badge: "METODOLÓGICO",
    badgeClass: "bg-success/10 text-success border border-success/20",
    items: [
      "22 tipologias com base legal explícita (Lei 14.133/2021, CF/88, Lei 9.613/98, Lei 12.529/2011, Código Penal, Lei de Improbidade)",
      "Scoring determinístico e reproduzível — nenhuma IA participa da geração de scores ou classificação de risco",
      "Thresholds baseados em distribuições históricas dos próprios dados públicos, não em critérios subjetivos",
      "IA generativa usada exclusivamente para explicações em linguagem natural (@explanatory_only decorator — TypeError se retornar algo além de texto)",
    ],
  },
  {
    icon: Scale,
    title: "Juridicamente Responsável",
    badge: "JURÍDICO",
    badgeClass: "bg-warning/10 text-warning border border-warning/20",
    items: [
      "Opera sobre transparência ativa obrigatória — dados que órgãos públicos são legalmente obrigados a publicar (LAI art. 8º)",
      "CPFs são hasheados via SHA-256 + salt imediatamente na ingestão — nunca persistidos em claro (LGPD art. 12)",
      "Cada sinal carrega aviso obrigatório: indicador estatístico, não acusação",
      "Aviso de que a plataforma não constitui processo judicial ou administrativo — contestação via POST /contestation",
    ],
  },
  {
    icon: Globe,
    title: "Publicamente Auditável",
    badge: "TRANSPARÊNCIA",
    badgeClass: "bg-blue-500/10 text-blue-400 border border-blue-500/20",
    items: [
      "GET /public/sources: expõe scores de veracidade, status de compliance e whitelist de domínios em tempo real",
      "GET /signal/{id}/provenance: cadeia completa do dado bruto ao sinal final",
      "Compliance automatizado toda segunda-feira 06:00 UTC: validação de domínios, probe de disponibilidade, alerta de exceções",
      "Código aberto (AGPL-3.0): qualquer pessoa pode verificar, reproduzir ou contestar qualquer cálculo",
    ],
  },
];

const LEGAL_BASIS = [
  {
    norm: "CF/88, art. 5º, XXXIII",
    scope: "Direito de qualquer cidadão obter informações de órgãos públicos",
    application: "Base constitucional para acesso aos dados analisados",
    url: "https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm",
  },
  {
    norm: "CF/88, art. 37, caput",
    scope: "Princípio da Publicidade da Administração Pública",
    application: "Impõe que atos administrativos sejam acessíveis ao público",
    url: "https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm",
  },
  {
    norm: "CF/88, art. 74, §1º",
    scope: "Qualquer cidadão tem legitimidade para denunciar ao TCU",
    application: "Plataforma fornece insumos para exercício desse direito",
    url: "https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm",
  },
  {
    norm: "Lei 12.527/2011 (LAI)",
    scope: "Obriga divulgação ativa de contratos, despesas e servidores",
    application: "Todos os dados coletados são de publicação obrigatória",
    url: "https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2011/lei/l12527.htm",
  },
  {
    norm: "Decreto 7.724/2012",
    scope: "Regulamenta a LAI; define dados de transparência ativa",
    application: "Define exatamente quais dados os órgãos devem publicar",
    url: "https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2012/decreto/d7724.htm",
  },
  {
    norm: "LGPD art. 7º, VI",
    scope: "Permite tratamento para exercício regular de direitos",
    application: "Base legal para análise de dados e suporte a denúncias",
    url: "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm",
  },
  {
    norm: "LGPD art. 12",
    scope: "Dados anonimizados não são dados pessoais",
    application: "CPFs hasheados (SHA-256 + salt) — não são dados pessoais",
    url: "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm",
  },
  {
    norm: "Lei 12.846/2013 (Anticorrupção)",
    scope: "Responsabilização de empresas por atos contra a administração",
    application: "Fundamenta a detecção de irregularidades na plataforma",
    url: "https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2013/lei/l12846.htm",
  },
  {
    norm: "Lei 8.429/1992 (Improbidade)",
    scope: "Define peculato, enriquecimento ilícito e fraude",
    application: "Base normativa das tipologias T09, T13, T17 e T18",
    url: "https://www.planalto.gov.br/ccivil_03/leis/l8429.htm",
  },
  {
    norm: "Lei 14.133/2021 (Licitações)",
    scope: "Nova Lei de Licitações e Contratos Administrativos",
    application: "Fundamenta T01–T08 (concentração, conluio, fracionamento)",
    url: "https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/L14133.htm",
  },
  {
    norm: "STF — RE 652.777",
    scope: "Legitimidade da publicação de remuneração de servidores",
    application: "Consolida a legalidade de exibir dados de servidores públicos",
    url: "https://portal.stf.jus.br/jurisprudencia/sumariosumula.asp?base=acordaos&docid=RE%20652777",
  },
];

const WHAT_WE_DONT = [
  { label: "Acusar pessoas ou empresas", detail: "Sinais são hipóteses estatísticas para triagem, não provas" },
  { label: "Armazenar CPFs em texto claro", detail: "Hash SHA-256 + salt imediato na ingestão (LGPD art. 12)" },
  { label: "Acessar dados sigilosos ou restritos", detail: "Apenas transparência ativa obrigatória por lei" },
  { label: "Usar IA para scoring ou acusações", detail: "LLM é exclusivamente explicativo — decorator @explanatory_only" },
  { label: "Concluir culpabilidade", detail: "Sinais de risco para investigação, não julgamento" },
  { label: "Coletar de fontes não autorizadas", detail: "Domain guard bloqueia domínios fora da whitelist no nível HTTP" },
];

export default function CompliancePage() {
  return (
    <div className="min-h-screen">

      {/* ── Page header ──────────────────────────────────────────── */}
      <div className="border-b border-border bg-surface-card">
        <div className="mx-auto max-w-[1280px] px-4 py-8 sm:px-6">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-accent-subtle border border-accent/20">
              <Shield className="h-6 w-6 text-accent" />
            </div>
            <div>
              <h1 className="font-display text-2xl font-bold tracking-tight text-primary sm:text-3xl">
                Plataforma Juridicamente Responsável
              </h1>
              <p className="mt-1.5 text-sm text-secondary leading-relaxed max-w-2xl">
                O OpenWatch opera exclusivamente sobre dados de transparência ativa obrigatória,
                com base legal explícita, metodologia auditável e compliance automatizado.
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-[1280px] px-4 py-8 sm:px-6 space-y-10">

        {/* ── Four Pillars ─────────────────────────────────────────── */}
        <section>
          <p className="mb-4 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-muted">
            Os Quatro Pilares
          </p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {PILLARS.map((pillar) => (
              <div
                key={pillar.title}
                className="rounded-xl border border-border bg-surface-card p-5"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent-subtle border border-accent/20">
                    <pillar.icon className="h-4 w-4 text-accent" />
                  </div>
                  <span className={`rounded-md px-2 py-0.5 text-[10px] font-semibold tracking-wide ${pillar.badgeClass}`}>
                    {pillar.badge}
                  </span>
                </div>
                <h2 className="font-display text-sm font-bold text-primary mb-3">{pillar.title}</h2>
                <ul className="space-y-2">
                  {pillar.items.map((item) => (
                    <li key={item} className="flex items-start gap-2">
                      <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-success" />
                      <span className="text-xs text-secondary leading-relaxed">{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>

        {/* ── Legal Basis ──────────────────────────────────────────── */}
        <section>
          <p className="mb-4 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-muted">
            Respaldo Legal Completo
          </p>
          <div className="rounded-xl border border-border overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-surface-base">
                  <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wide text-muted">Norma / Artigo</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wide text-muted hidden md:table-cell">Conteúdo</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wide text-muted">Aplicação ao projeto</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border bg-surface-card">
                {LEGAL_BASIS.map((row) => (
                  <tr key={row.norm} className="hover:bg-surface-subtle transition-colors">
                    <td className="px-4 py-3">
                      <a
                        href={row.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 font-mono text-xs font-medium text-accent hover:underline"
                      >
                        {row.norm}
                        <ExternalLink className="h-2.5 w-2.5" />
                      </a>
                    </td>
                    <td className="px-4 py-3 text-xs text-muted hidden md:table-cell">{row.scope}</td>
                    <td className="px-4 py-3 text-xs text-secondary">{row.application}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* ── What we don't do ─────────────────────────────────────── */}
        <section>
          <p className="mb-4 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-muted">
            O que a plataforma NÃO faz
          </p>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {WHAT_WE_DONT.map((item) => (
              <div
                key={item.label}
                className="flex items-start gap-3 rounded-lg border border-border bg-surface-card p-4"
              >
                <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-destructive/10 border border-destructive/20 mt-0.5">
                  <span className="text-[9px] font-bold text-destructive">✕</span>
                </div>
                <div>
                  <p className="text-xs font-semibold text-primary mb-0.5">{item.label}</p>
                  <p className="text-xs text-muted leading-relaxed">{item.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ── Compliance Plan ──────────────────────────────────────── */}
        <section>
          <p className="mb-4 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-muted">
            Plano de Compliance Contínuo
          </p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-border bg-surface-card p-5">
              <div className="flex items-center gap-2 mb-4">
                <Lock className="h-4 w-4 text-accent" />
                <h3 className="font-display text-sm font-bold text-primary">Auditoria Semanal Automatizada</h3>
              </div>
              <p className="text-xs text-secondary leading-relaxed mb-3">
                Toda segunda-feira às 06:00 UTC, a tarefa <code className="font-mono bg-surface-base px-1 rounded">check_source_compliance</code> executa:
              </p>
              <ul className="space-y-2">
                {[
                  "Validação de domínio — verifica whitelist governamental",
                  "Alerta 30 dias antes de exceções de domínio expirarem",
                  "HTTP HEAD em cada fonte — marca inacessíveis como warning",
                  "Atualiza coverage_registry com status ok / warning / violation",
                ].map((step) => (
                  <li key={step} className="flex items-start gap-2 text-xs text-secondary">
                    <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-success" />
                    {step}
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-xl border border-border bg-surface-card p-5">
              <div className="flex items-center gap-2 mb-4">
                <AlertTriangle className="h-4 w-4 text-warning" />
                <h3 className="font-display text-sm font-bold text-primary">Responsabilidade Editorial</h3>
              </div>
              <p className="text-xs text-secondary leading-relaxed mb-3">
                Todos os sinais carregam o seguinte aviso obrigatório:
              </p>
              <blockquote className="rounded-lg border border-warning/20 bg-warning/5 p-3 text-xs text-secondary italic leading-relaxed mb-3">
                &ldquo;Este resultado representa um indicador estatístico para triagem e controle social.
                Não configura acusação, prova definitiva ou juízo de culpa.&rdquo;
              </blockquote>
              <p className="text-xs text-muted leading-relaxed">
                A plataforma produz <strong className="font-semibold text-secondary">sinais</strong>, nunca <strong className="font-semibold text-secondary">provas</strong>. Provas são produzidas por autoridades competentes (CGU, TCU, MPF).
              </p>
            </div>
          </div>
        </section>

        {/* ── Links ────────────────────────────────────────────────── */}
        <section>
          <p className="mb-4 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-muted">
            Recursos Adicionais
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/methodology"
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-card px-4 py-2.5 text-xs font-medium text-secondary transition hover:border-accent/30 hover:text-primary"
            >
              <FileText className="h-3.5 w-3.5" />
              Metodologia técnica
              <ArrowRight className="h-3 w-3" />
            </Link>
            <a
              href={`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/public/sources`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-card px-4 py-2.5 text-xs font-medium text-secondary transition hover:border-accent/30 hover:text-primary"
            >
              <Globe className="h-3.5 w-3.5" />
              GET /public/sources
              <ExternalLink className="h-3 w-3" />
            </a>
            <a
              href="https://github.com/claudioemmanuel/openwatch"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-card px-4 py-2.5 text-xs font-medium text-secondary transition hover:border-accent/30 hover:text-primary"
            >
              <Code className="h-3.5 w-3.5" />
              Código-fonte (AGPL-3.0)
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </section>

        {/* ── Disclaimer ───────────────────────────────────────────── */}
        <footer className="rounded-xl border border-border bg-surface-base p-4">
          <div className="flex items-start gap-3">
            <Scale className="mt-0.5 h-4 w-4 shrink-0 text-muted" />
            <p className="text-xs text-muted leading-relaxed">
              <strong className="font-semibold text-secondary">Nota legal:</strong>{" "}
              Esta página documenta o posicionamento institucional e a base legal da plataforma para fins de
              transparência e controle social. Não constitui aconselhamento jurídico. Para situações específicas,
              consulte um advogado. Documento técnico-jurídico completo:{" "}
              <a href="https://github.com/claudioemmanuel/openwatch/blob/main/docs/COMPLIANCE.md"
                className="text-accent hover:underline" target="_blank" rel="noopener noreferrer">
                docs/COMPLIANCE.md
              </a>.
            </p>
          </div>
        </footer>
      </div>
    </div>
  );
}
