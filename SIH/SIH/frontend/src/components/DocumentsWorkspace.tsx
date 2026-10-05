import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Check, FileText, LoaderCircle, Minus, Upload, XCircle } from 'lucide-react'
import { getDocuments, getIngestionJob, uploadDocument } from '../api'
import { formatInterval, formatNumber, hazardLabel, sentenceCase } from '../format'
import type { EventEvidence, IngestionJob, IngestionStage } from '../types'
import { SourceViewer } from './SourceViewer'

const stages = [
  ['READ', 'Read pages'],
  ['OCR', 'Recover low-text pages'],
  ['EXTRACT', 'Extract structured events'],
  ['VERIFY', 'Verify exact evidence'],
  ['INDEX', 'Index searchable chunks'],
] as const

const stageStateLabel: Record<IngestionStage, string> = {
  pending: 'Waiting',
  running: 'Running',
  completed: 'Done',
  skipped: 'Skipped',
  failed: 'Failed',
}

const maxUploadBytes = 20 * 1024 * 1024

function StageIcon({ state }: { state: IngestionStage }) {
  if (state === 'running') return <LoaderCircle size={14} className="spin" />
  if (state === 'completed') return <Check size={14} strokeWidth={2.4} />
  if (state === 'failed') return <XCircle size={14} />
  if (state === 'skipped') return <Minus size={14} />
  return <i />
}

function formatBytes(bytes: number) {
  return bytes >= 1024 * 1024 ? `${formatNumber(bytes / 1024 / 1024, 1)} MB` : `${formatNumber(bytes / 1024, 1)} KB`
}

export function DocumentsWorkspace() {
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [documentType, setDocumentType] = useState('DDR')
  const [jobId, setJobId] = useState<string | null>(null)
  const [job, setJob] = useState<IngestionJob | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [evidence, setEvidence] = useState<EventEvidence | null>(null)
  const documents = useQuery({ queryKey: ['documents'], queryFn: getDocuments, refetchInterval: job && !['completed', 'failed'].includes(job.status) ? 1000 : false })

  useEffect(() => {
    if (!jobId) return
    let cancelled = false
    let timer: number | undefined
    let failures = 0
    const poll = async () => {
      try {
        const next = await getIngestionJob(jobId)
        if (cancelled) return
        failures = 0
        setError(null)
        setJob(next)
        if (next.status !== 'completed' && next.status !== 'failed') {
          timer = window.setTimeout(poll, 700)
        } else {
          void documents.refetch()
        }
      } catch (pollError) {
        if (cancelled) return
        // A dropped request must not freeze the pipeline view; keep retrying with backoff.
        failures += 1
        const reason = pollError instanceof Error ? pollError.message : 'no response'
        setError(`Lost contact with the ingestion service (${reason}). Retrying…`)
        timer = window.setTimeout(poll, Math.min(10_000, 1000 * 2 ** Math.min(failures, 4)))
      }
    }
    void poll()
    return () => {
      cancelled = true
      if (timer) window.clearTimeout(timer)
    }
  }, [jobId]) // eslint-disable-line react-hooks/exhaustive-deps

  const chooseFile = (next: File | null) => {
    setError(null)
    if (next && !/\.pdf$/i.test(next.name) && next.type !== 'application/pdf') {
      setFile(null)
      setError(`${next.name} is not a PDF. Choose a PDF drilling or completion report.`)
      return
    }
    if (next && next.size > maxUploadBytes) {
      setFile(null)
      setError(`${next.name} is ${formatBytes(next.size)}. Reports must be 20 MB or smaller.`)
      return
    }
    setFile(next)
  }

  const submit = async () => {
    if (!file) return
    setUploading(true)
    setError(null)
    setJob(null)
    try {
      const result = await uploadDocument(file, documentType)
      setJobId(result.ingestion_job_id)
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const running = Boolean(job && job.status !== 'completed' && job.status !== 'failed')

  return (
    <section className="page documents-workspace">
      <header className="page-header">
        <div>
          <h1>Documents</h1>
          <p className="page-lede">Turn drilling reports into events that cite the exact page they came from.</p>
        </div>
        <span className="data-badge">Synthetic demo workspace</span>
      </header>

      <div className="documents-grid">
        <div className="documents-column">
          <section className="card upload-panel" aria-labelledby="upload-title">
            <header className="card-header"><h2 id="upload-title">Add a report</h2></header>
            <button
              type="button"
              className={`drop-zone ${dragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`}
              onClick={() => inputRef.current?.click()}
              onDragOver={(event) => { event.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onDrop={(event) => {
                event.preventDefault()
                setDragging(false)
                chooseFile(event.dataTransfer.files[0] ?? null)
              }}
            >
              {file ? <FileText size={20} strokeWidth={1.6} /> : <Upload size={20} strokeWidth={1.6} />}
              <span className="drop-zone-text">
                <strong>{file ? file.name : 'Drop a PDF report here, or choose a file'}</strong>
                <small>{file ? `${formatBytes(file.size)} · click to choose a different file` : 'PDF only · up to 20 MB'}</small>
              </span>
            </button>
            <input ref={inputRef} className="visually-hidden" type="file" accept="application/pdf,.pdf" onChange={(event) => {
                chooseFile(event.target.files?.[0] ?? null)
                // Clear the input so choosing the same file again still fires a change.
                event.target.value = ''
              }}
              tabIndex={-1}
            />
            <div className="upload-options">
              <label className="select-field">
                <span>Report type</span>
                <select value={documentType} onChange={(event) => setDocumentType(event.target.value)}>
                  <option value="DDR">Daily drilling report</option>
                  <option value="WCR">Well completion report</option>
                  <option value="OTHER">Other engineering report</option>
                </select>
              </label>
              <button type="button" className="btn btn-primary" disabled={!file || uploading || running} onClick={() => void submit()}>
                {uploading ? <LoaderCircle size={15} className="spin" /> : <Upload size={15} />}
                {uploading ? 'Uploading…' : 'Ingest report'}
              </button>
            </div>
            {error && <div className="notice notice-error" role="alert">{error}</div>}
            <p className="footnote">Demo uploads attach to a synthetic Rajasthan context record. They do not change the six local offset wells or live alert scoring.</p>
          </section>

          <section className="card estate-panel" aria-labelledby="estate-title">
            <header className="card-header">
              <h2 id="estate-title">Stored reports</h2>
              <span className="card-meta tabular">{documents.data?.length ?? 0} on file</span>
            </header>
            {documents.isLoading && <div className="table-loading">{[0, 1, 2].map((item) => <i key={item} />)}</div>}
            <ul className="document-list">
              {documents.data?.slice(0, 8).map((document) => (
                <li key={document.id}>
                  <FileText size={15} strokeWidth={1.6} />
                  <span>
                    <strong className="mono">{document.filename}</strong>
                    <small>{document.document_type} · {document.page_count} page{document.page_count === 1 ? '' : 's'}</small>
                  </span>
                  <span className={`status-text status-${document.ingestion_status.toLowerCase()}`}>{sentenceCase(document.ingestion_status)}</span>
                </li>
              ))}
            </ul>
            {documents.data && documents.data.length > 8 && <p className="footnote">Showing the 8 most recent of {documents.data.length}.</p>}
          </section>
        </div>

        <div className="documents-column">
          <section className="card pipeline-panel" aria-labelledby="pipeline-title" aria-live="polite">
            <header className="card-header">
              <h2 id="pipeline-title">Ingestion</h2>
              <span className="card-meta mono">{job?.filename ?? 'No report submitted'}</span>
            </header>
            <ol className="pipeline-stages">
              {stages.map(([key, label]) => {
                const state = job?.stages[key] ?? 'pending'
                return (
                  <li key={key} className={`stage-${state}`}>
                    <span className="stage-marker"><StageIcon state={state} /></span>
                    <strong>{label}</strong>
                    <small>{stageStateLabel[state]}</small>
                  </li>
                )
              })}
            </ol>
            {!job && <p className="footnote pipeline-empty">Submit a report to follow it through reading, extraction, evidence checks and indexing.</p>}
            {job?.status === 'failed' && <div className="notice notice-error"><strong>Ingestion stopped.</strong> {job.error_message}</div>}
            {job?.status === 'completed' && (
              <div className="notice notice-success">
                <Check size={16} strokeWidth={2.4} />
                <span>
                  <strong>Report indexed.</strong> {job.page_count} pages · {job.chunk_count} searchable chunks · {job.events.length} validated event{job.events.length === 1 ? '' : 's'}
                </span>
                {job.cached_verified_extraction && <em className="tag">Verified demo cache</em>}
              </div>
            )}
          </section>

          <section className="card results-panel" aria-labelledby="results-title">
            <header className="card-header">
              <h2 id="results-title">Extracted events</h2>
              {job?.status === 'completed' && <span className="card-meta tabular">{job.events.length} validated</span>}
            </header>
            {job?.status === 'completed' && job.events.length > 0 ? (
              <div className="event-table">
                {job.events.map((event) => (
                  <article className="event-table-row" key={event.id}>
                    <div className="event-table-main">
                      <strong>{hazardLabel(event.hazard_type)}</strong>
                      <span>{event.formation_name}</span>
                      <span className="tabular">{formatInterval(event.start_md_m, event.end_md_m)}</span>
                      <span className={`severity-tag severity-${event.severity.toLowerCase()}`}>{sentenceCase(event.severity)}</span>
                    </div>
                    <p>{event.description}</p>
                    {event.evidence[0] ? (
                      <button type="button" className="source-chip" onClick={() => setEvidence(event.evidence[0])}>
                        <FileText size={14} strokeWidth={1.7} /> {event.evidence[0].filename} <em>p. {event.evidence[0].page_number}</em>
                      </button>
                    ) : (
                      <span className="notice notice-error">Rejected · no exact page evidence</span>
                    )}
                  </article>
                ))}
              </div>
            ) : (
              <div className="empty-state compact">
                <FileText size={20} strokeWidth={1.6} />
                <strong>No extracted events yet</strong>
                <span>An event appears here only after its quoted passage is found on the cited page.</span>
              </div>
            )}
          </section>
        </div>
      </div>
      {evidence && <SourceViewer evidence={evidence} onClose={() => setEvidence(null)} />}
    </section>
  )
}
