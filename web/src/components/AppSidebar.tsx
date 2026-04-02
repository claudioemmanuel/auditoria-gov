"use client";
import { useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "@/components/ThemeToggle";

const NAV_ITEMS = [
  { href: "/radar",       label: "Investigação", shortcut: "R" },
  { href: "/coverage",    label: "Cobertura",    shortcut: "C" },
  { href: "/methodology", label: "Metodologia",  shortcut: "M" },
  { href: "/api-health",  label: "Saúde API",    shortcut: "S" },
];

const SIDEBAR_BG   = "var(--color-sidebar-bg)";
const SIDEBAR_BORDER = "var(--color-sidebar-border)";
const SIDEBAR_TEXT = "var(--color-sidebar-text)";
const SIDEBAR_TEXT_ACTIVE = "var(--color-sidebar-text-active)";
const SIDEBAR_HOVER = "var(--color-sidebar-hover)";
const CYAN = "var(--color-accent-trust)";

export function AppSidebar() {
  const pathname = usePathname();

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      const item = NAV_ITEMS.find(i => i.shortcut === e.key.toUpperCase());
      if (item) window.location.href = item.href;
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <nav
      aria-label="Navegação principal"
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        height: "48px",
        zIndex: 40,
        display: "flex",
        alignItems: "stretch",
        backgroundColor: SIDEBAR_BG,
        borderBottom: `1px solid ${SIDEBAR_BORDER}`,
        boxShadow: "0 1px 12px rgba(0,0,0,0.35)",
      }}
    >
      {/* Logo */}
      <Link
        href="/"
        style={{
          padding: "0 1.25rem",
          fontFamily: "var(--font-mono)",
          fontSize: "0.8125rem",
          fontWeight: 600,
          color: SIDEBAR_TEXT_ACTIVE,
          textDecoration: "none",
          borderRight: `1px solid ${SIDEBAR_BORDER}`,
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
          letterSpacing: "0.06em",
          whiteSpace: "nowrap",
          flexShrink: 0,
        }}
      >
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: "20px",
            height: "20px",
            borderRadius: "4px",
            background: "var(--color-accent-trust)",
            color: "#fff",
            fontSize: "0.625rem",
            fontWeight: 700,
            letterSpacing: "0.05em",
            flexShrink: 0,
          }}
        >
          OW
        </span>
        <span>OpenWatch</span>
      </Link>

      {/* Nav links */}
      <div style={{ display: "flex", alignItems: "stretch", flex: 1 }}>
        {NAV_ITEMS.map(item => {
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              style={{
                padding: "0 1rem",
                display: "flex",
                alignItems: "center",
                fontSize: "0.8125rem",
                fontWeight: isActive ? 500 : 400,
                color: isActive ? SIDEBAR_TEXT_ACTIVE : SIDEBAR_TEXT,
                textDecoration: "none",
                borderBottom: isActive
                  ? `2px solid ${CYAN}`
                  : "2px solid transparent",
                background: "transparent",
                transition: "color 150ms ease-out, background 150ms ease-out, border-color 150ms ease-out",
                letterSpacing: "0.01em",
              }}
              onMouseEnter={e => {
                if (!isActive) (e.currentTarget as HTMLAnchorElement).style.background = SIDEBAR_HOVER;
              }}
              onMouseLeave={e => {
                if (!isActive) (e.currentTarget as HTMLAnchorElement).style.background = "transparent";
              }}
              aria-current={isActive ? "page" : undefined}
            >
              {item.label}
            </Link>
          );
        })}
      </div>

      {/* Right: keyboard hint + ThemeToggle */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.25rem",
          padding: "0 0.75rem",
          borderLeft: `1px solid ${SIDEBAR_BORDER}`,
          flexShrink: 0,
        }}
      >
        <ThemeToggle
          collapsed
          className="!text-[var(--color-sidebar-text)] hover:!bg-[var(--color-sidebar-hover)] hover:!text-[var(--color-sidebar-text-active)]"
        />
      </div>
    </nav>
  );
}
