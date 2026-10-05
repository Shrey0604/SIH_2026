import { useEffect, useState } from 'react'
import { ExternalLink, X } from 'lucide-react'
import { apiBaseUrl } from '../api'
import { sentenceCase } from '../format'
import { claimEscape, useDialogFocus } from '../hooks/useDialogFocus'
import type { EventEvidence } from '../types'

type Props = {
  evidence: EventEvidence
  onClose: () => void
}

export function SourceViewer({ evidence, onClose }: Props) {
  const pageUrl = `${apiBaseUrl}/api/documents/${evidence.document_id}/page/${evidence.page_number}`
  const [imageState, setImageState] = useState<'loading' | 'ready' | 'failed'>('loading')
  const dialogRef = useDialogFocus<HTMLElement>()
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (claimEscape(event, dialogRef.current)) onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose, dialogRef])
  return (
    <div className="source-viewer-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="source-viewer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="source-title"
        ref={dialogRef}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="sheet-header">
          <div>
            <span className="sheet-kicker">Source page</span>
            <h3 id="source-title"><span className="mono-title">{evidence.filename}</span> <small>Page {evidence.page_number}</small></h3>
          </div>
          <div className="source-actions">
            <a className="btn btn-quiet" href={pageUrl} target="_blank" rel="noreferrer"><ExternalLink size={14} /> Open full page</a>
            <button type="button" className="icon-button" onClick={onClose} aria-label="Close source viewer" data-autofocus><X size={17} /></button>
          </div>
        </header>
        <div className="source-viewer-body">
          <div className={`source-page-frame is-${imageState}`}>
            {imageState === 'failed' ? (
              <p className="quiet-copy">The page image could not be rendered. Use “Open full page” to try it directly.</p>
            ) : (
              <img
                src={pageUrl}
                alt={`${evidence.filename}, page ${evidence.page_number}`}
                onLoad={() => setImageState('ready')}
                onError={() => setImageState('failed')}
              />
            )}
          </div>
          <aside>
            <h4>Cited passage</h4>
            <blockquote>{evidence.evidence_text}</blockquote>
            <dl className="fact-list">
              <div><dt>Document</dt><dd>{evidence.document_title}</dd></div>
              <div><dt>Page</dt><dd className="tabular">{evidence.page_number}</dd></div>
              <div><dt>Data source</dt><dd>{sentenceCase(evidence.source_kind)}</dd></div>
            </dl>
            <p className="footnote">Rendered directly from the stored PDF page, not re-typed.</p>
          </aside>
        </div>
      </section>
    </div>
  )
}
