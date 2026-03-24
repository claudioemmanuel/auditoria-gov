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
        height: "40px",
        zIndex: 40,
        display: "flex",
        alignItems: "center",
        gap: "0",
        borderBottom: "1px solid var(--color-border)",
        backgroundColor: "var(--color-bg)",
      }}
    >
      {/* Logo */}
      <Link
        href="/"
        style={{
          padding: "0 1rem",
          fontFamily: "var(--font-mono)",
          fontSize: "0.75rem",
          fontWeight: 500,
          color: "var(--color-fg)",
          textDecoration: "none",
          borderRight: "1px solid var(--color-border)",
          height: "100%",
          display: "flex",
          alignItems: "center",
          letterSpacing: "0.1em",
        }}
      >
        OW
      </Link>

      {/* Nav links */}
      <div style={{ display: "flex", alignItems: "center", flex: 1, height: "100%" }}>
        {NAV_ITEMS.map(item => {
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              style={{
                padding: "0 1rem",
                height: "100%",
                display: "flex",
                alignItems: "center",
                fontSize: "0.75rem",
                color: isActive ? "var(--color-accent)" : "var(--color-muted)",
                textDecoration: "none",
                borderBottom: isActive ? "3px solid var(--color-accent)" : "3px solid transparent",
                fontWeight: isActive ? 500 : 400,
                transition: "color 150ms ease-out, border-color 150ms ease-out",
              }}
              aria-current={isActive ? "page" : undefined}
            >
              {item.label}
            </Link>
          );
        })}
      </div>

      {/* ThemeToggle */}
      <div style={{
        padding: "0 0.75rem",
        borderLeft: "1px solid var(--color-border)",
        height: "100%",
        display: "flex",
        alignItems: "center",
      }}>
        <ThemeToggle />
      </div>
    </nav>
  );
}
