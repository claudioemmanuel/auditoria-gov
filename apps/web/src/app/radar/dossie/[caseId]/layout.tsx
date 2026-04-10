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
      <div
        className="flex min-h-screen items-center justify-center"
        style={{ background: "var(--color-bg)" }}
      >
        <div className="flex flex-col items-center gap-3">
          <Loader2
            className="h-8 w-8 animate-spin"
            style={{ color: "var(--color-brand)" }}
          />
          <span
            className="font-mono text-sm"
            style={{ color: "var(--color-text-3)" }}
          >
            Carregando dossiê...
          </span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="flex min-h-screen items-center justify-center"
        style={{ background: "var(--color-bg)" }}
      >
        <div className="flex flex-col items-center gap-4 text-center">
          <AlertTriangle
            className="h-10 w-10"
            style={{ color: "var(--color-high)" }}
          />
          <p className="text-sm" style={{ color: "var(--color-text-2)" }}>
            {error}
          </p>
          <Link href="/radar" className="ow-btn ow-btn-outline ow-btn-sm">
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
