// Clean up → Empty folders: folders with no tracks left in the libraries you
// pick, with any non-track files still in them. Each is on to delete; click
// one to keep it. Deleted folders go to the trash; History undoes it.
// Backend: /api/library/empty-folders.
import { api } from './api'
import { toast } from './toast'
import { esc, fmtBytes } from './util'
import { errText, shortPath } from './staged'

type Found = { dir: string; root: string; count: number; bytes: number; files: string[] }

export async function openEmptyFolders(onDone: () => Promise<void>) {
  const libs = (await api.settings.libraries()).filter(l => l.active)
  const overlay = document.createElement('div')
  overlay.className = 'fix-confirm-overlay'
  overlay.innerHTML = `
    <div class="fix-confirm-modal pr-modal" role="dialog" aria-label="Empty folders">
      <div class="fix-confirm-header">
        <span class="fix-confirm-title">Empty folders</span>
        <button class="btn btn-ghost btn-icon fix-confirm-close" aria-label="Close">✕</button>
      </div>
      <div class="pr-controls ef-libs">
        <span class="ma-dim">Look in</span>
        <button type="button" class="tog" data-lib="*" aria-pressed="true">All libraries</button>
        ${libs.map(l => `<button type="button" class="tog" data-lib="${esc(l.path)}" aria-pressed="false" title="${esc(l.path)}">${esc(l.name)}</button>`).join('')}
      </div>
      <div class="pr-summary" id="ef-summary">Looking…</div>
      <div class="fix-confirm-body pr-body"><div id="ef-list" class="ef-list"></div></div>
      <div class="fix-confirm-footer">
        <span class="ma-dim lm-note">Folders with no audio files left. Click one to keep it.</span>
        <button class="btn btn-ghost" id="ef-cancel">Close</button>
        <button class="btn btn-danger" id="ef-ok" disabled>Delete</button>
      </div>
    </div>`
  document.body.appendChild(overlay)
  const $ = <T extends HTMLElement>(sel: string) => overlay.querySelector<T>(sel)!
  const listEl = $('#ef-list'), sumEl = $('#ef-summary'), okBtn = $<HTMLButtonElement>('#ef-ok')
  const close = () => { overlay.remove(); document.removeEventListener('keydown', onKey) }
  const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') close() }
  document.addEventListener('keydown', onKey)
  overlay.addEventListener('click', e => { if (e.target === overlay) close() })
  $('.fix-confirm-close').addEventListener('click', close)
  $('#ef-cancel').addEventListener('click', close)

  let found: Found[] = [], token = 0
  const keep = new Set<string>()
  const chosen = () => [...overlay.querySelectorAll<HTMLElement>('[data-lib][aria-pressed="true"]')].map(b => b.dataset.lib!).filter(x => x !== '*')

  const render = () => {
    const go = found.filter(f => !keep.has(f.dir))
    const withFiles = found.filter(f => f.count).length
    sumEl.innerHTML = found.length
      ? `<strong>${found.length}</strong> folder${found.length !== 1 ? 's' : ''} with no tracks${withFiles ? ` · ${withFiles} still hold other files` : ''}${keep.size ? ` · keeping ${keep.size}` : ''}`
      : 'No empty folders here.'
    listEl.innerHTML = found.map(f => {
      const off = keep.has(f.dir)
      const files = f.count
        ? `<div class="ef-files">${f.count} file${f.count !== 1 ? 's' : ''} (${fmtBytes(f.bytes)}): ${f.files.map(esc).join(', ')}${f.count > f.files.length ? `, +${f.count - f.files.length} more` : ''}</div>`
        : '<div class="ma-dim">Empty</div>'
      return `<button type="button" class="ef-row${off ? ' ef-keep' : ''}${f.count ? ' ef-has' : ''}" data-dir="${esc(f.dir)}"
        title="${off ? 'Kept — click to delete it' : 'Will be deleted — click to keep it'}">
        <span class="ef-mark">${off ? 'keep' : 'delete'}</span>
        <span class="ef-body"><span class="ef-path">${esc(shortPath(f.dir))}/</span>${files}</span></button>`
    }).join('')
    okBtn.disabled = !go.length
    okBtn.textContent = go.length ? `Delete ${go.length} folder${go.length !== 1 ? 's' : ''}` : 'Delete'
  }

  const load = async () => {
    const t = ++token
    sumEl.textContent = 'Looking…'; listEl.innerHTML = ''; okBtn.disabled = true
    try {
      const r = await api.library.emptyFolders(chosen())
      if (t !== token) return
      found = r.folders; keep.clear(); render()
    } catch (e) { if (t === token) sumEl.innerHTML = `<span class="pr-bad">${esc(errText(e))}</span>` }
  }

  overlay.querySelector('.ef-libs')!.addEventListener('click', (e) => {
    const b = (e.target as HTMLElement).closest<HTMLElement>('[data-lib]')
    if (!b) return
    const all = b.dataset.lib === '*'
    const on = b.getAttribute('aria-pressed') !== 'true'
    if (all) overlay.querySelectorAll('[data-lib]').forEach(x => x.setAttribute('aria-pressed', String(x === b)))
    else {
      b.setAttribute('aria-pressed', String(on))
      const any = chosen().length > 0
      overlay.querySelector('[data-lib="*"]')!.setAttribute('aria-pressed', String(!any))
    }
    load()
  })
  listEl.addEventListener('click', (e) => {
    const r = (e.target as HTMLElement).closest<HTMLElement>('.ef-row')
    if (!r) return
    const d = r.dataset.dir!
    if (!keep.delete(d)) keep.add(d)
    render()
  })
  okBtn.addEventListener('click', async () => {
    const dirs = found.filter(f => !keep.has(f.dir)).map(f => f.dir)
    okBtn.disabled = true
    try {
      const r = await api.library.deleteEmptyFolders(dirs)
      if (r.errors.length) toast(`Deleted ${r.deleted}; ${r.errors.length} not: ${r.errors[0].name}: ${r.errors[0].error}`, 'error')
      else toast(`Deleted ${r.deleted} folder${r.deleted !== 1 ? 's' : ''} (to the trash) — undo from History`, 'success')
      await onDone()
      await load()
    } catch (e) { toast(`Delete failed: ${errText(e)}`, 'error'); okBtn.disabled = false }
  })
  load()
}
