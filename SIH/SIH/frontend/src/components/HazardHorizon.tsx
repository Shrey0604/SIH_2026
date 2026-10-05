import { useLayoutEffect, useRef, useState } from 'react'
import { AlertTriangle, Info, MessageSquareText, ShieldCheck } from 'lucide-react'
import { formatDepth, formatNumber, hazardLabel, lithologyClass, shortWellName } from '../format'
import type { HazardState, LivePayload, ProjectedEvent } from '../types'

type View = 'section' | 'window'

const stateLabel: Record<HazardState, string> = { CLEAR: 'Clear', WATCH: 'Watch', ELEVATED: 'Elevated' }
const scoreNote = 'Relative signal built from analog relevance, recurrence, evidence quality and live corroboration. It is not a calibrated probability.'
const remarkPitch = 38

function useElementHeight<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [height, setHeight] = useState(0)
  useLayoutEffect(() => {
    const element = ref.current
    if (!element) return
    const observer = new ResizeObserver(([entry]) => setHeight(entry.contentRect.height))
    observer.observe(element)
    return () => observer.disconnect()
  }, [])
  return [ref, height] as const
}

/** Spreads remark labels so they never overlap, keeping each as close to its depth as possible. */
function layoutRemarks(targets: number[], height: number) {
  const half = remarkPitch / 2
  const positions: number[] = []
  let previous = -Infinity
  for (const target of targets) {
    const y = Math.max(target, previous + remarkPitch, half)
    positions.push(y)
    previous = y
  }
  let limit = height - half
  for (let index = positions.length - 1; index >= 0; index -= 1) {
    positions[index] = Math.min(positions[index], limit)
    limit = positions[index] - remarkPitch
  }
  return positions
}

function tickStep(range: number) {
  if (range > 700) return { major: 100, minor: 20 }
  if (range > 300) return { major: 50, minor: 10 }
  return { major: 25, minor: 5 }
}

export function HazardHorizon({
  payload,
  onExplain,
  onAskHazard,
  onSelectEvent,
}: {
  payload: LivePayload | null
  onExplain: () => void
  onAskHazard: () => void
  onSelectEvent: (eventId: string) => void
}) {
  const [view, setView] = useState<View>('section')
  const [stripRef, stripHeight] = useElementHeight<HTMLDivElement>()
  const formations = payload?.formations ?? []
  const sample = payload?.sample
  const hazard = payload?.active_hazard
  const state: HazardState = payload?.state ?? 'CLEAR'
  const windowM = payload?.lookahead_window_m ?? 150

  const sectionTop = formations[0]?.top_md_m ?? 2800
  const sectionBase = formations.at(-1)?.base_md_m ?? 3860
  let top = sectionTop
  let base = sectionBase
  if (view === 'window' && sample) {
    const span = windowM * 2.4
    top = Math.max(sectionTop, sample.md_m - windowM * 0.6)
    base = Math.min(sectionBase, top + span)
    top = Math.max(sectionTop, base - span)
  }
  const range = Math.max(1, base - top)
  const pct = (depth: number) => Math.max(0, Math.min(100, ((depth - top) / range) * 100))
  const inView = (depth: number) => depth >= top && depth <= base

  const { major, minor } = tickStep(range)
  // Thin the depth labels when the strip is short so they never touch.
  const labelStep = stripHeight > 0 && (major / range) * stripHeight < 28 ? major * 2 : major
  const ticks: { depth: number; major: boolean; labelled: boolean }[] = []
  for (let depth = Math.ceil(top / minor) * minor; depth <= base + 0.001; depth += minor) {
    const rounded = Math.round(depth)
    ticks.push({ depth, major: rounded % major === 0, labelled: rounded % labelStep === 0 })
  }

  const events: ProjectedEvent[] = [...(payload?.projected_events ?? [])]
    .filter((event) => inView(event.projected_md_m))
    .sort((a, b) => a.projected_md_m - b.projected_md_m)
  // Label as many events as the strip can hold; every event still gets its tick on the log.
  const capacity = stripHeight > 0 ? Math.max(1, Math.floor(stripHeight / remarkPitch)) : events.length
  const remarked = events.length > capacity ? events.slice(0, capacity - 1) : events
  const unlabelled = events.length - remarked.length
  const remarkTargets = remarked.map((event) => (pct(event.projected_md_m) / 100) * stripHeight)
  const remarkSpace = unlabelled > 0 ? stripHeight - remarkPitch : stripHeight
  const remarkPositions = stripHeight > 0 ? layoutRemarks(remarkTargets, remarkSpace) : remarkTargets

  const bitDepth = sample?.md_m
  const nextFormation = bitDepth === undefined ? undefined : formations.find((formation) => formation.top_md_m > bitDepth)
  const stateKey = `${state}-${hazard?.hazard_type ?? 'none'}`

  return (
    <section className={`panel horizon-panel state-${state.toLowerCase()}`} aria-labelledby="horizon-title">
      <header className="panel-header">
        <div className="panel-title">
          <h2 id="horizon-title">Look-ahead</h2>
          <span className="panel-meta">Formation-aligned · next {formatNumber(windowM)} m</span>
        </div>
        <div className="panel-tools">
          <div className="segmented" role="group" aria-label="Depth scale">
            <button type="button" aria-pressed={view === 'section'} onClick={() => setView('section')} title="Show the full formation section">Section</button>
            <button type="button" aria-pressed={view === 'window'} onClick={() => setView('window')} title="Zoom to the bit and its look-ahead window">Window</button>
          </div>
          <span className={`state-chip state-${state.toLowerCase()}`}><i aria-hidden="true" />{stateLabel[state]}</span>
        </div>
      </header>

      {!payload ? (
        <div className="statement statement-pending" aria-live="polite">
          <span className="statement-hazard">Connecting to the live feed…</span>
          <p className="statement-note">The look-ahead appears once the first telemetry sample arrives.</p>
        </div>
      ) : hazard ? (
        <div className="statement" key={stateKey} aria-live="polite">
          <div className="statement-main">
            <span className="statement-hazard"><AlertTriangle size={15} strokeWidth={2} />{hazardLabel(hazard.hazard_type)}</span>
            <strong className="statement-distance">
              <span className="statement-number tabular">{formatNumber(Math.max(0, hazard.lookahead_m))}</span>
              <span className="statement-unit">m ahead</span>
            </strong>
          </div>
          <dl className="statement-facts">
            <div><dt>Projected depth</dt><dd className="tabular">{formatDepth(hazard.projected_hazard_md_m, 1)}</dd></div>
            <div><dt>Offset wells</dt><dd className="tabular">{hazard.supporting_wells}</dd></div>
            <div title={scoreNote}>
              <dt>Evidence score <Info size={12} aria-label={scoreNote} /></dt>
              <dd className="tabular">{formatNumber(hazard.evidence_score)}<small>/100</small></dd>
            </div>
          </dl>
          <div className="statement-actions">
            <button type="button" className="btn btn-primary" onClick={onExplain}>Why this alert?</button>
            <button type="button" className="btn btn-quiet" onClick={onAskHazard}>
              <MessageSquareText size={14} strokeWidth={1.8} /> Ask about this hazard
            </button>
          </div>
        </div>
      ) : (
        <div className="statement statement-clear" key={stateKey} aria-live="polite">
          <div className="statement-main">
            <span className="statement-hazard"><ShieldCheck size={15} strokeWidth={2} />No offset events ahead</span>
            <strong className="statement-distance">
              <span className="statement-number tabular">{formatNumber(windowM)}</span>
              <span className="statement-unit">m clear</span>
            </strong>
          </div>
          <dl className="statement-facts">
            <div><dt>Bit depth</dt><dd className="tabular">{formatDepth(bitDepth, 1)}</dd></div>
            <div><dt>Formation</dt><dd>{payload.current_formation?.formation_name ?? '—'}</dd></div>
            <div>
              <dt>Next top</dt>
              <dd className="tabular">
                {nextFormation && bitDepth !== undefined
                  ? `${nextFormation.formation_name} in ${formatNumber(nextFormation.top_md_m - bitDepth)} m`
                  : 'None in section'}
              </dd>
            </div>
          </dl>
        </div>
      )}

      <div className="log-strip" ref={stripRef}>
        <div className="log-ruler" aria-hidden="true">
          {ticks.map((tick) => {
            const position = pct(tick.depth)
            const edge = position < 2 ? 'at-top' : position > 98 ? 'at-bottom' : ''
            return (
              <span key={tick.depth} className={`tick ${tick.major ? 'major' : 'minor'} ${edge}`} style={{ top: `${position}%` }}>
                {tick.labelled && <em>{formatNumber(tick.depth)}</em>}
              </span>
            )
          })}
          {sample && <i className="ruler-bit" style={{ top: `${pct(sample.md_m)}%` }} />}
        </div>

        <div className="log-formations" aria-hidden="true">
          {formations.filter((formation) => formation.base_md_m > top && formation.top_md_m < base).map((formation) => {
            const start = pct(Math.max(formation.top_md_m, top))
            const end = pct(Math.min(formation.base_md_m, base))
            const heightPx = ((end - start) / 100) * stripHeight
            const current = payload?.current_formation?.id === formation.id
            return (
              <span
                key={formation.id}
                className={current ? 'is-current' : ''}
                style={{ top: `${start}%`, height: `${end - start}%` }}
              >
                {heightPx > 48 && <strong>{formation.formation_name}</strong>}
              </span>
            )
          })}
        </div>

        <div className="log-track" role="img" aria-label={
          sample
            ? `Bit at ${formatDepth(sample.md_m, 1)} in ${payload?.current_formation?.formation_name ?? 'an unknown formation'}; ${events.length} projected offset event${events.length === 1 ? '' : 's'} in view.`
            : 'Formation log'
        }>
          {formations.filter((formation) => formation.base_md_m > top && formation.top_md_m < base).map((formation) => {
            const start = pct(Math.max(formation.top_md_m, top))
            const end = pct(Math.min(formation.base_md_m, base))
            const index = formations.indexOf(formation)
            return (
              <div
                key={formation.id}
                className={`formation-band ${lithologyClass(formation.formation_code, index)}`}
                style={{ top: `${start}%`, height: `${end - start}%` }}
                title={`${formation.formation_name}: ${formatNumber(formation.top_md_m)}–${formatNumber(formation.base_md_m)} m`}
              />
            )
          })}

          {sample && (
            <div
              className="lookahead-bracket"
              style={{ top: `${pct(sample.md_m)}%`, height: `${pct(sample.md_m + windowM) - pct(sample.md_m)}%` }}
            >
              <span>+{formatNumber(windowM)} m</span>
            </div>
          )}

          {events.map((event) => (
            <i
              key={event.id}
              className={`event-tick severity-${event.severity.toLowerCase()}`}
              style={{ top: `${pct(event.projected_md_m)}%` }}
            />
          ))}

          {sample && (
            <div className="bit-line" style={{ top: `${pct(sample.md_m)}%` }}>
              <strong><small>Bit</small>{formatNumber(sample.md_m, 1)} m</strong>
            </div>
          )}
        </div>

        <div className="log-remarks">
          {stripHeight > 0 && remarked.length > 0 && (
            <svg className="remark-leaders" width="26" height={stripHeight} aria-hidden="true">
              {remarked.map((event, index) => {
                const from = remarkTargets[index]
                const to = remarkPositions[index]
                return <path key={event.id} d={`M0 ${from} H8 L18 ${to} H26`} className={`severity-${event.severity.toLowerCase()}`} />
              })}
            </svg>
          )}
          {remarked.map((event, index) => (
            <button
              type="button"
              key={event.id}
              className={`remark severity-${event.severity.toLowerCase()}`}
              style={{ top: remarkPositions[index] ?? 0 }}
              onClick={() => onSelectEvent(event.id)}
              title={`${event.well_name}: ${hazardLabel(event.hazard_type)} recorded at ${formatNumber(event.start_md_m)} m, projected to ${formatNumber(event.projected_md_m, 1)} m here. Open evidence.`}
            >
              <strong>{shortWellName(event.well_name)} · {hazardLabel(event.hazard_type)}</strong>
              <small className="tabular">
                {formatNumber(event.projected_md_m)} m
                <span className="remark-offset"> · {formatNumber(Math.abs(event.lookahead_m))} m {event.lookahead_m >= 0 ? 'ahead' : 'behind'}</span>
              </small>
            </button>
          ))}
          {unlabelled > 0 && (
            <p className="remarks-more" style={{ top: stripHeight - remarkPitch / 2 }}>
              +{unlabelled} more deeper{view === 'section' ? ' · switch to Window to separate them' : ''}
            </p>
          )}
          {payload && events.length === 0 && (
            <p className="remarks-empty">No offset-well events project into this {view === 'window' ? 'window' : 'section'}.</p>
          )}
        </div>
      </div>
    </section>
  )
}
