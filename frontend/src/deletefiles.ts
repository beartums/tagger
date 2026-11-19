// Delete files…: the selected tracks go to the trash. For each folder they
// leave, its other files (cover, .cue, logs, Scans/…) can go too, and the
// folder be removed once empty -- both on when every track in it is deleted.
// Backend: /api/library/delete-files.
import { api, ExtrasFolder } from './api'
import { toast } from './toast'
import { esc } from './util'
import { errText, shortPath } from './staged'

type Folder = ExtrasFolder & { files_on: boolean; folder_on: boolean }

export function openDeleteFiles(ids: number[], onDone: () => Promise<void>) {
  const n = `${ids.length.toLocaleString()} file${ids.length !== 1 ? 's' : ''}`
  const overlay = document.createElement('div')
  overlay.className = 'fix-confirm-overlay'
  overlay.innerHTML = `
    <div class="fix-confirm-modal pr-modal df-modal" role="dialog" aria-label="Delete files">
      <div class="fix-confirm-header">
        <span class="fix-confirm-title">Delete ${n}</span>
        <button class="btn btn-ghost btn-icon fix-confirm-close" aria-label="Close">✕</button>
      </div>
      <div class="pr-summary">They go to the trash (Settings → Writing empties it); Undo in History puts everything back.</div>
      <div class="fix-confirm-body pr-body"><div id="df-folders" class="lm-extras">Looking at their folders…</div></div>
      <div class="fix-confirm-footer">
        <button class="btn btn-ghost" id="df-cancel">Cancel</button>
        <button class="btn btn-danger" id="df-ok" disabled>Delete</button>
      </div>
    </div>`
  document.body.appendChild(overlay)
  const $ = <T extends HTMLElement>(sel: string) => overlay.querySelector<T>(sel)!
  const okBtn = $<HTMLButtonElement>('#df-ok'), listEl = $('#df-folders')
  const close = () => { overlay.remove(); document.removeEventListener('keydown', onKey) }
  const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') close() }
  document.addEventListener('keydown', onKey)
  overlay.addEventListener('click', e => { if (e.target === overlay) close() })
  $('.fix-confirm-close').addEventListener('click', close)
  $('#df-cancel').addEventListener('click', close)

  let folders: Folder[] = []
  const pick: Record<string, { files: boolean; folder: boolean }> = {}
  // The folder can only go once it's empty: with other files left, it stays.
  const folderPossible = (f: Folder) => f.whole && (!f.items.length || pick[f.dir].files)

  const render = () => {
    const shown = folders.filter(f => f.whole || f.items.length)
    listEl.innerHTML = shown.length ? `<div class="lm-xh">Their folders</div>` + shown.map(f => {
      const p = pick[f.dir], canFolder = folderPossible(f)
      const listed = f.items.slice(0, 8).map(i => `${esc(i.name)}${i.dir ? `/ (${i.files})` : ''}`).join(', ') + (f.items.length > 8 ? `, +${f.items.length - 8} more` : '')
      return `<div class="lm-xf">
        <div class="df-togs">
          ${f.items.length ? `<button type="button" class="tog" data-df="files" data-dir="${esc(f.dir)}" aria-pressed="${p.files}"
             title="${esc(f.whole ? 'Every track in this folder is being deleted: its other files can go to the trash too.' : 'Some tracks stay in this folder; its other files are usually theirs too.')}">Delete its other files</button>` : ''}
          ${f.whole ? `<button type="button" class="tog" data-df="folder" data-dir="${esc(f.dir)}" aria-pressed="${p.folder && canFolder}" ${canFolder ? '' : 'disabled'}
             title="${esc(canFolder ? 'Remove the folder once it is empty (and parent folders left empty, never the library root)' : 'Its other files stay, so the folder does too')}">Remove the folder</button>` : ''}
        </div>
        <div class="lm-xbody"><div class="ma-dim">${esc(shortPath(f.dir))}/${f.discs ? ' (disc folders’ parent)' : ''}${f.whole ? ' · every track goes' : ' · some tracks stay'}</div>
          ${f.items.length ? `<div class="lm-xlist${p.files ? '' : ' df-kept'}">${f.files} other file${f.files !== 1 ? 's' : ''}: ${listed}</div>` : '<div class="ma-dim">No other files</div>'}</div>
      </div>`
    }).join('') : ''
    const others = folders.reduce((s, f) => s + (pick[f.dir].files ? f.files : 0), 0)
    const gone = folders.filter(f => pick[f.dir].folder && folderPossible(f)).length
    okBtn.textContent = `Delete ${n}${others ? ` + ${others} other` : ''}${gone ? ` · remove ${gone} folder${gone !== 1 ? 's' : ''}` : ''}`
  }

  listEl.addEventListener('click', (e) => {
    const b = (e.target as HTMLElement).closest<HTMLButtonElement>('[data-df]')
    if (!b || b.disabled) return
    const p = pick[b.dataset.dir!], key = b.dataset.df as 'files' | 'folder'
    p[key] = !p[key]
    render()
  })

  api.library.deletePreview(ids).then(r => {
    folders = r.folders as Folder[]
    for (const f of folders) pick[f.dir] = { files: f.files_on, folder: f.folder_on }
    render()
    okBtn.disabled = false
  }).catch(e => { listEl.innerHTML = `<span class="pr-bad">${esc(errText(e))}</span>` })

  okBtn.addEventListener('click', async () => {
    okBtn.disabled = true
    const sent: Record<string, { files: boolean; folder: boolean }> = {}
    for (const f of folders) sent[f.dir] = { files: pick[f.dir].files, folder: pick[f.dir].folder && folderPossible(f) }
    try {
      const r = await api.library.deleteWith(ids, sent)
      const extra = [r.other_files ? `${r.other_files} other file${r.other_files !== 1 ? 's' : ''}` : '',
                     r.folders_removed ? `${r.folders_removed} folder${r.folders_removed !== 1 ? 's' : ''} removed` : ''].filter(Boolean).join(', ')
      toast(`Moved ${r.deleted} file${r.deleted !== 1 ? 's' : ''} to trash${extra ? ` (${extra})` : ''}`, 'success')
      close()
      await onDone()
    } catch (e) { toast(`Delete failed: ${errText(e)}`, 'error'); okBtn.disabled = false }
  })
}
