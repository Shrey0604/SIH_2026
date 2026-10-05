import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertCircle, FileText, Search, X } from 'lucide-react'
import { getWells, searchKnowledge } from '../api'
import { formatInterval, hazardLabel, sentenceCase } from '../format'
import { EvidenceDrawer } from './EvidenceDrawer'

export function KnowledgeWorkspace() {
  const [draftQuery, setDraftQuery] = useState('')
  const [query, setQuery] = useState('')
  const [wellId, setWellId] = useState('')
  const [formation, setFormation] = useState('')
  const [hazardType, setHazardType] = useState('')
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null)

  const wells = useQuery({ queryKey: ['wells', 10], queryFn: () => getWells(10) })
  const knowledge = useQuery({
    queryKey: ['knowledge', query, wellId, formation, hazardType],
    queryFn: () => searchKnowledge({ query, wellId, formation, hazardType }),
  })
  const formations = useMemo(
    () => [...new Set(wells.data?.wells.flatMap((well) => well.formations.map((item) => item.formation_name)) ?? [])].sort(),
    [wells.data],
  )
  const filtersActive = Boolean(query || wellId || formation || hazardType)
  const clearAll = () => {
    setDraftQuery('')
    setQuery('')
    setWellId('')
    setFormation('')
    setHazardType('')
  }

  return (
    <section className="page knowledge-workspace">
      <header className="page-header">
        <div>
          <h1>Knowledge</h1>
          <p className="page-lede">Validated historical events. Each one is tied to an exact page in a stored report.</p>
        </div>
        <span className="data-badge">Synthetic demo corpus</span>
      </header>

      <form
        className="knowledge-controls"
        role="search"
        onSubmit={(event) => {
          event.preventDefault()
          setQuery(draftQuery.trim())
        }}
      >
        <label className="search-field">
          <Search size={17} strokeWidth={1.8} />
          <span className="visually-hidden">Search institutional memory</span>
          <input
            type="search"
            value={draftQuery}
            onChange={(event) => setDraftQuery(event.target.value)}
            placeholder="Search events, formations, wells, or recorded responses"
          />
          <button type="submit" className="btn btn-primary">Search</button>
        </label>
        <div className="filter-row" aria-label="Knowledge filters">
          <label className="select-field">
            <span>Well</span>
            <select value={wellId} onChange={(event) => setWellId(event.target.value)} aria-label="Well filter">
              <option value="">All wells</option>
              {wells.data?.wells.filter((well) => !well.is_active).map((well) => <option key={well.id} value={well.id}>{well.name}</option>)}
            </select>
          </label>
          <label className="select-field">
            <span>Formation</span>
            <select value={formation} onChange={(event) => setFormation(event.target.value)} aria-label="Formation filter">
              <option value="">All formations</option>
              {formations.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
          <label className="select-field">
            <span>Hazard</span>
            <select value={hazardType} onChange={(event) => setHazardType(event.target.value)} aria-label="Hazard filter">
              <option value="">All hazards</option>
              <option value="MUD_LOSS">Mud loss</option>
              <option value="STUCK_PIPE">Stuck pipe</option>
              <option value="KICK">Kick</option>
            </select>
          </label>
          {filtersActive && (
            <button type="button" className="link-button clear-filters" onClick={clearAll}><X size={14} /> Clear search and filters</button>
          )}
        </div>
      </form>

      <section className="table-panel" aria-live="polite" aria-busy={knowledge.isFetching}>
        <header className="table-panel-header">
          <h2>{knowledge.data ? `${knowledge.data.result_count} event${knowledge.data.result_count === 1 ? '' : 's'}` : 'Events'}</h2>
          <span>{query ? `Matching “${query}”` : 'Sorted by relevance'} · open a row to read its source page</span>
        </header>
        <div className="data-table knowledge-table">
          <div className="data-row data-head" aria-hidden="true">
            <span>Event</span>
            <span>Well</span>
            <span>Formation</span>
            <span>Depth</span>
            <span>Severity</span>
            <span>Source</span>
          </div>
          {knowledge.isLoading && (
            <div className="table-loading" aria-label="Loading knowledge results">
              {[0, 1, 2, 3].map((item) => <i key={item} />)}
            </div>
          )}
          {knowledge.isError && (
            <div className="empty-state is-error">
              <AlertCircle size={20} />
              <strong>Knowledge search is unavailable</strong>
              <span>Validated evidence could not be loaded. The live replay is not affected.</span>
              <button type="button" className="btn btn-quiet" onClick={() => knowledge.refetch()}>Try again</button>
            </div>
          )}
          {knowledge.data?.results.map((event) => (
            <button
              className="data-row"
              type="button"
              key={event.id}
              onClick={() => setSelectedEventId(event.id)}
              aria-label={`${hazardLabel(event.hazard_type)}, ${event.well_name}, ${event.formation_name}, ${formatInterval(event.start_md_m, event.end_md_m)}, ${sentenceCase(event.severity)} severity. Open evidence.`}
            >
              <strong>{hazardLabel(event.hazard_type)}</strong>
              <span className="mono">{event.well_name}</span>
              <span>{event.formation_name}</span>
              <span className="tabular">{formatInterval(event.start_md_m, event.end_md_m)}</span>
              <span><span className={`severity-tag severity-${event.severity.toLowerCase()}`}>{sentenceCase(event.severity)}</span></span>
              <span className="source-cell"><FileText size={14} strokeWidth={1.7} />{event.evidence[0]?.filename ?? '—'}<em>p. {event.evidence[0]?.page_number ?? '—'}</em></span>
            </button>
          ))}
          {knowledge.data && knowledge.data.results.length === 0 && (
            <div className="empty-state">
              <Search size={20} />
              <strong>No cited events match</strong>
              <span>Try a broader term, such as a hazard or formation name, or clear a filter.</span>
              {filtersActive && <button type="button" className="btn btn-quiet" onClick={clearAll}>Clear search and filters</button>}
            </div>
          )}
        </div>
      </section>

      {selectedEventId && (
        <EvidenceDrawer hazard={null} initialEventId={selectedEventId} onClose={() => setSelectedEventId(null)} />
      )}
    </section>
  )
}
