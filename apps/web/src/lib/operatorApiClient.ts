/**
 * operatorApiClient.ts
 *
 * HTTP client for /internal/* operator endpoints.
 * This file is intentionally separate from publicApiClient.ts to make
 * the security boundary explicit: internal endpoints require X-Internal-Api-Key
 * and must never be exposed to public users.
 *
 * IMPORTANT: Only import this file in operator/admin pages or components.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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

// ── Types ─────────────────────────────────────────────────────────────────────

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

// ── Operator functions ────────────────────────────────────────────────────────

export function getPipelineStatus(): Promise<PipelineStatusResponse> {
  return fetchJSON("/internal/pipeline/status");
}

export function triggerFullPipeline(): Promise<PipelineDispatchResponse> {
  return postJSON("/internal/pipeline/full");
}

export function requestYieldConnector(
  connector: string,
): Promise<{ status: string; jobs_signaled: number }> {
  return postJSON(`/internal/ingest/${connector}/yield`);
}

export function getPipelineCapacity(): Promise<PipelineCapacity> {
  return fetchJSON("/internal/pipeline/capacity");
}

export function dispatchNextPending(): Promise<DispatchNextResponse> {
  return postJSON("/internal/pipeline/dispatch-next");
}
