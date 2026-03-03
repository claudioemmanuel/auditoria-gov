export type SignalSeverity = "low" | "medium" | "high" | "critical";
export type CoverageStatus = "ok" | "warning" | "stale" | "error" | "pending";

export interface EvidenceRef {
  ref_type: "raw_source" | "event" | "entity" | "baseline" | "external_url";
  ref_id?: string;
  url?: string;
  source_hash?: string;
  captured_at?: string;
  snapshot_uri?: string;
  description: string;
}

export interface RiskSignal {
  id: string;
  typology_code: string;
  typology_name: string;
  severity: SignalSeverity;
  confidence: number;
  title: string;
  summary?: string;
  explanation_md?: string;
  completeness_score: number;
  completeness_status: "sufficient" | "insufficient";
  evidence_package_id?: string;
  factors: Record<string, unknown>;
  evidence_refs: EvidenceRef[];
  entity_ids: string[];
  event_ids: string[];
  period_start?: string;
  period_end?: string;
  created_at: string;
}

export interface FactorMeta {
  label: string;
  description: string;
  unit: string;
}

export interface SignalRoleDetail {
  code: string;
  label: string;
  count_in_signal: number;
}

export interface SignalEntity {
  id: string;
  type: string;
  name: string;
  identifiers: Record<string, string>;
  roles: string[];
  roles_detailed?: SignalRoleDetail[];
  role_explanation?: string | null;
}

export interface InvestigationSummary {
  what_crossed: string[];
  period_start?: string | null;
  period_end?: string | null;
  observed_total_brl?: number | null;
  legal_threshold_brl?: number | null;
  ratio_over_threshold?: number | null;
  legal_reference?: string | null;
}

export interface EvidenceStats {
  total_events: number;
  listed_refs: number;
  omitted_refs: number;
}

export interface SignalDetail extends RiskSignal {
  case_id?: string | null;
  case_title?: string | null;
  factor_descriptions?: Record<string, FactorMeta>;
  entities?: SignalEntity[];
  investigation_summary?: InvestigationSummary;
  evidence_stats?: EvidenceStats;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
}

export interface RadarV2Totals {
  signals: number;
  cases: number;
}

export interface RadarV2SeverityCounts {
  low: number;
  medium: number;
  high: number;
  critical: number;
}

export interface RadarV2TypologyCount {
  code: string;
  name: string;
  count: number;
}

export interface RadarV2SummaryResponse {
  snapshot_at: string;
  totals: RadarV2Totals;
  severity_counts: RadarV2SeverityCounts;
  typology_counts: RadarV2TypologyCount[];
  active_filters_count: number;
}

export interface RadarV2SignalItem {
  id: string;
  typology_code: string;
  typology_name: string;
  severity: SignalSeverity;
  confidence: number;
  title: string;
  summary?: string;
  period_start?: string | null;
  period_end?: string | null;
  created_at: string;
  event_count: number;
  entity_count: number;
  has_graph: boolean;
}

export interface RadarV2CaseItem {
  id: string;
  title: string;
  status: string;
  severity: SignalSeverity;
  summary?: string;
  signal_count: number;
  entity_count: number;
  typology_codes: string[];
  period_start?: string | null;
  period_end?: string | null;
  created_at: string;
}

export interface RadarV2SignalPreviewResponse {
  signal: SignalDetail;
  graph: SignalGraphResponse;
  evidence: SignalEvidencePage;
}

export interface RadarV2CasePreviewResponse {
  case: {
    id: string;
    title: string;
    status: string;
    severity: SignalSeverity;
    summary?: string | null;
    entity_names: string[];
    signal_count: number;
    period_start?: string | null;
    period_end?: string | null;
    total_value_brl?: number | null;
    created_at: string;
  };
  graph: CaseGraphResponse;
  top_signals: {
    id: string;
    typology_code: string;
    typology_name: string;
    severity: SignalSeverity;
    confidence: number;
    title: string;
    summary?: string | null;
    period_start?: string | null;
    period_end?: string | null;
    entity_count: number;
    event_count: number;
  }[];
}

export interface RadarV2CoverageSummary {
  apt_count: number;
  with_signals_30d: number;
  blocked_count: number;
  total_typologies: number;
}

export interface RadarV2CoverageResponse {
  summary: RadarV2CoverageSummary;
  items: AnalyticalCoverageItem[];
}

export interface CoverageV2StatusCounts {
  ok: number;
  warning: number;
  stale: number;
  error: number;
  pending: number;
}

export interface CoverageV2RuntimeTotals {
  running: number;
  stuck: number;
  failed_or_stuck: number;
}

export interface CoverageV2SummaryResponse {
  snapshot_at: string;
  totals: {
    connectors: number;
    jobs: number;
    jobs_enabled: number;
    signals_total: number;
    status_counts: CoverageV2StatusCounts;
    runtime: CoverageV2RuntimeTotals;
  };
  pipeline: {
    overall_status: "healthy" | "attention" | "blocked";
    stages: {
      code: "ingest" | "entity_resolution" | "baselines" | "signals" | string;
      label: string;
      status: "done" | "processing" | "warning" | "error" | "pending";
      reason: string;
    }[];
  };
  schedule_windows_brt: {
    job_code: string;
    window: string;
  }[];
}

export interface CoverageV2SourceRuntime {
  running_jobs: number;
  stuck_jobs: number;
  error_jobs: number;
}

export interface CoverageV2SourceItem {
  connector: string;
  connector_label: string;
  job_count: number;
  enabled_job_count: number;
  worst_status: CoverageStatus;
  status_counts: CoverageV2StatusCounts;
  runtime: CoverageV2SourceRuntime;
  last_success_at?: string | null;
  max_freshness_lag_hours?: number | null;
}

export interface CoverageV2SourcesResponse {
  items: CoverageV2SourceItem[];
  total: number;
  offset: number;
  limit: number;
}

export interface CoverageV2LatestRun {
  id: string;
  status: string;
  is_stuck: boolean;
  started_at?: string | null;
  finished_at?: string | null;
  items_fetched: number;
  items_normalized: number;
  error_message?: string | null;
}

export interface CoverageV2SourcePreviewResponse {
  connector: {
    connector: string;
    connector_label: string;
    worst_status: CoverageStatus;
    job_count: number;
    enabled_job_count: number;
    status_counts: CoverageV2StatusCounts;
  };
  jobs: {
    job: string;
    domain: string;
    description?: string | null;
    enabled_in_mvp: boolean;
    status: CoverageStatus;
    total_items: number;
    last_success_at?: string | null;
    freshness_lag_hours?: number | null;
    latest_run?: CoverageV2LatestRun | null;
  }[];
  recent_runs: CoverageV2LatestRun[];
  insights: string[];
}

export interface CoverageV2MapResponse {
  layer: "uf" | "municipio";
  metric: "coverage" | "freshness" | "risk";
  generated_at: string;
  date_ref: string;
  national: {
    regions_with_data: number;
    regions_without_data: number;
    total_events: number;
    total_signals: number;
  };
  items: CoverageMapItem[];
}

export interface CoverageV2AnalyticsResponse {
  summary: {
    total_typologies: number;
    apt_count: number;
    blocked_count: number;
    with_signals_30d: number;
  };
  items: AnalyticalCoverageItem[];
}

export interface CoverageMapItem {
  code: string;
  label: string;
  layer: "uf" | "municipio";
  event_count: number;
  signal_count: number;
  coverage_score: number;
  freshness_hours?: number;
  risk_score: number;
  status: CoverageStatus;
}

export interface IngestRunFieldProfile {
  key: string;
  present_count: number;
  coverage_pct: number;
  detected_types: string[];
  examples: unknown[];
}

export interface IngestRunSampleRecord {
  raw_id: string;
  created_at?: string | null;
  preview: Record<string, unknown>;
  raw_data: Record<string, unknown>;
}

export interface IngestRunDetailResponse {
  run: {
    id: string;
    connector: string;
    job: string;
    status: string;
    cursor_start?: string | null;
    cursor_end?: string | null;
    items_fetched: number;
    items_normalized: number;
    errors?: Record<string, unknown> | null;
    started_at?: string | null;
    finished_at?: string | null;
  };
  job: {
    connector: string;
    job: string;
    description?: string | null;
    domain?: string | null;
    supports_incremental?: boolean | null;
    enabled?: boolean | null;
    default_params?: Record<string, unknown>;
  };
  summary: {
    records_stored: number;
    distinct_raw_ids: number;
    duplicate_raw_ids: number;
    first_record_at?: string | null;
    last_record_at?: string | null;
    profile_sampled_records: number;
    profile_sample_limit: number;
  };
  field_profile: IngestRunFieldProfile[];
  samples: IngestRunSampleRecord[];
}

export interface EntityDetail {
  id: string;
  type: string;
  name: string;
  identifiers: Record<string, string>;
  attrs: Record<string, unknown>;
  cluster_id?: string;
  aliases: { type: string; value: string; source: string }[];
}

export interface GraphNode {
  id: string;
  entity_id: string;
  label: string;
  node_type: string;
  attrs: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  from_node_id: string;
  to_node_id: string;
  type: string;
  weight: number;
  edge_strength: "strong" | "weak" | string;
  verification_method?: string;
  verification_confidence?: number;
  attrs: Record<string, unknown>;
}

export interface NeighborhoodResponse {
  center_node_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  depth: number;
  truncated: boolean;
  diagnostics?: {
    graph_materialized: boolean;
    entity_event_count: number;
    co_participant_count: number;
    reason: string;
  };
  virtual_center_node?: {
    entity_id: string;
    label: string;
    node_type: string;
  };
  co_participants?: {
    entity_id: string;
    label: string;
    node_type: string;
    shared_events: number;
  }[];
}

export interface SignalEvidenceItem {
  event_id: string;
  occurred_at?: string | null;
  value_brl?: number | null;
  description: string;
  source_connector: string;
  source_id: string;
  modality: string;
  catmat_group: string;
  evidence_reason: string;
}

export interface SignalEvidencePage {
  signal_id: string;
  total: number;
  offset: number;
  limit: number;
  items: SignalEvidenceItem[];
}

export interface CaseSignalBrief {
  id: string;
  typology_code: string;
  typology_name: string;
  severity: SignalSeverity;
  confidence: number;
  title: string;
  summary?: string;
  entity_ids: string[];
}

export interface CaseGraphResponse {
  case_id: string;
  case_title: string;
  case_severity: SignalSeverity;
  case_status: string;
  seed_entity_ids: string[];
  nodes: GraphNode[];
  edges: GraphEdge[];
  signals: CaseSignalBrief[];
  truncated: boolean;
  er_pending?: boolean;
  focus_signal_summary?: {
    id: string;
    typology_code: string;
    typology_name: string;
    severity: SignalSeverity;
    confidence: number;
    title: string;
    summary?: string | null;
    period_start?: string | null;
    period_end?: string | null;
    pattern_label?: string | null;
  } | null;
  focus_entity_ids?: string[];
  focus_edge_ids?: string[];
}

export interface SignalGraphNode {
  id: string;
  entity_id: string;
  label: string;
  node_type: string;
  attrs: Record<string, unknown>;
}

export interface SignalGraphEdge {
  id: string;
  from_node_id: string;
  to_node_id: string;
  type: string;
  label: string;
  weight: number;
  evidence_event_ids: string[];
  first_seen_at?: string | null;
  last_seen_at?: string | null;
  attrs: Record<string, unknown>;
}

export interface SignalTimelineParticipant {
  entity_id: string;
  name: string;
  node_type: string;
  role: string;
  role_label: string;
}

export interface SignalTimelineEvent {
  event_id: string;
  occurred_at?: string | null;
  value_brl?: number | null;
  description: string;
  source_connector: string;
  source_id: string;
  participants: SignalTimelineParticipant[];
  evidence_reason: string;
}

export interface SignalInvolvedEntityRole {
  code: string;
  label: string;
  count_in_signal: number;
}

export interface SignalInvolvedEntityProfile {
  entity_id: string;
  name: string;
  node_type: string;
  identifiers: Record<string, string>;
  attrs: Record<string, unknown>;
  photo_url?: string | null;
  roles_in_signal: SignalInvolvedEntityRole[];
  event_count: number;
}

export interface SignalGraphResponse {
  signal: {
    id: string;
    typology_code: string;
    typology_name: string;
    severity: SignalSeverity;
    confidence: number;
    title: string;
    period_start?: string | null;
    period_end?: string | null;
  };
  pattern_story: {
    pattern_label: string;
    started_at?: string | null;
    ended_at?: string | null;
    started_from_entities: {
      entity_id: string;
      name: string;
      node_type: string;
      roles: string[];
      event_count: number;
    }[];
    flow_targets: {
      entity_id: string;
      name: string;
      node_type: string;
      roles: string[];
      event_count: number;
    }[];
    why_flagged: string;
  };
  overview: {
    nodes: SignalGraphNode[];
    edges: SignalGraphEdge[];
  };
  timeline: SignalTimelineEvent[];
  involved_entities: SignalInvolvedEntityProfile[];
  diagnostics: {
    events_total: number;
    events_loaded: number;
    events_missing: number;
    participants_total: number;
    unique_entities: number;
    has_minimum_network: boolean;
    fallback_reason?: string | null;
  };
}

export interface CaseListItem {
  id: string;
  title: string;
  status: string;
  severity: SignalSeverity;
  summary?: string;
  signal_count: number;
  created_at: string;
}

export interface CaseSignal {
  id: string;
  typology_code: string;
  typology_name: string;
  severity: SignalSeverity;
  confidence: number;
  title: string;
  summary?: string;
  explanation_md?: string;
  factors: Record<string, unknown>;
  factor_descriptions?: Record<string, FactorMeta>;
  entity_count?: number;
  evidence_count?: number;
  period_start?: string | null;
  period_end?: string | null;
  created_at: string;
}

export interface CaseDetail {
  id: string;
  title: string;
  status: string;
  severity: SignalSeverity;
  summary?: string;
  explanation?: string;
  entity_names?: string[];
  typology_names?: string[];
  total_value_brl?: number | null;
  period_start?: string | null;
  period_end?: string | null;
  attrs?: Record<string, unknown>;
  created_at: string;
  signals: CaseSignal[];
}

export interface AnalyticalCoverageItem {
  typology_code: string;
  typology_name: string;
  required_domains: string[];
  domains_available: string[];
  domains_missing: string[];
  apt: boolean;
  signals_30d: number;
  last_signal_at?: string | null;
  last_run_at?: string | null;
  last_run_status?: string | null;
  last_run_candidates?: number | null;
  last_run_signals_created?: number | null;
  last_run_signals_deduped?: number | null;
  last_run_signals_blocked?: number | null;
  last_success_at?: string | null;
  corruption_types?: string[];
  spheres?: string[];
  evidence_level?: string;
  description_legal?: string;
}

export interface BaselineMetrics {
  n: number;
  mean: number;
  std: number;
  median: number;
  p10: number;
  p25: number;
  p75: number;
  p90: number;
  p95: number;
  p99: number;
  min: number;
  max: number;
}

export interface PriceComparisonResult {
  catmat_code?: string;
  description?: string;
  baseline: BaselineMetrics | null;
  items: unknown[];
}

export interface OrgSummary {
  id: string;
  name: string;
  type: string;
  identifiers: Record<string, string>;
  attrs: Record<string, unknown>;
  total_events: number;
  total_signals: number;
  severity_distribution: Record<string, number>;
  total_contracts_value: number;
  risk_score?: number;
}
