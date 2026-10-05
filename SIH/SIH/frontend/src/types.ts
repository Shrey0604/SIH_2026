export type ReplayStatus = 'ready' | 'running' | 'paused' | 'complete'
export type HazardState = 'CLEAR' | 'WATCH' | 'ELEVATED'

export type TelemetrySample = {
  seq: number
  timestamp_offset_s: number
  md_m: number
  tvd_m: number | null
  rop_mph: number
  wob_kn: number
  rpm: number
  torque_knm: number
  spp_bar: number
  flow_in_lpm: number
  flow_out_lpm: number
  pit_volume_m3: number
  mud_weight_sg: number
  gas_units: number
}

export type FormationInterval = {
  id: string
  well_id: string
  formation_id: string
  formation_name: string
  formation_code: string
  top_md_m: number
  base_md_m: number
  normalized_position?: number
}

export type HistoricalEvent = {
  id: string
  well_id: string
  formation_id: string
  formation_name: string
  hazard_type: 'MUD_LOSS' | 'STUCK_PIPE' | 'KICK'
  start_md_m: number
  end_md_m: number | null
  severity: 'LOW' | 'MEDIUM' | 'HIGH'
  description: string
  historical_response: string | null
  extraction_confidence: number
  has_exact_page_evidence: boolean
}

export type EventEvidence = {
  id: string
  event_id: string
  document_id: string
  document_title: string
  filename: string
  page_number: number
  evidence_text: string
  bbox_json: Record<string, number> | null
  source_kind: string
}

export type EventDetail = HistoricalEvent & {
  well_name: string
  source: 'AI_EXTRACTED' | 'CACHED_VERIFIED' | 'SEEDED' | 'REVIEWED'
  evidence: EventEvidence[]
}

export type DocumentRecord = {
  id: string
  well_id: string | null
  title: string
  document_type: string
  filename: string
  page_count: number
  sha256: string
  ingestion_status: string
  source_kind: string
  created_at: string
}

export type IngestionStage = 'pending' | 'running' | 'completed' | 'skipped' | 'failed'

export type IngestionJob = {
  id: string
  document_id: string
  filename: string
  status: 'queued' | 'reading' | 'recovering_scan' | 'extracting' | 'validating' | 'indexing' | 'completed' | 'failed'
  stages: Record<'READ' | 'OCR' | 'EXTRACT' | 'VERIFY' | 'INDEX', IngestionStage>
  error_message: string | null
  cached_verified_extraction: boolean
  page_count: number
  chunk_count: number
  events: EventDetail[]
  created_at: string
  updated_at: string
}

export type UploadResult = {
  document_id: string
  ingestion_job_id: string
  status: string
  duplicate: boolean
}

export type ProjectedEvent = HistoricalEvent & {
  well_name: string
  distance_km: number
  relative_position: number
  projected_md_m: number
  lookahead_m: number
  analog_relevance: number
  score_breakdown: Record<string, number>
}

export type Hazard = {
  hazard_type: HistoricalEvent['hazard_type']
  state: HazardState
  evidence_score: number
  projected_hazard_md_m: number
  lookahead_m: number
  supporting_wells: number
  score_breakdown: {
    analog_support: number
    recurrence_score: number
    telemetry_score: number
  }
  live_signals: Record<string, number>
  analogs: ProjectedEvent[]
}

export type Well = {
  id: string
  name: string
  is_active: boolean
  latitude: number
  longitude: number
  field_name: string
  max_md_m: number
  status: string
  source_kind: string
  well_scope: 'LOCAL_OFFSET' | 'CONTEXT'
  distance_km: number
  event_count: number
  formations: FormationInterval[]
  events: HistoricalEvent[]
  hazards: HistoricalEvent['hazard_type'][]
}

export type WellsResponse = {
  active_well_id: string
  radius_km: number
  wells: Well[]
  synthetic_data: boolean
}

export type MapWellsResponse = {
  active_well_id: string
  local_offset_count: number
  context_well_count: number
  total_well_count: number
  context_wells: Well[]
  synthetic_data: boolean
}

export type LivePayload = {
  type: 'telemetry'
  replay: {
    status: ReplayStatus
    sequence: number
    sample: TelemetrySample
    sample_count: number
  }
  active_well: Omit<Well, 'distance_km' | 'event_count' | 'formations' | 'events' | 'hazards'>
  state: HazardState
  sample: TelemetrySample
  current_formation: FormationInterval | null
  formations: FormationInterval[]
  lookahead_window_m: number
  projected_events: ProjectedEvent[]
  active_hazard: Hazard | null
  hazards: Hazard[]
}

export type KnowledgeResult = EventDetail & {
  search_score: number
  evidence_preview: string
}

export type KnowledgeSearchResponse = {
  query: string
  filters: {
    well_id: string | null
    formation: string | null
    hazard_type: string | null
  }
  result_count: number
  results: KnowledgeResult[]
}

export type CopilotSource = {
  source_id: string
  event_id: string
  well_name: string
  formation: string
  hazard_type: HistoricalEvent['hazard_type']
  document_id: string
  document_title: string
  filename: string
  page_number: number
  evidence_text: string
  source_kind: string
}

export type CopilotResponse = {
  answer_markdown: string
  sources: CopilotSource[]
  insufficient_evidence: boolean
  generation_mode: 'gemini' | 'deterministic_evidence_summary' | 'insufficient_evidence'
  retrieval_mode: 'hybrid' | 'metadata_lexical' | 'insufficient'
  retrieved_count: number
  provider_error?: string
}

export type CopilotRequest = {
  question: string
  active_well_id: string
  current_md_m: number | null
  formation: string | null
  selected_well_ids: string[]
}
