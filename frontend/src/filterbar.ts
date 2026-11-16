// The filter bar under the toolbar: a funnel menu of every Quality check,
// quality rating, format and has-filter; each active one is a chip with ✕.
import { state } from './state'
import { api } from './api'
import { QUALITY_ISSUES } from './quality'
import { ICON } from './icons'
import { esc } from './util'

type Kind = 'issues' | 'formats' | 'qualities' | 'has'
type Item = { kind: Kind; key: string; label: string; icon: string; group: string }

const GROUP_ICON: Record<string, string> = {
  Tags: ICON.tag, Files: ICON.file, 'Cover art': ICON.image, MusicBrainz: ICON.brain,
  'CD rips': ICON.album, Quality: ICON.star, Format: ICON.file, Has: ICON.check,
}
// Quality checks without a group: the tag ones, then the file ones.
const FILE_CHECKS = new Set(['duplicate_tracks', 'duplicate_albums', 'not_in_layout', 'group_layout_conflict', 'missing_lyrics'])

let formats: string[] = []
let onChange = () => {}

function items(): Item[] {
  const out: Item[] = []
  for (const q of QUALITY_ISSUES) {
    if (q.key === 'missing_files') continue        // checked on disk, not a filter
    const group = q.group ?? (FILE_CHECKS.has(q.key) ? 'Files' : 'Tags')
    out.push({ kind: 'issues', key: q.key, label: q.label, icon: GROUP_ICON[group], group })
  }
  for (const [key, label] of [['good', 'Good'], ['fair', 'Fair'], ['poor', 'Poor']])
    out.push({ kind: 'qualities', key, label: `${label} quality`, icon: ICON.star, group: 'Quality' })
  for (const f of formats) out.push({ kind: 'formats', key: f, label: f, icon: ICON.file, group: 'Format' })
  out.push({ kind: 'has', key: 'lyrics', label: 'Has lyrics', icon: ICON.check, group: 'Has' })
  out.push({ kind: 'has', key: 'staged', label: 'Has staged changes', icon: ICON.check, group: 'Has' })
  return out
}

const isOn = (it: Item) => state.filters[it.kind].includes(it.key)
export const filtersActive = () => Object.values(state.filters).some(v => v.length > 0)

/** The filters as /tracks parameters. */
export function filterParams(p: Record<string, string | number>) {
  const f = state.filters
  if (f.issues.length) p.issues = f.issues.join(',')
  if (f.has.length) p.has = f.has.join(',')
  if (f.formats.length) p.format = f.formats.join(',')
  if (f.qualities.length) p.quality = f.qualities.join(',')
}

const KINDS: Kind[] = ['issues', 'formats', 'qualities', 'has']

/** The filters for the page address: "issues:a,b;formats:flac" ("" = none). */
export function filtersKey(): string {
  return KINDS.filter(k => state.filters[k].length).map(k => `${k}:${state.filters[k].join(',')}`).join(';')
}

/** Set the filters from an address's key and redraw the bar (no reload: the caller loads). */
export function setFiltersFromKey(key: string) {
  const f = { issues: [] as string[], formats: [] as string[], qualities: [] as string[], has: [] as string[] }
  for (const part of key.split(';')) {
    const [k, v] = part.split(':')
    if ((KINDS as string[]).includes(k) && v) f[k as Kind] = v.split(',').filter(Boolean)
  }
  state.filters = f
  if (document.getElementById('filter-chips')) { renderChips(); syncMenu() }
}

function toggle(kind: Kind, key: string) {
  const list = state.filters[kind]
  state.filters[kind] = list.includes(key) ? list.filter(k => k !== key) : [...list, key]
  renderChips(); syncMenu(); onChange()
}

const menuEl = () => document.getElementById('filter-menu')!
const btnEl = () => document.getElementById('filter-btn')!

function renderMenu() {
  const groups = new Map<string, Item[]>()
  for (const it of items()) groups.set(it.group, [...(groups.get(it.group) ?? []), it])
  // Three columns: tag and file checks | cover art, MusicBrainz, CD rips | the rest.
  const cols = [['Tags', 'Files'], ['Cover art', 'MusicBrainz', 'CD rips'], ['Quality', 'Format', 'Has']]
  menuEl().innerHTML = cols.map(names => `<div class="fm-col">${names.filter(n => groups.has(n)).map(n =>
    `<div class="fm-h">${GROUP_ICON[n]}${esc(n)}</div>` + groups.get(n)!.map(it =>
      `<button type="button" class="fm-i" role="menuitemcheckbox" aria-checked="${isOn(it)}" data-kind="${it.kind}" data-key="${esc(it.key)}">${esc(it.label)}</button>`).join('')
  ).join('')}</div>`).join('')
}

// Tick in place: re-rendering under the click would read as a click outside.
function syncMenu() {
  menuEl().querySelectorAll<HTMLElement>('.fm-i').forEach(b =>
    b.setAttribute('aria-checked', String(state.filters[b.dataset.kind as Kind].includes(b.dataset.key!))))
}

function renderChips() {
  const on = items().filter(isOn)
  // A filter whose format left the library still shows, so it can be removed.
  for (const f of state.filters.formats) if (!formats.includes(f)) on.push({ kind: 'formats', key: f, label: f, icon: ICON.file, group: 'Format' })
  const chips = document.getElementById('filter-chips')!
  chips.innerHTML = on.length ? on.map(it =>
    `<span class="fchip" title="${esc(it.group)}: ${esc(it.label)}">${it.icon}${esc(it.label)}<button type="button" class="fchip-x" data-kind="${it.kind}" data-key="${esc(it.key)}" aria-label="Remove filter ${esc(it.label)}">✕</button></span>`).join('')
    : '<span class="filter-none">No filters</span>'
  document.getElementById('filter-clear')!.hidden = on.length < 2
  btnEl().classList.toggle('active', on.length > 0)
}

function setOpen(open: boolean) {
  menuEl().hidden = !open
  btnEl().setAttribute('aria-expanded', String(open))
  btnEl().classList.toggle('open', open)
  if (open) renderMenu()
}

export async function refreshFormats() {
  try { formats = await api.library.formats() } catch { return }
  renderChips()
}

export function initFilterBar(changed: () => void) {
  onChange = changed
  renderChips()
  btnEl().addEventListener('click', () => setOpen(menuEl().hidden !== false))
  menuEl().addEventListener('click', e => {
    const b = (e.target as HTMLElement).closest<HTMLElement>('.fm-i')
    if (b) toggle(b.dataset.kind as Kind, b.dataset.key!)
  })
  document.getElementById('filter-chips')!.addEventListener('click', e => {
    const b = (e.target as HTMLElement).closest<HTMLElement>('.fchip-x')
    if (b) toggle(b.dataset.kind as Kind, b.dataset.key!)
  })
  document.getElementById('filter-clear')!.addEventListener('click', () => {
    state.filters = { issues: [], formats: [], qualities: [], has: [] }
    renderChips(); syncMenu(); onChange()
  })
  document.addEventListener('click', e => {
    if (!menuEl().hidden && !(e.target as HTMLElement).closest('.filter-wrap')) setOpen(false)
  })
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !menuEl().hidden) setOpen(false) })
}
