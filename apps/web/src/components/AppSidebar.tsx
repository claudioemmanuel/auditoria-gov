"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Radar,
  Activity,
  BookOpen,
  Scale,
  Eye,
  Search,
} from "lucide-react";
import { clsx } from "clsx";
import { OpenWatchLogo } from "./OpenWatchLogo";

const NAV = [
  {
    section: "Investigação",
    items: [
      { href: "/radar",       icon: Radar,      label: "Radar de Risco" },
    ],
  },
  {
    section: "Dados",
    items: [
      { href: "/coverage",    icon: Activity,   label: "Cobertura" },
      { href: "/methodology", icon: BookOpen,   label: "Metodologia" },
    ],
  },
  {
    section: "Mais",
    items: [
      { href: "/compliance",  icon: Scale,      label: "Conformidade" },
      { href: "/api-health",  icon: Eye,        label: "Status da API" },
    ],
  },
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="ow-sidebar">
      {/* Logo */}
      <div className="ow-sidebar-logo">
        <OpenWatchLogo />
      </div>

      {/* Search shortcut */}
      <div className="px-8 py-3 border-b border-[var(--color-border)]">
        <button
          className="w-full ow-btn ow-btn-ghost ow-btn-sm !justify-start gap-2 !text-[var(--color-text-3)] hover:!text-[var(--color-text-2)]"
          onClick={() => {
            const event = new KeyboardEvent("keydown", {
              key: "k",
              metaKey: true,
              bubbles: true,
            });
            document.dispatchEvent(event);
          }}
        >
          <Search size={13} />
          <span className="flex-1 text-left text-xs">Buscar...</span>
          <kbd className="text-mono-xs opacity-50 border border-[var(--color-border)] rounded px-1 py-0.5">⌘K</kbd>
        </button>
      </div>

      {/* Nav sections */}
      <nav className="ow-sidebar-nav" aria-label="Navegação principal">
        {NAV.map((section) => (
            <div key={section.section} className="ow-sidebar-section">
              <div className="ow-sidebar-section-label">{section.section}</div>
              {section.items.map((item) => {
                const isActive =
                  item.href === "/radar"
                    ? pathname === "/radar" || pathname?.startsWith("/signal") || pathname?.startsWith("/case")
                    : pathname?.startsWith(item.href);

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={clsx("ow-nav-item", isActive && "active")}
                  aria-current={isActive ? "page" : undefined}
                >
                  <item.icon className="ow-nav-icon" />
                  {item.label}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-[var(--color-border)]">
        <p className="text-xs text-[var(--color-text-3)] leading-relaxed">
          Auditoria cidadã de dados federais. Open source, LGPD-compliant.
        </p>
      </div>
    </aside>
  );
}
