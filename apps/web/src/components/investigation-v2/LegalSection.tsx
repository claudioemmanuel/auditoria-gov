"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Scale, BookOpen } from "lucide-react";
import { fetchTypologyLegalBasis, fetchCaseLegalHypotheses, getRadarV2Cases } from "@/lib/api";
import type { TypologyLegalBasis, LegalHypothesis, RadarV2TypologyCount } from "@/lib/types";
import { TableSkeleton } from "@/components/Skeleton";

interface TypologyLegalCardProps {
  code: string;
  name: string;
}

function TypologyLegalCard({ code, name }: TypologyLegalCardProps) {
  const [data, setData] = useState<TypologyLegalBasis | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchTypologyLegalBasis(code)
      .then(setData)
      .catch(() => setError(true));
  }, [code]);

  if (error) {
    return (
      <div className="rounded-xl border border-border bg-surface-card p-4 space-y-2">
        <div className="flex items-start gap-2">
          <Scale className="h-4 w-4 shrink-0 text-muted mt-0.5" />
          <div>
            <p className="font-mono text-[10px] uppercase tracking-widest text-muted">{code}</p>
            <p className="text-sm font-medium text-primary">{name}</p>
          </div>
        </div>
        <p className="text-xs text-muted">Base legal indisponivel.</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-surface-card p-4 space-y-3">
      <div className="flex items-start gap-2">
        <Scale className="h-4 w-4 shrink-0 text-accent mt-0.5" />
        <div>
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted">{code}</p>
          <p className="text-sm font-medium text-primary">{name}</p>
        </div>
      </div>

      {!data && (
        <div className="h-12 animate-pulse rounded-lg bg-surface-subtle" />
      )}

      {data && (
        <>
          {data.corruption_types.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {data.corruption_types.map((ct) => (
                <span key={ct} className="rounded-md bg-error/10 px-1.5 py-0.5 text-[10px] font-medium text-error">
                  {ct}
                </span>
              ))}
            </div>
          )}

          <p className="text-xs text-muted">
            Nivel de evidencia: <span className="font-medium text-secondary">{data.evidence_level}</span>
          </p>

          {data.law_articles.length > 0 && (
            <div className="space-y-1.5 border-t border-border pt-2">
              {data.law_articles.slice(0, 5).map((art, i) => (
                <div key={i} className="flex items-start gap-2 text-xs">
                  <BookOpen className="h-3 w-3 shrink-0 text-muted mt-0.5" />
                  <div>
                    <span className="font-medium text-primary">{art.law_name}</span>
                    <span className="text-muted"> — {art.article}</span>
                    {art.violation_type && <span className="text-muted"> ({art.violation_type})</span>}
                  </div>
                </div>
              ))}
              {data.law_articles.length > 5 && (
                <p className="text-[10px] text-muted pl-5">
                  +{data.law_articles.length - 5} artigos adicionais
                </p>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

interface RecentHypothesis {
  caseId: string;
  caseTitle: string;
  hypothesis: LegalHypothesis;
}

export function LegalSection({ typologyCounts }: { typologyCounts: RadarV2TypologyCount[] }) {
  const [hypotheses, setHypotheses] = useState<RecentHypothesis[]>([]);
  const [hypoLoading, setHypoLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const casesData = await getRadarV2Cases({ limit: 5 });
        const allHypos: RecentHypothesis[] = [];
        for (const c of casesData.items) {
          const hypos = await fetchCaseLegalHypotheses(c.id);
          for (const h of hypos) {
            allHypos.push({ caseId: c.id, caseTitle: c.title, hypothesis: h });
          }
        }
        setHypotheses(allHypos);
      } catch {
        // silent
      } finally {
        setHypoLoading(false);
      }
    })();
  }, []);

  const grouped = hypotheses.reduce<Record<string, RecentHypothesis[]>>((acc, h) => {
    const key = h.hypothesis.law_name;
    if (!acc[key]) acc[key] = [];
    acc[key].push(h);
    return acc;
  }, {});

  return (
    <div className="flex flex-1 mx-auto w-full max-w-[1280px] relative">
      <div className="flex-1 min-w-0 px-4 py-6 sm:px-6 space-y-8">
      {/* Typology legal basis grid */}
      <div>
        <p className="font-mono text-[10px] uppercase tracking-widest text-muted">Base Legal por Tipologia</p>
        <p className="text-xs text-secondary mt-0.5 mb-4">
          Mapeamento entre tipologias de corrupcao e legislacao brasileira aplicavel
        </p>

        {typologyCounts.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border bg-surface-card p-12 text-center">
            <Scale className="h-8 w-8 text-muted mx-auto mb-3 opacity-40" />
            <p className="text-sm font-medium text-secondary">Nenhuma tipologia ativa</p>
            <p className="mt-1 text-xs text-muted">Execute o pipeline de sinais para ativar as tipologias.</p>
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {typologyCounts.map((t) => (
              <TypologyLegalCard key={t.code} code={t.code} name={t.name} />
            ))}
          </div>
        )}
      </div>

      {/* Recent legal hypotheses */}
      <div className="border-t border-border pt-6">
        <p className="font-mono text-[10px] uppercase tracking-widest text-muted">Hipoteses Juridicas Recentes</p>
        <p className="text-xs text-secondary mt-0.5 mb-4">
          Inferencias legais automaticas baseadas nos sinais detectados
        </p>

        {hypoLoading && <TableSkeleton rows={4} />}

        {!hypoLoading && hypotheses.length === 0 && (
          <div className="rounded-xl border border-dashed border-border bg-surface-card p-12 text-center">
            <BookOpen className="h-8 w-8 text-muted mx-auto mb-3 opacity-40" />
            <p className="text-sm font-medium text-secondary">Nenhuma hipotese juridica gerada</p>
            <p className="mt-1 text-xs text-muted">Hipoteses sao geradas automaticamente a partir dos casos detectados.</p>
          </div>
        )}

        {!hypoLoading && Object.keys(grouped).length > 0 && (
          <div className="space-y-4">
            {Object.entries(grouped).map(([lawName, hypos]) => (
              <div key={lawName} className="rounded-xl border border-border bg-surface-card p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Scale className="h-4 w-4 text-accent" />
                  <p className="text-sm font-medium text-primary">{lawName}</p>
                  <span className="rounded-md bg-surface-subtle px-1.5 py-0.5 text-[10px] font-medium text-muted">
                    {hypos.length} hipotese{hypos.length !== 1 ? "s" : ""}
                  </span>
                </div>
                <div className="space-y-2">
                  {hypos.map((h, i) => (
                    <div key={i} className="flex items-start justify-between gap-3 text-xs">
                      <div className="min-w-0 flex-1">
                        {h.hypothesis.article && (
                          <span className="font-medium text-secondary">{h.hypothesis.article}</span>
                        )}
                        {h.hypothesis.violation_type && (
                          <span className="text-muted"> — {h.hypothesis.violation_type}</span>
                        )}
                        <Link href={`/case/${h.caseId}`} className="ml-2 text-accent hover:underline">
                          {h.caseTitle}
                        </Link>
                      </div>
                      <div className="flex items-center gap-1.5 shrink-0 w-20">
                        <div className="h-1.5 flex-1 rounded-full bg-surface-subtle overflow-hidden">
                          <div
                            className="h-full rounded-full bg-accent"
                            style={{ width: `${Math.round(h.hypothesis.confidence * 100)}%` }}
                          />
                        </div>
                        <span className="font-mono text-[10px] text-muted">
                          {Math.round(h.hypothesis.confidence * 100)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      </div>
    </div>
  );
}
