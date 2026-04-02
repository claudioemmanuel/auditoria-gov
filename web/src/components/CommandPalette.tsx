"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Search, ArrowRight, Radar, Activity, BookOpen, Scale, Eye, X } from "lucide-react";

const QUICK_ACTIONS = [
  { label: "Radar de Risco",    href: "/radar",       icon: Radar,    group: "Navegação" },
  { label: "Cobertura",         href: "/coverage",    icon: Activity, group: "Navegação" },
  { label: "Metodologia",       href: "/methodology", icon: BookOpen, group: "Navegação" },
  { label: "Conformidade",      href: "/compliance",  icon: Scale,    group: "Navegação" },
  { label: "Status da API",     href: "/api-health",  icon: Eye,      group: "Navegação" },
];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const filtered = query.trim()
    ? QUICK_ACTIONS.filter((a) =>
        a.label.toLowerCase().includes(query.toLowerCase())
      )
    : QUICK_ACTIONS;

  const handleSelect = useCallback(
    (href: string) => {
      router.push(href);
      setOpen(false);
      setQuery("");
      setSelected(0);
    },
    [router]
  );

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((v) => !v);
        setQuery("");
        setSelected(0);
      }
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 50);
  }, [open]);

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelected((v) => Math.min(v + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelected((v) => Math.max(v - 1, 0));
    } else if (e.key === "Enter" && filtered[selected]) {
      handleSelect(filtered[selected].href);
    }
  }

  if (!open) return null;

  return (
    <div className="ow-cmd-overlay" onClick={() => setOpen(false)}>
      <div
        className="ow-cmd-box animate-scale-in"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Paleta de comandos"
        aria-modal="true"
      >
        {/* Input */}
        <div className="relative">
          <Search
            size={15}
            className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--color-text-3)]"
          />
          <input
            ref={inputRef}
            className="ow-cmd-input pl-10 pr-10"
            placeholder="Buscar ou navegar..."
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSelected(0); }}
            onKeyDown={onKeyDown}
            aria-autocomplete="list"
          />
          <button
            onClick={() => setOpen(false)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-text-3)] hover:text-[var(--color-text-2)]"
            aria-label="Fechar"
          >
            <X size={15} />
          </button>
        </div>

        {/* Results */}
        <div className="pb-2 max-h-72 overflow-y-auto" role="listbox">
          {filtered.length === 0 ? (
            <p className="text-sm text-[var(--color-text-3)] text-center py-8">
              Nenhum resultado para &quot;{query}&quot;
            </p>
          ) : (
            filtered.map((item, i) => (
              <button
                key={item.href}
                role="option"
                aria-selected={i === selected}
                className={`ow-cmd-item w-full ${i === selected ? "selected" : ""}`}
                onClick={() => handleSelect(item.href)}
              >
                <item.icon size={15} className="text-[var(--color-text-3)]" />
                <span className="flex-1 text-left">{item.label}</span>
                <span className="text-xs text-[var(--color-text-3)]">{item.group}</span>
                <ArrowRight size={13} className="text-[var(--color-text-3)] opacity-50" />
              </button>
            ))
          )}
        </div>

        {/* Footer hint */}
        <div className="px-4 py-2 border-t border-[var(--color-border)] flex items-center gap-3 text-xs text-[var(--color-text-3)]">
          <span><kbd className="font-mono">↑↓</kbd> navegar</span>
          <span><kbd className="font-mono">↵</kbd> selecionar</span>
          <span><kbd className="font-mono">Esc</kbd> fechar</span>
        </div>
      </div>
    </div>
  );
}
