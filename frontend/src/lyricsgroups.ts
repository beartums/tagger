// Groups: the editor in Settings → Groups (name, Skip, lyrics queries tried
// in order), their layouts in Settings → Layouts, and "Group…" for a
// selection. Backend: core/lyricsgroups.py, core/layout.py.
import { api, LyricsGroup, LyricsQuery } from './api'
import { toast } from './toast'
import { esc } from './util'
import { errText } from './staged'

const BUILT_IN = new Set(['standard', 'none'])

function queryRow(q: LyricsQuery): string {
  const f = (k: keyof LyricsQuery, ph: string) =>
    `<input type="text" spellcheck="false" data-q="${k}" value="${esc(q[k])}" placeholder="${ph}" />`
  return `<div class="lyrics-query">${f('title', 'title')}${f('artist', 'artist (blank: by album)')}${f('album', 'album')}
    <button type="button" class="btn btn-ghost btn-sm" data-q-remove title="Remove this query">✕</button></div>`
}

let newKeys = 0
const keyOf = (g: LyricsGroup) => g.id || `new-${++newKeys}`

function groupCard(g: LyricsGroup, key = keyOf(g)): string {
  return `<div class="lyrics-group" data-id="${esc(g.id)}" data-key="${esc(key)}">
    <div class="lyrics-group-head">
      <input type="text" class="lyrics-group-name" value="${esc(g.name)}" placeholder="Group name" ${BUILT_IN.has(g.id) ? 'readonly title="Built in"' : ''} />
      <label class="settings-toggle"><input type="checkbox" data-skip ${g.skip ? 'checked' : ''} ${g.id === 'none' ? 'disabled' : ''} /><span>Skip</span></label>
      ${g.assigned ? `<span class="ma-dim">${g.assigned.toLocaleString()} tracks</span>` : ''}
      ${BUILT_IN.has(g.id) ? '' : '<button type="button" class="btn btn-ghost btn-sm" data-group-remove title="Delete this group (its tracks go back to their library\'s group)">Delete</button>'}
    </div>
    <div class="lyrics-queries" ${g.skip ? 'hidden' : ''}>${g.queries.map(queryRow).join('')}
      <button type="button" class="btn btn-link btn-sm" data-q-add>+ query</button></div>
  </div>`
}

export function renderLyricsGroups(el: HTMLElement, groups: LyricsGroup[]) {
  el.innerHTML = groups.map(g => groupCard(g)).join('')
}

const nameHtml = (name: string) => esc(name) || '<span class="ma-dim">(new group)</span>'

function layoutRow(key: string, name: string, layout: string): string {
  return `<tr data-group-layout="${esc(key)}"><td class="group-layout-name">${nameHtml(name)}</td>
    <td><input type="text" spellcheck="false" data-layout-input value="${esc(layout)}" placeholder="library's layout" /></td>
    <td><button type="button" class="btn btn-ghost btn-sm btn-icon" data-layout-remove title="Remove: the library's layout applies">✕</button></td></tr>`
}

/** Settings → Layouts: a row only for groups that have their own layout. */
export function renderGroupLayouts(layoutsEl: HTMLElement, groups: LyricsGroup[]) {
  layoutsEl.innerHTML = groups.filter(g => g.layout).map(g => layoutRow(g.id, g.name, g.layout ?? '')).join('')
}

/** Groups (as edited) without a layout row: what "Add a group layout" offers. */
export function groupLayoutChoices(el: HTMLElement, layoutsEl: HTMLElement): { key: string; name: string }[] {
  const has = new Set([...layoutsEl.querySelectorAll<HTMLElement>('[data-group-layout]')].map(r => r.dataset.groupLayout!))
  return [...el.querySelectorAll<HTMLElement>('.lyrics-group')]
    .map(c => ({ key: c.dataset.key!, name: c.querySelector<HTMLInputElement>('.lyrics-group-name')!.value.trim() || '(new group)' }))
    .filter(g => !has.has(g.key))
}

export function addGroupLayout(el: HTMLElement, layoutsEl: HTMLElement, key: string) {
  const card = el.querySelector<HTMLElement>(`.lyrics-group[data-key="${CSS.escape(key)}"]`)
  if (!card) return
  layoutsEl.insertAdjacentHTML('beforeend', layoutRow(key, card.querySelector<HTMLInputElement>('.lyrics-group-name')!.value.trim(), ''))
  layoutsEl.querySelector<HTMLInputElement>('tr:last-child [data-layout-input]')!.focus()
}

export function wireLyricsGroups(el: HTMLElement, addBtn: HTMLElement, layoutsEl: HTMLElement) {
  // Layout rows follow their group's card by key: renamed and deleted with it.
  const row = (card: Element) => layoutsEl.querySelector<HTMLElement>(`[data-group-layout="${CSS.escape((card as HTMLElement).dataset.key!)}"]`)
  addBtn.addEventListener('click', () => {
    el.insertAdjacentHTML('beforeend', groupCard({ id: '', name: '', skip: false,
      queries: [{ title: '{title_base}', artist: '{artist_first}', album: '' }] }))
    el.querySelector<HTMLInputElement>('.lyrics-group:last-child .lyrics-group-name')!.focus()
  })
  el.addEventListener('input', (e) => {
    const name = (e.target as HTMLElement).closest<HTMLInputElement>('.lyrics-group-name')
    const r = name && row(name.closest('.lyrics-group')!)
    if (r) r.querySelector('.group-layout-name')!.innerHTML = nameHtml(name!.value.trim())
  })
  layoutsEl.addEventListener('click', (e) => {
    (e.target as HTMLElement).closest('[data-layout-remove]')?.closest('tr')?.remove()
  })
  el.addEventListener('click', (e) => {
    const t = e.target as HTMLElement
    const card = t.closest<HTMLElement>('.lyrics-group')
    if (!card) return
    if (t.closest('[data-q-add]')) t.closest('[data-q-add]')!.insertAdjacentHTML('beforebegin', queryRow({ title: '{title}', artist: '', album: '' }))
    else if (t.closest('[data-q-remove]')) t.closest('.lyrics-query')!.remove()
    else if (t.closest('[data-group-remove]')) { row(card)?.remove(); card.remove() }
  })
  el.addEventListener('change', (e) => {
    const cb = e.target as HTMLInputElement
    if (cb.dataset.skip !== undefined) cb.closest('.lyrics-group')!.querySelector<HTMLElement>('.lyrics-queries')!.hidden = cb.checked
  })
}

/** The groups as edited, with their layouts, or null when the list never loaded (leave them as they are). */
export function readLyricsGroups(el: HTMLElement, layoutsEl: HTMLElement): LyricsGroup[] | null {
  const cards = [...el.querySelectorAll<HTMLElement>('.lyrics-group')]
  if (!cards.length) return null
  const layout = (key: string) => layoutsEl.querySelector<HTMLInputElement>(`[data-group-layout="${CSS.escape(key)}"] [data-layout-input]`)?.value.trim() ?? ''
  return cards.map(c => ({
    id: c.dataset.id ?? '',
    name: c.querySelector<HTMLInputElement>('.lyrics-group-name')!.value.trim(),
    skip: c.querySelector<HTMLInputElement>('[data-skip]')!.checked,
    queries: [...c.querySelectorAll<HTMLElement>('.lyrics-query')].map(r => {
      const v = (k: string) => r.querySelector<HTMLInputElement>(`[data-q="${k}"]`)!.value.trim()
      return { title: v('title'), artist: v('artist'), album: v('album') }
    }).filter(q => q.title),
    layout: layout(c.dataset.key!),
  }))
}

/** A library's default group, as a <select> for its row under Libraries. */
export function libraryGroupSelect(groups: LyricsGroup[], path: string, current: string): string {
  return `<select data-lyrics-path="${esc(path)}" aria-label="Group">
    ${groups.map(g => `<option value="${g.id === 'standard' ? '' : esc(g.id)}" ${(current || 'standard') === g.id ? 'selected' : ''}>${esc(g.name)}</option>`).join('')}
  </select>`
}

/** "Group…": put the selection in a group, or back to its library's. Opens on their current one. */
export async function openAssignGroup(ids: number[], onDone: () => Promise<void>) {
  let groups: LyricsGroup[], current: string | null
  try {
    [groups, { group_id: current }] = await Promise.all([api.lyrics.groups(), api.lyrics.assigned(ids)])
  } catch (e) { toast(`Failed: ${errText(e)}`, 'error'); return }
  const overlay = document.createElement('div')
  overlay.className = 'modal-overlay'
  const n = `${ids.length.toLocaleString()} track${ids.length !== 1 ? 's' : ''}`
  overlay.innerHTML = `
    <div class="modal-card">
      <div class="modal-title">Group for ${n}</div>
      <div class="lyrics-assign">
        ${current === null ? '<div class="ma-dim">These tracks are in different groups now.</div>' : ''}
        <label class="settings-toggle"><input type="radio" name="lg" value="" ${current === '' ? 'checked' : ''} /><span>Library's group <span class="ma-dim">(as set under Settings → Libraries)</span></span></label>
        ${groups.map(g => `<label class="settings-toggle"><input type="radio" name="lg" value="${esc(g.id)}" ${current === g.id ? 'checked' : ''} /><span>${esc(g.name)}${g.skip ? ' <span class="ma-dim">— never looked up, not "missing"</span>' : ''}</span></label>`).join('')}
      </div>
      <div class="modal-actions"><button class="btn btn-ghost" data-cancel>Cancel</button><button class="btn btn-primary" data-ok>Set group</button></div>
    </div>`
  document.body.appendChild(overlay)
  const close = () => overlay.remove()
  overlay.addEventListener('click', e => { if (e.target === overlay) close() })
  overlay.querySelector('[data-cancel]')!.addEventListener('click', close)
  overlay.querySelector<HTMLButtonElement>('[data-ok]')!.addEventListener('click', async (e) => {
    const picked = overlay.querySelector<HTMLInputElement>('input[name="lg"]:checked')
    if (!picked) { toast('Pick a group', 'info'); return }
    const id = picked.value || null
    ;(e.target as HTMLButtonElement).disabled = true
    try {
      await api.lyrics.assign(ids, id)
      toast(`${n} → ${id ? groups.find(g => g.id === id)!.name : "library's group"}`, 'success')
      close()
      await onDone()
    } catch (err) { toast(`Failed: ${errText(err)}`, 'error'); (e.target as HTMLButtonElement).disabled = false }
  })
}
