// Staged changes: overlay on tracks, the Review dialog and the History dialog.
import { api, EditResult, StagedLine, Track, WriteError } from './api'
import { toast } from './toast'
import { esc } from './util'
import { state } from './state'

const FIELD_LABELS: Record<string, string> = {
  title: 'Title', artist: 'Artist', album: 'Album', album_artist: 'Album Artist',
  year: 'Year', genre: 'Genre', track_number: 'Track #', disc_number: 'Disc #',
  comment: 'Comment', composer: 'Composer', bpm: 'BPM', lyrics: 'Lyrics',
  compilation: 'Compilation', mb_track_id: 'MB Track ID', mb_artist_id: 'MB Artist ID',
  mb_album_id: 'MB Album ID', mb_album_artist_id: 'MB Album Artist ID',
  mb_release_group_id: 'MB Release Group ID', mb_release_track_id: 'MB Release Track ID',
  rg_track_gain: 'ReplayGain (track)', rg_track_peak: 'Peak (track)',
  rg_album_gain: 'ReplayGain (album)', rg_album_peak: 'Peak (album)',
}

/** Show staged values in place of the on-file ones (kept in t._orig). */
export function overlayStaged(t: Track): Track {
  const tags = t.staged?.tags
  if (!tags) return t
  const rec = t as unknown as Record<string, string | null>
  t._orig = {}
  for (const [k, v] of Object.entries(tags)) {
    t._orig[k] = rec[k] ?? null
    rec[k] = v
  }
  return t
}

/** Path relative to the music dir it lives in, for display. */
export function shortPath(p: string): string {
  const root = state.musicDirs.find(d => p === d || p.startsWith(d + '/'))
  return root ? p.slice(root.length + 1) : p
}

/** "3 files missing (a, b, c) — rescan or restore": one message for a stale DB. */
export function missingText(errors: WriteError[]): string {
  const names = errors.map(e => e.name ?? e.dir ?? '?')
  const shown = names.slice(0, 3).join(', ') + (names.length > 3 ? `, +${names.length - 3}` : '')
  return `${names.length} file${names.length !== 1 ? 's' : ''} missing (${shown}) — rescan or restore`
}

/** Toast for a history undo: done, files missing (left as they are), or failed. */
export function undoToast(res: { restored: number; errors?: WriteError[] }) {
  const gone = (res.errors ?? []).filter(e => e.error.startsWith('file missing'))
  if (gone.length) {
    toast(`Undo incomplete — ${missingText(gone)}. Those tracks were left as they are; Undo again once the files are back.`, 'error')
  } else if (res.errors?.length) {
    toast(`Undo incomplete — ${res.errors.length} failed: ${res.errors[0].error}`, 'error')
  } else {
    toast(`Undone — restored ${res.restored} track${res.restored !== 1 ? 's' : ''}`, 'success')
  }
}

/** Toast for an editing call: "Staged …" or "Saved …", plus any write errors. */
export function editToast(res: EditResult | undefined, what: string) {
  if (!res || res.staged) {
    toast(`Staged ${what} — Review to write`, 'info')
  } else if (res.missing) {
    toast(`Nothing written: ${missingText(res.errors ?? [])}`, 'error')
  } else if (res.errors?.length) {
    toast(`Saved ${what}; ${res.errors.length} failed: ${res.errors[0].error}`, 'error')
  } else {
    toast(`Saved ${what}`, 'success')
  }
}

/** The server's message out of a failed request ("… → 400: {"detail": …}"). */
export function errText(e: unknown): string {
  const m = String(e).match(/→ \d+: ([\s\S]*)$/)
  if (!m) return String(e)
  try { return JSON.parse(m[1]).detail ?? m[1] } catch { return m[1] }
}

// ─── Review dialog ──────────────────────────────────────────────────────────

function modalShell(title: string) {
  const overlay = document.createElement('div')
  overlay.className = 'fix-confirm-overlay'
  overlay.innerHTML = `
    <div class="fix-confirm-modal review-modal" role="dialog" aria-label="${esc(title)}">
      <div class="fix-confirm-header">
        <span class="fix-confirm-title"></span>
        <button class="btn btn-ghost btn-icon fix-confirm-close" aria-label="Close">✕</button>
      </div>
      <div class="fix-confirm-body"></div>
      <div class="fix-confirm-footer"></div>
    </div>`
  document.body.appendChild(overlay)
  const close = () => { overlay.remove(); document.removeEventListener('keydown', onKey) }
  const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') close() }
  document.addEventListener('keydown', onKey)
  overlay.addEventListener('click', e => { if (e.target === overlay) close() })
  overlay.querySelector('.fix-confirm-close')!.addEventListener('click', close)
  return {
    titleEl: overlay.querySelector<HTMLElement>('.fix-confirm-title')!,
    body: overlay.querySelector<HTMLElement>('.fix-confirm-body')!,
    footer: overlay.querySelector<HTMLElement>('.fix-confirm-footer')!,
    close,
  }
}

function fmtVal(v: string | null): string {
  return v ? esc(v.length > 60 ? v.slice(0, 60) + '…' : v) : '<span class="fix-empty">empty</span>'
}

const base = (p: string) => p.split('/').pop() ?? p
const dirOf = (p: string) => p.slice(0, p.lastIndexOf('/'))

/** One compact line for one change. */
function lineHtml(l: StagedLine, failures: Map<string, string>): string {
  let what: string, from: string, to: string
  if (l.kind === 'tag') {
    what = `<span class="rv-subject">${esc(l.name)}</span> · ${esc(FIELD_LABELS[l.field] ?? l.field)}`
    from = fmtVal(l.old); to = fmtVal(l.new)
  } else if (l.kind === 'path') {
    const sameDir = dirOf(l.old!) === dirOf(l.new!)
    what = `<span class="rv-subject">${esc(l.name)}</span> · ${sameDir ? 'rename' : 'move'}`
    from = esc(sameDir ? base(l.old!) : shortPath(l.old!))
    to = esc(sameDir ? base(l.new!) : shortPath(l.new!))
  } else {
    what = `<span class="rv-subject">📁 ${esc(base(l.src))}</span> · folder (${l.tracks} track${l.tracks !== 1 ? 's' : ''} + files)`
    from = esc(l.old ? shortPath(l.old) : shortPath(l.src))
    to = l.new ? esc(shortPath(l.new)) : '<span class="fix-empty">stays</span>'
  }
  const key = l.kind === 'folder' ? `dir:${l.src}` : `id:${l.id}`
  const err = failures.get(key)
  const shared = l.kind === 'folder' && l.new && /\/Shared(\/|$)/.test(l.src) && !/\/Shared(\/|$)/.test(l.new)
  const x = l.kind === 'folder' ? `data-dir="${esc(l.src)}"` : `data-track="${l.id}" data-field="${l.kind === 'path' ? 'path' : esc(l.field)}"`
  return `<li class="rv-line${err ? ' rv-failed' : ''}">
      <button type="button" class="rv-x" ${x} title="Don't write this one: drop it from what's staged (the file is untouched)" aria-label="Discard this change">✕</button>
      <span class="rv-what">${what}</span>
      <span class="rv-from">${from}</span><span class="rv-arrow">→</span><span class="rv-to">${to}</span>
      ${err ? `<span class="rv-note rv-err">⚠ ${esc(err)}</span>` : ''}
      ${shared ? '<span class="rv-note rv-warn">leaving Shared: unmonitor in Lidarr first</span>' : ''}
    </li>`
}

const MAX_LINES = 500

/** Staged changes as actions (newest first); expand one to see its changes. */
export async function openReview(onChanged: () => Promise<void>) {
  const m = modalShell('Review changes')
  const failures = new Map<string, string>()
  const open = new Set<string>()

  const render = async () => {
    const r = await api.staged.actions()
    const groups: { key: string; summary: string; ts?: number; lines: StagedLine[]; details: boolean; count: number; undo: boolean }[] =
      r.steps.map((s, i) => ({ key: `s${s.id}`, summary: s.summary, ts: s.ts, lines: s.lines,
                               details: s.details, count: s.count, undo: i === 0 }))
    if (r.other.length) groups.push({ key: 'other', summary: 'Other staged changes', lines: r.other,
                                      details: true, count: r.other.length, undo: false })
    // Open anything with a failure, and a lone action.
    for (const g of groups) {
      if (g.lines.some(l => failures.has(l.kind === 'folder' ? `dir:${l.src}` : `id:${l.id}`))) open.add(g.key)
    }
    if (groups.length === 1) open.add(groups[0].key)

    m.titleEl.textContent = 'Review changes'
      + (groups.length ? ` — ${groups.length} action${groups.length !== 1 ? 's' : ''}` : '')
    m.body.innerHTML = ''
    m.footer.innerHTML = ''
    if (!groups.length) {
      m.body.innerHTML = '<p class="review-empty">Nothing staged. Edits wait here until you write them.</p>'
      const ok = document.createElement('button')
      ok.className = 'btn btn-ghost'
      ok.textContent = 'Close'
      ok.addEventListener('click', m.close)
      m.footer.append(ok)
      return
    }

    const list = document.createElement('ul')
    list.className = 'rv-actions'
    for (const g of groups) {
      const isOpen = open.has(g.key)
      const n = g.details ? g.lines.length : g.count
      const li = document.createElement('li')
      li.className = 'rv-action' + (isOpen ? ' rv-open' : '')
      const when = g.ts ? new Date(g.ts * 1000).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }) : ''
      li.innerHTML = `
        <div class="rv-head" data-key="${g.key}">
          <span class="rv-caret">${isOpen ? '▾' : '▸'}</span>
          <span class="rv-summary">${esc(g.summary)}</span>
          <span class="rv-meta">${n.toLocaleString()} change${n !== 1 ? 's' : ''}${when ? ' · ' + esc(when) : ''}</span>
          ${g.undo ? '<button class="btn btn-ghost btn-sm rv-undo" title="Undo the newest staged action: what it replaced comes back (files are untouched)">↶ Undo</button>' : ''}
          ${g.key.startsWith('s') && g.details ? `<button class="btn btn-ghost btn-sm rv-discard" data-step="${g.key.slice(1)}" title="Drop what this action staged, whichever action it is; changes staged by other actions stay">Discard</button>` : ''}
        </div>
        ${isOpen ? `<ul class="rv-lines">${
          !g.details ? '<li class="rv-line rv-nodetail">Details weren\'t recorded for this action (staged before this version).</li>'
          : g.lines.slice(0, MAX_LINES).map(l => lineHtml(l, failures)).join('')
            + (g.lines.length > MAX_LINES ? `<li class="rv-line rv-nodetail">…and ${(g.lines.length - MAX_LINES).toLocaleString()} more</li>` : '')
        }</ul>` : ''}`
      list.appendChild(li)
    }
    m.body.appendChild(list)

    list.querySelectorAll<HTMLElement>('.rv-head').forEach(h => {
      h.addEventListener('click', (e) => {
        if ((e.target as HTMLElement).closest('.rv-undo, .rv-discard')) return
        const k = h.dataset.key!
        open.has(k) ? open.delete(k) : open.add(k)
        render()
      })
    })
    list.querySelector<HTMLButtonElement>('.rv-undo')?.addEventListener('click', async (e) => {
      const b = e.currentTarget as HTMLButtonElement
      b.disabled = true
      try {
        const u = await api.staged.undo()
        toast(`Undid staged: ${u.summary}`, 'success')
        await onChanged()
        await render()
      } catch (err) {
        toast(`Undo failed: ${errText(err)}`, 'error')
        b.disabled = false
      }
    })

    // One action, or one change, dropped in any order.
    list.addEventListener('click', async (e) => {
      const t = e.target as HTMLElement
      const act = t.closest<HTMLButtonElement>('.rv-discard')
      const one = t.closest<HTMLButtonElement>('.rv-x')
      if (!act && !one) return
      const b = (act ?? one)!
      b.disabled = true
      try {
        if (act) await api.staged.discardStep(Number(act.dataset.step))
        else if (one!.dataset.dir) await api.staged.discard([], [one!.dataset.dir])
        else await api.staged.discardPart(Number(one!.dataset.track), one!.dataset.field!)
        await onChanged()
        await render()
      } catch (err) {
        toast(`Discard failed: ${errText(err)}`, 'error')
        b.disabled = false
      }
    })

    const discardAll = document.createElement('button')
    discardAll.className = 'btn btn-ghost'
    discardAll.textContent = 'Discard all'
    discardAll.addEventListener('click', async () => {
      if (!confirm('Discard everything staged?')) return
      await api.staged.discard()
      await onChanged()
      m.close()
      toast('Discarded staged changes', 'info')
    })
    const write = document.createElement('button')
    write.className = 'btn btn-primary'
    write.textContent = `Write all (${r.count.toLocaleString()} item${r.count !== 1 ? 's' : ''})`
    write.addEventListener('click', async () => {
      write.disabled = discardAll.disabled = true
      write.textContent = 'Writing…'
      const bar = document.createElement('div')
      bar.className = 'rv-progress'
      bar.innerHTML = '<div class="bg-progress"><div style="width:0%"></div></div><div class="ma-dim"></div>'
      m.footer.prepend(bar)
      try {
        const { id } = await api.staged.applyStart()
        let res
        for (;;) {
          const w = await api.staged.applyStatus(id)
          if (w.error) throw new Error(w.error)
          const pct = w.total ? (w.done / w.total) * 100 : 0
          bar.querySelector<HTMLElement>('.bg-progress > div')!.style.width = `${pct}%`
          bar.querySelector<HTMLElement>('.ma-dim')!.textContent = w.total
            ? `${w.done.toLocaleString()} of ${w.total.toLocaleString()}${w.current ? ' · ' + w.current : ''}` : 'Starting…'
          if (w.result) { res = w.result; break }
          await new Promise(r => setTimeout(r, 400))
        }
        bar.remove()
        await onChanged()
        failures.clear()
        for (const e of res.errors as WriteError[]) failures.set(e.dir ? `dir:${e.dir}` : `id:${e.id}`, e.error)
        const done = `Wrote ${res.applied} track${res.applied !== 1 ? 's' : ''}`
          + (res.folders ? ` · moved ${res.folders} folder${res.folders !== 1 ? 's' : ''}` : '')
        if (res.missing) {
          toast(`Nothing written: ${missingText(res.errors)}. Discard their changes, or rescan, then write again.`, 'error')
          await render()
        } else if (res.errors.length) {
          toast(`${done}; ${res.errors.length} need attention`, 'error')
          await render()
        } else {
          toast(done, 'success')
          m.close()
        }
      } catch (e) {
        bar.remove()
        toast(`Write failed: ${errText(e)}`, 'error')
        await onChanged()   // whatever was written before the failure is on file now
        write.disabled = discardAll.disabled = false
        write.textContent = 'Write all'
      }
    })
    m.footer.append(discardAll, write)
  }
  try { await render() } catch (e) { toast(`Failed to load changes: ${e}`, 'error'); m.close() }
}

// ─── History dialog ─────────────────────────────────────────────────────────

export async function openHistory(onChanged: () => Promise<void>) {
  const m = modalShell('History')
  m.titleEl.textContent = 'History'
  const closeBtn = document.createElement('button')
  closeBtn.className = 'btn btn-ghost'
  closeBtn.textContent = 'Close'
  closeBtn.addEventListener('click', m.close)
  m.footer.append(closeBtn)

  const render = async () => {
    const entries = await api.library.history(100)
    if (!entries.length) {
      m.body.innerHTML = '<p class="review-empty">No changes yet.</p>'
      return
    }
    m.body.innerHTML = `<p class="review-hint">Undo a whole change (newest first for each track), or open one to undo single fields and moves in any order. Cover art isn't recorded.</p>`
    const list = document.createElement('ul')
    list.className = 'history-list'
    for (const h of entries) {
      const li = document.createElement('li')
      li.className = 'history-item' + (h.undone ? ' history-undone' : '')
      const when = new Date(h.ts * 1000).toLocaleString()
      li.innerHTML = `
        <button type="button" class="history-open" data-id="${h.id}" aria-expanded="false" title="Show what it changed, to undo one piece">▸</button>
        <div class="history-main">
          <span class="history-summary">${esc(h.summary)}</span>
          <span class="history-meta">${esc(when)}${h.count ? ` · ${h.count} track${h.count !== 1 ? 's' : ''}` : ''}</span>
        </div>
        ${h.undone ? '<span class="history-badge">Undone</span>'
                   : `<button class="btn btn-ghost btn-sm history-undo" data-id="${h.id}">Undo</button>`}`
      list.appendChild(li)
    }
    m.body.appendChild(list)
    list.querySelectorAll<HTMLButtonElement>('.history-open').forEach(b => {
      b.addEventListener('click', async () => {
        const li = b.closest('li')!
        const open = li.querySelector('.history-parts')
        if (open) { open.remove(); b.textContent = '▸'; b.setAttribute('aria-expanded', 'false'); return }
        b.textContent = '▾'; b.setAttribute('aria-expanded', 'true')
        await showParts(li, Number(b.dataset.id))
      })
    })
    const showParts = async (li: HTMLElement, id: number) => {
      li.querySelector('.history-parts')?.remove()
      const ul = document.createElement('ul')
      ul.className = 'history-parts'
      li.appendChild(ul)
      let r
      try { r = await api.library.historyParts(id) } catch (e) { ul.innerHTML = `<li>${esc(errText(e))}</li>`; return }
      if (!r.parts) { ul.innerHTML = '<li class="ma-dim">Written before single-field undo: undo it whole.</li>'; return }
      const label = (f: string) => f === 'path' ? 'location' : (FIELD_LABELS[f] ?? f)
      const val = (f: string, v: string | null) => f === 'path' && v ? esc(shortPath(v)) : fmtVal(v)
      ul.innerHTML = r.parts.map(p => `<li class="history-part${p.undone ? ' history-undone' : ''}">
          <span class="rv-what"><span class="rv-subject">${esc(p.name)}</span> · ${esc(label(p.field))}</span>
          <span class="rv-from">${val(p.field, p.old)}</span><span class="rv-arrow">→</span><span class="rv-to">${val(p.field, p.new)}</span>
          ${p.undone ? '<span class="history-badge">Undone</span>'
            : p.blocked ? `<span class="history-blocked" title="${esc(p.blocked)}">can't yet</span>`
            : `<button class="btn btn-ghost btn-sm history-undo-part" data-track="${p.track_id}" data-field="${esc(p.field)}">Undo</button>`}
        </li>`).join('')
      ul.querySelectorAll<HTMLButtonElement>('.history-undo-part').forEach(pb => pb.addEventListener('click', async () => {
        pb.disabled = true
        try {
          const u = await api.library.undoPart(id, Number(pb.dataset.track), pb.dataset.field!)
          await onChanged()
          if (u.change_undone) await render()
          else await showParts(li, id)
        } catch (e) {
          toast(`Undo failed: ${errText(e)}`, 'error')
          pb.disabled = false
        }
      }))
    }
    list.querySelectorAll<HTMLButtonElement>('.history-undo').forEach(b => {
      b.addEventListener('click', async () => {
        b.disabled = true
        try {
          undoToast(await api.library.undo(Number(b.dataset.id)))
          await onChanged()
          await render()
        } catch (e) {
          toast(`Undo failed: ${errText(e)}`, 'error')
          b.disabled = false
        }
      })
    })
  }
  try { await render() } catch (e) { toast(`Failed to load history: ${e}`, 'error') }
}
