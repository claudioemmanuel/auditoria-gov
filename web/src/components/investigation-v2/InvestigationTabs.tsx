"use client";

import { useCallback, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";

export type InvestigationTab = "overview" | "cases" | "signals" | "entities" | "network" | "legal";

const TABS: { value: InvestigationTab; label: string }[] = [
  { value: "overview", label: "Visao Geral" },
  { value: "cases", label: "Casos" },
  { value: "signals", label: "Sinais" },
  { value: "entities", label: "Entidades" },
  { value: "network", label: "Rede" },
  { value: "legal", label: "Juridico" },
];

interface InvestigationTabsProps {
  activeTab: InvestigationTab;
  onChange: (tab: InvestigationTab) => void;
}

export function InvestigationTabs({ activeTab, onChange }: InvestigationTabsProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Scroll active tab into view on mount
  useEffect(() => {
    if (!containerRef.current) return;
    const activeEl = containerRef.current.querySelector("[data-active=true]") as HTMLElement | null;
    activeEl?.scrollIntoView({ inline: "center", block: "nearest" });
  }, [activeTab]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      const idx = TABS.findIndex((t) => t.value === activeTab);
      if (e.key === "ArrowRight") {
        e.preventDefault();
        const next = TABS[(idx + 1) % TABS.length];
        onChange(next.value);
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        const prev = TABS[(idx - 1 + TABS.length) % TABS.length];
        onChange(prev.value);
      }
    },
    [activeTab, onChange],
  );

  return (
    <div
      ref={containerRef}
      role="tablist"
      className="flex gap-1 overflow-x-auto scrollbar-none border-t border-border pt-4 -mb-px"
      onKeyDown={handleKeyDown}
    >
      {TABS.map((tab) => {
        const active = tab.value === activeTab;
        return (
          <button
            key={tab.value}
            role="tab"
            aria-selected={active}
            data-active={active}
            tabIndex={active ? 0 : -1}
            onClick={() => onChange(tab.value)}
            className={cn(
              "shrink-0 rounded-t-lg px-4 py-2 text-sm font-medium transition-colors duration-120",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50",
              active
                ? "border-b-2 border-accent text-accent bg-surface-card"
                : "text-muted hover:text-secondary hover:bg-surface-subtle",
            )}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
