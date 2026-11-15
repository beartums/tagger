import { Track, IssueKey } from './api'

// ─── Track quality rating ───────────────────────────────────────────────────────

// The row's dot runs the per-track Quality checks; one turned off in Settings → Quality
// is left out here too. Poor: the track can't be identified. Fair: incomplete.
type DotCheck = { key: IssueKey; label: string; poor?: boolean; missing: (t: Track) => boolean }
const blank = (v: unknown) => v == null || v === ''
const DOT_CHECKS: DotCheck[] = [
  { key: 'missing_title',        label: 'title',        poor: true, missing: t => blank(t.title) },
  { key: 'missing_artist',       label: 'artist',       poor: true, missing: t => blank(t.artist) },
  { key: 'missing_album',        label: 'album',        poor: true, missing: t => blank(t.album) },
  { key: 'missing_album_artist', label: 'album artist', missing: t => blank(t.album_artist) },
  { key: 'missing_year',         label: 'year',         missing: t => blank(t.year) },
  { key: 'missing_track_number', label: 'track #',      missing: t => blank(t.track_number) },
  { key: 'missing_genre',        label: 'genre',        missing: t => blank(t.genre) },
  { key: 'covers_none',          label: 'cover art',    missing: t => !t.has_cover && t.folder_cover === false },
  { key: 'mb_no_album',          label: 'MusicBrainz album ID', missing: t => blank(t.mb_album_id) },
  { key: 'mb_no_release_group',  label: 'MusicBrainz release group ID',
    missing: t => !blank(t.mb_album_id) && blank(t.mb_release_group_id) },
  { key: 'mb_track_ids',         label: 'MusicBrainz track IDs',
    missing: t => !blank(t.mb_album_id) && (blank(t.mb_track_id) || blank(t.mb_release_track_id)) },
]

let dotOff = new Set<string>()
/** The checks turned off in Settings → Quality (the dot skips them). */
export function setQualityOff(keys: string[] | undefined) { dotOff = new Set(keys ?? []) }

function dotMissing(t: Track): DotCheck[] {
  return DOT_CHECKS.filter(c => !dotOff.has(c.key) && c.missing(t))
}

export function trackQuality(t: Track): 'good' | 'fair' | 'poor' {
  const m = dotMissing(t)
  return m.some(c => c.poor) ? 'poor' : m.length ? 'fair' : 'good'
}

/** The dot's tooltip: the rating and exactly what's missing. */
export function qualityTitle(t: Track): string {
  const m = dotMissing(t)
  if (!m.length) return 'Good: nothing missing'
  return `${m.some(c => c.poor) ? 'Poor' : 'Fair'}: no ${m.map(c => c.label).join(', ')}`
}

export const QUALITY_TITLES = {
  good: 'Nothing missing',
  fair: 'Incomplete: album artist, year, track #, genre, cover art or MusicBrainz IDs',
  poor: 'Missing title, artist or album',
}

export const QUALITY_ISSUES: { key: IssueKey; label: string; warn?: boolean; group?: string }[] = [
  { key: 'missing_title',        label: 'Missing title'    },
  { key: 'missing_artist',       label: 'Missing artist'   },
  { key: 'missing_album',        label: 'Missing album'    },
  { key: 'missing_album_artist', label: 'Missing album artist' },
  { key: 'missing_year',         label: 'Missing year'     },
  { key: 'missing_genre',        label: 'Missing genre'    },
  { key: 'missing_track_number', label: 'Missing track #'  },
  { key: 'duplicate_tracks',     label: 'Duplicate tracks', warn: true },
  { key: 'duplicate_albums',     label: 'Duplicate albums', warn: true },
  { key: 'missing_files',        label: 'Missing files',    warn: true },
  { key: 'not_in_layout',        label: 'Not in layout'    },
  { key: 'missing_lyrics',       label: 'Missing lyrics'   },
  { key: 'covers_none',          label: 'No cover',               group: 'Cover art' },
  { key: 'covers_no_folder',     label: 'No folder cover',        group: 'Cover art' },
  { key: 'covers_no_tracks',     label: 'No track covers',        group: 'Cover art' },
  { key: 'covers_both',          label: 'Folder and track covers', group: 'Cover art' },
  { key: 'covers_oversized',     label: 'Larger than the size settings', group: 'Cover art' },
  { key: 'mb_no_album',          label: 'No album ID',            group: 'MusicBrainz' },
  { key: 'mb_no_release_group',  label: 'No release group ID',    group: 'MusicBrainz' },
  { key: 'mb_track_ids',         label: 'Track IDs incomplete',   group: 'MusicBrainz' },
  { key: 'mb_mixed_album',       label: 'Several releases in one folder', group: 'MusicBrainz', warn: true },
]

// ─── Case normalization ─────────────────────────────────────────────────────────

const SMALL_WORDS = new Set([
  'a', 'an', 'the', 'and', 'but', 'or', 'for', 'nor',
  'on', 'at', 'to', 'by', 'in', 'of', 'up', 'with', 'from',
])

export function toTitleCase(s: string): string {
  return s.replace(/\S+/g, (word, offset) => {
    const lower = word.toLowerCase()
    if (offset > 0 && SMALL_WORDS.has(lower)) return lower
    return lower.charAt(0).toUpperCase() + lower.slice(1)
  })
}

export function needsNormalization(s: string | null | undefined): boolean {
  if (!s || s.length < 2) return false
  if (!/[a-zA-Z]{2}/.test(s)) return false
  return s === s.toUpperCase() || s === s.toLowerCase()
}

export const NORMALIZE_FIELDS: (keyof Track)[] = ['title', 'artist', 'album', 'album_artist', 'genre']
