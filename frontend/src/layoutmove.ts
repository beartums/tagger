// Move to layout: the selected files as their layout would file them -- the
// final folders and names, each moved file showing where it comes from on
// hover -- then OK stages exactly that (backend: /api/tags/reorganize).
import { api } from './api'
import { toast } from './toast'
import { esc } from './util'
import { errText, missingText, shortPath } from './staged'

const dirOf = (p: string) => p.slice(0, p.lastIndexOf('/'))
const nameOf = (p: string) => p.slice(p.lastIndexOf('/') + 1)

export function openLayoutMove(ids: number[], stageChanges: boolean, onDone: (staged: boolean) => Promise<void>) {
  const overlay = document.createElement('div')
  overlay.className = 'fix-confirm-overlay'
  overlay.innerHTML = `
    <div class="fix-confirm-modal pr-modal" role="dialog" aria-label="Move to layout">
      <div class="fix-confirm-header">
        <span class="fix-confirm-title">Move to layout · ${ids.length.toLocaleString()} track${ids.length !== 1 ? 's' : ''}</span>
        <button class="btn btn-ghost btn-icon fix-confirm-close" aria-label="Close">✕</button>
      </div>
      <div class="pr-summary" id="lm-summary">Working out where each file goes…</div>
      <div class="fix-confirm-body pr-body"><div id="lm-tree" class="lm-tree"></div>
        <div id="lm-errors" class="ma-clashes"></div></div>
      <div class="fix-confirm-footer">
        <span class="ma-dim lm-note">${stageChanges ? 'Staged: nothing moves until you write it from Review.' : 'Files move now; undo is in History.'}</span>
        <button class="btn btn-ghost" id="lm-cancel">Cancel</button>
        <button class="btn btn-primary" id="lm-ok" disabled>OK</button>
      </div>
    </div>`
  document.body.appendChild(overlay)

  const $ = <T extends HTMLElement>(sel: string) => overlay.querySelector<T>(sel)!
  const okBtn = $<HTMLButtonElement>('#lm-ok')
  const close = () => { overlay.remove(); document.removeEventListener('keydown', onKey) }
  const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') close() }
  document.addEventListener('keydown', onKey)
  overlay.addEventListener('click', e => { if (e.target === overlay) close() })
  $('.fix-confirm-close').addEventListener('click', close)
  $('#lm-cancel').addEventListener('click', close)

  api.tags.refilePreview(ids).then(r => {
    // Final state: one block per destination folder, its files as they'll be named.
    const byDir = new Map<string, { from: string; to: string }[]>()
    for (const m of r.moves) {
      const d = dirOf(m.to)
      byDir.set(d, [...(byDir.get(d) ?? []), m])
    }
    const dirs = [...byDir.keys()].sort((a, b) => a.localeCompare(b))
    $('#lm-tree').innerHTML = dirs.map(d => {
      const files = byDir.get(d)!.sort((a, b) => a.to.localeCompare(b.to))
      const froms = [...new Set(files.map(f => shortPath(dirOf(f.from))))]
      const fromNote = froms.length === 1 ? `from ${froms[0]}` : `from ${froms.length} folders`
      return `<div class="lm-dir">
        <div class="lm-dir-h"><span class="lm-dir-name">${esc(shortPath(d))}/</span><span class="ma-dim">${esc(fromNote)}</span></div>
        ${files.map(f => `<div class="lm-file" data-diff-from="${esc(shortPath(f.from))}" data-diff-to="${esc(shortPath(f.to))}">${esc(nameOf(f.to))}</div>`).join('')}
      </div>`
    }).join('') || '<div class="pr-summary">Nothing to move.</div>'
    $('#lm-errors').innerHTML = r.errors.length
      ? `<div class="pr-bad">Left where they are (${r.errors.length}):</div>` +
        r.errors.slice(0, 50).map(e => `<div class="pr-msg">${esc(e.name ?? String(e.id))}: ${esc(e.error)}</div>`).join('')
      : ''
    const n = r.moves.length
    $('#lm-summary').innerHTML = [
      `<strong>${n.toLocaleString()}</strong> file${n !== 1 ? 's' : ''} move into ${dirs.length.toLocaleString()} folder${dirs.length !== 1 ? 's' : ''}`,
      r.in_place ? `${r.in_place.toLocaleString()} already in place` : '',
      r.errors.length ? `<span class="pr-bad">${r.errors.length} can't move</span>` : '',
    ].filter(Boolean).join(' · ') + (n ? ' — hover a file to see where it is now' : '')
    okBtn.disabled = n === 0
  }).catch(e => {
    $('#lm-summary').innerHTML = `<span class="pr-bad">${esc(errText(e))}</span>`
  })

  okBtn.addEventListener('click', async () => {
    okBtn.disabled = true
    try {
      const res = await api.tags.refile(ids)
      const errNote = res.errors.length ? ` — ${res.errors.length} left where they are` : ''
      if (res.missing) toast(`Nothing written: ${missingText(res.errors)}`, 'error')
      else if (res.staged) toast(`Staged moving ${res.planned} file${res.planned !== 1 ? 's' : ''} to the layout — Review to write${errNote}`, 'info')
      else toast(`Moved ${res.moved} file${res.moved !== 1 ? 's' : ''} to the layout${errNote}`, res.moved ? 'success' : 'error')
      close()
      await onDone(res.staged)
    } catch (e) {
      toast(`Move to layout failed: ${errText(e)}`, 'error'); okBtn.disabled = false
    }
  })
}
