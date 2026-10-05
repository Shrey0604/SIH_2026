import { useCallback, useEffect, useState } from 'react'

export type Theme = 'dark' | 'light'

const storageKey = 'nwis-theme'
const themeColor: Record<Theme, string> = { dark: '#111213', light: '#f0f0ed' }

export function readStoredTheme(): Theme {
  try {
    return window.localStorage.getItem(storageKey) === 'light' ? 'light' : 'dark'
  } catch {
    return 'dark'
  }
}

export function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme
  document.documentElement.style.colorScheme = theme
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', themeColor[theme])
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(readStoredTheme)
  useEffect(() => {
    applyTheme(theme)
    try {
      window.localStorage.setItem(storageKey, theme)
    } catch {
      // Storage can be unavailable (private mode); the theme still applies for this session.
    }
  }, [theme])
  const toggleTheme = useCallback(() => setTheme((current) => (current === 'dark' ? 'light' : 'dark')), [])
  return { theme, toggleTheme }
}
