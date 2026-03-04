import Link from "next/link";
import { Shield, ExternalLink, Scale } from "lucide-react";

const LEGAL_LINKS = [
  { label: "CF/88 (Constituição Federal)", href: "https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm" },
  { label: "Lei 12.527/2011 (LAI)", href: "https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2011/lei/l12527.htm" },
  { label: "Lei 13.709/2018 (LGPD)", href: "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm" },
  { label: "Lei 12.846/2013 (Anticorrupção)", href: "https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2013/lei/l12846.htm" },
  { label: "Lei 14.133/2021 (Licitações)", href: "https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/L14133.htm" },
];

const AUDIT_LINKS = [
  { label: "Fontes & Veracidade (GET /public/sources)", href: "/api/public/sources", external: true },
  { label: "Código-fonte (AGPL-3.0)", href: "https://github.com/claudioemmanuel/auditoria-gov", external: true },
  { label: "Política de Governança (GOVERNANCE.md)", href: "https://github.com/claudioemmanuel/auditoria-gov/blob/main/docs/GOVERNANCE.md", external: true },
];

const TRANSPARENCY_LINKS = [
  { label: "Metodologia", href: "/methodology", external: false },
  { label: "Cobertura de Dados", href: "/coverage", external: false },
  { label: "Saúde da API", href: "/api-health", external: false },
  { label: "Contestar Sinal", href: "/methodology#contestacao", external: false },
];

export function SiteFooter() {
  return (
    <footer className="border-t border-border bg-surface-base mt-auto">
      <div className="mx-auto max-w-[1280px] px-4 py-8 sm:px-6">

        {/* ── Four columns ────────────────────────────────── */}
        <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">

          {/* Col 1 — Brand */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent-subtle border border-accent/20">
                <Shield className="h-3.5 w-3.5 text-accent" />
              </div>
              <span className="font-display text-sm font-bold text-primary">AuditorIA Gov</span>
            </div>
            <p className="text-xs text-muted leading-relaxed mb-3">
              Plataforma de auditoria cidadã sobre dados públicos federais brasileiros.
              Sinais determinísticos, evidências rastreáveis.
            </p>
            <Link
              href="/compliance"
              className="inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline"
            >
              <Scale className="h-3 w-3" />
              Conformidade legal →
            </Link>
          </div>

          {/* Col 2 — Base Legal */}
          <div>
            <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-muted mb-3">
              Base Legal
            </p>
            <ul className="space-y-1.5">
              {LEGAL_LINKS.map((link) => (
                <li key={link.label}>
                  <a
                    href={link.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-secondary hover:text-primary transition-colors"
                  >
                    {link.label}
                    <ExternalLink className="h-2.5 w-2.5 text-muted" />
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Col 3 — Auditabilidade */}
          <div>
            <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-muted mb-3">
              Auditabilidade
            </p>
            <ul className="space-y-1.5">
              {AUDIT_LINKS.map((link) => (
                <li key={link.label}>
                  <a
                    href={link.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-secondary hover:text-primary transition-colors"
                  >
                    {link.label}
                    <ExternalLink className="h-2.5 w-2.5 text-muted" />
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Col 4 — Transparência */}
          <div>
            <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-muted mb-3">
              Transparência
            </p>
            <ul className="space-y-1.5">
              {TRANSPARENCY_LINKS.map((link) => (
                <li key={link.label}>
                  <Link
                    href={link.href}
                    className="text-xs text-secondary hover:text-primary transition-colors"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* ── Bottom bar ──────────────────────────────────── */}
        <div className="mt-8 pt-4 border-t border-border flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-[11px] text-muted leading-relaxed max-w-xl">
            <strong className="font-medium text-secondary">Aviso:</strong>{" "}
            Sinais são indicadores estatísticos para triagem — não configuram acusação, prova ou juízo de culpa.
            Dados de transparência ativa obrigatória (LAI art. 8º). CPFs anonimizados (LGPD art. 12).
          </p>
          <div className="flex items-center gap-3 shrink-0">
            <span className="rounded-md border border-border px-2 py-0.5 font-mono text-[10px] text-muted">
              AGPL-3.0
            </span>
            <span className="rounded-md border border-success/30 bg-success/5 px-2 py-0.5 font-mono text-[10px] text-success">
              OPEN SOURCE
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
