import { useEffect } from 'react'
import { ChevronRight, X } from 'lucide-react'
import { formatInterval, formatNumber, hazardLabel, lithologyClass, sentenceCase } from '../format'
import { claimEscape } from '../hooks/useDialogFocus'
import type { Well } from '../types'

export function WellDrawer({ well, onClose, onSelectEvent }: { well: Well; onClose: () => void; onSelectEvent: (eventId: string) => void }) {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (claimEscape(event, null)) onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose])
  return (
    <aside className="well-drawer" aria-label={`${well.name} details`}>
      <header className="sheet-header">
        <div>
          <span className="sheet-kicker">Offset well</span>
          <h3 className="mono-title">{well.name}</h3>
        </div>
        <button type="button" className="icon-button" onClick={onClose} aria-label="Close well details"><X size={16} /></button>
      </header>
      <dl className="stat-row">
        <div><dt>Distance</dt><dd className="tabular">{formatNumber(well.distance_km, 2)}<small> km</small></dd></div>
        <div><dt>Status</dt><dd>{sentenceCase(well.status)}</dd></div>
        <div><dt>Events</dt><dd className="tabular">{well.event_count}</dd></div>
      </dl>
      <section className="sheet-section">
        <h4>Formation tops</h4>
        <ul className="formation-list">
          {well.formations.map((formation, index) => (
            <li key={formation.id}>
              <i className={`litho-swatch ${lithologyClass(formation.formation_code, index)}`} aria-hidden="true" />
              <span>{formation.formation_name}</span>
              <code>{formatInterval(formation.top_md_m, formation.base_md_m)}</code>
            </li>
          ))}
        </ul>
      </section>
      <section className="sheet-section">
        <h4>Recorded events</h4>
        {well.events.length === 0 && <p className="quiet-copy">No events are recorded for this well.</p>}
        {well.events.map((event) => (
          <article className="event-row" key={event.id}>
            <div className="event-row-title">
              <span className={`severity-tag severity-${event.severity.toLowerCase()}`}>{sentenceCase(event.severity)}</span>
              <strong>{hazardLabel(event.hazard_type)}</strong>
              <code>{event.formation_name} · {formatInterval(event.start_md_m, event.end_md_m)}</code>
            </div>
            <p>{event.description}</p>
            <button type="button" className="link-button event-evidence-button" onClick={() => onSelectEvent(event.id)}>
              View evidence <ChevronRight size={14} />
            </button>
          </article>
        ))}
      </section>
    </aside>
  )
}
