"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

const SECTIONS = [
  { id: "principios", label: "Princípios" },
  { id: "pipeline", label: "Pipeline" },
  { id: "tipologias", label: "Tipologias" },
  { id: "scores", label: "Scores de Avaliação" },
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
    <nav aria-label="Tabela de Conteúdo" className="sticky top-8 self-start w-44 shrink-0">
      <p className="text-xs font-semibold uppercase tracking-widest text-muted mb-3">
        Conteúdo
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
                  : "text-secondary hover:text-primary"
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
