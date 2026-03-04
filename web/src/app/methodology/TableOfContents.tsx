"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

const SECTIONS = [
  { id: "principios", label: "Principios" },
  { id: "pipeline", label: "Pipeline" },
  { id: "tipologias", label: "Tipologias" },
  { id: "scores", label: "Scores de Avaliacao" },
  { id: "escopo", label: "Escopo" },
  { id: "base-legal", label: "Base Legal" },
];

export function TableOfContents() {
  const [activeId, setActiveId] = useState<string>("");

  useEffect(() => {
    const observers: IntersectionObserver[] = [];

    SECTIONS.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (!el) return;

      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              setActiveId(id);
            }
          });
        },
        { rootMargin: "-20% 0% -70% 0%", threshold: 0 }
      );

      observer.observe(el);
      observers.push(observer);
    });

    return () => {
      observers.forEach((obs) => obs.disconnect());
    };
  }, []);

  return (
    <nav aria-label="Tabela de Conteudo" className="sticky top-20 self-start w-48 flex-shrink-0">
      <p className="font-display text-xs font-semibold uppercase tracking-wider text-muted mb-3">
        Conteudo
      </p>
      <ol className="space-y-1">
        {SECTIONS.map(({ id, label }, i) => (
          <li key={id}>
            <a
              href={`#${id}`}
              onClick={(e) => {
                e.preventDefault();
                document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
              }}
              className={cn(
                "flex items-start gap-2 rounded px-2 py-1 text-xs leading-snug transition-colors",
                activeId === id
                  ? "text-accent font-medium"
                  : "text-secondary hover:text-accent"
              )}
            >
              <span className="font-mono tabular-nums text-muted shrink-0 w-4 text-right">
                {i + 1}.
              </span>
              <span>{label}</span>
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}
