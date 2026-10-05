import { useEffect, useRef, useState } from 'react'
import * as maplibregl from 'maplibre-gl'
import type { GeoJSONSource, Marker, StyleSpecification } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { formatNumber } from '../format'
import type { Theme } from '../theme'
import type { Well } from '../types'
import { WellDrawer } from './WellDrawer'

type MapView = 'active' | 'india'

type Props = {
  wells: Well[]
  contextWells: Well[]
  localOffsetCount: number
  totalWellCount: number
  radiusKm: number
  onRadiusChange: (radius: number) => void
  replaying: boolean
  supportingWellIds: string[]
  theme: Theme
  onSelectEvent: (eventId: string) => void
}

const overlayColors = {
  dark: {
    radius: '#f1efea',
    cluster: '#2a2c30',
    clusterStroke: '#8a8882',
    clusterText: '#f1efea',
    context: '#5d5f63',
    contextStroke: '#d4d1ca',
    boundary: '#b0aea8',
    fallbackBackground: '#141517',
    fallbackGrid: '#2a2c30',
  },
  light: {
    radius: '#151617',
    cluster: '#ffffff',
    clusterStroke: '#6b6c6f',
    clusterText: '#151617',
    context: '#8d8e91',
    contextStroke: '#ffffff',
    boundary: '#46474a',
    fallbackBackground: '#ecece8',
    fallbackGrid: '#d6d6d1',
  },
} satisfies Record<Theme, Record<string, string>>

const fallbackGrid = {
  type: 'FeatureCollection' as const,
  features: [
    ...[16, 20, 24, 28].map((latitude) => ({
      type: 'Feature' as const,
      properties: {},
      geometry: { type: 'LineString' as const, coordinates: [[68, latitude], [97, latitude]] },
    })),
    ...[72, 78, 84, 90, 96].map((longitude) => ({
      type: 'Feature' as const,
      properties: {},
      geometry: { type: 'LineString' as const, coordinates: [[longitude, 14], [longitude, 30]] },
    })),
  ],
}

function fallbackStyle(theme: Theme): StyleSpecification {
  const colors = overlayColors[theme]
  return {
    version: 8,
    sources: { grid: { type: 'geojson', data: fallbackGrid } },
    layers: [
      { id: 'background', type: 'background', paint: { 'background-color': colors.fallbackBackground } },
      {
        id: 'grid-lines',
        type: 'line',
        source: 'grid',
        paint: { 'line-color': colors.fallbackGrid, 'line-width': 1, 'line-opacity': 0.8 },
      },
    ],
  }
}

const configuredStyle: string = import.meta.env.VITE_OPENFREEMAP_STYLE_URL ?? 'https://tiles.openfreemap.org/styles/liberty'

/** OpenFreeMap ships matching light and dark styles; follow the app appearance when it is the configured provider. */
function basemapStyle(theme: Theme) {
  const match = configuredStyle.match(/^(https:\/\/tiles\.openfreemap\.org\/styles\/)(liberty|bright|positron|dark|fiord)\/?$/)
  return match ? `${match[1]}${theme === 'dark' ? 'dark' : 'positron'}` : configuredStyle
}

const officialBoundaryUrl = '/data/india-official-boundary.geojson'

function radiusPolygon(longitude: number, latitude: number, radiusKm: number) {
  const coordinates: [number, number][] = []
  const earthRadius = 6371.0088
  const angularDistance = radiusKm / earthRadius
  const lat = (latitude * Math.PI) / 180
  const lon = (longitude * Math.PI) / 180
  for (let bearingDegrees = 0; bearingDegrees <= 360; bearingDegrees += 6) {
    const bearing = (bearingDegrees * Math.PI) / 180
    const targetLat = Math.asin(
      Math.sin(lat) * Math.cos(angularDistance)
      + Math.cos(lat) * Math.sin(angularDistance) * Math.cos(bearing),
    )
    const targetLon = lon + Math.atan2(
      Math.sin(bearing) * Math.sin(angularDistance) * Math.cos(lat),
      Math.cos(angularDistance) - Math.sin(lat) * Math.sin(targetLat),
    )
    coordinates.push([(targetLon * 180) / Math.PI, (targetLat * 180) / Math.PI])
  }
  return {
    type: 'Feature' as const,
    properties: {},
    geometry: { type: 'Polygon' as const, coordinates: [coordinates] },
  }
}

function contextFeatureCollection(wells: Well[]) {
  return {
    type: 'FeatureCollection' as const,
    features: wells.map((well) => ({
      type: 'Feature' as const,
      id: well.id,
      properties: {
        id: well.id,
        name: well.name,
        region: well.field_name,
        well_scope: well.well_scope,
      },
      geometry: {
        type: 'Point' as const,
        coordinates: [well.longitude, well.latitude],
      },
    })),
  }
}

export function OffsetWellMap({
  wells,
  contextWells,
  localOffsetCount,
  totalWellCount,
  radiusKm,
  onRadiusChange,
  replaying,
  supportingWellIds,
  theme,
  onSelectEvent,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  // Style readiness is separate from source/tile loading. Adding one source
  // makes isStyleLoaded() false while its worker runs, but other layers can
  // (and must) still be installed in the same pass.
  const styleReadyRef = useRef(false)
  const fallbackAppliedRef = useRef(false)
  const appliedThemeRef = useRef(theme)
  const markersRef = useRef<Marker[]>([])
  const contextPopupRef = useRef<maplibregl.Popup | null>(null)
  const [viewMode, setViewMode] = useState<MapView>('active')
  const [selectedWell, setSelectedWell] = useState<Well | null>(null)
  const [basemapAvailable, setBasemapAvailable] = useState(true)
  const dataRef = useRef({ wells, contextWells, radiusKm, viewMode, theme })
  const supportingKey = [...supportingWellIds].sort().join(',')
  const selectedWellId = selectedWell?.id ?? ''
  dataRef.current = { wells, contextWells, radiusKm, viewMode, theme }

  const renderRadius = () => {
    const map = mapRef.current
    const active = dataRef.current.wells.find((well) => well.is_active)
    if (!map || !active || !styleReadyRef.current) return
    const colors = overlayColors[dataRef.current.theme]
    const data = radiusPolygon(active.longitude, active.latitude, dataRef.current.radiusKm)
    const source = map.getSource('radius') as GeoJSONSource | undefined
    if (source) source.setData(data)
    else {
      map.addSource('radius', { type: 'geojson', data })
      map.addLayer({
        id: 'radius-fill',
        type: 'fill',
        source: 'radius',
        paint: { 'fill-color': colors.radius, 'fill-opacity': 0.04 },
      })
      map.addLayer({
        id: 'radius-line',
        type: 'line',
        source: 'radius',
        paint: {
          'line-color': colors.radius,
          'line-width': 1.2,
          'line-opacity': 0.55,
          'line-dasharray': [3, 3],
        },
      })
    }
    const visibility = dataRef.current.viewMode === 'active' ? 'visible' : 'none'
    map.setLayoutProperty('radius-fill', 'visibility', visibility)
    map.setLayoutProperty('radius-line', 'visibility', visibility)
  }

  const renderContextWells = () => {
    const map = mapRef.current
    if (!map || !styleReadyRef.current) return
    const colors = overlayColors[dataRef.current.theme]
    const data = contextFeatureCollection(dataRef.current.contextWells)
    const source = map.getSource('context-wells') as GeoJSONSource | undefined
    if (source) {
      source.setData(data)
      return
    }
    map.addSource('context-wells', {
      type: 'geojson',
      data,
      cluster: true,
      clusterMaxZoom: 8,
      clusterRadius: 42,
    })
    map.addLayer({
      id: 'context-clusters',
      type: 'circle',
      source: 'context-wells',
      filter: ['has', 'point_count'],
      paint: {
        'circle-color': colors.cluster,
        'circle-opacity': 0.95,
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 3, 10, 7, 14, 9, 17],
        'circle-stroke-color': colors.clusterStroke,
        'circle-stroke-width': 1,
      },
    })
    map.addLayer({
      id: 'context-cluster-count',
      type: 'symbol',
      source: 'context-wells',
      filter: ['has', 'point_count'],
      layout: {
        'text-field': ['get', 'point_count_abbreviated'],
        'text-size': 11,
        'text-allow-overlap': false,
      },
      paint: { 'text-color': colors.clusterText },
    })
    map.addLayer({
      id: 'context-unclustered',
      type: 'circle',
      source: 'context-wells',
      filter: ['!', ['has', 'point_count']],
      paint: {
        'circle-color': colors.context,
        'circle-opacity': 0.95,
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 3, 3, 7, 4, 10, 5.5],
        'circle-stroke-color': colors.contextStroke,
        'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 3, 0.8, 10, 1.4],
      },
    })
  }

  const renderOfficialBoundary = () => {
    const map = mapRef.current
    if (!map || !styleReadyRef.current || map.getSource('india-official-boundary')) return
    map.addSource('india-official-boundary', {
      type: 'geojson',
      data: officialBoundaryUrl,
    })
    map.addLayer({
      id: 'india-official-boundary-line',
      type: 'line',
      source: 'india-official-boundary',
      paint: {
        'line-color': overlayColors[dataRef.current.theme].boundary,
        'line-width': ['interpolate', ['linear'], ['zoom'], 3, 1.4, 7, 1.1, 11, 0.8],
        'line-opacity': ['interpolate', ['linear'], ['zoom'], 3, 0.9, 7, 0.7, 11, 0.4],
      },
    })
  }

  useEffect(() => {
    if (!containerRef.current) return
    const active = wells.find((well) => well.is_active)
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: basemapStyle(dataRef.current.theme),
      center: active ? [active.longitude, active.latitude] : [71.3924, 25.7552],
      zoom: 10.5,
      attributionControl: false,
      // On touch screens one finger scrolls the page and two fingers move the map,
      // so the map never traps the reader mid-scroll. Desktop keeps normal gestures.
      cooperativeGestures: window.matchMedia('(pointer: coarse)').matches,
    })
    mapRef.current = map
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right')
    map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right')
    // Keep the credit one tap away (the ⓘ button) instead of covering the radius ring on load.
    map.once('load', () => {
      containerRef.current?.querySelector('.maplibregl-ctrl-attrib')?.classList.remove('maplibregl-compact-show')
    })
    const updateZoomBand = () => {
      const container = containerRef.current
      if (!container) return
      const zoom = map.getZoom()
      // Keep camera state on the map-owned node; React replaces the panel's
      // className when the view mode or fallback state changes.
      container.dataset.zoomBand = zoom < 6.5 ? 'country' : zoom < 9 ? 'regional' : 'local'
    }
    updateZoomBand()
    map.on('zoom', updateZoomBand)
    let basemapSourceIds = new Set<string>()
    const renderMapData = () => {
      styleReadyRef.current = true
      basemapSourceIds = new Set(Object.keys(map.getStyle().sources))
      renderOfficialBoundary()
      renderRadius()
      renderContextWells()
    }
    // Reinstall all overlays after initial load, an appearance change, and a fallback style swap.
    map.on('style.load', renderMapData)
    map.on('click', async (event) => {
      const layers = ['context-clusters', 'context-unclustered'].filter((id) => map.getLayer(id))
      if (!layers.length) return
      const feature = map.queryRenderedFeatures(event.point, { layers })[0]
      if (!feature) return
      if (feature.layer.id === 'context-clusters') {
        const clusterId = Number(feature.properties?.cluster_id)
        const source = map.getSource('context-wells') as GeoJSONSource
        const zoom = await source.getClusterExpansionZoom(clusterId)
        const point = feature.geometry.type === 'Point' ? feature.geometry.coordinates : null
        if (point) map.easeTo({ center: [point[0], point[1]], zoom, duration: 500 })
      }
    })
    map.on('mousemove', (event) => {
      const layers = ['context-clusters', 'context-unclustered'].filter((id) => map.getLayer(id))
      const feature = layers.length ? map.queryRenderedFeatures(event.point, { layers })[0] : undefined
      map.getCanvas().style.cursor = feature ? 'pointer' : ''
      if (!feature || feature.layer.id !== 'context-unclustered' || feature.geometry.type !== 'Point') {
        contextPopupRef.current?.remove()
        return
      }
      const coordinates = feature.geometry.coordinates
      const popup = contextPopupRef.current ?? new maplibregl.Popup({
        closeButton: false,
        closeOnClick: false,
        offset: 10,
        className: 'well-map-popup',
      })
      contextPopupRef.current = popup
      popup
        .setLngLat([coordinates[0], coordinates[1]])
        .setHTML(`<strong>${feature.properties?.name}</strong><span>${feature.properties?.region} · context well</span>`)
        .addTo(map)
    })
    map.on('error', (event) => {
      if (fallbackAppliedRef.current) return
      const sourceId = 'sourceId' in event ? String(event.sourceId) : undefined
      // Boundary/well/font errors must not discard the working basemap.
      if (styleReadyRef.current && (!sourceId || !basemapSourceIds.has(sourceId))) return
      console.warn('NWIS basemap unavailable; switching to the offline grid.', sourceId ?? '', event.error)
      fallbackAppliedRef.current = true
      styleReadyRef.current = false
      setBasemapAvailable(false)
      map.setStyle(fallbackStyle(dataRef.current.theme), { diff: false })
    })
    return () => {
      styleReadyRef.current = false
      markersRef.current.forEach((marker) => marker.remove())
      markersRef.current = []
      contextPopupRef.current?.remove()
      map.remove()
      mapRef.current = null
    }
    // The map is intentionally created once; live data is applied by the next effects.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (!map || appliedThemeRef.current === theme) return
    appliedThemeRef.current = theme
    styleReadyRef.current = false
    contextPopupRef.current?.remove()
    map.setStyle(fallbackAppliedRef.current ? fallbackStyle(theme) : basemapStyle(theme), { diff: false })
  }, [theme])

  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    const supportingIds = new Set(supportingKey ? supportingKey.split(',') : [])
    const popups: maplibregl.Popup[] = []
    markersRef.current.forEach((marker) => marker.remove())
    markersRef.current = wells.map((well) => {
      // MapLibre exclusively owns the outer element's positioning/transform.
      // The inner button owns the fixed-pixel symbol, rotation, and pulse.
      const anchorElement = document.createElement('div')
      anchorElement.className = 'well-marker-anchor'
      const markerElement = document.createElement('button')
      markerElement.type = 'button'
      const classes = ['well-marker', well.is_active ? 'active-well' : 'offset-well']
      if (well.is_active && replaying) classes.push('replaying')
      if (!well.is_active && well.event_count) classes.push('has-event')
      if (supportingIds.has(well.id)) classes.push('supporting-well')
      if (selectedWellId === well.id) classes.push('selected-well')
      markerElement.className = classes.join(' ')
      markerElement.title = well.is_active
        ? `${well.name} · active well`
        : `${well.name} · ${well.distance_km.toFixed(2)} km · ${well.event_count} events`
      markerElement.setAttribute('aria-label', markerElement.title)
      const popup = new maplibregl.Popup({
        closeButton: false,
        closeOnClick: false,
        offset: 16,
        className: 'well-map-popup',
      }).setHTML(
        well.is_active
          ? `<strong>${well.name}</strong><span>Active well · drilling now</span>`
          : `<strong>${well.name}</strong><span>${formatNumber(well.distance_km, 2)} km away · ${well.event_count} relevant event${well.event_count === 1 ? '' : 's'}${supportingIds.has(well.id) ? '<br />Supports the current alert' : ''}</span>`,
      )
      popups.push(popup)
      markerElement.addEventListener('mouseenter', () => {
        popup.setLngLat([well.longitude, well.latitude]).addTo(map)
      })
      markerElement.addEventListener('mouseleave', () => popup.remove())
      markerElement.addEventListener('click', () => {
        if (!well.is_active) setSelectedWell(well)
        setViewMode('active')
        map.flyTo({ center: [well.longitude, well.latitude], zoom: 11, duration: 600 })
      })
      anchorElement.appendChild(markerElement)
      return new maplibregl.Marker({ element: anchorElement })
        .setLngLat([well.longitude, well.latitude])
        .addTo(map)
    })
    renderContextWells()
    renderRadius()
    return () => {
      popups.forEach((popup) => popup.remove())
      markersRef.current.forEach((marker) => marker.remove())
      markersRef.current = []
    }
  }, [contextWells, radiusKm, replaying, selectedWellId, supportingKey, viewMode, wells])

  useEffect(() => {
    const map = mapRef.current
    const active = wells.find((well) => well.is_active)
    if (!map || !active) return
    if (viewMode === 'india' && contextWells.length) {
      const bounds = new maplibregl.LngLatBounds()
      ;[...contextWells, ...wells].forEach((well) => bounds.extend([well.longitude, well.latitude]))
      map.fitBounds(bounds, { padding: 48, maxZoom: 5.2, duration: 650 })
      renderRadius()
      return
    }
    const latitudeDelta = radiusKm / 111.32
    const longitudeDelta = radiusKm / (111.32 * Math.cos((active.latitude * Math.PI) / 180))
    map.fitBounds(
      [
        [active.longitude - longitudeDelta, active.latitude - latitudeDelta],
        [active.longitude + longitudeDelta, active.latitude + latitudeDelta],
      ],
      { padding: { top: 64, bottom: 48, left: 40, right: 40 }, maxZoom: 11, duration: 600 },
    )
    renderRadius()
  }, [contextWells, radiusKm, viewMode, wells])

  const offsetsInRadius = wells.filter((well) => !well.is_active).length

  return (
    <section
      className={`panel map-panel map-mode-${viewMode} ${basemapAvailable ? '' : 'basemap-fallback'}`}
      aria-labelledby="map-title"
    >
      <header className="panel-header">
        <div className="panel-title">
          <h2 id="map-title">{viewMode === 'active' ? 'Offset wells' : 'Historical well estate'}</h2>
          <span className="panel-meta">
            {viewMode === 'active'
              ? `Rajasthan operations block · ${wells.length ? offsetsInRadius : localOffsetCount} within ${radiusKm} km`
              : `${totalWellCount} wells across India`}
          </span>
        </div>
        <div className="panel-tools">
          <div className="segmented" role="group" aria-label="Map view">
            <button type="button" aria-pressed={viewMode === 'active'} className={viewMode === 'active' ? 'selected' : ''} onClick={() => setViewMode('active')}>Active Area</button>
            <button type="button" aria-pressed={viewMode === 'india'} className={viewMode === 'india' ? 'selected' : ''} onClick={() => setViewMode('india')}>India Overview</button>
          </div>
        </div>
      </header>
      <div className="map-frame">
        <div className="map-canvas" ref={containerRef} />
        {viewMode === 'active' && (
          <div className="map-float map-radius segmented" role="group" aria-label="Offset search radius">
            {[2, 5, 10].map((radius) => (
              <button
                type="button"
                aria-pressed={radiusKm === radius}
                className={radiusKm === radius ? 'selected' : ''}
                onClick={() => onRadiusChange(radius)}
                key={radius}
              >{radius} km</button>
            ))}
          </div>
        )}
        {!basemapAvailable && <div className="map-fallback" role="status">Basemap offline · well positions are still exact</div>}
        <div className="map-legend">
          {viewMode === 'active' ? (
            <>
              <span><i className="legend-active" /> Active well</span>
              <span><i className="legend-offset" /> Offset well</span>
              <span><i className="legend-event" /> Supports alert</span>
            </>
          ) : (
            <>
              <span><i className="legend-active" /> Active area</span>
              <span><i className="legend-context" /> Context well</span>
              <span><i className="legend-cluster" /> Cluster</span>
              <span><i className="legend-boundary" /> India boundary</span>
            </>
          )}
        </div>
        {viewMode === 'india' && (
          <a
            className="boundary-source"
            href="https://surveyofindia.gov.in/pages/public-awareness"
            target="_blank"
            rel="noreferrer"
          >
            Boundary: Survey of India, 1:16M
          </a>
        )}
        {selectedWell && <WellDrawer well={selectedWell} onClose={() => setSelectedWell(null)} onSelectEvent={onSelectEvent} />}
      </div>
    </section>
  )
}
