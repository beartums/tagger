// Match albums: more than one album folder selected. Each folder gets its best
// MusicBrainz release (searched by its tags, else its folder names; the top
// few scored track by track) and the album-level tags it would get are listed
// for approval. Review… opens the full Match album for one folder (titles,
// numbers, pairing). Staged per album, like any edit; the release's cover art
// (or one picked by hand) is written now, where Settings → Cover Art says.
// Backend: /api/lookup/album/*, /api/covers/set.
import { api, CoverAlbum, MbMatch } from './api'
import { caa, hasArt, openChangeCover, CoverSrc } from './covers'
import { toast } from './toast'
import { esc } from './util'
import { errText, shortPath } from './staged'
import { openMbAlbum, KEEP } from './mbalbum'

const TRIES = 4           // candidates scored per album
const GOOD = 0.9          // share of your tracks paired with the release (titles agree) at or above: ticked

const FIELDS: { key: string; label: string }[] = [
  { key: 'album', label: 'Album' }, { key: 'album_artist', label: 'Album artist' }, { key: 'year', label: 'Year' },
  { key: 'genre', label: 'Genre' }, { key: 'composer', label: 'Composer' }, { key: 'mb', label: 'MusicBrainz IDs' },
]
const TAG_KEYS = FIELDS.map(f => f.key)
const splitGenres = (g: string | null | undefined) => (g ?? '').split(';').map(x => x.trim()).filter(Boolean)
const MB_IDS = ['mb_track_id', 'mb_artist_id', 'mb_album_id', 'mb_album_artist_id', 'mb_release_group_id', 'mb_release_track_id']

interface Row {
  a: CoverAlbum
  status: 'waiting' | 'searching' | 'found' | 'none' | 'error' | 'staged'
  match: MbMatch | null
  quality: number
  paired: number           // share of the folder's tracks paired with a release track
  on: boolean
  off: Set<string>         // tags left out for this album (the switches above still apply to all)
  offGenres: Set<string>   // single genres left out
  cover: { src: CoverSrc; preview: string; label: string } | null
  coverCheck: 'waiting' | 'checking' | 'done'
  note: string
}

export function openMbAlbums(albums: CoverAlbum[], onDone: () => Promise<void>) {
  const rows: Row[] = albums.map(a => ({ a, status: 'waiting', match: null, quality: 0, paired: 0, on: false, off: new Set(), offGenres: new Set(),
    cover: null, coverCheck: 'waiting', note: '' }))
  let closed = false, busy = false, staged = false
  const overlay = document.createElement('div')
  overlay.className = 'fix-confirm-overlay'
  overlay.innerHTML = `
    <div class="fix-confirm-modal bc-modal mbb-modal" role="dialog" aria-label="Match albums on MusicBrainz">
      <div class="fix-confirm-header">
        <span class="fix-confirm-title">Match albums on MusicBrainz · ${albums.length} albums</span>
        <button class="btn btn-ghost btn-icon fix-confirm-close" aria-label="Close">✕</button>
      </div>
      <div class="mbb-fields" id="mbb-fields">
        <span class="mbb-fields-h">Write</span>
        ${FIELDS.map(f => `<button type="button" class="tog" data-field="${f.key}" aria-pressed="true" title="Click to leave it out for every album">${f.label}</button>`).join('')}
        <button type="button" class="tog" data-field="cover" aria-pressed="true" title="Written now, not staged; on per album only where it has no cover yet">Cover art</button>
        <span class="mbb-fields-h">Options</span>
        <button type="button" class="tog" id="mbb-orig" aria-pressed="true" title="The first release's year, not this edition's">Original year</button>
        <button type="button" class="tog" id="mbb-keep" aria-pressed="true" title="Off: replace the genre and composer tracks already have">Keep existing genre &amp; composer</button>
      </div>
      <div class="bc-body"><table class="track-table bc-table mbb-table"><thead><tr>
        <th class="bc-check"><input type="checkbox" id="mbb-all" title="All found matches" /></th><th>Your album → its MusicBrainz match</th><th></th>
      </tr></thead><tbody></tbody></table></div>
      <div class="settings-hint bc-where" id="mbb-hint">Only what would change is listed. Click a line (or one genre, or the new cover) to leave it out for that album. Titles and track numbers: <strong>Review…</strong>.</div>
      <div class="fix-confirm-footer">
        <span id="mbb-sum" class="ma-dim bc-sum"></span>
        <button class="btn btn-ghost" id="mbb-cancel">Cancel</button>
        <button class="btn btn-primary" id="mbb-go" disabled>Stage</button>
      </div>
    </div>`
  document.body.appendChild(overlay)
  const $ = <T extends HTMLElement>(sel: string) => overlay.querySelector<T>(sel)!
  const tbody = $('tbody'), goBtn = $<HTMLButtonElement>('#mbb-go'), sumEl = $('#mbb-sum'), allEl = $<HTMLInputElement>('#mbb-all')
  const pressed = (el: Element) => el.getAttribute('aria-pressed') === 'true'
  const origOn = () => pressed($('#mbb-orig')), keepOn = () => pressed($('#mbb-keep'))
  const fieldOn = (f: string) => pressed(overlay.querySelector(`#mbb-fields [data-field="${f}"]`)!)

  const close = async () => {
    if (busy) return
    closed = true
    for (const r of rows) if (r.cover?.src.file) URL.revokeObjectURL(r.cover.preview)
    overlay.remove(); document.removeEventListener('keydown', onKey)
    if (staged) await onDone()
  }
  // Escape closes the topmost dialog only (Review… sits above this one).
  const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape' && document.body.lastElementChild === overlay) close() }
  document.addEventListener('keydown', onKey)
  overlay.addEventListener('click', e => { if (e.target === overlay) close() })
  $('.fix-confirm-close').addEventListener('click', close)
  $('#mbb-cancel').addEventListener('click', close)

  const usable = (r: Row) => !!r.match && r.status === 'found'

  // What a row would write: its tag fields, its genres, its cover.
  const tagFields = (r: Row) => TAG_KEYS.filter(f => fieldOn(f) && !r.off.has(f)
    && (f !== 'genre' || splitGenres(r.match?.release.genre).some(g => !r.offGenres.has(g))))
  const coverOn = (r: Row) => !!r.cover && fieldOn('cover') && !r.off.has('cover')
  const anything = (r: Row) => tagFields(r).length > 0 || coverOn(r)

  function renderRow(i: number) {
    const r = rows[i], a = r.a, m = r.match
    const tr = tbody.querySelector<HTMLElement>(`tr[data-i="${i}"]`) ?? tbody.appendChild(document.createElement('tr'))
    tr.dataset.i = String(i)
    const cur = m?.current ?? { album: a.album, album_artist: a.artist, year: null, genre: null }
    const hasCover = a.folder || a.embedded > 0
    const nTracks = `${a.track_ids.length} track${a.track_ids.length !== 1 ? 's' : ''}`
    const title = `<div class="mbb-title">${esc(cur.album || '(no album)')}${cur.album_artist ? ` <span class="mbb-by">· ${esc(cur.album_artist)}</span>` : ''}</div>
      <div class="ma-dim bc-folder" title="${esc(a.directory)}">${esc(shortPath(a.directory))} · ${nTracks}</div>`
    const myCover = `<img class="mbb-cover" src="/api/covers/${a.track_ids[0]}" alt="" title="Its cover now" onerror="this.outerHTML='<span class=&quot;mbb-cover mbb-cover-none&quot; title=&quot;No cover now&quot;>no art</span>'" />`
    let covers = myCover, score = '', lines = '', same = ''
    if (m) {
      const rel = m.release
      const year = (origOn() ? rel.original_year : null) || rel.year
      const paired = m.items.filter(it => it.key)
      const writers = [...new Set(paired.map(it => m.release_tracks.find(t => t.key === it.key)?.composer).filter(Boolean))] as string[]
      const cls = r.paired >= GOOD ? 'mb-good' : r.paired >= 0.5 ? 'mb-ok' : 'mb-bad'
      score = `<span class="mb-score ${cls}" title="Your tracks whose title (or number and length) pairs with one of its tracks · overall fit ${Math.round(r.quality * 100)}%">${paired.length} of ${m.items.length} tracks match</span>`
        + `<div class="ma-dim bc-folder">${[rel.date, rel.country, `${m.release_tracks.length} on the release`].filter(Boolean).map(x => esc(String(x))).join(' · ')}</div>`
      // One line per field that would change: label · now → MusicBrainz. Click to leave it out.
      const sameAs: string[] = []
      const line = (f: string, label: string, now: string | null | undefined, next: string, nextHtml = esc(next)) => {
        if (!next) return ''
        if ((now ?? '') === next) { sameAs.push(label); return '' }
        const off = !fieldOn(f) || r.off.has(f)
        const why = !fieldOn(f) ? 'Off for every album (Write, above)' : `Click to ${off ? 'write it' : 'leave it out'} for this album`
        return `<button type="button" class="mbb-line${off ? ' mbb-line-off' : ''}" data-chip="${f}" title="${esc(why)}" ${fieldOn(f) && !busy ? '' : 'disabled'}>
          <span class="mbb-l">${label}</span><span class="mbb-now">${now ? esc(now) : '<i>none</i>'}</span><span class="mbb-arrow">→</span><span class="mbb-next">${nextHtml}</span></button>`
      }
      // Genres: one chip each (click one to leave it out); kept when the tracks have one and Keep is on.
      const genres = splitGenres(rel.genre)
      const kept = keepOn() && !!cur.genre
      let genreLine = ''
      if (genres.length && genres.join('; ').toLowerCase() !== (cur.genre ?? '').toLowerCase()) {
        const chips = genres.map(g => {
          const off = !fieldOn('genre') || r.off.has('genre') || r.offGenres.has(g) || kept
          return `<button type="button" class="mbb-chip${off ? ' mbb-off' : ''}" data-chip="genre" data-value="${esc(g)}" ${fieldOn('genre') && !busy && !kept ? '' : 'disabled'}
            title="${esc(kept ? 'Kept: the tracks already have a genre (Keep existing, above)' : `Click to ${off ? 'add' : 'leave out'} ${g}`)}">${esc(g)}</button>`
        }).join('')
        genreLine = `<div class="mbb-line mbb-line-static${kept || !fieldOn('genre') ? ' mbb-line-off' : ''}"><span class="mbb-l">Genre</span><span class="mbb-now">${cur.genre ? esc(cur.genre) : '<i>none</i>'}</span><span class="mbb-arrow">→</span><span class="mbb-next mbb-chips">${chips}${kept ? ' <span class="ma-dim">kept</span>' : ''}</span></div>`
      } else if (genres.length) sameAs.push('Genre')
      const had = [...new Set(m.items.map(it => it.composer).filter(Boolean))] as string[]
      const curComp = had.length ? `${had.slice(0, 2).join(', ')}${had.length > 2 ? ` +${had.length - 2}` : ''}` : ''
      const comp = writers.length ? `${writers.slice(0, 2).join(', ')}${writers.length > 2 ? ` +${writers.length - 2}` : ''}` : ''
      lines = [
        line('album', 'Album', cur.album, rel.album ?? ''),
        line('album_artist', 'Album artist', cur.album_artist, rel.album_artist ?? ''),
        line('year', 'Year', cur.year, year ? String(year) : ''),
        genreLine,
        line('composer', 'Composer', curComp || null, comp),
        line('mb', 'MusicBrainz IDs', null, 'added to every track'),
      ].join('')
      same = sameAs.length ? `<div class="mbb-same">Already the same: ${sameAs.join(', ')}</div>` : ''
      const newCover = r.cover
        ? `<button type="button" class="mbb-cover ${coverOn(r) ? '' : 'mbb-cover-off'}" data-chip="cover" ${fieldOn('cover') && !busy ? '' : 'disabled'}
             title="${esc(`${r.cover.label}${hasCover ? ' · this album already has a cover' : ''} — click to ${coverOn(r) ? 'leave it out' : 'write it'}`)}"><img src="${esc(r.cover.preview)}" alt="" /></button>`
        : `<span class="mbb-cover mbb-cover-none">${r.coverCheck === 'done' ? 'no art' : '…'}</span>`
      covers = `${myCover}<span class="mbb-arrow">→</span>${newCover}`
    }
    const status = {
      waiting: '<span class="ma-dim">Waiting…</span>', searching: '<span class="ma-dim">Searching MusicBrainz…</span>',
      none: '<span class="ma-dim">No release found — Review… to search by hand</span>',
      error: `<span class="review-error">${esc(r.note)}</span>`, found: '', staged: '',
    }[r.status]
    tr.className = r.on && usable(r) ? '' : 'mbb-row-off'
    tr.innerHTML = `
      <td class="bc-check"><input type="checkbox" ${r.on ? 'checked' : ''} ${usable(r) ? '' : 'disabled'} aria-label="Stage this album" /></td>
      <td class="bc-album">
        <div class="mbb-head"><div class="mbb-covers">${covers}</div><div class="mbb-id">${title}</div><div class="mbb-score-wrap">${score}</div></div>
        ${m ? `<div class="mbb-release">MusicBrainz: <strong>${esc(m.release.album ?? '')}</strong>${m.release.album_artist ? ` · ${esc(m.release.album_artist)}` : ''}${r.paired < GOOD ? ' <span class="mb-bad-note">— weak match, check it with Review…</span>' : ''}</div>` : ''}
        ${lines ? `<div class="mbb-lines">${lines}</div>` : ''}${same}
        ${status ? `<div>${status}</div>` : ''}${r.status === 'staged' ? `<div class="bc-done">✓ ${esc(r.note || 'Staged')}</div>` : ''}</td>
      <td class="mbb-actions"><button type="button" class="btn btn-ghost btn-sm" data-review ${r.status === 'staged' || busy ? 'disabled' : ''} title="Match it track by track">Review…</button>
        ${usable(r) ? `<button type="button" class="btn btn-ghost btn-sm" data-pick-cover ${busy ? 'disabled' : ''} title="Another cover: search MusicBrainz, a URL or a file">Cover…</button>` : ''}</td>`
  }
  function summary() {
    const n = rows.filter(r => r.on && usable(r) && anything(r)).length
    const pending = rows.filter(r => r.status === 'waiting' || r.status === 'searching').length
    sumEl.textContent = (pending ? `Searching… ${rows.length - pending} of ${rows.length} done · ` : '') + `${n} album${n !== 1 ? 's' : ''} to stage`
    goBtn.disabled = busy || !n
    goBtn.textContent = n ? `Stage ${n} album${n !== 1 ? 's' : ''}` : 'Stage'
    const can = rows.filter(usable)
    allEl.checked = can.length > 0 && can.every(r => r.on)
    allEl.indeterminate = !allEl.checked && can.some(r => r.on)
  }
  const renderAll = () => { rows.forEach((_, i) => renderRow(i)); summary() }
  renderAll()

  $('#mbb-fields').addEventListener('click', e => {
    const t = (e.target as HTMLElement).closest<HTMLButtonElement>('.tog')
    if (!t || busy) return
    t.setAttribute('aria-pressed', String(!pressed(t)))
    renderAll()
  })
  tbody.addEventListener('change', e => {
    const cb = e.target as HTMLInputElement
    const i = Number(cb.closest<HTMLElement>('tr')!.dataset.i)
    rows[i].on = cb.checked
    renderRow(i); summary()
  })
  allEl.addEventListener('change', () => {
    rows.forEach(r => { if (usable(r)) r.on = allEl.checked })
    renderAll()
  })
  tbody.addEventListener('click', e => {
    const c = (e.target as HTMLElement).closest<HTMLElement>('[data-chip]')
    if (c) {
      const i = Number(c.closest<HTMLElement>('tr')!.dataset.i), f = c.dataset.chip!, r = rows[i]
      if (c.dataset.value !== undefined) {
        const g = c.dataset.value
        if (!r.offGenres.delete(g)) r.offGenres.add(g)
      } else if (!r.off.delete(f)) r.off.add(f)
      renderRow(i); summary()
      return
    }
    const pc = (e.target as HTMLElement).closest<HTMLElement>('[data-pick-cover]')
    if (pc) {
      const i = Number(pc.closest<HTMLElement>('tr')!.dataset.i), r = rows[i], rel = r.match!.release
      openChangeCover(r.a.track_ids, rel.mb_album_id, { album: rel.album, artist: rel.album_artist ?? '' }, async () => {}, (src, preview) => {
        if (r.cover?.src.file) URL.revokeObjectURL(r.cover.preview)
        r.cover = { src, preview, label: src.file ? `From disk: ${src.file.name}` : src.url ? `From ${src.url}` : 'Picked by hand' }
        r.off.delete('cover')
        renderRow(i); summary()
      })
      return
    }
    const b = (e.target as HTMLElement).closest<HTMLElement>('[data-review]')
    if (!b) return
    const i = Number(b.closest<HTMLElement>('tr')!.dataset.i), r = rows[i]
    openMbAlbum(r.a.track_ids, async () => {
      Object.assign(r, { status: 'staged', on: false, note: 'Staged from Review' })
      staged = true
      renderRow(i); summary()
    })
  })

  // The best of the first few candidates, scored track by track; stop early on a near-perfect one.
  async function find(r: Row) {
    const s = await api.lookup.albumSearch(r.a.track_ids)
    let best: { id: string; quality: number } | null = null, failed: unknown = null
    for (const c of s.candidates.slice(0, TRIES)) {
      if (closed) return
      let q
      try { q = await api.lookup.albumScore(r.a.track_ids, c.mb_album_id) } catch (e) { failed = e; continue }   // try the next one
      if (!best || q.quality > best.quality) best = { id: c.mb_album_id, quality: q.quality }
      if (q.quality >= 0.9) break
    }
    if (!best && failed) throw failed
    if (!best || closed) { r.status = 'none'; return }
    const m = r.match = await api.lookup.albumMatch(r.a.track_ids, best.id)
    const paired = m.items.length ? m.items.filter(it => it.key).length / m.items.length : 0
    Object.assign(r, { quality: best.quality, paired, status: 'found', on: paired >= GOOD })
    // Its cover: written by default only where the album has none.
    if (r.a.folder || r.a.embedded > 0) r.off.add('cover')
    r.coverCheck = 'checking'
    // The release's own art, else the album's (another edition's, via its release group).
    const id = m.release.mb_album_id, rg = m.release.rg_id
    const rgArt = (size: number) => `https://coverartarchive.org/release-group/${rg}/front-${size}`
    ;(async () => {
      if (await hasArt(caa(id))) r.cover ??= { src: { mb_album_id: id }, preview: caa(id), label: "The release's cover (Cover Art Archive)" }
      else if (rg && await hasArt(rgArt(250))) r.cover ??= { src: { url: rgArt(1200) }, preview: rgArt(250), label: "The album's cover from another edition (Cover Art Archive)" }
      r.coverCheck = 'done'
      if (!closed) { renderRow(rows.indexOf(r)); summary() }
    })()
  }

  ;(async () => {
    // Two at a time: MusicBrainz is throttled server side, one request a second.
    let next = 0
    const worker = async () => {
      while (!closed && next < rows.length) {
        const i = next++, r = rows[i]
        if (r.status === 'staged') continue
        r.status = 'searching'; renderRow(i); summary()
        try { await find(r) } catch (e) { r.status = 'error'; r.note = errText(e) }
        if (closed) return
        renderRow(i); summary()
      }
    }
    await Promise.all([worker(), worker()])
  })()

  goBtn.addEventListener('click', async () => {
    busy = true; renderAll()
    let albumsDone = 0, tracks = 0, covers = 0, failed = 0, direct = false
    for (const [i, r] of rows.entries()) {
      if (!r.on || !usable(r) || !anything(r)) continue
      const m = r.match!
      sumEl.textContent = `Staging ${m.release.album}…`
      const done: string[] = []
      try {
        const fields = tagFields(r).flatMap(f => f === 'mb' ? MB_IDS : [f])
        if (fields.length) {
          const pairs: Record<number, string> = {}
          for (const it of m.items) if (it.key) pairs[it.id] = it.key
          const genres = splitGenres(m.release.genre)
          const res = await api.lookup.albumApply({
            mb_album_id: m.release.mb_album_id, pairs, fields, original_year: origOn(), cover: false,
            keep: keepOn() ? KEEP : [],
            unpaired: m.items.filter(it => !it.key).map(it => it.id),
            genre: r.offGenres.size ? genres.filter(g => !r.offGenres.has(g)).join('; ') : undefined,
          })
          tracks += res.changed; albumsDone++
          direct ||= res.changed > 0 && !res.staged     // staging off in Settings: written now
          done.push(res.changed ? `${res.staged ? 'Staged' : 'Written to'} ${res.changed} track${res.changed !== 1 ? 's' : ''}` : 'Tags already match')
        }
        if (coverOn(r)) {
          const res = await api.covers.set(r.a.track_ids, r.cover!.src)
          if (res.errors.length) throw new Error(`cover: ${res.errors[0].error}`)
          covers++; done.push('cover written')
        }
        Object.assign(r, { status: 'staged', on: false, note: done.join(' · ') })
      } catch (e) { failed++; r.status = 'error'; r.note = [...done, errText(e)].join(' · ') }
      staged = true
      renderRow(i)
    }
    busy = false; renderAll()
    const parts = [albumsDone ? `MusicBrainz tags ${direct ? 'written to' : 'staged on'} ${tracks} track${tracks !== 1 ? 's' : ''} in ${albumsDone} album${albumsDone !== 1 ? 's' : ''}` : '',
                   covers ? `${covers} cover${covers !== 1 ? 's' : ''} written` : ''].filter(Boolean)
    if (parts.length) toast(`${parts.join(' · ')}${albumsDone && !direct ? ' — Review to write the tags' : ''}${failed ? ` · ${failed} failed` : ''}`, failed ? 'error' : 'success')
    else if (failed) toast(`Match albums: ${failed} failed`, 'error')
    if (!failed) close()
  })
}
