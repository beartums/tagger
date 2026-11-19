# Changelog

## Unreleased

- **Delete files… can take the album's folder with it**: it now opens a
  dialog listing each folder the tracks leave. When every track in a folder
  is deleted, its other files (cover, .cue, logs, Scans/…) go to the trash too
  and the emptied folder is removed — each a toggle, and the folder can only
  go once its other files do. Undo puts everything back; Empty trash now also
  clears folders in it.
- **Moving a whole album brings its other files and removes the old folder**:
  cover art, .cue, rip logs, booklets, Scans/ and the like follow the tracks,
  a lyrics sidecar (.lrc) is renamed with its track, and the emptied folder is
  removed. Move to layout lists them per folder with a toggle (on when every
  track in the folder moves). A name already taken at the destination keeps
  what's there; moving into another album's folder sends the cover to the
  trash. Undo puts everything back.
- **Match album shows the cover it would write**: the album's cover now → the
  release's cover from MusicBrainz. It's on by default when the album has no
  cover yet and off when it has one; click the new cover to switch. (It was an
  unticked checkbox with no preview.)
- **Files → Move to layout…**: moves the selected files to where their layout
  puts them. It first shows the final folders and file names (hover a file to
  see where it is now) and what will stay put and why; OK stages exactly that.
  Quality → Not in layout's "Re-file selected" now opens the same preview.
- **Add to MusicBrainz works for albums with many guest artists**: each
  artist is looked up in its own request, with progress shown in the
  MusicBrainz tab (one request for all of them ran past the proxy's 30 s).
- **Error messages stay until clicked**, so there's time to read them.
- **A message log** (bell, top right): every message tggr has shown, newest
  first, kept across reloads (last 200). The bell is marked while there are
  errors you haven't looked at.
- **A Groups tab** beside Tags, Files and Quality: tracks in any group, each
  group (with its count), and those in no group.
- **Groups in the filter bar**: pick one or more (tracks in any of them),
  combined with the other filters.
- **The editor opens for several albums too**: album-wide fields, differing
  values locked as for several tracks.
- **See the selection**: click "N selected" to show only what's selected
  (a *Selected only* chip; ✕ or Back returns with the selection kept). Unticking
  takes rows out; when none are left it goes back.
- **Hide or show the tag editor** with the panel icon on the top line, whenever
  something is selected (remembered).
- **A landing page.** The logo (and a visit without an address) opens it: the
  counts, what's waiting (staged changes, running jobs, Quality checks with
  findings), libraries, recently added albums and recent changes, each a way
  in; plus the version and how long since it was deployed.
- **Backup by parts**: Data (database + trash), Settings, Interface and
  Environment (a `tggr.env` of the `TGGR_*` settings; secrets only when asked).
  Restore takes the parts you pick; an environment file is shown to set on the
  container.
- **About** adds how long ago it was deployed, the data folder and sizes,
  changelog / releases / issues links, the license and the upstream credit.
- **Groups are yours.** There are none until you make one (Settings → Groups),
  and a track can be in several (**Files ▾ → Groups…**, which also makes a new
  one). Each group can have a **Layout**, which wins over the library and
  default layouts, and **Quality** checks that leave its tracks out (Missing
  lyrics for an Instrumental group). Two of a track's groups with different
  layouts: re-filing it is an error naming them, and Quality lists it under
  *Groups' layouts clash*.
- **Lyrics lookups are the same for every track**: the plain queries first,
  then the cast-album and soundtrack ones. Groups no longer change them; the
  built-in Standard / Cast / Soundtrack / No lyrics groups and the per-library
  default group are gone. A track LRCLIB calls instrumental stops counting as
  missing lyrics.
- **An emptied view goes back.** When an opened album, a filter, a Quality
  check or a search loses all its tracks to something you did (fixed, written,
  moved, removed, deleted), tggr returns to the view before it and says so.
  Going somewhere that happens to be empty stays put.
- **Filters survive a refresh.** They're part of the page address now, so
  refresh, Back/Forward and copied links keep them. The album view's count no
  longer shows a stale number before its list loads.
- **Add to MusicBrainz comes back to your tab.** MusicBrainz opens in one tab
  of its own; when you submit, that tab hands the new release to the tggr tab
  you started from (still on the same view) and closes.
- **Add to MusicBrainz links the artists.** Each artist arrives linked in the
  release editor: from the tags when the files were matched before, else the
  one MusicBrainz artist with exactly that name. Names shared by several
  artists, or new to MusicBrainz, are left for you, and the message says which.
- **Add to MusicBrainz: no "Unknown field" warning.** It sent a medium
  position MusicBrainz doesn't take; now only documented fields go, and a test
  holds it to that list.
- **Undo one piece at a time, in any order.** In Review, ✕ on any line drops
  that one staged field (or move) and **Discard** on any action drops what it
  staged, oldest or newest. In History, open a change (▸) to undo one field or
  one move on one track. The only limit: a field a later change set again on
  the same track can't be undone until that later piece is (it says which).
- **Add to MusicBrainz: disc ID afterwards.** MusicBrainz's release editor has
  no disc ID field, so tggr no longer sends one; when MusicBrainz sends you
  back, a next-steps box links to its Attach CD TOC page with the disc's ID
  filled in, then Match album.
- **CD rips: what the ripper recorded.** tggr reads the disc ID, table of
  contents, barcode, ISRCs, how the ripper named the disc (exact / near /
  none) and cdparanoia's per-track trouble. One album selected shows them in a
  "From the CD" box, with **Attach on MusicBrainz** (the disc ID) and
  **Submit to MusicBrainz** (ISRCs, via MagicISRC) links. Two Quality checks:
  *Named by a near match* and *Read trouble while ripping*.
- **Add to MusicBrainz…** (Tags menu): opens MusicBrainz's Add release page
  filled in from the album (titles, lengths, artist, year, barcode, recordings,
  the CD's disc ID); you check it and submit there, and MusicBrainz sends you
  back to Match album with the new release first.
- **Disc IDs from track lengths** (Tags menu): older rips get their disc ID and
  table of contents worked out from the tracks' exact lengths, checked against
  MusicBrainz, and staged.
- **Match album tries the disc ID first**: releases MusicBrainz has the rip's
  disc ID on come first, marked *disc ID*.
- **Tagger is now tggr.** The name in the app, README, logo, user agents and
  links (the repo becomes `beartums/tggr`, the image `ghcr.io/beartums/tggr`).
  Every `TAGGER_*` setting also works as `TGGR_*` (`TGGR_` wins when both are
  set), and interface preferences carry over by themselves. Compose examples
  now name the volume `tggr-config`: an existing `tagger-config` volume keeps
  working if you keep its name, or move with Backup.
- **Backup and restore** (Settings → Data → Backup): one zip with the
  database, settings, the trash Undo uses, and this browser's interface
  preferences. Restore replaces them all, so tggr can move to a new config
  volume without renaming the old one.
- **ReplayGain is staged.** ReplayGain… (Tags menu) measures the selection and
  stages the gain and peak tags, so they show in Review, write with the rest
  and can be undone. Each album is measured on its own; album gain is set only
  when the whole album is selected (before, several albums got one shared
  album gain).
- **A cleaner toolbar.** The top line holds the count and the view controls as
  icons (tracks | albums, list | tiles, sheet edit in the track list only,
  columns). Select something and it turns into the selection: Match, Tags ▾,
  Files ▾ and Export M3U as one icon bar (Remove and Delete are at the bottom
  of Files; Export M3U exports the selection).
- **A real filter bar.** The funnel lists every Quality check, quality rating,
  format, has lyrics and has staged changes; each filter is a chip with ✕, and
  they combine (checks all apply, formats and ratings any of).
- **Album editing.** One album selected: the editor shows album fields only,
  with artist and composer locked. More than one album: no editor; use the
  actions.
- **Locked fields.** Several tracks (or an album) selected: a field holding
  different values is locked; hover the lock to see that what you type replaces
  it on every track, click it to edit.
- **Match albums is easier to read.** Each album is a header (cover now →
  MusicBrainz cover, the album, how many tracks match) and a short table of
  only what would change: field · now → MusicBrainz. Unchanged fields are
  summed up in one line. Click a line (or one genre) to leave it out; the
  Write and Options switches across the top are buttons, not checkboxes.
- **The album view counts albums** in the side panel: Tags values and Quality
  checks show albums instead of tracks (hover for both).
- **Album pager always says where you are**: "albums 1–60 of 60 · page 1 of
  1", even when everything fits on one page.
- **Bigger covers in the album list**: drag the edge of the cover column;
  covers and rows grow with it (double-click to reset). Remembered per
  browser.
- **Settings, reorganized**: sections down the left, grouped (Library ·
  Sources · Output), each with a heading and a line on what it's for. Each
  topic is a card with a real heading, what it's for, and a status pill
  (Set up, Not set up, Tool missing; Connected or Failed after a Test). Field
  names sit left of their inputs in normal case; one Test per card, in its
  footer. The save bar names the sections with unsaved changes, and the rail
  marks them with a dot.
- **Settings → Sources is split** into **Integrations** (Lidarr, Navidrome,
  Music Assistant, player rescans) and **Metadata** (AcoustID, Discogs,
  LRCLIB). ReplayGain moved to Writing.
- **Fixed: paging in the album view.** The pager paged tracks, so Next said
  you'd moved on while the same albums stayed. In the album view (list and
  tiles) it now pages albums and counts them ("albums 51–60 of 60"); the
  header box selects that page's albums.
- **Quality checks are switched in the Quality panel** (Settings → Quality is
  gone). Every check is listed with a small switch; one that's off isn't run
  with the panel, shows its last count dimmed, and has ↻ to check it now.
- **Layouts: one default, overrides only where you want them.** Library and
  group layouts list only the ones you add (Add a library/group layout…, ✕ to
  remove). Which libraries are checked against their layout is a row of
  switches under the default.
- **Characters in names, per character.** Smart colons is a switch; each of
  / \ : ? * < > | " can have its own replacement, the rest get "all others".
  Start from Lidarr's, Remove all, Underscores, Look-alikes (／ ： ？ …) or your
  Lidarr's settings. Several to a line; examples in the text. Moved below all
  the layouts. (Saved before? Your Lidarr-style choice carries over.)
- **Settings: Cancel** shows once you change something; leaving Settings with
  unsaved changes asks first.
- **The Tagger logo on Settings** returns to the screen you were on.
- **The status bar is back** at the bottom of the window: where you are, the
  view's track count, and the selection (with Clear). The bar under the list
  is just the pager now, shown only when there's paging to do.
- **Albums select like tracks**: a box on each album list row (and a
  select-all in the header) and in the corner of each tile; Shift-click a box
  for a range. Clicking the album itself still opens it.
- **Match albums** ticks a release only when at least 90% of the album's
  tracks pair with it (was 80%), taking the first candidate that fits that
  well; Review… opens the track-by-track match for any album.
- **Fixed: staging during a scan failed with "database is locked".** The scan
  held the database's write lock while it read the next 200 files (seconds on
  a NAS), longer than other writes waited (5 s). It now reads with no lock
  held and writes each batch (200 files or 1 s) in one short transaction, and
  other writes wait up to 30 s.
- **Fixed: "unsaved changes" warnings with nothing changed.** The tag editor
  counted any control it holds (a chip's search box, other inputs) as an
  edit, and refilling it never cleared those. Now only what Save writes
  counts: a tag field whose value differs from what it was filled with, the
  Compilation box, or chip changes on a multi-track selection.
- **Album quality dots**: the album list and album tiles get the same dot as
  tracks, rated by the album's worst track; the tooltip says how many tracks
  miss each thing ("no genre (3 of 10 tracks)"). Counted with the Quality
  panel's own checks, and skipping the ones turned off in Settings → Quality.
- **Sort the album list** by any column (click a header; again to reverse),
  Quality included. Remembered per browser.
- **The list's quality dot checks more**: red when a track has no title,
  artist or album; yellow for no album artist, year, track #, genre, cover art
  (in the file or the folder) or MusicBrainz album ID, or incomplete
  MusicBrainz release group / track IDs. The tooltip names everything
  missing. Checks turned off in Settings → Quality are skipped by the dot
  too. New Quality check: *Missing album artist*.
- **Settings → Quality**: turn any Quality check off (struck through) so the
  Quality panel stops running it -- Missing files, duplicates and Not in
  layout are slow on a big library. **Check** runs one on demand and keeps its
  count of tracks and albums with the date; the panel shows a check that's
  off dimmed, with that last result. `GET /api/library/issues` now returns
  `{tracks, albums, at, off}` per check.
- **MusicBrainz Release Group and Release Track IDs**: Match album (single
  and bulk) and Auto-fix now write them with the other MusicBrainz IDs (one
  switch, as before). Lidarr matches on both.
- **MusicBrainz IDs are read from the files**: they were written but never
  read back, so the library didn't know which files had them. The next scan
  re-reads every file once.
- **Quality → MusicBrainz**: *No album ID* (never matched), *No release group
  ID* and *Track IDs incomplete* (matched before this release, or by a tool
  that skips them), *Several releases in one folder* (album IDs differ within
  a folder -- Lidarr splits those).
- **Sheet edit mode edits cells only**: no row checkboxes, no tag editor
  beside it, and clicks (shift-click too) edit the cell instead of selecting.
  Starting it asks first if the tag editor has unsaved changes.
- **No silent loss of edits**: a value typed in an open table cell is kept
  when the list changes under it (search, paging, Back). The tag editor asks
  before any selection change (click, arrows, Esc, Clear, close) throws away
  its unsaved changes, and keeps them when the same tracks are re-shown;
  closing or reloading the tab asks too.
- **One bar under the list**: the status bar is gone. Where you are, the
  pager (prev/next, editable top row, page N of M, rows per page) and the
  selection share one row below the track list, replacing the old Prev/Next.
  The track count stays in the toolbar.
- **Integrations** (Settings → Sources), each optional, keys encrypted:
  - **Lidarr**: Settings → Layouts → *Copy from Lidarr* sets *Characters in
    names* from Lidarr's own naming choices and shows its folder and track
    formats beside them.
  - **Navidrome** and **Music Assistant** rescan after Tagger changes files
    (tags, moves, covers, ReplayGain); a big write is one rescan. *Player
    rescans* sets when: N minutes after the last change (each change restarts
    the wait; default 5), N seconds after a change (later changes don't push it
    back), or off. A rescan that's waiting shows when it's due.
  - **Just the changed folders**: map Tagger folders to Navidrome libraries
    (`/music = 1:`; Test lists the library ids) and Navidrome scans only the
    folders that changed -- both ends of a move, the nearest folder that still
    exists for one moved away. Unmapped changes or more than 50 folders: a
    full scan. Music Assistant can only sync whole providers, so its map
    (Tagger folder = provider instance id) syncs just the providers whose
    folders changed. Both need an admin (Navidrome's `startScan`, MA's `music/sync`);
    Test says so, and MA's Test lists its file providers to pick from. The
    last result shows under each; *Rescan now* forces one.
- **Names follow Lidarr's character rules**: a "/" inside a tag no longer
  makes an extra folder (AC/DC filed as `AC/DC/…`); each value is cleaned on
  its own, as Lidarr does. With the defaults (Lidarr's *Replace Illegal
  Characters* on, colons *Smart*): `/` and `\` → `+`, `?` → `!`, `*` → `-`,
  `< > | "` removed, `a: b` → `a - b`, `10:30` → `10-30`. Settings → Layouts →
  *Characters in names* matches other Lidarr choices. Folders named the old
  way (`_` for these characters) now show under *Not in layout*; Re-file moves
  them. Typed folder renames use the same rules.
- **Browse paths in the Tags panel**: each tag opens down through the tags
  you choose, in your order (Genre › Album Artist › Album, Year › Genre, …).
  ✎ beside a tag opens its path: drag tags in or along it, × to remove (or
  click a tag to add it at the end). Saved in Settings; the default keeps
  Artist › Album and Album Artist › Album. Every level filters by the whole
  path above it; links and the back button carry the path (old links still
  open).
- Each level of the Tags tree counts the level below and the tracks:
  "Electronic — 3 album artists · 21"; the last level shows tracks only.
  Tag headers count their values ("10 artists").
- **Artist and composer chips**: with several tracks selected, artist and
  composer are edited like genre -- add or remove one value on every track,
  keeping the values each track already has. Album artist stays one value
  (players group albums by it). Long names in the chip menu wrap instead of
  being cut off.

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

### Fixes
- The page bar under the table hid itself only in name: after a search
  shrank the view it stayed, with the old "1–50 of 78".
- Album tiles showed a compilation once per track artist; across artists it
  is now one tile for its album artist, opening all its tracks.

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
