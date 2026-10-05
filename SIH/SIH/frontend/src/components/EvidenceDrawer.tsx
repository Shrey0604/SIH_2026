import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, ChevronRight, FileText, X } from 'lucide-react'
import { getEvent } from '../api'
import { formatDepth, formatInterval, formatNumber, hazardLabel, sentenceCase, shortWellName, signalLabel } from '../format'
import { claimEscape, useDialogFocus } from '../hooks/useDialogFocus'
import type { EventEvidence, Hazard } from '../types'
import { SourceViewer } from './SourceViewer'

type Props = {
  hazard: Hazard | null
  initialEventId: string | null
  onClose: () => void
}

const stateLabel = { CLEAR: 'Clear', WATCH: 'Watch', ELEVATED: 'Elevated' } as const
const sourceLabel = {
  AI_EXTRACTED: 'Extracted from report',
  CACHED_VERIFIED: 'Verified extraction',
  SEEDED: 'Seeded record',
  REVIEWED: 'Reviewed record',
} as const

export function EvidenceDrawer({ hazard, initialEventId, onClose }: Props) {
  const [eventId, setEventId] = useState(initialEventId ?? hazard?.analogs[0]?.id ?? null)
  const [source, setSource] = useState<EventEvidence | null>(null)
  const sheetRef = useDialogFocus<HTMLElement>()
  // The live hazard is a new object every telemetry sample. Only move the
  // selection when the caller asks for a different event or the reader's
  // choice is no longer among the supporting analogs.
  const analogKey = hazard?.analogs.map((analog) => analog.id).join(',') ?? ''
  useEffect(() => {
    const analogIds = analogKey ? analogKey.split(',') : []
    setEventId((current) => {
      if (initialEventId) return initialEventId
      if (current && analogIds.includes(current)) return current
      return analogIds[0] ?? current
    })
  }, [analogKey, initialEventId])
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (claimEscape(event, sheetRef.current)) onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose, sheetRef])
  const event = useQuery({
    queryKey: ['event', eventId],
    queryFn: () => getEvent(eventId as string),
    enabled: Boolean(eventId),
  })

  return (
    <>
      <div className="sheet-scrim" onMouseDown={onClose} />
      <aside
        className="sheet evidence-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="evidence-title"
        ref={sheetRef}
      >
        <header className="sheet-header sheet-header-sticky">
          <div>
            <h2 id="evidence-title">{hazard ? 'Why this alert?' : 'Event evidence'}</h2>
            <p className="sheet-lede">Every figure here traces back to a stored report page.</p>
          </div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Close evidence drawer" data-autofocus><X size={18} /></button>
        </header>

        {hazard && (
          <section className={`sheet-section alert-summary state-${hazard.state.toLowerCase()}`}>
            <div className="summary-title">
              <AlertTriangle size={18} strokeWidth={2} />
              <strong>{hazardLabel(hazard.hazard_type)}</strong>
              <span className={`state-chip state-${hazard.state.toLowerCase()}`}><i aria-hidden="true" />{stateLabel[hazard.state]}</span>
            </div>
            <dl className="stat-row stat-row-large">
              <div><dt>Ahead of bit</dt><dd className="tabular">{formatNumber(hazard.lookahead_m, 1)}<small> m</small></dd></div>
              <div title="Relative signal from historical similarity, recurrence, evidence quality, and live corroboration. Not a calibrated probability.">
                <dt>Evidence score</dt><dd className="tabular">{formatNumber(hazard.evidence_score, 1)}<small> /100</small></dd>
              </div>
              <div><dt>Offset wells</dt><dd className="tabular">{hazard.supporting_wells}</dd></div>
            </dl>
            <p className="footnote">The evidence score is a relative decision-support signal, not a calibrated probability.</p>
          </section>
        )}

        {hazard && (
          <section className="sheet-section">
            <h3>Score breakdown</h3>
            <div className="score-bars">
              {Object.entries(hazard.score_breakdown).map(([label, value]) => (
                <div key={label}>
                  <span>{sentenceCase(label)}</span>
                  <i><b style={{ transform: `scaleX(${Math.min(1, Math.max(0, value))})` }} /></i>
                  <code className="tabular">{formatNumber(value * 100)}</code>
                </div>
              ))}
            </div>
          </section>
        )}

        {hazard && (
          <section className="sheet-section">
            <h3>Live signals now</h3>
            <dl className="signal-grid">
              {Object.entries(hazard.live_signals).map(([key, value]) => {
                const { label, unit } = signalLabel(key)
                return (
                  <div key={key}>
                    <dt>{label}</dt>
                    <dd className="tabular">{value.toFixed(Math.abs(value) < 1 ? 3 : 1)}{unit && <small> {unit}</small>}</dd>
                  </div>
                )
              })}
            </dl>
          </section>
        )}

        {hazard && (
          <section className="sheet-section">
            <h3>Supporting offset events</h3>
            <div className="analog-list">
              {hazard.analogs.map((analog) => (
                <button
                  type="button"
                  className={eventId === analog.id ? 'selected' : ''}
                  aria-pressed={eventId === analog.id}
                  key={analog.id}
                  onClick={() => setEventId(analog.id)}
                >
                  <span>
                    <strong>{shortWellName(analog.well_name)}</strong>
                    <small>{analog.formation_name} · {formatInterval(analog.start_md_m, analog.end_md_m)}</small>
                  </span>
                  <code className="tabular">{formatNumber(analog.lookahead_m)} m ahead</code>
                  <ChevronRight size={15} />
                </button>
              ))}
            </div>
          </section>
        )}

        <section className="sheet-section event-evidence-section" aria-live="polite">
          <h3>Stored evidence</h3>
          {event.isLoading && <div className="skeleton-lines" aria-label="Loading stored evidence"><i /><i /><i /></div>}
          {event.isError && (
            <div className="notice notice-error">
              Stored evidence for this event could not be loaded.
              <button type="button" className="link-button" onClick={() => event.refetch()}>Try again</button>
            </div>
          )}
          {!eventId && <p className="quiet-copy">Select a supporting event to read its source.</p>}
          {event.data && (
            <>
              <div className="event-detail-heading">
                <span className={`severity-tag severity-${event.data.severity.toLowerCase()}`}>{sentenceCase(event.data.severity)}</span>
                <strong>{hazardLabel(event.data.hazard_type)}</strong>
                <code>{event.data.well_name} · {event.data.formation_name}</code>
              </div>
              <p className="event-description">{event.data.description}</p>
              {event.data.historical_response && (
                <div className="historical-response"><span>Historical response observed</span>{event.data.historical_response}</div>
              )}
              <dl className="fact-list">
                <div><dt>Recorded depth</dt><dd className="tabular">{event.data.end_md_m ? `${formatNumber(event.data.start_md_m, 1)}–${formatNumber(event.data.end_md_m, 1)} m` : formatDepth(event.data.start_md_m, 1)}</dd></div>
                <div><dt>Extraction confidence</dt><dd className="tabular">{formatNumber(event.data.extraction_confidence * 100)}%</dd></div>
                <div><dt>Record type</dt><dd>{sourceLabel[event.data.source] ?? sentenceCase(event.data.source)}</dd></div>
              </dl>
              <div className="source-list">
                {event.data.evidence.map((reference) => (
                  <button type="button" className="source-reference" key={reference.id} onClick={() => setSource(reference)}>
                    <FileText size={16} strokeWidth={1.7} />
                    <span>
                      <strong>{reference.filename} <em>p. {reference.page_number}</em></strong>
                      <small>“{reference.evidence_text}”</small>
                    </span>
                    <ChevronRight size={15} />
                  </button>
                ))}
              </div>
              {event.data.evidence.length === 0 && <div className="notice notice-error">This event has no stored page evidence, so it cannot support an alert.</div>}
            </>
          )}
        </section>
      </aside>
      {source && <SourceViewer evidence={source} onClose={() => setSource(null)} />}
    </>
  )
}
