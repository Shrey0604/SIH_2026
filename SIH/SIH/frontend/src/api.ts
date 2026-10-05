import type {
  DocumentRecord,
  EventDetail,
  IngestionJob,
  KnowledgeSearchResponse,
  LivePayload,
  MapWellsResponse,
  CopilotRequest,
  CopilotResponse,
  UploadResult,
  WellsResponse,
} from './types'

export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new Error(payload?.detail ?? `NWIS API request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export function getDocuments(): Promise<DocumentRecord[]> {
  return fetch(`${apiBaseUrl}/api/documents`).then(readJson<DocumentRecord[]>)
}

export function uploadDocument(file: File, documentType: string): Promise<UploadResult> {
  const form = new FormData()
  form.append('file', file)
  form.append('document_type', documentType)
  return fetch(`${apiBaseUrl}/api/documents/upload`, {
    method: 'POST',
    body: form,
  }).then(readJson<UploadResult>)
}

export function getIngestionJob(jobId: string): Promise<IngestionJob> {
  return fetch(`${apiBaseUrl}/api/ingestion/${jobId}`).then(readJson<IngestionJob>)
}

export function getWells(radiusKm: number): Promise<WellsResponse> {
  return fetch(`${apiBaseUrl}/api/wells?active_well_id=active-01&radius_km=${radiusKm}`).then(
    readJson<WellsResponse>,
  )
}

export function getMapWells(): Promise<MapWellsResponse> {
  return fetch(`${apiBaseUrl}/api/map/wells`).then(readJson<MapWellsResponse>)
}

export function getEvent(eventId: string): Promise<EventDetail> {
  return fetch(`${apiBaseUrl}/api/events/${eventId}`).then(readJson<EventDetail>)
}

export function searchKnowledge(filters: {
  query?: string
  wellId?: string
  formation?: string
  hazardType?: string
}): Promise<KnowledgeSearchResponse> {
  const parameters = new URLSearchParams()
  if (filters.query) parameters.set('q', filters.query)
  if (filters.wellId) parameters.set('well_id', filters.wellId)
  if (filters.formation) parameters.set('formation', filters.formation)
  if (filters.hazardType) parameters.set('hazard_type', filters.hazardType)
  return fetch(`${apiBaseUrl}/api/knowledge/search?${parameters}`).then(
    readJson<KnowledgeSearchResponse>,
  )
}

export function queryCopilot(request: CopilotRequest): Promise<CopilotResponse> {
  return fetch(`${apiBaseUrl}/api/copilot/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  }).then(readJson<CopilotResponse>)
}

export function getCurrentTelemetry(radiusKm: number): Promise<LivePayload> {
  return fetch(`${apiBaseUrl}/api/telemetry/active-01/current?radius_km=${radiusKm}`).then(
    readJson<LivePayload>,
  )
}

export function getNextTelemetry(radiusKm: number): Promise<LivePayload> {
  return fetch(`${apiBaseUrl}/api/telemetry/active-01/next?radius_km=${radiusKm}`).then(
    readJson<LivePayload>,
  )
}

export function controlTelemetry(
  action: 'start' | 'pause' | 'resume' | 'reset',
  radiusKm: number,
): Promise<LivePayload> {
  return fetch(`${apiBaseUrl}/api/telemetry/active-01/control?radius_km=${radiusKm}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action }),
  }).then(readJson<LivePayload>)
}
