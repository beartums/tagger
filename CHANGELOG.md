# Changelog

## Unreleased

## 0.3.0 — 2026-11-14

The first release of [beartums/tagger](https://github.com/beartums/tagger),
developed separately from [rnhinson/tagger](https://github.com/rnhinson/tagger)
since 2026-09.

### Paging & selection
- The status bar pages the track list: rows per page (50–1000), an editable
  top row, page N of M, and the number of tracks selected.
- ⌘/Ctrl-click adds or removes one track; Shift-click selects from the last
  track clicked, across pages.
- The header **Scan** follows the Files selection at any folder level; *Scan
  all* otherwise. A back button returns to the previous view.

### Edit mode
- **✎** turns the table's tag cells into a spreadsheet: type in place, move
  with Tab, Enter and the arrows, undo with ⌘/Ctrl-Z. Edited cells are marked
  with their old value on hover, and one click stages every edit.

### Search and find & replace
- Glob and regex toggles for track search. Settings → **Search** picks the
  fields searched; the full-text index covers every searchable field but
  lyrics and rebuilds itself when that list changes.
- Find & replace takes regular expressions with captures and a live preview,
  and works on year, track/disc number, BPM and lyrics too.
- Staging updates the rows in place instead of reloading the page and losing
  the scroll position.

### Review
- Staged changes are written in the background, with a progress bar in Review.

### Auto-fix & matching
- **Auto-fix** enriches the best three AcoustID matches from MusicBrainz,
  picks the release that matches the file's album, and proposes album, album
  artist, year, track/disc numbers, genre (per-genre chips) and composer.
- Click a row or field to leave it out, ✕ drops a track, and each track can
  take another match or edition. No checkboxes.
- **Match albums** matches several albums at once, covers included.
- Match album: *Unknown* tags fall back to folder names, unnamed tracks pair
  by number and length, and underscored names (`track_01`) count as
  placeholders.
- Fix: AcoustID enrichment always failed (musicbrainzngs rejected the
  `release-groups` include on recording lookups).

### Cover art
- Settings choose where covers go (folder file, embedded in tracks, or both)
  and the size they're resized to; cover size and bytes are tracked.
- **Change cover…** from disk, the Cover Art Archive, a MusicBrainz search
  (album/artist or release id, with thumbnails) or a URL.
- Find covers for many albums at once. **Covers…** moves, copies, shrinks or
  deletes the selection's covers. Quality → *Cover art* lists missing and
  oversized covers.

### Layout
- *Not in layout*: a resizable Layout column; hovering shows both paths with
  the differences marked.

### Project
- Repository, badges, image and user agents point at beartums/tagger; the
  README credits the original. Renovate keeps dependencies current.

### Staged changes
- **Review before writing.** Edits, auto-fix, find/replace, auto-number and
  moves are held as staged changes; the topbar **Review N changes** button
  shows a field-by-field diff and planned moves, and writes them as one
  undoable change (or discards them, all or per track). Settings → *Review
  changes before writing* turns it off. Cover art and ReplayGain still write
  immediately.
- The track list shows staged values in place (amber, with the on-file value
  on hover); rows with a planned move are marked.
- **History** dialog: every change, undo any of them newest-first per track.
- **Undo staged steps.** Each staging action (save, bulk edit, move,
  find/replace, auto-number) is a step, labelled by the fields it changed;
  ↶ undoes the newest staged step first, and Review has *Undo last step*.
  Writing or discarding a track drops it from the steps.

### Browsing
- The Tags panel is a tree: tag (Artist, Album Artist, Album, Genre, Year,
  Composer) → its values with counts → (for artists) albums. `(none)` lists
  tracks missing that tag. `GET /api/library/tag-values`, and `tag`/`value`
  filters on `/tracks` and the M3U export.
- Folder tree shows an open/close arrow only on folders with subfolders.
- **Sorting and the Quality/Format filters run on the server** over the whole
  view (every page), and combine with search. Numbers sort as numbers.
- **Select all N in this view**: after selecting the page, one click selects
  every track in the folder/tag/search across pages. The editor shows the
  values the whole selection shares (`POST /api/library/summary`).
- **Saving sends only the fields you changed** -- the form can stand for
  tracks on other pages, so re-sending untouched fields would overwrite them.

### Folders
- **Move…** and **Rename…** a folder from the Files panel: staged, written
  as one directory move (cover art and other files come along), undone as
  one. Destination must be inside a library root; library roots themselves
  can't be moved. Review warns when a folder leaves Shared (Lidarr).
- **Drag and drop** in the Files tree: drag a folder onto a folder, or
  tracks (the selection, across pages) onto a folder -- each drop is a
  staged move. Hovering a closed folder while dragging opens it. Folders
  holding library roots can't be moved.
- Staging no longer reloads the folder tree, and a reload after a write
  keeps open folders open.
- **Rename files…** (PowerRename-style) for the selection: plain or regex
  search, `$1` / `${name}` / `$0` captures, `${start=,increment=,padding=}`
  counters, apply to name / extension / both, case formatting, and a live
  before/after preview with per-row opt-out. Clashes (same new name, an
  existing file, rename chains) are flagged and never staged.
- The default track order sorts disc/track numbers as numbers (it put 10
  before 2).
- **Review lists actions, not files**: one row per staging action ("Rename
  29 files", "Set genre on 120 tracks", newest first) with ↶ Undo on the
  newest; expand a row for one compact line per change. Changes staged
  outside an action (e.g. a move left by a failed write) appear under
  "Other staged changes". Steps now record their result (`after`);
  steps from earlier versions still list and undo, without details.

### Safe moves
- **Library roots**: rename templates are relative to the deepest root
  containing the file (`TAGGER_LIBRARY_ROOTS` or Settings, globs allowed),
  so re-filing keeps files inside their library. Files outside every root are
  refused. Previously the template was relative to `TAGGER_MUSIC_DIR`, which
  could place files outside any mounted volume.
- Moves never overwrite, work across filesystems, handle case-only renames on
  case-insensitive shares, and prune the folders they empty. A move onto a
  different filesystem than the source is refused.
- **Undo of a move works across filesystems** (it used `Path.rename`, which
  fails with EXDEV), each track is committed on its own, and a partly failed
  undo stays retryable instead of being marked done.
- Settings PATCH only changes the fields sent (it used to reset the rest to
  defaults).
- **Write checks the files first.** If any staged track's file (or a staged
  folder) is gone from disk, nothing is written and one message lists them:
  rescan or restore. Previously each track failed on its own.
- **Undo checks the files, not just the DB.** A track whose file is missing
  (or whose tags can't be written back) is left as it is and listed; the
  change stays not-undone, so Undo can run again once the files are back.
  Undoing a delete whose trash copy is gone no longer re-adds the row.
- Template output keeps dots in the last part ("Vol. 2.mp3", not "Vol.mp3").

### Library layouts
- **Standard layout** (Settings → Layout, formerly the rename template) with
  **Check layout** per library (Settings → Libraries); ✎ gives a library its
  own layout, edited in place. Rename on save uses the library's layout.
- Quality → **Not in layout** lists tracks whose path differs from their
  library's layout, with the path the layout gives. **Re-file selected**
  stages moves for the chosen tracks only, reviewed before anything moves.
- Template variables `{artist_the}`, `{album_artist_the}`, `{album_the}`:
  a leading The/A/An moves to the end ("The Pogues" → "Pogues, The"), as
  Lidarr names folders.
- The default layout is now `{album_artist_the}/{album_the}/{track_number:02d} {title}`
  ("Pogues, The/…", as Lidarr names folders). A saved copy of the old default
  follows it.
- **Group layouts**: a group can set its own layout. A track uses the first
  set of its group's (one it was put in by hand), its library's, the standard.

### Settings
- Split into sections: Libraries · Layouts · Groups · Scanning · Sources ·
  Writing. Every layout (standard, per library with its Check, per group) is
  under Layouts; libraries are a table (on/off, tracks, group).
- **API keys and tokens encrypted at rest** (AcoustID, Discogs, LRCLIB) in
  settings.json with `TAGGER_SECRET_KEY` (a Fernet key; keep it in a
  Kubernetes Secret, not the config volume). Plain values already saved are
  encrypted at startup. The API never returns them — Settings shows "Saved",
  with Replace / Remove. Without the variable, storage stays plain text.
- **Test** beside each key/token (AcoustID, Discogs, LRCLIB): checks what
  you typed, else the saved one, with the service. Install hints for
  chromaprint / rsgain appear only when the tool is missing.
- **Logo**: the braces + tag lines + waveform mark in the header, the
  browser tab (favicon, light/dark) and About. No wordmark yet.
- Dark inputs throughout; built-in group names readable; hints no longer
  shouted in capitals.

### Duplicates
- **Duplicate tracks** match on cleaned-up title + first artist ("The",
  "feat. X", "(Remastered)", " - 2009 Remaster" ignored) **and lengths within
  2 s**, so live takes and remixes aren't duplicates; or **by sound** --
  chromaprint fingerprints from a background *Fingerprint* job (fpcalc, first
  30 s, resumable), which catches copies whose tags disagree.
- **Review duplicates…** replaces one-click *Keep best*: each group with its
  suggested keeper (lossless, then bitrate, sample rate, size) picked; change
  it, untick a group, then remove the rest from the library or move their
  files to the trash -- both undoable from History.
- **Duplicate albums** (Quality): the same cleaned-up album + album artist in
  more than one folder, shown in the album list.

### Selection & views
- **Lyrics column** (Columns menu): synced / plain / none, sortable.
- Quality views add their own column right after Title: *Missing lyrics* →
  **Lookup** (group, last lookup, a per-row **Search…**); *Not in layout* →
  where the layout puts it.
- **Albums can be multi-selected:** Ctrl/⌘-click or Shift-click in the album
  list or tiles; their tracks become the selection. A plain click still opens one.
- **Shift-click ranges across pages** (from the last track clicked, in view order).
- The selection toolbar is grouped (Tags · Look up · Files), destructive
  buttons at the right.
- **Group…** opens on the selection's current group; *Look up all…* names its
  scope ("Look up all N…" / "Look up N selected…"); the editor's lyrics
  Search… shows only for one track.
- Search lyrics: query buttons wrap instead of truncating, the picked hit's
  lyrics show beside the results, long artist/album names are clipped.
- **Lyrics… can search with one query for the whole selection:** Title /
  Artist / Album start as the shared value, or the `{placeholder}` where the
  tracks differ; edit and Fetch again to use it on every track (No lyrics
  ones too). *Use groups' queries* goes back.
- **Plain lyrics get upgraded:** tracks whose lyrics are plain text are looked
  up again (Lyrics… and background lookups of a selection); a synced find is
  offered in their place, otherwise they keep what they have ("plain kept").
  Not when Prefer is Plain.
- **Leftover cover art:** a staged move that empties a folder of everything
  but images moves them along when the tracks went to a folder the move
  created, else to the trash; the folder is pruned and undo puts them back.

### Lyrics
- **Quality → Missing lyrics** lists tracks with no lyrics, with each one's
  lyrics group and how its last lookup went.
- **Lyrics groups** (Settings → Lyrics groups): queries tried in order on
  LRCLIB, as title / artist / album templates. Built in: Standard, Cast album
  and Soundtrack (fall back to title + album with no artist, and drop
  "(Original Broadway Cast Recording)", "(From …)"), and **No lyrics** (a skip
  group: never looked up, never "missing"). Add your own. A track's group is
  the one it was put in (**Lyrics group…** on a selection; kept in Tagger's DB,
  not the files), else its library's (Settings → Libraries), else Standard.
- **Look up all…** (Missing lyrics view) runs a background lookup with
  progress and Cancel under Settings → Background. Finds are staged in batches
  for Review; tracks LRCLIB calls instrumental move to No lyrics; tracks
  already not found are skipped next time.
- **Search…** (editor, and per row in Lyrics…): search LRCLIB by hand from
  the group's queries, your own fields or free text; every hit with album,
  length (± against the track) and synced/plain, readable before you use it.
- LRCLIB's rate limit is respected: requests are spaced out (~80/min), a 429
  waits its Retry-After and retries, and a lookup that's still refused stops
  with what it found staged instead of recording tracks as "not found".
  Optional **LRCLIB app ID + API key** (Settings → Sources) for a registered app's
  far higher limit.
- "Lyrics groups" are now **Groups** (they carry a layout too);
  **Group…** on a selection.

### Audio quality
- Per-file **spectrogram** in the tag editor, rendered on demand by ffmpeg and
  cached by track + mtime — a lossy transcode dressed up as lossless shows up
  as a hard frequency shelf the codec and bitrate columns can't reveal.
- Click the spectrogram to open it full size in a dismissible lightbox.

### Metadata
- MusicBrainz rate limiting (1 req/s) and retry-with-backoff.
- Edition picker: list the releases a recording appears on and tag from the
  one you actually own.
- Lyrics and compilation tag fields, written per format.

### Library & scanning
- Scan-exclude glob patterns, and an opt-in auto-rescan interval.
- Windowed album grid and lazy-loaded cover art, so large libraries stay
  responsive.
- Empty the trash from Settings.

### UI
- Drag-resizable sidebar and tag-editor panes; widths persist per browser and
  reset on double-click.
- Responsive layout for phones and tablets, visible focus outlines, and a
  keyboard-shortcut help modal on `?`.
- Per-file rename preview in the editor, and a context-aware empty state.

### Operations & hardening
- `GET /api/health` for liveness/version checks, exempt from auth.
- Configurable `TAGGER_LOG_LEVEL`, structured scan-job logging, a JSON 500
  handler, and OpenAPI docs at `/docs`.
- Security: symlink-aware path containment, a cap on cover uploads, UUID
  validation before Cover Art Archive fetches, and FTS query sanitizing.

## 0.2.0

A large feature and hardening release building on the 0.1 proof of concept.

### Metadata & tagging
- Composer and BPM tag fields.
- Discogs as an optional second metadata source (token-gated).
- Tag inference from a file's path/name ("From filename").
- Album flows: auto-number by filename, and find/replace within a tag.
- Case normalization for shouty/lowercase tags.

### Library & files
- Full-library or single-folder rescan, with a concurrent-scan guard.
- File operations: move to a recoverable trash, or reorganize on disk using
  the rename template — both undoable.
- "Keep best quality" de-duplicator on the duplicates panel.
- Audio-quality columns (bitrate / sample rate / channels).
- Undo/redo history for tag edits, bulk edits, renames, removals, deletes,
  and reorganizes.

### Playback, playlists, loudness
- Inline, range-streamed audio playback in the tag editor.
- Export the current view or search as an `.m3u` playlist.
- ReplayGain scanning via `rsgain`/`loudgain`, bundled in the Docker image.

### Access & operations
- Optional single-password authentication with login rate-limiting.
- Live rename-template preview in settings.
- Multi-arch (`amd64` + `arm64`) images published to GHCR on version tags;
  runs under Docker and Apple's `container` runtime.
- GitHub Actions CI (backend pytest + frontend typecheck/build).
- Test suite covering pure logic, the HTTP API, and real-audio round-trips.

## 0.1.0

Initial proof of concept: browse a library, read/edit tags for FLAC/MP3/
AAC-M4A/OGG, bulk edits, MusicBrainz/AcoustID lookup, cover art, and
template-based rename-on-save.
