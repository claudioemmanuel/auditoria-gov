import type {
  ApiHeartbeatResponse,
  CaseDetail,
  CaseGraphResponse,
  CaseProvenanceWeb,
  CoverageV2AnalyticsResponse,
  CoverageV2MapResponse,
  CoverageV2SourcePreviewResponse,
  CoverageV2SourcesResponse,
  CoverageV2SummaryResponse,
  DossierSummaryResponse,
  DossierTimelineResponse,
  EntityDetail,
  EventRawSourcesResponse,
  IngestRunDetailResponse,
  LegalHypothesis,
  NeighborhoodResponse,
  OrgSummary,
  PaginatedResponse,
  PriceComparisonResult,
  RadarV2CaseItem,
  RadarV2CaseBatchPreviewItem,
  RadarV2CasePreviewResponse,
  RadarV2CoverageResponse,
  RadarV2SignalItem,
  RadarV2SignalPreviewResponse,
  RadarV2SummaryResponse,
  RelatedCase,
  RelatedSignal,
  SignalEvidencePage,
  SignalDetail,
  SignalGraphResponse,
  SignalProvenanceResponse,
  TypologyLegalBasis,
  EntitySearchResponse,
  EntityPathResponse,
} from "./types";

// Client: relative URL goes through Next.js proxy rewrite (/api/* → backend)
// Server: must use absolute URL — Next.js 15 does not resolve relative URLs in server components
const API_BASE =
  typeof window === "undefined"
    ? `${process.env.NEXT_PUBLIC_API_URL ?? "http://api:8000"}`
    : "/api";

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

async function postJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { method: "POST" });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export function getApiHeartbeat(): Promise<ApiHeartbeatResponse> {
  return fetchJSON("/health");
}

export function getIngestRunDetail(runId: string): Promise<IngestRunDetailResponse> {
  return fetchJSON(`/public/coverage/v2/run/${runId}`);
}

export function getCoverageV2Summary(): Promise<CoverageV2SummaryResponse> {
  return fetchJSON("/public/coverage/v2/summary");
}

export function getCoverageV2Sources(params?: {
  offset?: number;
  limit?: number;
  status?: "ok" | "warning" | "stale" | "error" | "pending";
  domain?: string;
  enabled_only?: boolean;
  q?: string;
  sort?: "status_desc" | "name_asc" | "freshness_desc" | "jobs_desc";
}): Promise<CoverageV2SourcesResponse> {
  const search = new URLSearchParams();
  if (params?.offset != null) search.set("offset", String(params.offset));
  if (params?.limit != null) search.set("limit", String(params.limit));
  if (params?.status) search.set("status", params.status);
  if (params?.domain) search.set("domain", params.domain);
  if (params?.enabled_only != null) search.set("enabled_only", String(params.enabled_only));
  if (params?.q) search.set("q", params.q);
  if (params?.sort) search.set("sort", params.sort);
  const qs = search.toString();
  return fetchJSON(`/public/coverage/v2/sources${qs ? `?${qs}` : ""}`);
}

export function getCoverageV2SourcePreview(
  connector: string,
  params?: { runs_limit?: number },
): Promise<CoverageV2SourcePreviewResponse> {
  const search = new URLSearchParams();
  if (params?.runs_limit != null) search.set("runs_limit", String(params.runs_limit));
  const qs = search.toString();
  return fetchJSON(`/public/coverage/v2/source/${connector}/preview${qs ? `?${qs}` : ""}`);
}

export function getCoverageV2Map(params?: {
  layer?: "uf" | "municipio";
  metric?: "coverage" | "freshness" | "risk";
}): Promise<CoverageV2MapResponse> {
  const search = new URLSearchParams();
  if (params?.layer) search.set("layer", params.layer);
  if (params?.metric) search.set("metric", params.metric);
  const qs = search.toString();
  return fetchJSON(`/public/coverage/v2/map${qs ? `?${qs}` : ""}`);
}

export function getCoverageV2Analytics(): Promise<CoverageV2AnalyticsResponse> {
  return fetchJSON("/public/coverage/v2/analytics");
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

export async function getRadarV2CaseBatchPreview(
  caseIds: string[],
): Promise<Record<string, RadarV2CaseBatchPreviewItem>> {
  if (caseIds.length === 0) return {};
  const res = await fetch(`${API_BASE}/public/radar/v2/cases/batch-preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ case_ids: caseIds }),
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  const data = await res.json();
  return data.previews ?? {};
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

export function getSignalProvenance(signalId: string): Promise<SignalProvenanceResponse> {
  return fetchJSON(`/public/signal/${signalId}/provenance`);
}

export function getEventRawSources(eventId: string): Promise<EventRawSourcesResponse> {
  return fetchJSON(`/public/event/${eventId}/raw-sources`);
}

export function getCaseProvenance(caseId: string): Promise<CaseProvenanceWeb> {
  return fetchJSON(`/public/case/${caseId}/provenance`);
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

export interface PipelineDispatchResponse {
  status: "dispatched";
  stages: {
    ingest: { task_id: string };
    entity_resolution: { task_id: string };
    signals: { task_id: string };
  };
}

export interface PipelineStatusResponse {
  is_running: boolean;
  stages: {
    ingest: "running" | "idle";
    entity_resolution: "running" | "idle";
    signals: "running" | "idle";
  };
}

export function getPipelineStatus(): Promise<PipelineStatusResponse> {
  return fetchJSON("/internal/pipeline/status");
}

export function triggerFullPipeline(): Promise<PipelineDispatchResponse> {
  return postJSON("/internal/pipeline/full");
}

export function requestYieldConnector(connector: string): Promise<{ status: string; jobs_signaled: number }> {
  return postJSON(`/internal/ingest/${connector}/yield`);
}

export interface PipelineCapacity {
  running_ingest_jobs: number;
  max_concurrent_ingest: number;
  er_running: boolean;
  slots_available: number;
  can_dispatch: {
    ingest: boolean;
    entity_resolution: boolean;
    baselines: boolean;
    signals: boolean;
  };
  recommendation: "idle" | "ingest_active" | "er_active";
}

export interface DispatchNextResponse {
  status: "dispatched" | "blocked" | "nothing_pending";
  reason?: string;
  dispatched: { connector: string; job: string; task_id: string } | null;
  slots_remaining?: number;
}

export function getPipelineCapacity(): Promise<PipelineCapacity> {
  return fetchJSON("/internal/pipeline/capacity");
}

export function dispatchNextPending(): Promise<DispatchNextResponse> {
  return postJSON("/internal/pipeline/dispatch-next");
}

export function fetchTypologyLegalBasis(code: string): Promise<TypologyLegalBasis> {
  return fetchJSON(`/public/typology/${code}/legal-basis`);
}

export async function fetchCaseLegalHypotheses(caseId: string): Promise<LegalHypothesis[]> {
  const res = await fetch(`${API_BASE}/public/case/${caseId}/legal-hypothesis`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchRelatedSignals(signalId: string): Promise<RelatedSignal[]> {
  try {
    return await fetchJSON<RelatedSignal[]>(`/public/signal/${signalId}/related`);
  } catch {
    return [];
  }
}

export async function fetchRelatedCases(caseId: string): Promise<RelatedCase[]> {
  try {
    return await fetchJSON<RelatedCase[]>(`/public/case/${caseId}/related`);
  } catch {
    return [];
  }
}

export function searchEntities(q: string, type?: string, limit?: number): Promise<EntitySearchResponse> {
  const search = new URLSearchParams();
  search.set("q", q);
  if (type) search.set("type", type);
  if (limit != null) search.set("limit", String(limit));
  return fetchJSON(`/public/entity/search?${search.toString()}`);
}

export function getGraphPath(sourceId: string, targetId: string): Promise<EntityPathResponse> {
  return fetchJSON(`/public/graph/path?source=${sourceId}&target=${targetId}`);
}

export function getDossierSummary(caseId: string): Promise<DossierSummaryResponse> {
  return fetchJSON(`/public/case/${caseId}/dossier-summary`);
}

export function getDossierTimeline(caseId: string): Promise<DossierTimelineResponse> {
  return fetchJSON(`/public/case/${caseId}/dossier-timeline`);
}
