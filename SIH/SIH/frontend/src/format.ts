const hazardNames: Record<string, string> = {
  MUD_LOSS: 'Mud loss',
  STUCK_PIPE: 'Stuck pipe',
  KICK: 'Kick',
}

/** Human name for a hazard code, e.g. MUD_LOSS → "Mud loss". */
export function hazardLabel(value: string) {
  return hazardNames[value] ?? sentenceCase(value)
}

/** snake_case or UPPER_CASE → "Sentence case". */
export function sentenceCase(value: string) {
  const words = value.replaceAll('_', ' ').trim().toLowerCase()
  return words.charAt(0).toUpperCase() + words.slice(1)
}

/** Fixed-precision number with thousands separators: 3268.62 → "3,268.6". */
export function formatNumber(value: number | null | undefined, digits = 0) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return value.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

export function formatDepth(value: number | null | undefined, digits = 0) {
  return value === null || value === undefined ? '—' : `${formatNumber(value, digits)} m`
}

export function formatInterval(start: number, end: number | null | undefined) {
  return end === null || end === undefined || Math.round(end) === Math.round(start)
    ? `${formatNumber(start)} m`
    : `${formatNumber(start)}–${formatNumber(end)} m`
}

/** Seconds → "02:19". */
export function formatClock(totalSeconds: number) {
  const seconds = Math.max(0, Math.round(totalSeconds))
  return `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`
}

/** Live-signal keys carry their unit as a suffix; surface it as a readable label. */
export function signalLabel(key: string) {
  const units: [string, string][] = [
    ['_m3_per_sample', 'm³/sample'],
    ['_lpm', 'L/min'],
    ['_bar', 'bar'],
  ]
  for (const [suffix, unit] of units) {
    if (key.endsWith(suffix)) return { label: sentenceCase(key.slice(0, -suffix.length)), unit }
  }
  return { label: sentenceCase(key), unit: '' }
}

/** Shortens "NWIS-OFF-01" to "OFF-01" where space is tight. */
export function shortWellName(name: string) {
  return name.replace(/^NWIS-/, '')
}

/** Lithology fill used for a formation, following mud-log symbol conventions. */
export function lithologyClass(formationCode: string | undefined, index: number) {
  const byCode: Record<string, string> = {
    TIPAM: 'litho-sand',
    BARAIL: 'litho-interbed',
    KOPILI: 'litho-shale',
  }
  const fallback = ['litho-sand', 'litho-interbed', 'litho-shale']
  return (formationCode && byCode[formationCode.toUpperCase()]) ?? fallback[index % fallback.length]
}
