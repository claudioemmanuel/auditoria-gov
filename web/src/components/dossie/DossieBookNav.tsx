"use client";

import { useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { useDossieBook } from "./DossieBookContext";

export function DossieBookNav() {
  const router = useRouter();
  const { pages, currentIndex } = useDossieBook();

  const totalPages = pages.length;
  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex < totalPages - 1;
  const currentPage = pages[currentIndex];

  const goPrev = useCallback(() => {
    if (hasPrev) {
      const prev = pages[currentIndex - 1];
      if (prev) router.push(prev.href);
    }
  }, [hasPrev, pages, currentIndex, router]);

  const goNext = useCallback(() => {
    if (hasNext) {
      const next = pages[currentIndex + 1];
      if (next) router.push(next.href);
    }
  }, [hasNext, pages, currentIndex, router]);

  // Keyboard navigation
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        goPrev();
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        goNext();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [goPrev, goNext]);

  if (totalPages === 0 || currentIndex < 0) return null;

  const showDots = totalPages <= 11;

  return (
    <>
      {/* Desktop side arrows */}
      <button
        onClick={goPrev}
        disabled={!hasPrev}
        aria-label="Pagina anterior"
        className={cn(
          "fixed left-4 top-1/2 z-50 hidden -translate-y-1/2 rounded-full border border-border bg-surface-card/90 p-2.5 shadow-lg backdrop-blur transition-all md:flex",
          hasPrev
            ? "text-primary hover:bg-surface-subtle hover:border-accent/30"
            : "cursor-not-allowed text-muted opacity-40",
        )}
      >
        <ChevronLeft className="h-5 w-5" />
      </button>

      <button
        onClick={goNext}
        disabled={!hasNext}
        aria-label="Proxima pagina"
        className={cn(
          "fixed right-4 top-1/2 z-50 hidden -translate-y-1/2 rounded-full border border-border bg-surface-card/90 p-2.5 shadow-lg backdrop-blur transition-all md:flex",
          hasNext
            ? "text-primary hover:bg-surface-subtle hover:border-accent/30"
            : "cursor-not-allowed text-muted opacity-40",
        )}
      >
        <ChevronRight className="h-5 w-5" />
      </button>

      {/* Bottom bar (always visible) */}
      <div className="fixed bottom-0 left-0 right-0 z-50 flex h-12 items-center justify-between border-t border-border bg-surface-card/90 px-4 backdrop-blur">
        {/* Mobile prev */}
        <button
          onClick={goPrev}
          disabled={!hasPrev}
          className={cn(
            "flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium transition-colors md:hidden",
            hasPrev ? "text-primary hover:bg-surface-subtle" : "text-muted opacity-40",
          )}
        >
          <ChevronLeft className="h-4 w-4" />
          Ant.
        </button>

        {/* Center: label + page indicator + dots */}
        <div className="flex flex-1 flex-col items-center justify-center gap-0.5 overflow-hidden">
          <span className="max-w-[240px] truncate text-xs font-medium text-primary sm:max-w-[400px]">
            {currentPage?.label}
          </span>
          <div className="flex items-center gap-2">
            {showDots && (
              <div className="flex items-center gap-1">
                {pages.map((page, i) => (
                  <button
                    key={page.href}
                    onClick={() => router.push(page.href)}
                    aria-label={`Ir para ${page.label}`}
                    className={cn(
                      "h-1.5 w-1.5 rounded-full transition-all",
                      i === currentIndex
                        ? "bg-accent scale-125"
                        : "bg-muted/40 hover:bg-muted",
                    )}
                  />
                ))}
              </div>
            )}
            <span className="font-mono text-[10px] text-muted">
              Pagina {currentIndex + 1} de {totalPages}
            </span>
          </div>
        </div>

        {/* Mobile next */}
        <button
          onClick={goNext}
          disabled={!hasNext}
          className={cn(
            "flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium transition-colors md:hidden",
            hasNext ? "text-primary hover:bg-surface-subtle" : "text-muted opacity-40",
          )}
        >
          Prox.
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </>
  );
}
