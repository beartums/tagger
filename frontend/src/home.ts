// The landing page (#home): the library at a glance, what's waiting, and what
// changed lately. The logo and a visit without an address open it. Its links
// call back into main.ts (HomeActions) to open views.
import { api, ChangeLogEntry } from './api'
import { esc } from './util'
import { QUALITY_ISSUES } from './quality'
import { LOGO_MARK } from './logo'

export interface HomeActions {
  allTracks(): void
  albums(): void
  library(path: string): void
  album(directory: string): void
  quality(key: string): void
  review(): void
  history(): void
  scanAll(): void
  settings(section?: string): void
  about(): void
}

export function ago(ts: number): string {
  const s = Math.max(0, Date.now() / 1000 - ts)
  const [n, u] = s < 90 ? [Math.round(s), 'second'] : s < 5400 ? [Math.round(s / 60), 'minute']
    : s < 129600 ? [Math.round(s / 3600), 'hour'] : [Math.round(s / 86400), 'day']
  return `${n} ${u}${n === 1 ? '' : 's'} ago`
}

const plural = (n: number, w: string) => `${n.toLocaleString()} ${w}${n === 1 ? '' : 's'}`

export async function renderHome(el: HTMLElement, act: HomeActions) {
  el.innerHTML = '<div class="home-loading">Loading…</div>'
  let h, about
  try { [h, about] = await Promise.all([api.home(), api.about()]) } catch (e) {
    el.innerHTML = `<div class="review-error">${esc(String(e))}</div>`; return
  }
  const label = new Map<string, string>(QUALITY_ISSUES.map(q => [q.key, q.label]))
  const libs = h.libraries.filter(l => l.active)
  const todo: string[] = []
  if (h.staged) todo.push(`<button class="home-row" data-go="review"><b>${plural(h.staged, 'staged change')}</b><span>review and write them</span></button>`)
  for (const j of h.jobs) todo.push(`<button class="home-row" data-go="background"><b>${j.kind === 'lyrics' ? 'Lyrics lookup' : 'Scan'} running</b><span>${j.total ? `${j.scanned.toLocaleString()} of ${j.total.toLocaleString()}` : 'starting'}</span></button>`)
  for (const q of h.quality.slice(0, 8)) todo.push(`<button class="home-row" data-quality="${esc(q.key)}"><b>${esc(label.get(q.key) ?? q.key)}</b><span>${plural(q.tracks, 'track')} · ${plural(q.albums, 'album')}</span></button>`)
  const change = (c: ChangeLogEntry) => `<li class="${c.undone ? 'home-undone' : ''}"><span>${esc(c.summary)}</span><span class="ma-dim">${ago(c.ts)}${c.undone ? ' · undone' : ''}</span></li>`

  el.innerHTML = `<div class="home">
    <header class="home-hero">
      <span class="home-mark">${LOGO_MARK}</span>
      <div class="home-title"><h1>tggr</h1><p class="ma-dim"><em>"the tggr's a wonderful thing!"</em></p></div>
      <button class="home-version" data-go="about" title="About tggr">${esc(about.image || 'v' + about.version)} · deployed ${ago(about.started)}</button>
    </header>
    <section class="home-stats">
      <button class="home-stat" data-go="tracks"><b>${h.tracks.toLocaleString()}</b><span>tracks</span></button>
      <button class="home-stat" data-go="albums"><b>${h.albums.toLocaleString()}</b><span>albums</span></button>
      <button class="home-stat" data-go="settings:libraries"><b>${libs.length}</b><span>librar${libs.length === 1 ? 'y' : 'ies'}</span></button>
      <button class="home-stat${h.staged ? ' home-stat-hot' : ''}" data-go="review"><b>${h.staged.toLocaleString()}</b><span>staged changes</span></button>
    </section>
    <div class="home-grid">
      <section class="home-card"><h2>To do</h2>
        ${todo.length ? todo.join('') : '<p class="ma-dim">Nothing waiting. Quality checks that have run found nothing.</p>'}
        ${h.quality.length > 8 ? `<button class="btn btn-link btn-sm" data-quality="">All ${h.quality.length} Quality checks with findings</button>` : ''}
      </section>
      <section class="home-card"><h2>Libraries</h2>
        ${h.libraries.length ? h.libraries.map(l => `<button class="home-row${l.active ? '' : ' home-off'}" data-library="${esc(l.path)}"><b>${l.writable ? '' : '🔒 '}${esc(l.name)}</b><span>${l.active ? plural(l.tracks, 'track') : 'off'}</span></button>`).join('')
          : '<p class="ma-dim">No library roots set: every music folder is one library.</p>'}
      </section>
      <section class="home-card"><h2>Recently added</h2>
        ${h.recent_albums.map(a => `<button class="home-album" data-album="${esc(a.directory)}">
            <img src="/api/covers/${a.cover_track_id}" alt="" loading="lazy" onerror="this.style.visibility='hidden'" />
            <span><b>${esc(a.album || a.directory.split('/').pop() || '')}</b><span class="ma-dim">${esc(a.artist || '')} · ${plural(a.tracks, 'track')}</span></span>
          </button>`).join('') || '<p class="ma-dim">No tracks yet: Scan all.</p>'}
      </section>
      <section class="home-card"><h2>Recent changes</h2>
        ${h.changes.length ? `<ul class="home-changes">${h.changes.map(change).join('')}</ul><button class="btn btn-link btn-sm" data-go="history">Open History</button>` : '<p class="ma-dim">Nothing written yet.</p>'}
      </section>
    </div>
    <nav class="home-actions">
      <button class="btn" data-go="tracks">Browse tracks</button>
      <button class="btn" data-go="albums">Albums</button>
      <button class="btn" data-go="scan">Scan all</button>
      <button class="btn btn-ghost" data-go="settings:backup">Backup</button>
      <button class="btn btn-ghost" data-go="settings">Settings</button>
      <a class="btn btn-ghost" href="${esc(about.source)}" target="_blank" rel="noopener">GitHub ↗</a>
    </nav>
  </div>`

  el.onclick = (e) => {
    const t = (e.target as HTMLElement).closest<HTMLElement>('[data-go], [data-quality], [data-library], [data-album]')
    if (!t) return
    if (t.dataset.quality !== undefined) return act.quality(t.dataset.quality)
    if (t.dataset.library) return act.library(t.dataset.library)
    if (t.dataset.album) return act.album(t.dataset.album)
    const go = t.dataset.go!
    if (go === 'tracks') act.allTracks()
    else if (go === 'albums') act.albums()
    else if (go === 'review') act.review()
    else if (go === 'history') act.history()
    else if (go === 'scan') act.scanAll()
    else if (go === 'about') act.about()
    else if (go === 'background') act.settings('background')
    else if (go.startsWith('settings')) act.settings(go.split(':')[1])
  }
}
