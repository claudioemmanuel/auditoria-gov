"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Radar,
  Database,
  BookOpen,
  Shield,
  ChevronLeft,
  ChevronRight,
  Menu,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";

const STORAGE_KEY = "ui:sidebar-collapsed";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { href: "/radar", label: "Radar", icon: Radar, exact: false },
  { href: "/coverage", label: "Cobertura", icon: Database, exact: false },
  { href: "/methodology", label: "Metodologia", icon: BookOpen, exact: false },
];

function ApiHealthDot() {
  const [status, setStatus] = useState<"ok" | "error" | "loading">("loading");

  const ping = useCallback(async () => {
    try {
      const res = await fetch("/api/health", {
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
        status === "ok" && "bg-green-500",
        status === "error" && "bg-red-500",
        status === "loading" && "bg-muted animate-pulse",
      )}
    />
  );
}

export function AppSidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  // Restore collapse state from localStorage
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

  // Close mobile menu on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  // Close mobile menu on Escape
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
    <div className="flex h-full flex-col">
      {/* Logo + collapse toggle */}
      <div className="flex h-14 items-center justify-between border-b border-border px-3">
        {(!collapsed || isMobile) && (
          <Link
            href="/"
            className="flex items-center gap-2 font-semibold text-primary"
            onClick={() => isMobile && setMobileOpen(false)}
          >
            <Shield className="h-5 w-5 shrink-0 text-accent" />
            <span className="truncate text-sm">AuditorIA</span>
          </Link>
        )}
        {collapsed && !isMobile && (
          <Link href="/" className="flex items-center justify-center">
            <Shield className="h-5 w-5 text-accent" />
          </Link>
        )}
        {!isMobile && (
          <button
            onClick={toggleCollapsed}
            className="ml-auto flex h-7 w-7 items-center justify-center rounded-md text-muted hover:bg-surface-subtle hover:text-secondary"
            aria-label={collapsed ? "Expandir menu" : "Recolher menu"}
          >
            {collapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </button>
        )}
        {isMobile && (
          <button
            onClick={() => setMobileOpen(false)}
            className="ml-auto flex h-7 w-7 items-center justify-center rounded-md text-muted hover:bg-surface-subtle"
            aria-label="Fechar menu"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Nav items */}
      <nav className="flex-1 space-y-0.5 overflow-y-auto p-2">
        {NAV_ITEMS.map((item) => {
          const active = isActive(item);
          return (
            <Link
              key={item.href}
              href={item.href}
              title={collapsed && !isMobile ? item.label : undefined}
              className={cn(
                "group flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm font-medium transition-colors",
                "border-l-2",
                active
                  ? "border-accent bg-accent-subtle text-accent"
                  : "border-transparent text-secondary hover:bg-surface-subtle hover:text-primary",
              )}
            >
              <item.icon
                className={cn(
                  "h-4 w-4 shrink-0",
                  active ? "text-accent" : "text-muted group-hover:text-secondary",
                )}
              />
              {(!collapsed || isMobile) && (
                <span className="truncate">{item.label}</span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* API health */}
      <div className="border-t border-border p-3">
        {collapsed && !isMobile ? (
          <div className="flex justify-center">
            <ApiHealthDot />
          </div>
        ) : (
          <div className="flex items-center gap-2 text-xs text-muted">
            <ApiHealthDot />
            <span>API</span>
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
          "hidden lg:flex lg:flex-col",
          "fixed inset-y-0 left-0 z-30 border-r border-border bg-surface-card",
          "transition-[width] duration-200",
          collapsed ? "w-14" : "w-56",
        )}
      >
        {sidebarContent()}
      </aside>

      {/* Desktop spacer */}
      <div
        className={cn(
          "hidden lg:block shrink-0 transition-[width] duration-200",
          collapsed ? "w-14" : "w-56",
        )}
      />

      {/* Mobile hamburger */}
      <button
        onClick={() => setMobileOpen(true)}
        className="fixed left-4 top-3 z-40 flex h-8 w-8 items-center justify-center rounded-md border border-border bg-surface-card text-secondary shadow-sm lg:hidden"
        aria-label="Abrir menu"
      >
        <Menu className="h-4 w-4" />
      </button>

      {/* Mobile slide-over */}
      {mobileOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40 bg-black/40 lg:hidden"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
          {/* Drawer */}
          <aside className="fixed inset-y-0 left-0 z-50 w-64 border-r border-border bg-surface-card lg:hidden">
            {sidebarContent(true)}
          </aside>
        </>
      )}
    </>
  );
}
