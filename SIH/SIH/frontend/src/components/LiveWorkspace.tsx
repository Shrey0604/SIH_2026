import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertCircle } from 'lucide-react'
import { apiBaseUrl, getMapWells, getWells } from '../api'
import type { Theme } from '../theme'
import type { Hazard, LivePayload, TelemetrySample } from '../types'
import { HazardHorizon } from './HazardHorizon'
import { OffsetWellMap } from './OffsetWellMap'
import { TelemetryStrip } from './TelemetryStrip'
import { EvidenceDrawer } from './EvidenceDrawer'

type Props = {
  radiusKm: number
  onRadiusChange: (radius: number) => void
  payload: LivePayload | null
  history: TelemetrySample[]
  error: string | null
  theme: Theme
  onOpenCopilot: () => void
}

export function LiveWorkspace({ radiusKm, onRadiusChange, payload, history, error, theme, onOpenCopilot }: Props) {
  const [evidenceOpen, setEvidenceOpen] = useState(false)
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null)
  // The alert the reader opened. Keeps the sheet readable if the live state clears while it is open.
  const [explainedHazard, setExplainedHazard] = useState<Hazard | null>(null)
  const wells = useQuery({
    queryKey: ['wells', radiusKm],
    queryFn: () => getWells(radiusKm),
  })
  const mapWells = useQuery({
    queryKey: ['map-wells'],
    queryFn: getMapWells,
    staleTime: Infinity,
  })
  const openEvent = (eventId: string) => {
    setSelectedEventId(eventId)
    setEvidenceOpen(true)
  }
  return (
    <div className="live-workspace">
      {error && (
        <div className="inline-error" role="alert">
          <AlertCircle size={15} />
          <span><strong>Live data unavailable.</strong> {error.replace(/\.$/, '')}. Check that the API is running at {apiBaseUrl}.</span>
        </div>
      )}
      <div className="live-grid">
        <HazardHorizon
          payload={payload}
          onExplain={() => {
            setSelectedEventId(null)
            setExplainedHazard(payload?.active_hazard ?? null)
            setEvidenceOpen(true)
          }}
          onAskHazard={onOpenCopilot}
          onSelectEvent={openEvent}
        />
        <OffsetWellMap
          wells={wells.data?.wells ?? []}
          contextWells={mapWells.data?.context_wells ?? []}
          localOffsetCount={mapWells.data?.local_offset_count ?? 6}
          totalWellCount={mapWells.data?.total_well_count ?? 31}
          radiusKm={radiusKm}
          onRadiusChange={onRadiusChange}
          replaying={payload?.replay.status === 'running'}
          supportingWellIds={payload?.active_hazard?.analogs.map((analog) => analog.well_id) ?? []}
          theme={theme}
          onSelectEvent={openEvent}
        />
        <TelemetryStrip history={history} />
      </div>
      {evidenceOpen && (
        <EvidenceDrawer
          hazard={selectedEventId ? null : payload?.active_hazard ?? explainedHazard}
          initialEventId={selectedEventId}
          onClose={() => setEvidenceOpen(false)}
        />
      )}
    </div>
  )
}
