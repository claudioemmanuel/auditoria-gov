"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Radar,
  Database,
  BookOpen,
  Activity,
  ChevronLeft,
  ChevronRight,
  Menu,
  X,
  Search,
  Shield,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/ThemeToggle";

const STORAGE_KEY = "ui:sidebar-collapsed";

const NAV_ITEMS = [
  { href: "/radar", label: "Investigacao", icon: Radar, exact: false, shortcut: "R" },
  { href: "/coverage", label: "Cobertura", icon: Database, exact: false, shortcut: "C" },
  { href: "/methodology", label: "Metodologia", icon: BookOpen, exact: false, shortcut: "M" },
  { href: "/api-health", label: "Saude API", icon: Activity, exact: false, shortcut: "H" },
];

function ApiHealthDot() {
  const [status, setStatus] = useState<"ok" | "error" | "loading">("loading");

  const ping = useCallback(async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/health`, {
        signal: AbortSignal.timeout(5000),
        cache: "no-store",
      });
      setStatus(res.ok ? "ok" : "error");
    } catch {
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    ping();
    const id = setInterval(ping, 60_000);
    return () => clearInterval(id);
  }, [ping]);

  return (
    <span
      className={cn(
        "inline-block h-2 w-2 rounded-full",
        status === "ok" && "bg-success",
        status === "error" && "bg-error",
        status === "loading" && "bg-sidebar-text animate-pulse",
      )}
    />
  );
}

export function AppSidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored !== null) setCollapsed(stored === "true");
    } catch {}
  }, []);

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(STORAGE_KEY, String(next));
      } catch {}
      return next;
    });
  };

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMobileOpen(false);
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  function isActive(item: (typeof NAV_ITEMS)[number]) {
    if (item.exact) return pathname === item.href;
    return pathname === item.href || pathname.startsWith(item.href + "/");
  }

  const sidebarContent = (isMobile = false) => (
    <div className="flex h-full flex-col bg-sidebar-bg">
      {/* ── Brand header ───────────────────────────────── */}
      <div className="flex h-14 items-center gap-2 border-b border-sidebar-border px-3">
        {!collapsed || isMobile ? (
          <Link
            href="/"
            className="flex items-center gap-2.5"
            onClick={() => isMobile && setMobileOpen(false)}
          >
            <Shield className="h-4 w-4 shrink-0 text-accent" />
            <div className="flex flex-col leading-none">
              <span className="font-display text-[12px] font-bold tracking-tight text-sidebar-text-active">
                OpenWatch
              </span>
              <span className="font-mono text-[9px] tracking-widest text-sidebar-text/40 uppercase">
                Gov · v2
              </span>
            </div>
          </Link>
        ) : (
          <Link href="/" className="flex w-full items-center justify-center">
            <Shield className="h-5 w-5 text-accent" />
          </Link>
        )}
        {!isMobile && !collapsed && (
          <button
            onClick={toggleCollapsed}
            className="ml-auto flex h-6 w-6 items-center justify-center rounded-[6px] text-sidebar-text hover:bg-sidebar-hover hover:text-sidebar-text-active"
            aria-label="Recolher menu"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </button>
        )}
        {!isMobile && collapsed && (
          <button
            onClick={toggleCollapsed}
            className="ml-auto flex h-6 w-6 items-center justify-center rounded-[6px] text-sidebar-text hover:bg-sidebar-hover hover:text-sidebar-text-active"
            aria-label="Expandir menu"
          >
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        )}
        {isMobile && (
          <button
            onClick={() => setMobileOpen(false)}
            className="ml-auto flex h-6 w-6 items-center justify-center rounded-[6px] text-sidebar-text hover:bg-sidebar-hover"
            aria-label="Fechar menu"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>


      {/* ── Navigation ─────────────────────────────────── */}
      <nav className="flex-1 overflow-y-auto px-2 pt-2 pb-2">
        {(!collapsed || isMobile) && (
          <div className="mx-2.5 mb-2 border-t border-sidebar-border/50" />
        )}
        <div className="space-y-0.5">
        {NAV_ITEMS.map((item) => {
          const active = isActive(item);
          return (
            <Link
              key={item.href}
              href={item.href}
              title={collapsed && !isMobile ? item.label : undefined}
              className={cn(
                "group flex items-center gap-2.5 rounded-[8px] px-2.5 py-1.5 text-sm font-medium transition-colors duration-100",
                active
                  ? "bg-accent/12 text-accent"
                  : "text-sidebar-text hover:bg-sidebar-hover/80 hover:text-sidebar-text-active",
              )}
            >
              <item.icon
                className={cn(
                  "h-4 w-4 shrink-0",
                  active
                    ? "text-accent"
                    : "text-sidebar-text group-hover:text-sidebar-text-active",
                )}
              />
              {(!collapsed || isMobile) && (
                <>
                  <span className="flex-1 truncate">{item.label}</span>
                  <kbd
                    className={cn(
                      "rounded-[3px] bg-sidebar-hover px-1 py-0.5 font-mono text-[9px] transition-opacity duration-100",
                      active
                        ? "text-sidebar-text opacity-60"
                        : "text-sidebar-text/50 opacity-0 group-hover:opacity-100",
                    )}
                  >
                    {item.shortcut}
                  </kbd>
                </>
              )}
            </Link>
          );
        })}
        </div>
      </nav>

      {/* ── Footer: theme toggle + API health ──────────── */}
      <div className="border-t border-sidebar-border p-2">
        {collapsed && !isMobile ? (
          <div className="flex flex-col items-center gap-2 py-1">
            <ThemeToggle collapsed={true} />
            <ApiHealthDot />
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <ThemeToggle collapsed={false} />
            <span className="text-sidebar-border/60 text-xs select-none">·</span>
            <div className="flex items-center gap-1.5 font-mono text-[10px] text-sidebar-text">
              <ApiHealthDot />
              <span>API</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className={cn(
          "hidden lg:flex lg:flex-col lg:shrink-0",
          "border-r border-sidebar-border bg-sidebar-bg border-t-2 border-t-accent",
          "transition-[width] duration-200",
          collapsed ? "w-[56px]" : "w-[220px]",
        )}
      >
        {sidebarContent()}
      </aside>

      {/* Mobile hamburger */}
      <button
        onClick={() => setMobileOpen(true)}
        className="fixed left-3 top-3 z-40 flex h-8 w-8 items-center justify-center rounded-[10px] bg-sidebar-bg text-sidebar-text-active shadow-lg lg:hidden"
        aria-label="Abrir menu"
      >
        <Menu className="h-4 w-4" />
      </button>

      {/* Mobile slide-over */}
      {mobileOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/50 lg:hidden"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
          <aside className="fixed inset-y-0 left-0 z-50 w-[260px] lg:hidden">
            {sidebarContent(true)}
          </aside>
        </>
      )}
    </>
  );
}
