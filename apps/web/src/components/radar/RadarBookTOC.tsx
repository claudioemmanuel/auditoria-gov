"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { BookPage } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useRadarBook } from "@/components/radar/RadarBookContext";

// ─── Types ────────────────────────────────────────────────────────────────────

interface RadarBookTOCProps {
  /** Controlled from parent for mobile drawer mode */
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const MODULE_TYPES = new Set<BookPage["type"]>([
  "radar-hub",
  "radar-rede",
  "radar-juridico",
]);

const DOSSIER_TYPES = new Set<BookPage["type"]>([
  "overview",
  "chapter",
  "signal",
  "network",
  "legal",
]);

const SEVERITY_DOT_STYLE: Record<string, string> = {
  critical: "bg-severity-critical",
  high: "bg-severity-high",
  medium: "bg-severity-medium",
  low: "bg-severity-low",
};

function readCollapsed(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return localStorage.getItem("radar-toc-collapsed") === "true";
  } catch {
    return false;
  }
}

// ─── Sub-components ───────────────────────────────────────────────────────────

interface NavItemProps {
  page: BookPage;
  isActive: boolean;
  collapsed: boolean;
}

function NavItem({ page, isActive, collapsed }: NavItemProps): React.ReactElement {
  const isSignal = page.type === "signal";
  const isChapter = page.type === "chapter";

  const severity = isChapter ? (page as Extract<BookPage, { type: "chapter" }>).severity : null;
  const dotClass = severity ? (SEVERITY_DOT_STYLE[severity] ?? "bg-severity-low") : null;

  return (
    <Link
      href={page.href}
      title={page.label}
      className={cn(
        "flex items-center gap-1.5 rounded-sm py-1 text-xs transition-colors",
        collapsed ? "justify-center px-1" : "px-2",
        isSignal && !collapsed && "pl-6",
        isActive
          ? "border-l-2 border-[var(--color-brand)] bg-[var(--color-bg-2)] text-[var(--color-text)] font-medium"
          : "border-l-2 border-transparent text-[var(--color-text-2)] hover:text-[var(--color-text)] hover:bg-[var(--color-bg-2)]",
      )}
    >
      {/* severity dot for chapters */}
      {dotClass && (
        <span
          className={cn("inline-block h-2 w-2 shrink-0 rounded-full", dotClass)}
          aria-hidden="true"
        />
      )}

      {/* plain dot for non-chapter, non-signal items */}
      {!dotClass && !isSignal && (
        <span
          className={cn(
            "inline-block h-1.5 w-1.5 shrink-0 rounded-full",
            isActive ? "bg-[var(--color-brand)]" : "bg-[var(--color-text-3,var(--color-text-2))]",
          )}
          aria-hidden="true"
        />
      )}

      {/* signal dash */}
      {isSignal && !collapsed && (
        <span className="mr-0.5 text-[var(--color-text-2)]" aria-hidden="true">
          ·
        </span>
      )}

      {!collapsed && (
        <span className="truncate">{page.label}</span>
      )}

      {collapsed && (
        <span className="text-[10px] font-semibold leading-none">
          {page.label.charAt(0).toUpperCase()}
        </span>
      )}
    </Link>
  );
}

interface SectionGroupProps {
  label: string;
  pages: BookPage[];
  allPages: BookPage[];
  currentIndex: number;
  collapsed: boolean;
}

function SectionGroup({
  label,
  pages,
  allPages,
  currentIndex,
  collapsed,
}: SectionGroupProps): React.ReactElement {
  return (
    <div className="mb-3">
      {!collapsed && (
        <p className="mb-1 px-2 text-[10px] font-semibold uppercase tracking-widest text-[var(--color-text-2)]">
          {label}
        </p>
      )}
      {collapsed && (
        <div className="mb-1 flex justify-center">
          <span className="h-px w-5 bg-[var(--color-border,var(--color-bg-2))]" />
        </div>
      )}
      <nav aria-label={label}>
        {pages.map((page) => {
          const idx = allPages.indexOf(page);
          return (
            <NavItem
              key={page.href}
              page={page}
              isActive={idx === currentIndex}
              collapsed={collapsed}
            />
          );
        })}
      </nav>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function RadarBookTOC({
  mobileOpen,
  onMobileClose,
}: RadarBookTOCProps): React.ReactElement {
  const { pages, currentIndex } = useRadarBook();

  const [collapsed, setCollapsed] = useState<boolean>(readCollapsed);

  const toggleCollapsed = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem("radar-toc-collapsed", String(next));
      } catch {
        // ignore
      }
      return next;
    });
  }, []);

  const modulePages = pages.filter((p) => MODULE_TYPES.has(p.type));
  const dossierPages = pages.filter((p) => DOSSIER_TYPES.has(p.type));

  const sidebarContent = (
    <div
      className={cn(
        "flex h-full flex-col overflow-hidden border-r border-[var(--color-border,var(--color-bg-2))] bg-[var(--color-bg)] transition-[width] duration-200",
        collapsed ? "w-10" : "w-48",
      )}
    >
      {/* Header */}
      <div
        className={cn(
          "flex shrink-0 items-center border-b border-[var(--color-border,var(--color-bg-2))] py-2",
          collapsed ? "justify-center px-1" : "justify-between px-2",
        )}
      >
        {!collapsed && (
          <span className="text-xs font-semibold text-[var(--color-text)]">
            Radar ▼
          </span>
        )}
        <button
          type="button"
          onClick={toggleCollapsed}
          aria-label={collapsed ? "Expandir menu" : "Colapsar menu"}
          className="flex h-6 w-6 items-center justify-center rounded text-[var(--color-text-2)] hover:bg-[var(--color-bg-2)] hover:text-[var(--color-text)]"
        >
          {collapsed ? (
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
              <path d="M5 3l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          ) : (
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
              <path d="M9 3L5 7l4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          )}
        </button>
      </div>

      {/* Nav content */}
      <div className="flex-1 overflow-y-auto py-2">
        {modulePages.length > 0 && (
          <SectionGroup
            label="Módulos"
            pages={modulePages}
            allPages={pages}
            currentIndex={currentIndex}
            collapsed={collapsed}
          />
        )}

        {dossierPages.length > 0 && (
          <SectionGroup
            label="Dossiê"
            pages={dossierPages}
            allPages={pages}
            currentIndex={currentIndex}
            collapsed={collapsed}
          />
        )}
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop sidebar — always in layout flow, shrinks to w-10 when collapsed */}
      <aside className="hidden md:flex" aria-label="Navegação do Radar">
        {sidebarContent}
      </aside>

      {/* Mobile overlay drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          {/* backdrop */}
          <div
            className="absolute inset-0 bg-black/50"
            aria-hidden="true"
            onClick={onMobileClose}
          />
          {/* drawer panel */}
          <aside
            className="absolute inset-y-0 left-0 flex w-64 flex-col"
            aria-label="Navegação do Radar"
          >
            {/* close button row */}
            <div className="flex items-center justify-between border-b border-[var(--color-border,var(--color-bg-2))] bg-[var(--color-bg)] px-3 py-2">
              <span className="text-xs font-semibold text-[var(--color-text)]">Radar</span>
              <button
                type="button"
                onClick={onMobileClose}
                aria-label="Fechar menu"
                className="flex h-6 w-6 items-center justify-center rounded text-[var(--color-text-2)] hover:bg-[var(--color-bg-2)]"
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                  <path d="M2 2l10 10M12 2L2 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
              </button>
            </div>

            {/* nav */}
            <div className="flex-1 overflow-y-auto bg-[var(--color-bg)] py-2 px-0">
              {modulePages.length > 0 && (
                <SectionGroup
                  label="Módulos"
                  pages={modulePages}
                  allPages={pages}
                  currentIndex={currentIndex}
                  collapsed={false}
                />
              )}
              {dossierPages.length > 0 && (
                <SectionGroup
                  label="Dossiê"
                  pages={dossierPages}
                  allPages={pages}
                  currentIndex={currentIndex}
                  collapsed={false}
                />
              )}
            </div>
          </aside>
        </div>
      )}
    </>
  );
}
