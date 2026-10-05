import { useEffect, useRef } from 'react'

/**
 * Moves keyboard focus into a sheet or dialog when it opens and returns it to
 * the control that opened it when it closes.
 */
export function useDialogFocus<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  useEffect(() => {
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const target = ref.current?.querySelector<HTMLElement>('[data-autofocus]') ?? ref.current
    target?.focus({ preventScroll: true })
    return () => previous?.focus({ preventScroll: true })
  }, [])
  return ref
}

function isTopmostDialog(element: HTMLElement | null) {
  const dialogs = document.querySelectorAll('[aria-modal="true"]')
  return dialogs.length === 0 ? element === null : dialogs[dialogs.length - 1] === element
}

/**
 * Every layer listens for Escape on window. A layer closes only when it is the
 * topmost modal (pass null for a non-modal layer such as the map's well card)
 * and no other layer has already consumed this key press, so one Escape closes
 * one layer: source page → evidence sheet → well card.
 */
export function claimEscape(event: KeyboardEvent, element: HTMLElement | null) {
  if (event.key !== 'Escape' || event.defaultPrevented || !isTopmostDialog(element)) return false
  event.preventDefault()
  return true
}
