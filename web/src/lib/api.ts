import type {
  AnalyticalCoverageItem,
  CaseDetail,
  CaseGraphResponse,
  CoverageItem,
  CoverageMapResponse,
  EntityDetail,
  IngestRunDetailResponse,
  IngestStatusResponse,
  NeighborhoodResponse,
  OrgSummary,
  PaginatedResponse,
  PriceComparisonResult,
  RadarV2CaseItem,
  RadarV2CasePreviewResponse,
  RadarV2CoverageResponse,
  RadarV2SignalItem,
  RadarV2SignalPreviewResponse,
  RadarV2SummaryResponse,
  RiskSignal,
  SignalEvidencePage,
  SignalDetail,
  SignalGraphResponse,
} from "./types";

const API_BASE = "/api";

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export function getCoverage(): Promise<CoverageItem[]> {
  return fetchJSON("/public/coverage");
}

export function getCoverageMap(params?: {
  layer?: "uf" | "municipio";
  metric?: "coverage" | "freshness" | "risk";
}): Promise<CoverageMapResponse> {
  const search = new URLSearchParams();
  if (params?.layer) search.set("layer", params.layer);
  if (params?.metric) search.set("metric", params.metric);
  const qs = search.toString();
  return fetchJSON(`/public/coverage/map${qs ? `?${qs}` : ""}`);
}

export function getAnalyticalCoverage(): Promise<AnalyticalCoverageItem[]> {
  return fetchJSON("/public/coverage/analytics");
}

export function getIngestStatus(): Promise<IngestStatusResponse> {
  return fetchJSON("/internal/ingest/status");
}

export function getIngestRunDetail(runId: string): Promise<IngestRunDetailResponse> {
  return fetchJSON(`/internal/ingest/run/${runId}`);
}

export function getRadar(params?: {
  offset?: number;
  limit?: number;
  typology?: string;
  severity?: string;
  sort?: "analysis_date" | "ingestion_date";
  period_from?: string;
  period_to?: string;
  corruption_type?: string;
  sphere?: string;
}): Promise<PaginatedResponse<RiskSignal>> {
  const search = new URLSearchParams();
  if (params?.offset != null) search.set("offset", String(params.offset));
  if (params?.limit != null) search.set("limit", String(params.limit));
  if (params?.typology) search.set("typology", params.typology);
  if (params?.severity) search.set("severity", params.severity);
  if (params?.sort) search.set("sort", params.sort);
  if (params?.period_from) search.set("period_from", params.period_from);
  if (params?.period_to) search.set("period_to", params.period_to);
  if (params?.corruption_type) search.set("corruption_type", params.corruption_type);
  if (params?.sphere) search.set("sphere", params.sphere);
  const qs = search.toString();
  return fetchJSON(`/public/radar${qs ? `?${qs}` : ""}`);
}

export function getRadarV2Summary(params?: {
  typology?: string;
  severity?: string;
  period_from?: string;
  period_to?: string;
  corruption_type?: string;
  sphere?: string;
}): Promise<RadarV2SummaryResponse> {
  const search = new URLSearchParams();
  if (params?.typology) search.set("typology", params.typology);
  if (params?.severity) search.set("severity", params.severity);
  if (params?.period_from) search.set("period_from", params.period_from);
  if (params?.period_to) search.set("period_to", params.period_to);
  if (params?.corruption_type) search.set("corruption_type", params.corruption_type);
  if (params?.sphere) search.set("sphere", params.sphere);
  const qs = search.toString();
  return fetchJSON(`/public/radar/v2/summary${qs ? `?${qs}` : ""}`);
}

export function getRadarV2Signals(params?: {
  offset?: number;
  limit?: number;
  typology?: string;
  severity?: string;
  sort?: "analysis_date" | "ingestion_date";
  period_from?: string;
  period_to?: string;
  corruption_type?: string;
  sphere?: string;
}): Promise<PaginatedResponse<RadarV2SignalItem>> {
  const search = new URLSearchParams();
  if (params?.offset != null) search.set("offset", String(params.offset));
  if (params?.limit != null) search.set("limit", String(params.limit));
  if (params?.typology) search.set("typology", params.typology);
  if (params?.severity) search.set("severity", params.severity);
  if (params?.sort) search.set("sort", params.sort);
  if (params?.period_from) search.set("period_from", params.period_from);
  if (params?.period_to) search.set("period_to", params.period_to);
  if (params?.corruption_type) search.set("corruption_type", params.corruption_type);
  if (params?.sphere) search.set("sphere", params.sphere);
  const qs = search.toString();
  return fetchJSON(`/public/radar/v2/signals${qs ? `?${qs}` : ""}`);
}

export function getRadarV2Cases(params?: {
  offset?: number;
  limit?: number;
  typology?: string;
  severity?: string;
  period_from?: string;
  period_to?: string;
  corruption_type?: string;
  sphere?: string;
}): Promise<PaginatedResponse<RadarV2CaseItem>> {
  const search = new URLSearchParams();
  if (params?.offset != null) search.set("offset", String(params.offset));
  if (params?.limit != null) search.set("limit", String(params.limit));
  if (params?.typology) search.set("typology", params.typology);
  if (params?.severity) search.set("severity", params.severity);
  if (params?.period_from) search.set("period_from", params.period_from);
  if (params?.period_to) search.set("period_to", params.period_to);
  if (params?.corruption_type) search.set("corruption_type", params.corruption_type);
  if (params?.sphere) search.set("sphere", params.sphere);
  const qs = search.toString();
  return fetchJSON(`/public/radar/v2/cases${qs ? `?${qs}` : ""}`);
}

export function getRadarV2SignalPreview(
  signalId: string,
  params?: { limit?: number },
): Promise<RadarV2SignalPreviewResponse> {
  const search = new URLSearchParams();
  if (params?.limit != null) search.set("limit", String(params.limit));
  const qs = search.toString();
  return fetchJSON(`/public/radar/v2/signal/${signalId}/preview${qs ? `?${qs}` : ""}`);
}

export function getRadarV2CasePreview(caseId: string): Promise<RadarV2CasePreviewResponse> {
  return fetchJSON(`/public/radar/v2/case/${caseId}/preview`);
}

export function getRadarV2Coverage(): Promise<RadarV2CoverageResponse> {
  return fetchJSON("/public/radar/v2/coverage");
}

export function getSignal(id: string): Promise<SignalDetail> {
  return fetchJSON(`/public/signal/${id}`);
}

export function getSignalEvidence(
  id: string,
  params?: {
    offset?: number;
    limit?: number;
    sort?: "occurred_at_desc" | "occurred_at_asc" | "value_desc" | "value_asc";
  },
): Promise<SignalEvidencePage> {
  const search = new URLSearchParams();
  if (params?.offset != null) search.set("offset", String(params.offset));
  if (params?.limit != null) search.set("limit", String(params.limit));
  if (params?.sort) search.set("sort", params.sort);
  const qs = search.toString();
  return fetchJSON(`/public/signal/${id}/evidence${qs ? `?${qs}` : ""}`);
}

export function getCase(id: string): Promise<CaseDetail> {
  return fetchJSON(`/public/case/${id}`);
}

export function getEntity(id: string): Promise<EntityDetail> {
  return fetchJSON(`/public/entity/${id}`);
}

export function getOrg(id: string): Promise<OrgSummary> {
  return fetchJSON(`/public/org/${id}`);
}

export function getGraphNeighborhood(
  entityId: string,
  depth: number = 1,
): Promise<NeighborhoodResponse> {
  return fetchJSON(`/public/graph/neighborhood?entity_id=${entityId}&depth=${depth}`);
}

export function getCaseGraph(
  caseId: string,
  depth: number = 1,
  params?: {
    focus_signal_id?: string;
  },
): Promise<CaseGraphResponse> {
  const search = new URLSearchParams();
  search.set("depth", String(depth));
  if (params?.focus_signal_id) {
    search.set("focus_signal_id", params.focus_signal_id);
  }
  return fetchJSON(`/public/case/${caseId}/graph?${search.toString()}`);
}

export function getSignalGraph(signalId: string): Promise<SignalGraphResponse> {
  return fetchJSON(`/public/signal/${signalId}/graph`);
}

export function comparePrices(params?: {
  catmat_code?: string;
  description?: string;
}): Promise<PriceComparisonResult> {
  const search = new URLSearchParams();
  if (params?.catmat_code) search.set("catmat_code", params.catmat_code);
  if (params?.description) search.set("description", params.description);
  const qs = search.toString();
  return fetchJSON(`/public/compare/prices${qs ? `?${qs}` : ""}`);
}
