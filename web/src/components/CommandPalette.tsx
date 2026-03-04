"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Radar,
  Database,
  BookOpen,
  Activity,
} from "lucide-react";

const COMMANDS = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard, shortcut: "D" },
  { label: "Radar — Central de Riscos", href: "/radar", icon: Radar, shortcut: "R" },
  { label: "Cobertura de Dados", href: "/coverage", icon: Database, shortcut: "C" },
  { label: "Metodologia", href: "/methodology", icon: BookOpen, shortcut: "M" },
  { label: "Status da API", href: "/api-health", icon: Activity },
];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const router = useRouter();

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

  const filtered = COMMANDS.filter((cmd) =>
    cmd.label.toLowerCase().includes(search.toLowerCase()),
  );

  const navigate = (href: string) => {
    router.push(href);
    setOpen(false);
    setSearch("");
  };

  if (!open) return null;

  return (
    <>
      <div
        className="fixed inset-0 z-50 bg-black/50"
        onClick={() => setOpen(false)}
      />
      <div className="fixed left-1/2 top-[20%] z-50 w-full max-w-lg -translate-x-1/2 rounded-xl border border-border bg-surface-card shadow-2xl">
        <div className="border-b border-border px-4 py-3">
          <input
            autoFocus
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar paginas..."
            className="w-full bg-transparent text-sm text-primary placeholder:text-placeholder outline-none"
          />
        </div>
        <div className="max-h-72 overflow-y-auto p-2">
          {filtered.length === 0 ? (
            <p className="px-3 py-6 text-center text-sm text-muted">
              Nenhum resultado encontrado.
            </p>
          ) : (
            filtered.map((cmd) => (
              <button
                key={cmd.href}
                onClick={() => navigate(cmd.href)}
                className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-secondary hover:bg-surface-subtle hover:text-primary"
              >
                <cmd.icon className="h-4 w-4 text-muted" />
                <span className="flex-1 text-left">{cmd.label}</span>
                {cmd.shortcut && (
                  <kbd className="rounded border border-border bg-surface-subtle px-1.5 py-0.5 font-mono text-[10px] text-muted">
                    {cmd.shortcut}
                  </kbd>
                )}
              </button>
            ))
          )}
        </div>
      </div>
    </>
  );
}
