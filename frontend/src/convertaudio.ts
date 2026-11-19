// Clean up → Convert audio: files tggr can't read, in the libraries you pick.
// WAV/AIFF -> FLAC (lossless), WMA/MP2 -> MP3 V0 (lossy to lossy). Protected
// iTunes .m4p are listed but can't be converted: download them again (Apple
// offers DRM-free .m4a for most old purchases). Each folder is on; click one to
// leave it. Runs in the background; originals go to the trash, History undoes it.
// Backend: /api/library/convert (core/convert.py).
import { api } from './api'
import { toast } from './toast'
import { esc, fmtBytes } from './util'
import { errText, shortPath } from './staged'

type File = { path: string; name: string; ext: string; to: string | null; size: number; protected: boolean; taken: boolean }
type Folder = { dir: string; root: string; files: File[] }
const canDo = (f: File) => !!f.to && !f.protected && !f.taken

export async function openConvertAudio(onDone: () => Promise<void>) {
  const libs = (await api.settings.libraries()).filter(l => l.active)
  const overlay = document.createElement('div')
  overlay.className = 'fix-confirm-overlay'
  overlay.innerHTML = `
    <div class="fix-confirm-modal pr-modal" role="dialog" aria-label="Convert audio">
      <div class="fix-confirm-header">
        <span class="fix-confirm-title">Convert audio tggr can't read</span>
        <button class="btn btn-ghost btn-icon fix-confirm-close" aria-label="Close">✕</button>
      </div>
      <div class="pr-controls ef-libs">
        <span class="ma-dim">Look in</span>
        <button type="button" class="tog" data-lib="*" aria-pressed="true">All libraries</button>
        ${libs.map(l => `<button type="button" class="tog" data-lib="${esc(l.path)}" aria-pressed="false" title="${esc(l.path)}">${esc(l.name)}</button>`).join('')}
      </div>
      <div class="pr-summary" id="ca-summary">Looking…</div>
      <div class="fix-confirm-body pr-body"><div id="ca-list" class="ef-list"></div></div>
      <div class="fix-confirm-footer">
        <span class="ma-dim lm-note">WAV/AIFF → FLAC loses nothing; WMA → MP3 loses a little. Originals go to the trash.</span>
        <button class="btn btn-ghost" id="ca-cancel">Close</button>
        <button class="btn btn-primary" id="ca-ok" disabled>Convert</button>
      </div>
    </div>`
  document.body.appendChild(overlay)
  const $ = <T extends HTMLElement>(sel: string) => overlay.querySelector<T>(sel)!
  const listEl = $('#ca-list'), sumEl = $('#ca-summary'), okBtn = $<HTMLButtonElement>('#ca-ok')
  const close = () => { overlay.remove(); document.removeEventListener('keydown', onKey) }
  const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') close() }
  document.addEventListener('keydown', onKey)
  overlay.addEventListener('click', e => { if (e.target === overlay) close() })
  $('.fix-confirm-close').addEventListener('click', close)
  $('#ca-cancel').addEventListener('click', close)

  let found: Folder[] = [], token = 0, ffmpeg = true
  const skip = new Set<string>()
  const chosen = () => [...overlay.querySelectorAll<HTMLElement>('[data-lib][aria-pressed="true"]')].map(b => b.dataset.lib!).filter(x => x !== '*')
  const todo = () => found.filter(f => !skip.has(f.dir)).flatMap(f => f.files.filter(canDo))

  const render = () => {
    const all = found.flatMap(f => f.files)
    const prot = all.filter(f => f.protected).length
    const n = todo().length
    sumEl.innerHTML = !ffmpeg ? '<span class="pr-bad">ffmpeg isn’t installed, so nothing can be converted.</span>'
      : all.length ? [`<strong>${all.filter(canDo).length}</strong> file${all.filter(canDo).length !== 1 ? 's' : ''} to convert in ${found.length} folder${found.length !== 1 ? 's' : ''}`,
          prot ? `${prot} protected iTunes .m4p (download again from your purchases)` : ''].filter(Boolean).join(' · ')
      : 'Nothing to convert here.'
    listEl.innerHTML = found.map(f => {
      const off = skip.has(f.dir), convertible = f.files.some(canDo)
      const items = f.files.map(x => x.protected
        ? `<span class="ca-prot" title="Protected iTunes purchase: can't be converted. Download it again from your iTunes purchases (DRM-free .m4a)">${esc(x.name)} 🔒</span>`
        : x.taken ? `<span class="ca-prot" title="${esc(x.to!)} is already there">${esc(x.name)} (${esc(x.to!)} exists)</span>`
        : `${esc(x.name)} → ${esc(x.ext === '.wma' || x.ext === '.mp2' || x.ext === '.mpa' ? 'MP3' : 'FLAC')} <span class="ma-dim">${fmtBytes(x.size)}</span>`).join(' · ')
      return `<button type="button" class="ef-row${off || !convertible ? ' ef-keep' : ''}" data-dir="${esc(f.dir)}" ${convertible ? '' : 'disabled'}
        title="${!convertible ? 'Nothing here can be converted' : off ? 'Left as is — click to convert' : 'Will be converted — click to leave it'}">
        <span class="ef-mark ca-mark">${!convertible ? '—' : off ? 'leave' : 'convert'}</span>
        <span class="ef-body"><span class="ef-path">${esc(shortPath(f.dir))}/</span><div class="ef-files">${items}</div></span></button>`
    }).join('')
    okBtn.disabled = !ffmpeg || !n
    okBtn.textContent = n ? `Convert ${n} file${n !== 1 ? 's' : ''}` : 'Convert'
  }

  const load = async () => {
    const t = ++token
    sumEl.textContent = 'Looking…'; listEl.innerHTML = ''; okBtn.disabled = true
    try {
      const r = await api.library.convertible(chosen())
      if (t !== token) return
      found = r.folders; ffmpeg = r.available; skip.clear(); render()
    } catch (e) { if (t === token) sumEl.innerHTML = `<span class="pr-bad">${esc(errText(e))}</span>` }
  }

  overlay.querySelector('.ef-libs')!.addEventListener('click', (e) => {
    const b = (e.target as HTMLElement).closest<HTMLElement>('[data-lib]')
    if (!b) return
    if (b.dataset.lib === '*') overlay.querySelectorAll('[data-lib]').forEach(x => x.setAttribute('aria-pressed', String(x === b)))
    else {
      b.setAttribute('aria-pressed', String(b.getAttribute('aria-pressed') !== 'true'))
      overlay.querySelector('[data-lib="*"]')!.setAttribute('aria-pressed', String(!chosen().length))
    }
    load()
  })
  listEl.addEventListener('click', (e) => {
    const r = (e.target as HTMLElement).closest<HTMLButtonElement>('.ef-row')
    if (!r || r.disabled) return
    if (!skip.delete(r.dataset.dir!)) skip.add(r.dataset.dir!)
    render()
  })
  okBtn.addEventListener('click', async () => {
    const paths = todo().map(f => f.path)
    okBtn.disabled = true
    try {
      const { job_id } = await api.library.convert(paths)
      window.dispatchEvent(new Event('tggr:job'))
      toast(`Converting ${paths.length} file${paths.length !== 1 ? 's' : ''} in the background (Settings → Background)`, 'info')
      close()
      const timer = setInterval(async () => {
        try {
          const j = await api.jobs.get(job_id)
          if (j.status === 'running' || j.status === 'pending') return
          clearInterval(timer)
          const n = j.changed ?? 0
          if (j.status === 'error') toast(`Convert failed: ${j.error ?? ''}`, 'error')
          else toast(`Converted ${n} of ${j.total} file${j.total !== 1 ? 's' : ''}${j.error ? ` — ${j.error}` : ''} — undo from History`, j.error ? 'error' : 'success')
          await onDone()
        } catch { clearInterval(timer) }
      }, 2000)
    } catch (e) { toast(`Convert: ${errText(e)}`, 'error'); okBtn.disabled = false }
  })
  load()
}
