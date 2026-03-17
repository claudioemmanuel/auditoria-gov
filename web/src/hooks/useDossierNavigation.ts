"use client";

import { useCallback, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export interface DossierNavState {
  expandedCases: Set<string>;
  selectedCaseId: string | null;
  selectedSignalId: string | null;
  selectedEntityId: string | null;
  panelMode: "signal" | "entity" | "network" | null;
}

export function useDossierNavigation() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const state = useMemo<DossierNavState>(() => {
    const caseParam = searchParams.get("case") || null;
    const signalParam = searchParams.get("signal") || null;
    const entityParam = searchParams.get("entity") || null;

    const expanded = new Set<string>();
    if (caseParam) expanded.add(caseParam);

    let panelMode: DossierNavState["panelMode"] = null;
    if (entityParam) panelMode = "entity";
    else if (signalParam) panelMode = "signal";

    return {
      expandedCases: expanded,
      selectedCaseId: caseParam,
      selectedSignalId: signalParam,
      selectedEntityId: entityParam,
      panelMode,
    };
  }, [searchParams]);

  const updateParams = useCallback(
    (updates: Record<string, string>) => {
      const params = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(updates)) {
        if (value) params.set(key, value);
        else params.delete(key);
      }
      router.replace(`?${params.toString()}`, { scroll: false });
    },
    [router, searchParams],
  );

  const expandCase = useCallback(
    (caseId: string) => {
      const isExpanded = state.expandedCases.has(caseId);
      if (isExpanded) {
        // Collapse: clear case + signal + entity
        updateParams({ case: "", signal: "", entity: "" });
      } else {
        // Expand: set case, clear signal + entity
        updateParams({ case: caseId, signal: "", entity: "" });
      }
    },
    [state.expandedCases, updateParams],
  );

  const selectSignal = useCallback(
    (caseId: string, signalId: string) => {
      updateParams({ case: caseId, signal: signalId, entity: "" });
    },
    [updateParams],
  );

  const selectEntity = useCallback(
    (entityId: string) => {
      updateParams({ entity: entityId });
    },
    [updateParams],
  );

  const goBack = useCallback(() => {
    if (state.selectedEntityId) {
      // entity → signal
      updateParams({ entity: "" });
    } else if (state.selectedSignalId) {
      // signal → case (panel closes)
      updateParams({ signal: "" });
    } else if (state.selectedCaseId) {
      // case → closed
      updateParams({ case: "" });
    }
  }, [state, updateParams]);

  const closePanel = useCallback(() => {
    updateParams({ signal: "", entity: "" });
  }, [updateParams]);

  const navigateToNetwork = useCallback(
    (entityId: string) => {
      updateParams({ tab: "rede", entity: entityId, case: "", signal: "" });
    },
    [updateParams],
  );

  return {
    state,
    expandCase,
    selectSignal,
    selectEntity,
    goBack,
    closePanel,
    navigateToNetwork,
  };
}
