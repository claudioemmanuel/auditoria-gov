"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  getRadarV2CasePreview,
  getRadarV2Cases,
} from "@/lib/api";
import type {
  RadarV2CaseItem,
  RadarV2CasePreviewResponse,
} from "@/lib/types";
import { DossierTree } from "./DossierTree";
import { DossierDetailPanel } from "./DossierDetailPanel";
import type { DossierNavState } from "@/hooks/useDossierNavigation";

const PAGE_SIZE = 20;

interface DossierSectionProps {
  // Navigation state from hook
  navState: DossierNavState;
  onExpandCase: (caseId: string) => void;
  onSelectSignal: (caseId: string, signalId: string) => void;
  onSelectEntity: (entityId: string) => void;
  onGoBack: () => void;
  onClosePanel: () => void;
  onNavigateToNetwork: (entityId: string) => void;
  // Filter state from page
  typology: string;
  periodFrom: string;
  periodTo: string;
  corruptionType: string;
  sphere: string;
  offset: number;
  onTypologyChange: (v: string) => void;
  onPeriodFromChange: (v: string) => void;
  onPeriodToChange: (v: string) => void;
  onCorruptionTypeChange: (v: string) => void;
  onSphereChange: (v: string) => void;
  onOffsetChange: (v: number) => void;
  onClearAll: () => void;
  onCoverageClick: () => void;
}

export function DossierSection({
  navState,
  onExpandCase,
  onSelectSignal,
  onSelectEntity,
  onGoBack,
  onClosePanel,
  onNavigateToNetwork,
  typology,
  periodFrom,
  periodTo,
  corruptionType,
  sphere,
  offset,
  onTypologyChange,
  onPeriodFromChange,
  onPeriodToChange,
  onCorruptionTypeChange,
  onSphereChange,
  onOffsetChange,
  onClearAll,
  onCoverageClick,
}: DossierSectionProps) {
  const [search, setSearch] = useState("");
  const [cases, setCases] = useState<RadarV2CaseItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Case preview cache
  const [casePreviewCache, setCasePreviewCache] = useState<Map<string, RadarV2CasePreviewResponse>>(new Map());
  const [casePreviewLoading, setCasePreviewLoading] = useState<Set<string>>(new Set());
  const fetchedCases = useRef<Set<string>>(new Set());

  // Load cases
  useEffect(() => {
    setLoading(true);
    setError(null);
    setCasePreviewCache(new Map());
    setCasePreviewLoading(new Set());
    fetchedCases.current = new Set();
    getRadarV2Cases({
      offset,
      limit: PAGE_SIZE,
      typology: typology || undefined,
      period_from: periodFrom || undefined,
      period_to: periodTo || undefined,
      corruption_type: corruptionType || undefined,
      sphere: sphere || undefined,
    })
      .then((data) => {
        setTotal(data.total);
        setCases(data.items as RadarV2CaseItem[]);
      })
      .catch(() => setError("Erro ao carregar dados do Radar. Verifique a API e tente novamente."))
      .finally(() => setLoading(false));
  }, [offset, typology, periodFrom, periodTo, corruptionType, sphere]);

  // Lazy-load case previews: first 5 immediately, rest after a short delay
  useEffect(() => {
    if (loading || cases.length === 0) return;

    const fetchPreview = (c: RadarV2CaseItem) => {
      fetchedCases.current.add(c.id);
      setCasePreviewLoading((prev) => new Set(prev).add(c.id));
      getRadarV2CasePreview(c.id)
        .then((preview) => setCasePreviewCache((prev) => new Map(prev).set(c.id, preview)))
        .catch(() => { /* silent */ })
        .finally(() => {
          setCasePreviewLoading((prev) => {
            const next = new Set(prev);
            next.delete(c.id);
            return next;
          });
        });
    };

    // Priority batch: first 5
    const priority = cases.slice(0, 5).filter((c) => !fetchedCases.current.has(c.id));
    for (const c of priority) fetchPreview(c);

    // Remaining batch: staggered with requestIdleCallback or setTimeout fallback
    const remaining = cases.slice(5).filter((c) => !fetchedCases.current.has(c.id));
    if (remaining.length === 0) return;

    const schedule = typeof requestIdleCallback === "function" ? requestIdleCallback : (cb: () => void) => setTimeout(cb, 200);
    const handle = schedule(() => {
      for (const c of remaining) fetchPreview(c);
    });

    return () => {
      if (typeof cancelIdleCallback === "function" && typeof handle === "number") {
        cancelIdleCallback(handle);
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cases, loading]);

  // Merge URL-expanded cases with user-expanded cases
  const expandedCases = navState.expandedCases;

  const handleToggleExpand = useCallback(
    (caseId: string) => {
      onExpandCase(caseId);
    },
    [onExpandCase],
  );

  return (
    <div className="flex flex-1 mx-auto w-full max-w-[1280px] relative">
      <DossierTree
        cases={cases}
        total={total}
        loading={loading}
        error={error}
        offset={offset}
        onOffsetChange={onOffsetChange}
        casePreviewCache={casePreviewCache}
        casePreviewLoading={casePreviewLoading}
        expandedCases={expandedCases}
        onToggleExpand={handleToggleExpand}
        onSignalClick={onSelectSignal}
        activeSignalId={navState.selectedSignalId}
        panelOpen={navState.panelMode !== null}
        search={search}
        onSearchChange={setSearch}
        typology={typology}
        periodFrom={periodFrom}
        periodTo={periodTo}
        corruptionType={corruptionType}
        sphere={sphere}
        onTypologyChange={onTypologyChange}
        onPeriodFromChange={onPeriodFromChange}
        onPeriodToChange={onPeriodToChange}
        onCorruptionTypeChange={onCorruptionTypeChange}
        onSphereChange={onSphereChange}
        onClearAll={onClearAll}
        onCoverageClick={onCoverageClick}
      />

      <DossierDetailPanel
        panelMode={navState.panelMode}
        selectedSignalId={navState.selectedSignalId}
        selectedEntityId={navState.selectedEntityId}
        selectedCaseId={navState.selectedCaseId}
        onClose={onClosePanel}
        onGoBack={onGoBack}
        onSelectEntity={onSelectEntity}
        onNavigateToNetwork={onNavigateToNetwork}
      />
    </div>
  );
}
