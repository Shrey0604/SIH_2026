import { useQuery } from '@tanstack/react-query'
import {
  BookOpenText,
  Database,
  FileText,
  Gauge,
  MapPinned,
  TextSearch,
  Moon,
  Pause,
  Play,
  RotateCcw,
  Sun,
} from 'lucide-react'
import { apiBaseUrl } from '../api'
import { formatClock, formatDepth } from '../format'
import type { Theme } from '../theme'
import type { LivePayload, ReplayStatus } from '../types'

type Props = {
  path: string
  navigate: (path: string) => void
  payload: LivePayload | null
  transport: string
  control: (action: 'start' | 'pause' | 'resume' | 'reset') => void
  theme: Theme
  onToggleTheme: () => void
  onOpenCopilot: () => void
  children: React.ReactNode
}

const navigation = [
  { path: '/live', label: 'Live', icon: Gauge },
  { path: '/wells', label: 'Wells', icon: MapPinned },
  { path: '/knowledge', label: 'Knowledge', icon: BookOpenText },
  { path: '/documents', label: 'Documents', icon: FileText },
]

const replayLabels: Record<ReplayStatus, string> = {
  ready: 'Ready',
  running: 'Live replay',
  paused: 'Paused',
  complete: 'Replay complete',
}

const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform)

async function getHealth() {
  const response = await fetch(`${apiBaseUrl}/api/health`)
  if (!response.ok) throw new Error('Backend unavailable')
  return response.json() as Promise<{
    database: string
    data_backend: string
    configured_data_backend: string
    data_fallback_reason: string | null
  }>
}

function Wordmark() {
  return (
    <svg className="wordmark-glyph" viewBox="0 0 32 32" aria-hidden="true">
      <rect x="14" y="5" width="4" height="22" rx="1" className="glyph-bore" />
      <rect x="14" y="17" width="4" height="10" rx="1" className="glyph-ahead" />
      <path d="M7 14.5 11.5 17 7 19.5z" className="glyph-bit" />
    </svg>
  )
}

export function AppShell({
  path,
  navigate,
  payload,
  transport,
  control,
  theme,
  onToggleTheme,
  onOpenCopilot,
  children,
}: Props) {
  const health = useQuery({ queryKey: ['health'], queryFn: getHealth, refetchInterval: 15_000 })
  const replayStatus: ReplayStatus = payload?.replay.status ?? 'ready'
  const isRunning = replayStatus === 'running'
  const isPaused = replayStatus === 'paused'
  const sampleCount = payload?.replay.sample_count ?? 0
  const progress = sampleCount > 1 ? (payload?.replay.sequence ?? 0) / (sampleCount - 1) : 0
  const fallbackReason = health.data?.data_fallback_reason
  // Only surface the data backend when it is degraded; a healthy backend needs no top-bar label.
  const backendLabel = health.isError ? 'API offline' : fallbackReason ? 'Local fallback' : null
  const transportLabel = transport === 'websocket' ? 'Streaming' : transport === 'rest' ? 'Polling' : 'Connecting'

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">Skip to content</a>
      <aside className="side-rail" aria-label="Primary navigation">
        <a
          className="rail-mark"
          href="/live"
          aria-label="NWIS live view"
          onClick={(event) => {
            event.preventDefault()
            navigate('/live')
          }}
        >
          <Wordmark />
        </a>
        <nav>
          {navigation.map((item) => {
            const Icon = item.icon
            const active = path === item.path || path.startsWith(`${item.path}/`)
            return (
              <a
                key={item.path}
                href={item.path}
                className={active ? 'rail-item active' : 'rail-item'}
                aria-current={active ? 'page' : undefined}
                onClick={(event) => {
                  if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return
                  event.preventDefault()
                  navigate(item.path)
                }}
              >
                <span className="rail-icon"><Icon size={19} strokeWidth={1.7} /></span>
                <span className="rail-label">{item.label}</span>
              </a>
            )
          })}
        </nav>
        <button
          type="button"
          className="rail-theme"
          onClick={onToggleTheme}
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} appearance`}
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} appearance`}
        >
          {theme === 'dark' ? <Sun size={17} strokeWidth={1.7} /> : <Moon size={17} strokeWidth={1.7} />}
        </button>
      </aside>

      <header className="top-bar">
        <div className="well-context">
          <span className="product-name">NWIS</span>
          <span className="well-id">{payload?.active_well.name ?? 'NWIS-ACT-01'}</span>
          <span className="well-readout" aria-live="off">
            <span>{payload?.current_formation?.formation_name ?? '—'}</span>
            <span className="tabular">{formatDepth(payload?.sample.md_m, 1)}</span>
          </span>
        </div>

        <div className="transport" role="group" aria-label="Replay controls">
          <span className={`replay-state replay-${replayStatus}`}>
            <i aria-hidden="true" />
            {replayLabels[replayStatus]}
          </span>
          <div className="transport-buttons">
            <button
              type="button"
              className="transport-button transport-play"
              onClick={() => control(isPaused ? 'resume' : 'start')}
              disabled={isRunning}
              title={isPaused ? 'Resume replay' : 'Start replay'}
              aria-label={isPaused ? 'Resume replay' : 'Start replay'}
            >
              <Play size={13} fill="currentColor" /> <span className="transport-label">{isPaused ? 'Resume' : 'Start'}</span>
            </button>
            <button
              type="button"
              className="transport-button"
              onClick={() => control('pause')}
              disabled={!isRunning}
              title="Pause replay"
              aria-label="Pause replay"
            >
              <Pause size={13} fill="currentColor" /> <span className="transport-label">Pause</span>
            </button>
            <button type="button" className="transport-button" onClick={() => control('reset')} title="Reset replay to the first sample" aria-label="Reset replay">
              <RotateCcw size={13} /> <span className="transport-label">Reset</span>
            </button>
          </div>
          <div
            className="replay-progress"
            role="progressbar"
            aria-label="Replay position"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(progress * 100)}
          >
            <span className="progress-track"><i style={{ transform: `scaleX(${progress})` }} /></span>
            <span className="progress-clock tabular">
              {formatClock(payload?.sample.timestamp_offset_s ?? 0)}
              <small> / {formatClock(Math.max(0, sampleCount - 1))}</small>
            </span>
          </div>
        </div>

        <div className="system-cluster">
          <span
            className={`system-status transport-status ${transport === 'rest' ? 'is-degraded' : ''}`}
            title={`Live transport: ${transport === 'websocket' ? 'WebSocket' : transport === 'rest' ? 'REST polling fallback' : 'connecting'}`}
          >
            <i aria-hidden="true" /> {transportLabel}
          </span>
          {backendLabel && (
            <span className="system-status is-degraded" title={fallbackReason ?? `No response from ${apiBaseUrl}`}>
              <Database size={13} strokeWidth={1.8} /> {backendLabel}
            </span>
          )}
          <button type="button" className="ask-button" onClick={onOpenCopilot} title="Ask questions of historical well evidence" aria-label="Ask NWIS">
            <TextSearch size={16} strokeWidth={1.9} aria-hidden="true" />
            <span>Ask NWIS</span>
            <kbd>{isMac ? '⌘' : 'Ctrl'} K</kbd>
          </button>
        </div>
      </header>

      <main id="main" className="workspace" tabIndex={-1}>
        {children}
      </main>
    </div>
  )
}
