export type ToastLevel = 'info' | 'success' | 'error'

// ─── Message log: every toast is kept, so one that vanished can still be read ──
type Logged = { at: number; level: ToastLevel; message: string }
const LOG_KEY = 'tggr.messages'
const LOG_MAX = 200
let log: Logged[] = (() => { try { return JSON.parse(localStorage.getItem(LOG_KEY) || '[]') } catch { return [] } })()
let unseenErrors = 0
const onLogChange: (() => void)[] = []

function record(level: ToastLevel, message: string) {
  log.push({ at: Date.now(), level, message })
  if (log.length > LOG_MAX) log = log.slice(-LOG_MAX)
  if (level === 'error') unseenErrors++
  try { localStorage.setItem(LOG_KEY, JSON.stringify(log)) } catch { /* storage blocked: kept for this visit */ }
  onLogChange.forEach(f => f())
}

const esc = (t: string) => t.replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!)
const when = (t: number) => {
  const d = new Date(t), today = new Date().toDateString() === d.toDateString()
  return today ? d.toLocaleTimeString() : d.toLocaleString()
}

/** The toolbar button that opens the log; marked while there are errors you haven't looked at. */
export function wireMessageLog(btn: HTMLElement) {
  const mark = () => {
    btn.classList.toggle('msglog-unseen', unseenErrors > 0)
    btn.title = unseenErrors ? `Messages: ${unseenErrors} new error${unseenErrors === 1 ? '' : 's'}` : 'Messages: everything tggr has told you'
    btn.setAttribute('aria-label', btn.title)
  }
  onLogChange.push(mark); mark()
  let panel: HTMLElement | null = null
  const close = () => { panel?.remove(); panel = null; document.removeEventListener('mousedown', outside, true); document.removeEventListener('keydown', key) }
  const outside = (e: Event) => { if (panel && !panel.contains(e.target as Node) && !btn.contains(e.target as Node)) close() }
  const key = (e: KeyboardEvent) => { if (e.key === 'Escape') close() }
  const render = () => {
    if (!panel) return
    const rows = [...log].reverse().map(m => `<li class="msglog-${m.level}"><time>${esc(when(m.at))}</time><span>${esc(m.message)}</span></li>`).join('')
    panel.innerHTML = `<div class="msglog-h"><b>Messages</b><span>${log.length ? `${log.length}, newest first` : ''}</span>
      ${log.length ? '<button type="button" class="btn btn-ghost btn-sm msglog-clear">Clear</button>' : ''}</div>
      ${rows ? `<ul>${rows}</ul>` : '<p class="msglog-empty">No messages yet.</p>'}`
    panel.querySelector('.msglog-clear')?.addEventListener('click', () => {
      log = []; try { localStorage.removeItem(LOG_KEY) } catch { /* storage blocked */ }
      render()
    })
  }
  onLogChange.push(() => { if (panel) { unseenErrors = 0; mark(); render() } })
  btn.addEventListener('click', () => {
    if (panel) { close(); return }
    panel = document.createElement('div')
    panel.className = 'msglog'
    document.body.appendChild(panel)
    const r = btn.getBoundingClientRect()
    panel.style.top = `${r.bottom + 6}px`
    panel.style.right = `${Math.max(8, window.innerWidth - r.right)}px`
    unseenErrors = 0; mark(); render()
    document.addEventListener('mousedown', outside, true); document.addEventListener('keydown', key)
  })
}

let muted = false
/** After the session expires, failures are the banner's job, not a toast per call. */
export function muteErrorToasts() { muted = true }

/** An error stays until clicked (unless given a duration), so there's time to read it. Any toast closes on a click. */
export function toast(message: string, level: ToastLevel = 'info', duration?: number): void {
  if (muted && level === 'error') return
  record(level, message)
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
