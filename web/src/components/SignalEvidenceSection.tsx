"use client";

import { useState, useEffect } from "react";
import { getSignalEvidence } from "@/lib/api";
import { EvidenceList } from "@/components/EvidenceList";
import type { EvidenceRef, EvidenceStats, SignalEvidencePage } from "@/lib/types";

const EVIDENCE_PAGE_SIZE = 20;

interface SignalEvidenceSectionProps {
  signalId: string;
  evidenceRefs: EvidenceRef[];
  evidenceStats?: EvidenceStats;
}

export function SignalEvidenceSection({
  signalId,
  evidenceRefs,
  evidenceStats,
}: SignalEvidenceSectionProps) {
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<SignalEvidencePage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getSignalEvidence(signalId, {
      offset,
      limit: EVIDENCE_PAGE_SIZE,
      sort: "occurred_at_desc",
    })
      .then(setPage)
      .catch(() => setError("Erro ao carregar evidências"))
      .finally(() => setLoading(false));
  }, [signalId, offset]);

  const total =
    page?.total ??
    evidenceStats?.total_events ??
    evidenceRefs.length;

  const items = page?.items ?? [];

  if (error) {
    return (
      <p className="mt-6 text-sm text-error">{error}</p>
    );
  }

  return (
    <EvidenceList
      signalId={signalId}
      items={items}
      total={total}
      offset={offset}
      limit={EVIDENCE_PAGE_SIZE}
      onPageChange={setOffset}
      loading={loading}
      refs={evidenceRefs}
    />
  );
}
