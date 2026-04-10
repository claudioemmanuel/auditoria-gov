"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Radar, Radio, Search, Menu, X, BookOpen, Activity, Scale, Eye } from "lucide-react";
import { clsx } from "clsx";
import { OpenWatchLogo } from "./OpenWatchLogo";

const MOBILE_NAV = [
  { href: "/radar", label: "Radar de Risco" },
  { href: "/coverage", icon: Activity, label: "Cobertura" },
  { href: "/methodology", icon: BookOpen, label: "Metodologia" },
  { href: "/compliance", icon: Scale, label: "Conformidade" },
  { href: "/api-health", icon: Eye, label: "Status da API" },
];

function triggerCmdK() {
  document.dispatchEvent(
    new KeyboardEvent("keydown", { key: "k", metaKey: true, bubbles: true }),
  );
}

export function Topbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();

  const isSignalDomain = pathname?.startsWith("/signal");
  const isRadarDomain =
    pathname?.startsWith("/radar") ||
    (!isSignalDomain &&
      !pathname?.startsWith("/coverage") &&
      !pathname?.startsWith("/methodology") &&
      !pathname?.startsWith("/compliance") &&
      !pathname?.startsWith("/api-health"));

  return (
    <>
      <header className="ow-topbar">
        {/* Logo */}
        <Link href="/" className="ow-topbar-logo" aria-label="OpenWatch — página inicial">
          <OpenWatchLogo size="sm" />
        </Link>

        {/* Domain Switcher */}
        <div className="ow-domain-switcher hidden sm:flex" role="navigation" aria-label="Domínio">
          <Link
            href="/radar"
            className={clsx("ow-domain-tab", isRadarDomain && "active")}
            aria-current={isRadarDomain ? "page" : undefined}
          >
            <Radar size={13} aria-hidden="true" />
            Radar
          </Link>
          <span
            className="ow-domain-tab"
            style={{ opacity: 0.35, cursor: "not-allowed" }}
            title="Signal Explorer — em breve"
            aria-disabled="true"
          >
            <Radio size={13} aria-hidden="true" />
            Signal
            <span
              className="text-[0.5rem] font-bold uppercase tracking-widest ml-0.5 opacity-80"
              style={{ color: "var(--color-brand)" }}
            >
              soon
            </span>
          </span>
        </div>

        {/* Spacer */}
        <div className="flex-1" aria-hidden="true" />

        {/* Search */}
        <button
          className="ow-topbar-action hidden sm:flex"
          onClick={triggerCmdK}
          aria-label="Buscar (⌘K)"
        >
          <Search size={14} aria-hidden="true" />
          <span className="hidden lg:inline text-xs text-[var(--color-text-3)]">Buscar...</span>
          <kbd className="hidden lg:inline text-[0.625rem] opacity-40 border border-[var(--color-border)] rounded px-1 py-0.5 font-mono">
            ⌘K
          </kbd>
        </button>

        {/* Mobile hamburger */}
        <button
          className="ow-topbar-action sm:hidden"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label={mobileOpen ? "Fechar menu" : "Abrir menu"}
          aria-expanded={mobileOpen}
          aria-controls="mobile-nav"
        >
          {mobileOpen ? <X size={18} /> : <Menu size={18} />}
        </button>
      </header>

      {/* Mobile drawer */}
      {mobileOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm sm:hidden"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
          <nav
            id="mobile-nav"
            className="fixed top-[var(--topbar-height)] left-0 right-0 z-50 bg-[var(--color-surface-2)] border-b border-[var(--color-border)] sm:hidden animate-slide-up"
            aria-label="Menu móvel"
          >
            <div className="p-3 flex flex-col gap-1">
              {/* Domain switcher */}
              <div className="flex gap-2 pb-3 mb-1 border-b border-[var(--color-border)]">
                <Link
                  href="/radar"
                  className={clsx("ow-domain-tab flex-1 justify-center", isRadarDomain && "active")}
                  onClick={() => setMobileOpen(false)}
                >
                  <Radar size={13} />
                  Radar
                </Link>
                <span
                  className="ow-domain-tab flex-1 justify-center"
                  style={{ opacity: 0.35, cursor: "not-allowed" }}
                  aria-disabled="true"
                  title="Signal Explorer — em breve"
                >
                  <Radio size={13} />
                  Signal
                </span>
              </div>

              {/* Search */}
              <button
                className="ow-nav-item"
                onClick={() => { setMobileOpen(false); triggerCmdK(); }}
              >
                <Search size={14} className="ow-nav-icon" />
                Buscar...
                <kbd className="ml-auto text-[0.625rem] opacity-40 border border-[var(--color-border)] rounded px-1 py-0.5 font-mono">
                  ⌘K
                </kbd>
              </button>

              <div className="h-px bg-[var(--color-border)] my-1" />

              {MOBILE_NAV.map((item) => {
                const isActive =
                  pathname === item.href || pathname?.startsWith(item.href + "/");
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={clsx("ow-nav-item", isActive && "active")}
                    onClick={() => setMobileOpen(false)}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </nav>
        </>
      )}
    </>
  );
}
