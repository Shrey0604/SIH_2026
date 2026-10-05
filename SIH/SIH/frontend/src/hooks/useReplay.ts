import { useCallback, useEffect, useRef, useState } from 'react'
import { apiBaseUrl, controlTelemetry, getCurrentTelemetry, getNextTelemetry } from '../api'
import type { LivePayload, TelemetrySample } from '../types'

type ReplayAction = 'start' | 'pause' | 'resume' | 'reset'
type Transport = 'connecting' | 'websocket' | 'rest'

function websocketUrl(radiusKm: number) {
  const base = apiBaseUrl.replace(/^http/, 'ws')
  return `${base}/api/ws/telemetry/active-01?radius_km=${radiusKm}`
}

/** 1 s, 2 s, 4 s … capped, so a restarting API is picked up quickly without hammering it. */
function backoff(attempt: number, capMs: number) {
  return Math.min(capMs, 1000 * 2 ** Math.min(attempt, 4))
}

export function useReplay(radiusKm: number) {
  const [payload, setPayload] = useState<LivePayload | null>(null)
  const [history, setHistory] = useState<TelemetrySample[]>([])
  const [transport, setTransport] = useState<Transport>('connecting')
  const [error, setError] = useState<string | null>(null)
  const socketRef = useRef<WebSocket | null>(null)

  const acceptPayload = useCallback((next: LivePayload) => {
    setPayload(next)
    setError(null)
    setHistory((current) => {
      if (next.replay.status === 'ready') return [next.sample]
      const withoutDuplicate = current.filter((sample) => sample.seq !== next.sample.seq)
      return [...withoutDuplicate, next.sample].sort((a, b) => a.seq - b.seq).slice(-120)
    })
  }, [])

  useEffect(() => {
    let disposed = false
    let loadTimer: number | undefined
    let reconnectTimer: number | undefined
    let loadAttempts = 0
    let socketAttempts = 0
    setTransport('connecting')

    // The API can come up after the page (make dev starts both at once) or restart
    // mid-demo, so the first snapshot is retried until it arrives.
    const loadCurrent = () => {
      getCurrentTelemetry(radiusKm).then((next) => {
        if (!disposed) acceptPayload(next)
      }).catch((reason: unknown) => {
        if (disposed) return
        setError(reason instanceof Error ? reason.message : 'Backend unavailable')
        loadAttempts += 1
        loadTimer = window.setTimeout(loadCurrent, backoff(loadAttempts, 8000))
      })
    }
    loadCurrent()

    if (import.meta.env.VITE_FORCE_REST === 'true') {
      setTransport('rest')
      return () => {
        disposed = true
        window.clearTimeout(loadTimer)
      }
    }

    const connect = () => {
      const socket = new WebSocket(websocketUrl(radiusKm))
      socketRef.current = socket
      socket.onopen = () => {
        if (disposed) return
        socketAttempts = 0
        setTransport('websocket')
      }
      socket.onmessage = (event) => {
        if (!disposed) acceptPayload(JSON.parse(String(event.data)) as LivePayload)
      }
      // onerror is always followed by onclose; reconnect from one place.
      socket.onclose = () => {
        if (socketRef.current === socket) socketRef.current = null
        if (disposed) return
        setTransport('rest')
        socketAttempts += 1
        reconnectTimer = window.setTimeout(connect, backoff(socketAttempts, 15_000))
      }
    }
    connect()

    return () => {
      disposed = true
      window.clearTimeout(loadTimer)
      window.clearTimeout(reconnectTimer)
      socketRef.current?.close()
      socketRef.current = null
    }
  }, [acceptPayload, radiusKm])

  useEffect(() => {
    if (transport !== 'rest' || payload?.replay.status !== 'running') return
    const timer = window.setInterval(() => {
      getNextTelemetry(radiusKm).then(acceptPayload).catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : 'Replay polling failed')
      })
    }, 1000)
    return () => window.clearInterval(timer)
  }, [acceptPayload, payload?.replay.status, radiusKm, transport])

  const control = useCallback(
    async (action: ReplayAction) => {
      const socket = socketRef.current
      if (socket?.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ action }))
        return
      }
      try {
        acceptPayload(await controlTelemetry(action, radiusKm))
        setTransport('rest')
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : 'Replay control failed')
      }
    },
    [acceptPayload, radiusKm],
  )

  return { payload, history, transport, error, control }
}
