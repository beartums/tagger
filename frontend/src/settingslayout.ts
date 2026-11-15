// Settings page layout: a heading per section, each topic a card (title, what
// it's for, a status pill, fields as label | input rows, its Test in the
// card's footer), and which sections have unsaved changes. The markup stays
// in template.ts; this shapes it once at startup.
import { esc } from './util'

const SECTS: Record<string, [string, string]> = {
  libraries:    ['Libraries', 'What Tagger scans, and where its library roots are.'],
  layouts:      ['Layouts', 'Where files belong, and how tag values become folder and file names.'],
  groups:       ['Groups', 'Sets of tracks with their own lyrics lookups (and, under Layouts, their own layout).'],
  scanning:     ['Scanning', 'What a scan reads and skips, and when it runs on its own.'],
  integrations: ['Integrations', "Your own self-hosted music apps. Tagger reads Lidarr's naming rules and asks the players to rescan after it writes files."],
  metadata:     ['Metadata', 'Where tags, matches and lyrics come from. MusicBrainz needs no setup; these add to it.'],
  writing:      ['Writing', 'How changes reach your files: staging, cover art, volume tags, the trash.'],
  search:       ['Search', 'What the search box looks in.'],
}

// Card title -> [card key, what it's for]. The key matches its Test (data-source-test).
const CARDS: Record<string, [string, string]> = {
  'Lidarr':          ['lidarr', 'naming rules'],
  'Navidrome':       ['navidrome', 'rescan after writes'],
  'Music Assistant': ['music_assistant', 'rescan after writes'],
  'Player rescans':  ['rescans', 'all players'],
  'AcoustID':        ['acoustid', 'identify by fingerprint'],
  'Discogs':         ['discogs', 'second match source'],
  'LRCLIB (lyrics)': ['lrclib', 'lyrics'],
  'ReplayGain':      ['replaygain', 'even volume'],
}

export type PillKind = 'ok' | 'warn' | 'off'

/** Shape the Settings pane (once). */
export function shapeSettings(pane: HTMLElement) {
  for (const sect of pane.querySelectorAll<HTMLElement>('.settings-sect')) {
    const meta = SECTS[sect.dataset.sect!]
    if (meta) sect.insertAdjacentHTML('afterbegin', `<div class="sect-head"><h2>${esc(meta[0])}</h2><p>${esc(meta[1])}</p></div>`)
  }
  for (const card of pane.querySelectorAll<HTMLElement>('.settings-section')) {
    const titleEl = card.querySelector<HTMLElement>(':scope > .settings-section-title')
    if (!titleEl) continue
    const title = titleEl.textContent!.trim()
    const [key, what] = CARDS[title] ?? ['', '']
    if (key) card.dataset.card = key
    const head = document.createElement('div')
    head.className = 'card-h'
    head.innerHTML = `<h3>${esc(title.replace(' (lyrics)', ''))}</h3>${what ? `<span class="card-what">${esc(what)}</span>` : ''}<span class="pill" hidden></span>`
    const body = document.createElement('div')
    body.className = 'card-b'
    titleEl.remove()
    body.append(...card.childNodes)
    card.append(head, body)
    // One Test per card, in its footer, with its result just above.
    const tests = [...body.querySelectorAll<HTMLElement>('[data-source-test]')]
    if (tests.length) {
      const foot = document.createElement('div')
      foot.className = 'card-f'
      foot.append(...tests)
      body.append(...body.querySelectorAll('.source-test-result'), foot)
    }
  }
}

export function setPill(pane: HTMLElement, key: string, kind: PillKind | null, text = '') {
  const pill = pane.querySelector<HTMLElement>(`[data-card="${key}"] .pill`)
  if (!pill) return
  pill.hidden = !kind
  pill.className = `pill${kind ? ' pill-' + kind : ''}`
  pill.textContent = text
}

// ─── Unsaved changes: per section, from what its controls hold ──────────────

// A library's On box saves at once (it scans or removes), so it's never unsaved.
const controls = (sect: HTMLElement) =>
  [...sect.querySelectorAll<HTMLElement>('input, select, textarea, button.tog[aria-pressed]')].filter(el => !el.closest('#libraries-list') || el.tagName === 'SELECT')
const valueOf = (el: HTMLElement) =>
  el instanceof HTMLInputElement ? (el.type === 'checkbox' || el.type === 'radio' ? String(el.checked) : el.value)
  : el instanceof HTMLSelectElement || el instanceof HTMLTextAreaElement ? el.value
  : String(el.getAttribute('aria-pressed'))

let baseline = new Map<string, string[]>()

/** Remember every section as it is now (just loaded, or saved). */
export function snapshotSettings(pane: HTMLElement) {
  baseline = new Map([...pane.querySelectorAll<HTMLElement>('.settings-sect')].map(s => [s.dataset.sect!, controls(s).map(valueOf)]))
}

/** The sections whose controls changed since the snapshot. */
export function changedSections(pane: HTMLElement): string[] {
  const out: string[] = []
  for (const s of pane.querySelectorAll<HTMLElement>('.settings-sect')) {
    const before = baseline.get(s.dataset.sect!) ?? []
    const now = controls(s).map(valueOf)
    if (now.length !== before.length || now.some((v, i) => v !== before[i])) out.push(s.dataset.sect!)
  }
  return out
}

export const sectionName = (key: string) => SECTS[key]?.[0] ?? key
