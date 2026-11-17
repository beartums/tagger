export type ToastLevel = 'info' | 'success' | 'error'

let muted = false
/** After the session expires, failures are the banner's job, not a toast per call. */
export function muteErrorToasts() { muted = true }

/** An error stays until clicked (unless given a duration), so there's time to read it. Any toast closes on a click. */
export function toast(message: string, level: ToastLevel = 'info', duration?: number): void {
  if (muted && level === 'error') return
  const container = getContainer()
  const el = document.createElement('div')
  el.className = `toast toast-${level}`
  el.textContent = message
  el.title = 'Click to close'
  el.addEventListener('click', () => dismiss(el), { once: true })
  container.appendChild(el)
  // Errors that stay can pile up (a lost connection fails every call): keep the newest few.
  const shown = container.querySelectorAll<HTMLElement>('.toast.toast-show')
  for (let i = 0; i < shown.length - 4; i++) dismiss(shown[i])
  requestAnimationFrame(() => requestAnimationFrame(() => el.classList.add('toast-show')))
  const ms = duration ?? (level === 'error' ? 0 : 3500)
  if (ms > 0) setTimeout(() => dismiss(el), ms)
}

function dismiss(el: HTMLElement) {
  el.classList.remove('toast-show')
  el.addEventListener('transitionend', () => el.remove(), { once: true })
}

function getContainer(): HTMLElement {
  let c = document.getElementById('toast-container')
  if (!c) {
    c = document.createElement('div')
    c.id = 'toast-container'
    document.body.appendChild(c)
  }
  return c
}
