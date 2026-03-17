"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  Radar,
  Database,
  BookOpen,
  Activity,
} from "lucide-react";
import { cn } from "@/lib/utils";

const COMMANDS = [
  { label: "Investigacao — Central de Riscos", href: "/radar", icon: Radar, shortcut: "R" },
  { label: "Cobertura de Dados", href: "/coverage", icon: Database, shortcut: "C" },
  { label: "Metodologia", href: "/methodology", icon: BookOpen, shortcut: "M" },
  { label: "Saude da API", href: "/api-health", icon: Activity, shortcut: "H" },
];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const filtered = COMMANDS.filter((cmd) =>
    cmd.label.toLowerCase().includes(search.toLowerCase()),
  );

  // Reset selection when filter changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [search]);

  // Open/close with Cmd+K
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
      if (e.key === "Escape") {
        setOpen(false);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  // Focus input when opening
  useEffect(() => {
    if (open) {
      setSearch("");
      setSelectedIndex(0);
      // Small delay for animation
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  const navigate = useCallback(
    (href: string) => {
      router.push(href);
      setOpen(false);
      setSearch("");
    },
    [router],
  );

  // Keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % filtered.length);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + filtered.length) % filtered.length);
      } else if (e.key === "Enter" && filtered[selectedIndex]) {
        e.preventDefault();
        navigate(filtered[selectedIndex].href);
      }
    },
    [filtered, selectedIndex, navigate],
  );

  // Scroll selected item into view
  useEffect(() => {
    if (!listRef.current) return;
    const el = listRef.current.children[selectedIndex] as HTMLElement | undefined;
    el?.scrollIntoView({ block: "nearest" });
  }, [selectedIndex]);

  if (!open) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px] animate-[fadeIn_180ms_ease]"
        onClick={() => setOpen(false)}
      />

      {/* Palette */}
      <div
        className="fixed left-1/2 top-[20%] z-50 w-full max-w-lg -translate-x-1/2 rounded-[14px] border border-border bg-surface-card shadow-2xl animate-[slideDown_220ms_ease]"
        role="dialog"
        aria-label="Busca rapida"
      >
        {/* Search input */}
        <div className="border-b border-border px-4 py-3">
          <input
            ref={inputRef}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Buscar paginas..."
            className="w-full bg-transparent text-sm text-primary placeholder:text-placeholder outline-none"
          />
        </div>

        {/* Results */}
        <div ref={listRef} className="max-h-72 overflow-y-auto p-2">
          {filtered.length === 0 ? (
            <p className="px-3 py-6 text-center text-sm text-muted">
              Nenhum resultado encontrado.
            </p>
          ) : (
            filtered.map((cmd, i) => (
              <button
                key={cmd.href}
                onClick={() => navigate(cmd.href)}
                className={cn(
                  "flex w-full items-center gap-3 rounded-[10px] px-3 py-2 text-sm transition-colors duration-120",
                  i === selectedIndex
                    ? "bg-accent text-white"
                    : "text-secondary hover:bg-surface-subtle hover:text-primary",
                )}
              >
                <cmd.icon className={cn("h-4 w-4", i === selectedIndex ? "text-white/80" : "text-muted")} />
                <span className="flex-1 text-left">{cmd.label}</span>
                {cmd.shortcut && (
                  <kbd
                    className={cn(
                      "rounded-[4px] border px-1.5 py-0.5 font-mono text-[10px]",
                      i === selectedIndex
                        ? "border-white/20 text-white/70"
                        : "border-border bg-surface-subtle text-muted",
                    )}
                  >
                    {cmd.shortcut}
                  </kbd>
                )}
              </button>
            ))
          )}
        </div>
      </div>

      {/* Animations */}
      <style jsx global>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes slideDown {
          from {
            opacity: 0;
            transform: translate(-50%, -8px);
          }
          to {
            opacity: 1;
            transform: translate(-50%, 0);
          }
        }
      `}</style>
    </>
  );
}
