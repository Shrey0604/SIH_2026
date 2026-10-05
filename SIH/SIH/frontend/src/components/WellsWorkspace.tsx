import { useQuery } from '@tanstack/react-query'
import { AlertCircle, ArrowRight } from 'lucide-react'
import { getWells } from '../api'
import { formatNumber, hazardLabel } from '../format'

type Props = { onOpenLive: () => void }

const registerRadiusKm = 10

export function WellsWorkspace({ onOpenLive }: Props) {
  const wells = useQuery({ queryKey: ['wells', registerRadiusKm], queryFn: () => getWells(registerRadiusKm) })
  const maxDistance = Math.max(1, ...(wells.data?.wells.map((well) => well.distance_km) ?? [1]))
  const sorted = [...(wells.data?.wells ?? [])].sort((a, b) => Number(b.is_active) - Number(a.is_active) || a.distance_km - b.distance_km)
  return (
    <section className="page wells-workspace">
      <header className="page-header">
        <div>
          <h1>Wells</h1>
          <p className="page-lede">The active well and the local offsets used for projection and alert scoring. Context wells elsewhere in India are excluded from alerts.</p>
        </div>
        <button type="button" className="btn btn-primary" onClick={onOpenLive}>Open live view <ArrowRight size={15} /></button>
      </header>

      <section className="table-panel">
        <header className="table-panel-header">
          <h2>{wells.data ? `${wells.data.wells.length} wells` : 'Well register'}</h2>
          <span>Rajasthan operations block · within {registerRadiusKm} km of the active well</span>
        </header>
        <div className="data-table wells-table" role="table" aria-label="Well register">
          <div className="data-row data-head" role="row">
            <span role="columnheader">Well</span>
            <span role="columnheader">Role</span>
            <span role="columnheader">Distance</span>
            <span role="columnheader">Events</span>
            <span role="columnheader">Hazards recorded</span>
          </div>
          {wells.isLoading && <div className="table-loading">{[0, 1, 2, 3].map((item) => <i key={item} />)}</div>}
          {wells.isError && (
            <div className="empty-state is-error">
              <AlertCircle size={20} />
              <strong>Well register unavailable</strong>
              <span>The API did not return the local well set.</span>
              <button type="button" className="btn btn-quiet" onClick={() => wells.refetch()}>Try again</button>
            </div>
          )}
          {sorted.map((well) => (
            <div className={`data-row ${well.is_active ? 'is-active-well' : ''}`} role="row" key={well.id}>
              <span role="cell" className="well-cell">
                <i className={well.is_active ? 'well-glyph active' : 'well-glyph'} aria-hidden="true" />
                <span><strong className="mono">{well.name}</strong><small>{well.field_name}</small></span>
              </span>
              <span role="cell">{well.is_active ? 'Active · drilling' : 'Local offset'}</span>
              <span role="cell" className="distance-cell">
                {well.is_active ? (
                  <span className="quiet-copy">—</span>
                ) : (
                  <>
                    <span className="tabular">{formatNumber(well.distance_km, 2)} km</span>
                    <i aria-hidden="true"><b style={{ transform: `scaleX(${well.distance_km / maxDistance})` }} /></i>
                  </>
                )}
              </span>
              <span role="cell" className="tabular">{well.event_count}</span>
              <span role="cell" className="hazard-tags">
                {well.hazards.length
                  ? [...new Set(well.hazards)].map((item) => <span className="tag" key={item}>{hazardLabel(item)}</span>)
                  : <span className="quiet-copy">None recorded</span>}
              </span>
            </div>
          ))}
        </div>
      </section>
    </section>
  )
}
