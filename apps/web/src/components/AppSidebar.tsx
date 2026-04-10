"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  ArrowLeft,
  BookOpen,
  Eye,
  FileText,
  GitMerge,
  History,
  Layers,
  Network,
  Radar,
  Radio,
  Scale,
  Share2,
  Zap,
} from "lucide-react";
import { clsx } from "clsx";

/* ─── Nav Definitions ─────────────────────────────────────────── */

const RADAR_NAV = [
  {
    section: "Monitoramento",
    items: [
      { href: "/radar", icon: Radar, label: "Visão Geral", exact: true },
      { href: "/radar/rede", icon: Network, label: "Entidades" },
      { href: "/radar/juridico", icon: Scale, label: "Hipóteses Jurídicas" },
    ],
  },
  {
    section: "Dados",
    items: [
      { href: "/coverage", icon: Activity, label: "Cobertura" },
      { href: "/methodology", icon: BookOpen, label: "Metodologia" },
    ],
  },
];

const SIGNAL_NAV = [
  {
    section: "Sinais",
    items: [
      { href: "/radar", icon: Zap, label: "Live Feed" },
      { href: "/coverage", icon: Layers, label: "Pipelines" },
      { href: "/coverage", icon: Activity, label: "Fontes" },
      { href: "/radar", icon: History, label: "Histórico" },
    ],
  },
  {
    section: "Mais",
    items: [
      { href: "/compliance", icon: Scale, label: "Conformidade" },
      { href: "/api-health", icon: Eye, label: "Status da API" },
    ],
  },
];

const GLOBAL_NAV = [
  {
    section: "Plataforma",
    items: [
      { href: "/radar", icon: Radar, label: "Radar de Risco", exact: true },
      { href: "/coverage", icon: Activity, label: "Cobertura" },
      { href: "/methodology", icon: BookOpen, label: "Metodologia" },
    ],
  },
  {
    section: "Mais",
    items: [
      { href: "/compliance", icon: Scale, label: "Conformidade" },
      { href: "/api-health", icon: Eye, label: "Status da API" },
    ],
  },
];

/* ─── Types ───────────────────────────────────────────────────── */

type NavItem = {
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  exact?: boolean;
};

type NavSection = {
  section: string;
  items: NavItem[];
};

/* ─── NavSection renderer ─────────────────────────────────────── */

function NavSections({
  sections,
  pathname,
}: {
  sections: NavSection[];
  pathname: string | null;
}) {
  return (
    <>
      {sections.map((s) => (
        <div key={s.section} className="ow-sidebar-section">
          <div className="ow-sidebar-section-label">{s.section}</div>
          {s.items.map((item) => {
            const isActive =
              item.exact
                ? pathname === item.href
                : !!pathname?.startsWith(item.href);
            return (
              <Link
                key={`${item.href}-${item.label}`}
                href={item.href}
                className={clsx("ow-nav-item", isActive && "active")}
                aria-current={isActive ? "page" : undefined}
              >
                <item.icon className="ow-nav-icon" aria-hidden="true" />
                {item.label}
              </Link>
            );
          })}
        </div>
      ))}
    </>
  );
}

/* ─── Main Component ──────────────────────────────────────────── */

export function AppSidebar() {
  const pathname = usePathname();

  // Domain detection (order matters: dossier ⊂ radar)
  const isDossier = !!pathname?.startsWith("/radar/dossie");
  const isRadar = !isDossier && !!pathname?.startsWith("/radar");
  const isSignal = !!pathname?.startsWith("/signal");

  // Extract caseId when inside a dossier
  const dossierMatch = pathname?.match(/^\/radar\/dossie\/([^/]+)/);
  const caseId = dossierMatch?.[1];

  return (
    <aside className="ow-sidebar" aria-label="Navegação lateral">
      {/* Domain badge */}
      {isDossier ? (
        <span className="ow-sidebar-domain-badge dossier">
          <FileText size={9} aria-hidden="true" />
          Dossiê
        </span>
      ) : isRadar ? (
        <span className="ow-sidebar-domain-badge radar">
          <Radar size={9} aria-hidden="true" />
          Radar
        </span>
      ) : isSignal ? (
        <span className="ow-sidebar-domain-badge signal">
          <Radio size={9} aria-hidden="true" />
          Signal
        </span>
      ) : null}

      <nav className="ow-sidebar-nav">
        {/* ── Dossier nav ── */}
        {isDossier && caseId ? (
          <>
            <div className="ow-sidebar-section">
              <Link href="/radar" className="ow-sidebar-back">
                <ArrowLeft size={13} aria-hidden="true" />
                Voltar ao Radar
              </Link>
              <div className="ow-sidebar-section-label">Navegação</div>
              {(
                [
                  {
                    href: `/radar/dossie/${caseId}`,
                    icon: FileText,
                    label: "Visão Geral",
                    exact: true,
                  },
                  {
                    href: `/radar/dossie/${caseId}/rede`,
                    icon: Share2,
                    label: "Rede de Entidades",
                  },
                  {
                    href: `/radar/dossie/${caseId}/juridico`,
                    icon: Scale,
                    label: "Hipóteses Jurídicas",
                  },
                ] as NavItem[]
              ).map((item) => {
                const isActive = item.exact
                  ? pathname === item.href
                  : !!pathname?.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={clsx("ow-nav-item", isActive && "active")}
                    aria-current={isActive ? "page" : undefined}
                  >
                    <item.icon className="ow-nav-icon" aria-hidden="true" />
                    {item.label}
                  </Link>
                );
              })}
            </div>
            <div className="ow-sidebar-section">
              <div className="ow-sidebar-section-label">Caso</div>
              <Link
                href={`/radar/caso/${caseId}`}
                className={clsx(
                  "ow-nav-item",
                  pathname?.startsWith(`/radar/caso/${caseId}`) && "active",
                )}
              >
                <GitMerge className="ow-nav-icon" aria-hidden="true" />
                Visão do Caso
              </Link>
            </div>
          </>
        ) : isRadar ? (
          <NavSections sections={RADAR_NAV} pathname={pathname} />
        ) : isSignal ? (
          <NavSections sections={SIGNAL_NAV} pathname={pathname} />
        ) : (
          <NavSections sections={GLOBAL_NAV} pathname={pathname} />
        )}
      </nav>

      <div className="p-4 border-t border-[var(--color-border)]">
        <p className="text-xs text-[var(--color-text-3)] leading-relaxed">
          Auditoria cidadã · Open source · LGPD-compliant
        </p>
      </div>
    </aside>
  );
}
