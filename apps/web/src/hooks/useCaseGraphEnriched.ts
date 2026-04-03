"use client";

import { useMemo } from "react";
import { useCaseGraph, type EdgeContext, type GLink } from "./useCaseGraph";
import { useDossieBook } from "@/components/dossie/DossieBookContext";

/**
 * Wraps `useCaseGraph` and enriches edges with investigative context
 * derived from the dossie timeline (shared events between connected entities).
 */
export function useCaseGraphEnriched(caseId: string, focusSignalId?: string, depth: number = 0) {
  const caseGraph = useCaseGraph(caseId, focusSignalId, depth);
  const { data: dossieData } = useDossieBook();

  // Map graph node id → entity_id
  const nodeIdToEntityId = useMemo(() => {
    const map = new Map<string, string>();
    for (const node of caseGraph.graphData.nodes) {
      map.set(node.id, node.entity_id);
    }
    return map;
  }, [caseGraph.graphData.nodes]);

  // Build nodeAttrsMap: graph node id → entity attrs from timeline
  const nodeAttrsMap = useMemo<Record<string, Record<string, unknown>>>(() => {
    if (!dossieData) return {};
    const entityMap = new Map(dossieData.entities.map((e) => [e.id, e]));
    const result: Record<string, Record<string, unknown>> = {};
    for (const node of caseGraph.graphData.nodes) {
      const entity = entityMap.get(node.entity_id);
      if (entity) {
        result[node.id] = { ...entity.attrs, ...entity.identifiers };
      }
    }
    return result;
  }, [caseGraph.graphData.nodes, dossieData]);

  // Index events by participant entity_id for fast lookup
  const eventsByEntityId = useMemo(() => {
    if (!dossieData) return new Map<string, number[]>();
    const map = new Map<string, number[]>();
    for (let i = 0; i < dossieData.events.length; i++) {
      const ev = dossieData.events[i]!;
      for (const p of ev.participants) {
        const list = map.get(p.entity_id);
        if (list) {
          list.push(i);
        } else {
          map.set(p.entity_id, [i]);
        }
      }
    }
    return map;
  }, [dossieData]);

  // Enrich edges with shared-event context
  const enrichedLinks = useMemo<GLink[]>(() => {
    if (!dossieData) return caseGraph.graphData.links;

    const events = dossieData.events;

    return caseGraph.graphData.links.map((link) => {
      const srcEntityId = nodeIdToEntityId.get(
        typeof link.source === "string" ? link.source : (link.source as unknown as { id: string }).id,
      );
      const tgtEntityId = nodeIdToEntityId.get(
        typeof link.target === "string" ? link.target : (link.target as unknown as { id: string }).id,
      );

      if (!srcEntityId || !tgtEntityId) return link;

      const srcIndices = eventsByEntityId.get(srcEntityId);
      const tgtIndices = eventsByEntityId.get(tgtEntityId);
      if (!srcIndices || !tgtIndices) return link;

      const tgtSet = new Set(tgtIndices);
      const sharedIndices = srcIndices.filter((i) => tgtSet.has(i));

      if (sharedIndices.length === 0) return link;

      let totalValueBrl = 0;
      let earliest: string | null = null;
      let latest: string | null = null;

      const sharedEvents = sharedIndices.map((i) => {
        const ev = events[i]!;
        if (ev.value_brl) totalValueBrl += ev.value_brl;
        if (!earliest || ev.occurred_at < earliest) earliest = ev.occurred_at;
        if (!latest || ev.occurred_at > latest) latest = ev.occurred_at;
        return ev;
      });

      // Top 3 events by value (desc), then by date (desc)
      const topEvents = [...sharedEvents]
        .sort((a, b) => (b.value_brl ?? 0) - (a.value_brl ?? 0) || b.occurred_at.localeCompare(a.occurred_at))
        .slice(0, 3)
        .map((ev) => ({
          occurred_at: ev.occurred_at,
          description: ev.description,
          value_brl: ev.value_brl,
          source_connector: ev.source_connector,
        }));

      const context: EdgeContext = {
        sharedEventCount: sharedEvents.length,
        totalValueBrl,
        dateRange: earliest && latest ? { earliest, latest } : null,
        topEvents,
      };

      return { ...link, context };
    });
  }, [caseGraph.graphData.links, dossieData, nodeIdToEntityId, eventsByEntityId]);

  const enrichedGraphData = useMemo(
    () => ({ nodes: caseGraph.graphData.nodes, links: enrichedLinks }),
    [caseGraph.graphData.nodes, enrichedLinks],
  );

  return {
    ...caseGraph,
    graphData: enrichedGraphData,
    nodeAttrsMap,
  };
}
