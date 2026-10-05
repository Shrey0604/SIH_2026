import { useCallback, useEffect, useState } from 'react'
import { AppShell } from './components/AppShell'
import { LiveWorkspace } from './components/LiveWorkspace'
import { DocumentsWorkspace } from './components/DocumentsWorkspace'
import { KnowledgeWorkspace } from './components/KnowledgeWorkspace'
import { WellsWorkspace } from './components/WellsWorkspace'
import { CopilotDrawer } from './components/CopilotDrawer'
import { useReplay } from './hooks/useReplay'
import { useTheme } from './theme'

function usePathname() {
  const [path, setPath] = useState(window.location.pathname)
  useEffect(() => {
    if (window.location.pathname === '/') {
      window.history.replaceState({}, '', '/live')
      setPath('/live')
    }
    const onPopState = () => setPath(window.location.pathname)
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])
  const navigate = useCallback((next: string) => {
    if (next === window.location.pathname) return
    window.history.pushState({}, '', next)
    setPath(next)
    window.scrollTo(0, 0)
  }, [])
  return { path, navigate }
}

export default function App() {
  const { path, navigate } = usePathname()
  const { theme, toggleTheme } = useTheme()
  const [radiusKm, setRadiusKm] = useState(5)
  const [copilotOpen, setCopilotOpen] = useState(false)
  const replay = useReplay(radiusKm)
  const openCopilot = useCallback(() => setCopilotOpen(true), [])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setCopilotOpen((open) => !open)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  let content: React.ReactNode
  if (path === '/live') {
    content = (
      <LiveWorkspace
        radiusKm={radiusKm}
        onRadiusChange={setRadiusKm}
        payload={replay.payload}
        history={replay.history}
        error={replay.error}
        theme={theme}
        onOpenCopilot={openCopilot}
      />
    )
  } else if (path.startsWith('/wells')) {
    content = <WellsWorkspace onOpenLive={() => navigate('/live')} />
  } else if (path === '/knowledge') {
    content = <KnowledgeWorkspace />
  } else if (path === '/documents') {
    content = <DocumentsWorkspace />
  } else {
    content = (
      <section className="page route-missing">
        <p className="page-kicker">Page not found</p>
        <h1>Nothing is filed at {path}</h1>
        <p className="page-lede">The address may be mistyped, or the page may have moved.</p>
        <button type="button" className="btn btn-primary" onClick={() => navigate('/live')}>Go to live view</button>
      </section>
    )
  }

  return (
    <>
      <AppShell
        path={path}
        navigate={navigate}
        payload={replay.payload}
        transport={replay.transport}
        control={replay.control}
        theme={theme}
        onToggleTheme={toggleTheme}
        onOpenCopilot={openCopilot}
      >
        {content}
      </AppShell>
      {copilotOpen && (
        <CopilotDrawer
          payload={replay.payload}
          onClose={() => setCopilotOpen(false)}
        />
      )}
    </>
  )
}
