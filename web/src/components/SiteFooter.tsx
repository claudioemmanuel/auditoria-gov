import Link from "next/link";
import { Eye, Github, ExternalLink } from "lucide-react";

export function SiteFooter() {
  return (
    <footer className="border-t border-[var(--color-border)] bg-[var(--color-surface-2)] mt-auto">
      <div className="max-w-7xl mx-auto px-6 py-10">
        {/* Top row */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          {/* Brand */}
          <div className="md:col-span-1">
            <div className="flex items-center gap-2 mb-3">
              <div className="ow-sidebar-logo-mark">
                <Eye size={14} color="#09090b" strokeWidth={2.5} />
              </div>
              <span className="ow-sidebar-wordmark">OpenWatch</span>
            </div>
            <p className="text-xs text-[var(--color-text-3)] leading-relaxed">
              Plataforma open-source de auditoria cidadã sobre dados federais brasileiros.
            </p>
          </div>

          {/* Navigation */}
          <div>
            <h4 className="text-label text-[var(--color-text-3)] mb-3">Investigação</h4>
            <ul className="space-y-2">
              {[
                { href: "/radar", label: "Radar de Risco" },
                { href: "/radar?view=cases", label: "Casos" },
                { href: "/coverage", label: "Cobertura de Dados" },
              ].map((l) => (
                <li key={l.href}>
                  <Link href={l.href} className="text-sm text-[var(--color-text-2)] hover:text-[var(--color-text)] transition-colors">
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h4 className="text-label text-[var(--color-text-3)] mb-3">Legal</h4>
            <ul className="space-y-2">
              {[
                { href: "/methodology", label: "Metodologia" },
                { href: "/methodology#legal", label: "Base Legal" },
                { href: "/methodology#lgpd", label: "Política LGPD" },
                { href: "/compliance", label: "Conformidade" },
              ].map((l) => (
                <li key={l.href}>
                  <Link href={l.href} className="text-sm text-[var(--color-text-2)] hover:text-[var(--color-text)] transition-colors">
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Resources */}
          <div>
            <h4 className="text-label text-[var(--color-text-3)] mb-3">Recursos</h4>
            <ul className="space-y-2">
              {[
                { href: "https://github.com", label: "GitHub", ext: true },
                { href: "https://docs.openwatch.org", label: "Documentação", ext: true },
                { href: "/api-health", label: "Status da API", ext: false },
              ].map((l) => (
                <li key={l.href}>
                  <a
                    href={l.href}
                    target={l.ext ? "_blank" : undefined}
                    rel={l.ext ? "noopener noreferrer" : undefined}
                    className="text-sm text-[var(--color-text-2)] hover:text-[var(--color-text)] transition-colors inline-flex items-center gap-1"
                  >
                    {l.label}
                    {l.ext && <ExternalLink size={11} />}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Legal disclaimer */}
        <div className="ow-disclaimer mb-6">
          <strong className="text-[var(--color-text-2)]">Aviso Legal:</strong>{" "}
          Esta plataforma é uma ferramenta de triagem para controle social e auditoria cidadã.
          Os resultados representam hipóteses investigáveis baseadas em dados públicos e{" "}
          <strong className="text-[var(--color-text-2)]">não constituem acusações, provas definitivas ou julgamento de culpa.</strong>{" "}
          Tratamento de dados em conformidade com a LGPD (Lei 13.709/2018), art. 7º, VII.
          Dados pessoais anonimizados conforme art. 12.
        </div>

        {/* Bottom bar */}
        <div className="flex items-center justify-between flex-wrap gap-4 pt-6 border-t border-[var(--color-border)]">
          <p className="text-xs text-[var(--color-text-3)]">
            © 2026 OpenWatch. Open source sob licença MIT.
          </p>
          <p className="text-xs text-[var(--color-text-3)]">
            LAI · Constituição · LGPD · Lei Anticorrupção
          </p>
        </div>
      </div>
    </footer>
  );
}
