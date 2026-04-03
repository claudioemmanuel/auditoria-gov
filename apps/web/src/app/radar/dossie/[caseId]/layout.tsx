"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams, usePathname } from "next/navigation";
import Link from "next/link";
import { Loader2, AlertTriangle } from "lucide-react";
import { getDossierTimeline } from "@/lib/api";
import type { DossierTimelineResponse, BookPage } from "@/lib/types";
import {
  DossieBookContext,
  buildBookSequence,
} from "@/components/dossie/DossieBookContext";
import { DossieBookNav } from "@/components/dossie/DossieBookNav";

export default function DossieBookLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { caseId } = useParams<{ caseId: string }>();
  const pathname = usePathname();

  const [data, setData] = useState<DossierTimelineResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!caseId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);

    getDossierTimeline(caseId)
      .then((res) => {
        if (!cancelled) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Erro ao carregar dados");
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [caseId]);

  const pages = useMemo<BookPage[]>(() => {
    if (!data || !caseId) return [];
    return buildBookSequence(caseId, data);
  }, [data, caseId]);

  const currentIndex = useMemo(() => {
    if (pages.length === 0) return -1;
    // Match current pathname to a page href
    const idx = pages.findIndex((p) => pathname === p.href);
    if (idx >= 0) return idx;
    // Fallback: try matching without trailing slash
    const clean = pathname.replace(/\/$/, "");
    return pages.findIndex((p) => p.href === clean);
  }, [pages, pathname]);

  const contextValue = useMemo(
    () => ({ data, loading, error, pages, currentIndex }),
    [data, loading, error, pages, currentIndex],
  );

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface-base">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-accent" />
          <span className="font-mono text-sm text-muted">
            Carregando dossie...
          </span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface-base">
        <div className="flex flex-col items-center gap-4 text-center">
          <AlertTriangle className="h-10 w-10 text-severity-high" />
          <p className="text-sm text-secondary">{error}</p>
          <Link
            href="/radar"
            className="rounded-lg border border-border bg-surface-card px-4 py-2 text-sm font-medium text-primary hover:bg-surface-subtle"
          >
            Voltar ao Radar
          </Link>
        </div>
      </div>
    );
  }

  return (
    <DossieBookContext.Provider value={contextValue}>
      <div className="pb-14">{children}</div>
      <DossieBookNav />
    </DossieBookContext.Provider>
  );
}
