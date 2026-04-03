"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Eye, Menu, X, Radar, Activity, BookOpen, Scale } from "lucide-react";
import { clsx } from "clsx";

const MOBILE_NAV = [
  { href: "/radar",       icon: Radar,    label: "Radar" },
  { href: "/coverage",    icon: Activity, label: "Cobertura" },
  { href: "/methodology", icon: BookOpen, label: "Metodologia" },
  { href: "/compliance",  icon: Scale,    label: "Conformidade" },
];

export function Header() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  return (
    <>
      <header className="ow-header md:hidden">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 flex-1" onClick={() => setOpen(false)}>
          <div className="ow-sidebar-logo-mark" aria-hidden="true">
            <Eye size={14} color="#09090b" strokeWidth={2.5} />
          </div>
          <span className="ow-sidebar-wordmark">OpenWatch</span>
        </Link>

        {/* Hamburger */}
        <button
          onClick={() => setOpen(!open)}
          className="ow-btn ow-btn-ghost ow-btn-icon"
          aria-label={open ? "Fechar menu" : "Abrir menu"}
          aria-expanded={open}
        >
          {open ? <X size={18} /> : <Menu size={18} />}
        </button>
      </header>

      {/* Mobile drawer */}
      {open && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
            onClick={() => setOpen(false)}
          />
          <nav
            className="fixed top-[var(--header-height)] left-0 right-0 z-50 bg-[var(--color-surface-2)] border-b border-[var(--color-border)] md:hidden animate-slide-up"
            aria-label="Menu móvel"
          >
            <div className="p-3 flex flex-col gap-1">
              {MOBILE_NAV.map((item) => {
                const isActive = pathname === item.href || pathname?.startsWith(item.href + "/");
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={clsx("ow-nav-item", isActive && "active")}
                    onClick={() => setOpen(false)}
                  >
                    <item.icon className="ow-nav-icon" />
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

export default Header;
