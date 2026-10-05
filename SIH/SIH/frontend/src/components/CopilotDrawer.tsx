import { Fragment, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useMutation } from '@tanstack/react-query'
import { AlertCircle, ArrowUp, ArrowUpRight, FileText, ShieldCheck, X } from 'lucide-react'
import { queryCopilot } from '../api'
import { formatDepth, hazardLabel, lithologyClass, shortWellName } from '../format'
import { claimEscape, useDialogFocus } from '../hooks/useDialogFocus'
import type { CopilotResponse, CopilotSource, EventEvidence, LivePayload } from '../types'
import { SourceViewer } from './SourceViewer'

type Props = {
  payload: LivePayload | null
  onClose: () => void
}

const modeLabel: Record<CopilotResponse['generation_mode'], string> = {
  gemini: 'Written from cited evidence',
  deterministic_evidence_summary: 'Evidence summary · model unavailable',
  insufficient_evidence: 'Not enough evidence to answer',
}

function toEvidence(source: CopilotSource): EventEvidence {
  return {
    id: source.source_id,
    event_id: source.event_id,
    document_id: source.document_id,
    document_title: source.document_title,
    filename: source.filename,
    page_number: source.page_number,
    evidence_text: source.evidence_text,
    bbox_json: null,
    source_kind: source.source_kind,
  }
}

type CiteProps = {
  sources: CopilotSource[]
  onOpen: (source: CopilotSource) => void
  onHover: (sourceId: string | null) => void
}

/**
 * Answers cite sources inline as [source-id] or [id-a, id-b]. Known IDs become
 * numbered chips that open the cited page; anything else stays as written.
 */
function renderInline(text: string, { sources, onOpen, onHover }: CiteProps): ReactNode[] {
  const order = new Map(sources.map((source, index) => [source.source_id, index]))
  const parts: ReactNode[] = []
  const pattern = /\[([^\]\n]+)\]|\*\*([^*\n]+)\*\*/g
  let cursor = 0
  for (const match of text.matchAll(pattern)) {
    const start = match.index ?? 0
    if (match[2] !== undefined) {
      parts.push(text.slice(cursor, start), <strong key={start}>{match[2]}</strong>)
      cursor = start + match[0].length
      continue
    }
    const ids = match[1].split(/\s*[,;]\s*/)
    if (!ids.every((id) => order.has(id))) continue
    // Keep the chips on the line of the word they cite and the punctuation after them.
    const [, before, lastWord] = /^([\s\S]*?)(\S*)\s*$/.exec(text.slice(cursor, start)) ?? ['', '', '']
    const end = start + match[0].length
    const trailing = /^[.,;:)]*/.exec(text.slice(end))?.[0] ?? ''
    parts.push(before)
    parts.push(
      <span className="cite-anchor" key={start}>
        {lastWord}
        <span className="cite-group">
          {ids.map((id) => {
            const index = order.get(id) ?? 0
            const source = sources[index]
            return (
              <button
                type="button"
                key={id}
                className="cite-chip tabular"
                onClick={() => onOpen(source)}
                onMouseEnter={() => onHover(id)}
                onMouseLeave={() => onHover(null)}
                onFocus={() => onHover(id)}
                onBlur={() => onHover(null)}
                aria-label={`Source ${index + 1}: ${source.filename}, page ${source.page_number}`}
              >
                {index + 1}
              </button>
            )
          })}
        </span>
        {trailing}
      </span>,
    )
    cursor = end + trailing.length
  }
  parts.push(text.slice(cursor))
  return parts
}

/** Paragraphs and "- " lists; an indented line continues the list item above it. */
function AnswerBody({ text, ...cite }: CiteProps & { text: string }) {
  const blocks: ({ kind: 'p'; lines: string[] } | { kind: 'ul'; items: string[][] })[] = []
  for (const raw of text.split('\n')) {
    const line = raw.trimEnd()
    const last = blocks[blocks.length - 1]
    if (!line.trim()) {
      blocks.push({ kind: 'p', lines: [] })
    } else if (/^\s{0,1}[-*•]\s+/.test(line)) {
      const item = [line.replace(/^\s*[-*•]\s+/, '')]
      if (last?.kind === 'ul') last.items.push(item)
      else blocks.push({ kind: 'ul', items: [item] })
    } else if (/^\s{2,}/.test(line) && last?.kind === 'ul') {
      last.items[last.items.length - 1].push(line.trim())
    } else if (last?.kind === 'p') {
      last.lines.push(line.trim())
    } else {
      blocks.push({ kind: 'p', lines: [line.trim()] })
    }
  }

  return (
    <div className="ask-answer">
      {blocks.map((block, index) => {
        if (block.kind === 'ul') {
          return (
            <ul key={index}>
              {block.items.map(([first, ...rest], itemIndex) => (
                <li key={itemIndex}>
                  <span>{renderInline(first, cite)}</span>
                  {rest.map((line, lineIndex) => <span className="ask-answer-detail" key={lineIndex}>{renderInline(line, cite)}</span>)}
                </li>
              ))}
            </ul>
          )
        }
        if (block.lines.length === 0) return null
        return (
          <p key={index}>
            {block.lines.map((line, lineIndex) => (
              <Fragment key={lineIndex}>{lineIndex > 0 && ' '}{renderInline(line, cite)}</Fragment>
            ))}
          </p>
        )
      })}
    </div>
  )
}

export function CopilotDrawer({ payload, onClose }: Props) {
  const [question, setQuestion] = useState('')
  const [askedQuestion, setAskedQuestion] = useState('')
  const [source, setSource] = useState<EventEvidence | null>(null)
  const [linkedSource, setLinkedSource] = useState<string | null>(null)
  const sheetRef = useDialogFocus<HTMLElement>()
  const selectedWellIds = useMemo(
    () => [...new Set(payload?.active_hazard?.analogs.map((event) => event.well_id) ?? [])],
    [payload?.active_hazard],
  )
  const answer = useMutation({
    mutationFn: (value: string) => queryCopilot({
      question: value,
      active_well_id: payload?.active_well.id ?? 'active-01',
      current_md_m: payload?.sample.md_m ?? null,
      formation: payload?.current_formation?.formation_name ?? null,
      selected_well_ids: selectedWellIds,
    }),
  })

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (claimEscape(event, sheetRef.current)) onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose, sheetRef])

  const ask = (value: string) => {
    const normalized = value.trim()
    if (normalized.length < 3 || answer.isPending) return
    setQuestion(normalized)
    setAskedQuestion(normalized)
    answer.mutate(normalized)
  }

  const formation = payload?.current_formation ?? null
  const formationIndex = formation ? payload?.formations.findIndex((item) => item.id === formation.id) ?? 0 : 0
  const bitDepth = payload ? formatDepth(payload.sample.md_m, 1) : '—'
  const suggestions = [
    `What happened in nearby wells in the ${formation?.formation_name ?? 'Barail'} interval ahead of us?`,
    'What supports the current alert?',
    'What responses were historically recorded for mud loss?',
  ]
  const cite: CiteProps = {
    sources: answer.data?.sources ?? [],
    onOpen: (item) => setSource(toEvidence(item)),
    onHover: setLinkedSource,
  }
  const showThread = answer.isPending || answer.isError || Boolean(answer.data)

  return (
    <>
      <div className="sheet-scrim" onMouseDown={onClose} />
      <aside className="sheet copilot-drawer" role="dialog" aria-modal="true" aria-labelledby="copilot-title" ref={sheetRef}>
        <header className="sheet-header sheet-header-sticky ask-header">
          <div>
            <span className="ask-eyebrow"><i className="ask-mark" aria-hidden="true" />Evidence copilot</span>
            <h2 id="copilot-title">Ask NWIS</h2>
            <p className="sheet-lede">Answers come only from validated offset-well events, and every claim links to the report page it came from.</p>
          </div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Close Ask NWIS"><X size={18} /></button>
        </header>

        <section className="ask-bore" aria-label="Asking from">
          <i className={`ask-core ${lithologyClass(formation?.formation_code, formationIndex)}`} aria-hidden="true"><b /></i>
          <div className="ask-bore-body">
            <span className="ask-label">Asking from</span>
            <dl>
              <div><dt>Well</dt><dd className="mono">{payload?.active_well.name ?? 'NWIS-ACT-01'}</dd></div>
              <div><dt>Formation</dt><dd>{formation?.formation_name ?? '—'}</dd></div>
              <div className="ask-bore-depth"><dt>Bit depth</dt><dd className="tabular">{bitDepth}<small> MD</small></dd></div>
            </dl>
          </div>
        </section>

        <form className="copilot-query" onSubmit={(event) => { event.preventDefault(); ask(question) }}>
          <label htmlFor="copilot-question" className="visually-hidden">Question</label>
          <div className="composer ask-composer">
            <textarea
              id="copilot-question"
              data-autofocus
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
                  event.preventDefault()
                  ask(question)
                }
              }}
              placeholder="Ask about recorded events, formations, or historical responses"
              rows={3}
            />
            <div className="ask-composer-bar">
              <span className="composer-hint"><kbd>Enter</kbd> to ask · <kbd>Shift</kbd> + <kbd>Enter</kbd> for a new line</span>
              <button type="submit" className="ask-submit" disabled={answer.isPending || question.trim().length < 3}>
                Ask <ArrowUp size={14} strokeWidth={2.4} />
              </button>
            </div>
          </div>
        </form>

        {!showThread && (
          <section className="ask-suggestions">
            <h3 className="ask-label">Suggested questions</h3>
            <ul>
              {suggestions.map((item) => (
                <li key={item}>
                  <button type="button" onClick={() => ask(item)}>
                    <span>{item}</span><ArrowUpRight size={15} aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )}

        {showThread && (
          <section className="ask-thread" aria-live="polite">
            <div className="ask-question">
              <span className="ask-label">You asked</span>
              <p>{askedQuestion}</p>
            </div>

            {answer.isPending && (
              <div className="ask-card ask-pending">
                <div className="loading-line" aria-hidden="true"><i /></div>
                <strong>Searching validated events</strong>
                <span>Near {bitDepth} in {formation?.formation_name ?? 'the current formation'}, ranked before an answer is written.</span>
                <div className="ask-skeleton" aria-hidden="true"><i /><i /><i /></div>
              </div>
            )}

            {answer.isError && (
              <div className="notice notice-error">
                <AlertCircle size={16} />
                <span><strong>No answer returned.</strong> {answer.error.message}</span>
                <button type="button" className="link-button" onClick={() => ask(askedQuestion || question)}>Try again</button>
              </div>
            )}

            {answer.data && (
              <>
                <div className="ask-card">
                  <div className={`generation-status mode-${answer.data.generation_mode}`}>
                    <i aria-hidden="true" />
                    <span>{modeLabel[answer.data.generation_mode]}</span>
                    <code className="tabular">{answer.data.retrieved_count} event{answer.data.retrieved_count === 1 ? '' : 's'} retrieved</code>
                  </div>
                  <AnswerBody text={answer.data.answer_markdown} {...cite} />
                  {answer.data.insufficient_evidence && <p className="notice">No answer was written, because the retrieved records do not support one.</p>}
                  {answer.data.generation_mode === 'deterministic_evidence_summary' && <p className="notice notice-watch">The language model was unavailable, so the text above is the retrieved records shown as they are stored.</p>}
                </div>

                {answer.data.sources.length > 0 && (
                  <div className="copilot-citations">
                    <h3 className="ask-label">Cited pages <span className="tabular">{answer.data.sources.length}</span></h3>
                    <ol>
                      {answer.data.sources.map((item, index) => (
                        <li key={item.source_id}>
                          <button
                            type="button"
                            className={linkedSource === item.source_id ? 'is-linked' : undefined}
                            onClick={() => setSource(toEvidence(item))}
                          >
                            <span className="citation-index tabular">{index + 1}</span>
                            <span className="citation-body">
                              <strong>{shortWellName(item.well_name)} · {item.formation}</strong>
                              <em>{hazardLabel(item.hazard_type)}</em>
                              <small><FileText size={12} /> {item.filename}</small>
                            </span>
                            <span className="citation-page tabular"><small>Page</small>{item.page_number}</span>
                          </button>
                        </li>
                      ))}
                    </ol>
                  </div>
                )}
              </>
            )}
          </section>
        )}

        <footer className="ask-footer">
          <ShieldCheck size={14} aria-hidden="true" />
          <span>NWIS reports what offset wells recorded. It does not give drilling-control instructions.</span>
        </footer>
      </aside>
      {source && <SourceViewer evidence={source} onClose={() => setSource(null)} />}
    </>
  )
}
