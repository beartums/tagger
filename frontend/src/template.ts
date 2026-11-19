import { LOGO_MARK } from './logo'
import { ICON } from './icons'

export const APP_HTML = `
  <header class="topbar">
    <button id="sidebar-toggle" class="btn btn-ghost btn-icon" title="Toggle sidebar" aria-label="Toggle sidebar">☰</button>
    <a id="logo" class="logo" href="#" title="Home">${LOGO_MARK}tggr</a>
    <div class="search-wrap">
      <input id="search" class="search-input" type="search" placeholder="Search tracks…" aria-label="Search tracks" autocomplete="off" />
      <button type="button" class="search-mode" data-qmode="glob" aria-pressed="false" title="Glob: * any text, ? one character, [abc] one of; matches a whole tag (love* = starts with love); which tags: Settings → Search. Click again for plain search">*</button>
      <button type="button" class="search-mode" data-qmode="regex" aria-pressed="false" title="Regex: matches anywhere in a tag, ignoring case; which tags: Settings → Search. Click again for plain search">.*</button>
    </div>
    <div class="topbar-actions">
      <button id="scan-status" class="scan-status" type="button" title="Scan progress — click for details" hidden></button>
      <button id="review-btn" class="btn btn-review btn-sm" title="Review staged changes, then write them to the files" hidden></button>
      <button id="undo-btn" class="btn btn-ghost btn-icon" title="Undo last change" aria-label="Undo last change" hidden>↶</button>
      <div class="ib-wrap">
        <button id="cleanup-btn" class="btn btn-ghost btn-sm" type="button" aria-haspopup="menu" aria-expanded="false" title="Tidy tags and folders">Clean up</button>
        <div id="cleanup-menu" class="ib-menu" role="menu" hidden>
          <button id="cleanup-tags-btn" class="ib-mi" type="button" role="menuitem" title="Standardize tag separators (Folk/Celtic → Folk; Celtic)">Tag separators…</button>
          <button id="cleanup-folders-btn" class="ib-mi" type="button" role="menuitem" title="Folders with no tracks left, in one, some or all libraries: pick which to delete">Empty folders…</button>
        </div>
      </div>
      <button id="history-btn" class="btn btn-ghost btn-sm" title="Change history and undo">History</button>
      <button id="scan-btn" class="btn btn-ghost btn-sm scan-btn" title="Scan the whole library">Scan all</button>
      <button id="msglog-btn" class="btn btn-ghost btn-icon msglog-btn" type="button" title="Messages" aria-label="Messages">${ICON.bell}</button>
      <button id="settings-btn" class="btn btn-ghost btn-icon" title="Settings" aria-label="Settings">⚙</button>
    </div>
  </header>

  <aside id="settings-sidebar" class="settings-sidebar settings-page">
    <div class="settings-sidebar-header">
      <nav class="settings-tabs" role="tablist">
        <button class="settings-tab active" data-tab="settings" role="tab">Settings</button>
        <button class="settings-tab" data-tab="background" role="tab">Background <span id="bg-dot" class="bg-dot" hidden></span></button>
        <button class="settings-tab" data-tab="about" role="tab">About</button>
      </nav>
      <button id="settings-modal-close" class="btn btn-ghost btn-icon" aria-label="Close settings">✕</button>
    </div>
    <div id="pane-background" class="settings-sidebar-body settings-pane" hidden></div>
    <div id="pane-about" class="settings-sidebar-body settings-pane" hidden></div>
    <div id="pane-settings" class="settings-sidebar-body settings-pane">
      <nav class="settings-subnav" role="tablist" aria-label="Settings sections">
        <div class="rail-h">Library</div>
        <button type="button" data-sect="libraries" class="active">Libraries</button>
        <button type="button" data-sect="layouts">Layouts</button>
        <button type="button" data-sect="groups">Groups</button>
        <button type="button" data-sect="scanning">Scanning</button>
        <div class="rail-h">Sources</div>
        <button type="button" data-sect="integrations">Integrations</button>
        <button type="button" data-sect="metadata">Metadata</button>
        <div class="rail-h">Output</div>
        <button type="button" data-sect="writing">Writing</button>
        <button type="button" data-sect="search">Search</button>
        <div class="rail-h">Data</div>
        <button type="button" data-sect="backup">Backup</button>
      </nav>
      <div class="settings-sect" data-sect="libraries">
      <div class="settings-section">
        <div class="settings-section-title">Libraries</div>
        <p class="settings-hint">A full scan covers the libraries switched on. Switching one off removes its tracks from tggr (files untouched); switching it on scans it. 🔒 = read-only: shown, never written. <strong>Group</strong>: the group its tracks are in unless put in another (Groups).</p>
        <table class="settings-table libraries-table"><thead><tr><th>On</th><th>Library</th><th>Tracks</th></tr></thead>
          <tbody id="libraries-list"></tbody></table>
      </div>
      <div class="settings-section">
        <div class="settings-section-title">Library Roots</div>
        <p class="settings-hint">Folders layouts are relative to — each file is organized inside the deepest root that contains it, never outside. One per line; <code>*</code> matches each subfolder (e.g. <code>/music/Libraries/*</code>). Empty uses <span id="library-roots-default"></span>.</p>
        <label class="field-label">Roots
          <textarea id="setting-library-roots" rows="3" placeholder="/music/Shared&#10;/music/Libraries/*"></textarea>
        </label>
        <div id="library-roots-effective" class="settings-hint"></div>
      </div>
      <div class="settings-section">
        <div class="settings-section-title">Music Directories</div>
        <p class="settings-hint">Directories scanned for audio files when no library roots are set. The default from <code>TGGR_MUSIC_DIR</code> is always included.</p>
        <div id="music-dirs-default" class="music-dir-row music-dir-default"></div>
        <ul id="music-dirs-list" class="music-dirs-list"></ul>
        <div class="music-dir-add-row">
          <input id="music-dir-input" type="text" placeholder="Absolute path, e.g. /mnt/data/Music" />
          <button id="music-dir-add-btn" class="btn btn-ghost btn-sm">Add</button>
        </div>
      </div>
      </div>
      <div class="settings-sect" data-sect="layouts" hidden>
      <div class="settings-section">
        <div class="settings-section-title">Default layout</div>
        <p class="settings-hint">Where a file belongs, relative to its library. A library or group layout below overrides it: a track uses its group's, else its library's, else this one.</p>
        <label class="field-label" id="rename-template-wrap">
          <input id="setting-rename-template" type="text" spellcheck="false" aria-label="Default layout" />
          <div id="rename-preview" class="rename-preview"></div>
        </label>
        <p class="settings-hint">Variables: {title} {artist} {album} {album_artist} {year} {genre} {track_number:02d} {disc_number}, and {artist_the} {album_artist_the} {album_the} ("The Pogues" → "Pogues, The", as Lidarr names folders).</p>
        <label class="settings-toggle">
          <input id="setting-rename-on-save" type="checkbox" />
          <span>Rename files on save — saving a track's tags also plans a move to where its layout puts it</span>
        </label>
        <div class="field-label">Check these libraries</div>
        <p class="settings-hint">Tracks not where their layout puts them are listed under Quality → <em>Not in layout</em>, to re-file the ones you choose. Click a library to switch it.</p>
        <div id="layout-check-libs" class="tog-row"></div>
      </div>
      <div class="settings-section">
        <div class="settings-section-title">Library layouts</div>
        <p class="settings-hint">Only if a library's tracks belong somewhere else than the default. A group's layout (Settings → Groups) wins over both.</p>
        <table class="settings-table layouts-table"><tbody id="library-layouts-list"></tbody></table>
        <select id="library-layout-add" class="layout-add" aria-label="Add a library layout"></select>
      </div>
      <div class="settings-section">
        <div class="settings-section-title">Characters in names</div>
        <p class="settings-hint">How a tag value's characters become a folder or file name, for every layout above. Set these like Lidarr's <em>Media Management</em> so Lidarr's folders count as in layout. Each value is cleaned on its own, so a "/" in a tag never makes a folder.</p>
        <div class="naming-presets">Start from
          <button type="button" class="btn btn-ghost btn-sm" data-naming-preset="lidarr" title="\\ and / → +, ? → !, * → -, smart colons, the rest removed (Lidarr's Replace Illegal Characters on)">Lidarr</button>
          <button type="button" class="btn btn-ghost btn-sm" data-naming-preset="remove" title="Every one removed (Lidarr's Replace Illegal Characters off)">Remove all</button>
          <button type="button" class="btn btn-ghost btn-sm" data-naming-preset="underscore" title="Every one → _">Underscores</button>
          <button type="button" class="btn btn-ghost btn-sm" data-naming-preset="lookalike" title="Each → a Unicode look-alike (／ ： ？ ＊ …), so names read like the tag">Look-alikes</button>
          <button type="button" id="naming-from-lidarr" class="btn btn-ghost btn-sm" title="Your Lidarr's own settings (Settings → Integrations → Lidarr)">Copy from Lidarr</button>
        </div>
        <p class="settings-hint"><button type="button" id="naming-smart-colon" class="tog" aria-pressed="true">Smart colons</button>
          On: "Live: Tokyo" → "Live - Tokyo" and "10:30" → "10-30"; off: a colon is replaced like the characters below.</p>
        <p class="settings-hint">Click a character to give it its own replacement (blank removes it); the rest get <strong>all others</strong>. With Lidarr's: "AC/DC" → "AC+DC", "Why?" → "Why!", "Me &lt;3" → "Me 3".</p>
        <div id="naming-chars" class="naming-chars"></div>
        <div id="naming-preview" class="rename-preview"></div>
        <div id="lidarr-formats" class="settings-hint" hidden></div>
      </div>
      </div>
      <div class="settings-sect" data-sect="groups" hidden>
      <div class="settings-section">
        <div class="settings-section-title">Groups</div>
        <p class="settings-hint">Sets of tracks you make; put tracks in with <strong>Files ▾ → Groups…</strong>. A track can be in several. Each group can have a <strong>Layout</strong> (wins over the library and default layouts; two of a track's groups with different layouts is an error when re-filing, listed under Quality) and <strong>Quality</strong> checks that leave its tracks out (Missing lyrics for instrumentals).</p>
        <div id="groups-list" class="groups-list"></div>
        <button type="button" id="group-add" class="btn btn-ghost btn-sm">Add group</button>
      </div>
      </div>
      <div class="settings-sect" data-sect="scanning" hidden>
      <div class="settings-section">
        <div class="settings-section-title">Scan Tags</div>
        <p class="settings-hint">Choose which tags are read from audio files during a library scan. Disabled tags will be left empty in the database.</p>
        <div id="scan-tags-list" class="scan-tags-list">
          <label class="settings-toggle"><input type="checkbox" data-tag="title" /><span>Title</span></label>
          <label class="settings-toggle"><input type="checkbox" data-tag="artist" /><span>Artist</span></label>
          <label class="settings-toggle"><input type="checkbox" data-tag="album" /><span>Album</span></label>
          <label class="settings-toggle"><input type="checkbox" data-tag="album_artist" /><span>Album Artist</span></label>
          <label class="settings-toggle"><input type="checkbox" data-tag="year" /><span>Year</span></label>
          <label class="settings-toggle"><input type="checkbox" data-tag="genre" /><span>Genre</span></label>
          <label class="settings-toggle"><input type="checkbox" data-tag="track_number" /><span>Track Number</span></label>
          <label class="settings-toggle"><input type="checkbox" data-tag="disc_number" /><span>Disc Number</span></label>
          <label class="settings-toggle"><input type="checkbox" data-tag="comment" /><span>Comment</span></label>
          <label class="settings-toggle"><input type="checkbox" data-tag="composer" /><span>Composer</span></label>
          <label class="settings-toggle"><input type="checkbox" data-tag="bpm" /><span>BPM</span></label>
          <label class="settings-toggle"><input type="checkbox" data-tag="lyrics" /><span>Lyrics</span></label>
          <label class="settings-toggle"><input type="checkbox" data-tag="compilation" /><span>Compilation</span></label>
        </div>
      </div>
      <div class="settings-section">
        <div class="settings-section-title">Scan Options</div>
        <label class="field-label">Exclude patterns
          <textarea id="setting-scan-exclude" rows="3" placeholder="One glob per line — e.g. *Podcasts*  or  ._*"></textarea>
          <span class="settings-hint">Files or folders matching any pattern are skipped during scans.</span>
        </label>
        <label class="field-label">Auto-rescan interval (minutes)
          <input id="setting-auto-scan" type="number" min="0" step="1" />
          <span class="settings-hint">Automatically rescan the library on this interval. 0 disables it.</span>
        </label>
        <div class="scan-now-row"><button type="button" class="btn btn-ghost btn-sm" data-scan-now>Scan library now</button>
          <span class="settings-hint">Progress and Cancel are on the Background tab.</span></div>
      </div>
      </div>
      <div class="settings-sect" data-sect="metadata" hidden>
      <p class="settings-hint secrets-note"></p>
      <div class="settings-section">
        <div class="settings-section-title">AcoustID</div>
        <p class="settings-hint">Identifies audio by fingerprint — much more accurate than text search. Get a free application API key at <span class="settings-link">acoustid.org</span>.</p>
        <label class="field-label">API Key
          <span class="secret-row"><input id="setting-acoustid-key" data-secret="acoustid_api_key" type="password" autocomplete="off" placeholder="Paste your AcoustID API key…" data-placeholder="Paste your AcoustID API key…" /><button type="button" class="btn btn-ghost btn-sm" data-secret-remove hidden>Remove</button><button type="button" class="btn btn-ghost btn-sm" data-source-test="acoustid" title="Check it with the service (what you typed, else the saved one)">Test</button></span>
        </label>
        <div class="source-test-result" data-test-result="acoustid" hidden></div>
        <div id="acoustid-status" class="acoustid-status"></div>
      </div>
      <div class="settings-section">
        <div class="settings-section-title">Discogs</div>
        <p class="settings-hint">Optional second metadata source. Supplements MusicBrainz text search with release-level matches. Get a personal-access token from your Discogs account's developer settings.</p>
        <label class="field-label">Token
          <span class="secret-row"><input id="setting-discogs-token" data-secret="discogs_token" type="password" autocomplete="off" placeholder="Paste your Discogs token…" data-placeholder="Paste your Discogs token…" /><button type="button" class="btn btn-ghost btn-sm" data-secret-remove hidden>Remove</button><button type="button" class="btn btn-ghost btn-sm" data-source-test="discogs" title="Check it with the service (what you typed, else the saved one)">Test</button></span>
        </label>
        <div class="source-test-result" data-test-result="discogs" hidden></div>
      </div>
      <div class="settings-section">
        <div class="settings-section-title">LRCLIB (lyrics)</div>
        <p class="settings-hint">Free, no key needed: about 90 lookups a minute, spaced out automatically. Register an app at <span class="settings-link">lrclib.net/developers</span> (server-side) and paste its app ID and key for a far higher limit.</p>
        <label class="field-label">App ID
          <input id="setting-lrclib-app-id" type="text" autocomplete="off" spellcheck="false" placeholder="Optional" />
        </label>
        <label class="field-label">API key
          <span class="secret-row"><input id="setting-lrclib-key" data-secret="lrclib_api_key" type="password" autocomplete="off" placeholder="Optional" data-placeholder="Optional" /><button type="button" class="btn btn-ghost btn-sm" data-secret-remove hidden>Remove</button><button type="button" class="btn btn-ghost btn-sm" data-source-test="lrclib" title="Check it with the service (what you typed, else the saved one)">Test</button></span>
        </label>
        <div class="source-test-result" data-test-result="lrclib" hidden></div>
      </div>
      </div>
      <div class="settings-sect" data-sect="integrations" hidden>
      <p class="settings-hint secrets-note"></p>
      <div class="settings-section">
        <div class="settings-section-title">Lidarr</div>
        <p class="settings-hint">Optional. Lets Settings → Layouts → <em>Characters in names</em> copy Lidarr's naming choices. API key: Lidarr → Settings → General.</p>
        <label class="field-label">URL
          <input id="setting-lidarr-url" data-integ-url type="text" spellcheck="false" placeholder="http://lidarr:8686" /></label>
        <label class="field-label">API key
          <span class="secret-row"><input id="setting-lidarr-key" data-secret="lidarr_api_key" type="password" autocomplete="off" placeholder="Paste Lidarr's API key…" data-placeholder="Paste Lidarr's API key…" /><button type="button" class="btn btn-ghost btn-sm" data-secret-remove hidden>Remove</button><button type="button" class="btn btn-ghost btn-sm" data-source-test="lidarr" title="Check the connection (what you typed, else the saved values)">Test</button></span>
        </label>
        <div class="source-test-result" data-test-result="lidarr" hidden></div>
      </div>
      <div class="settings-section">
        <div class="settings-section-title">Navidrome</div>
        <p class="settings-hint">Optional. Navidrome rescans 30 s after tggr last changes a file. Needs an <strong>admin</strong> user (rescans are admin-only).</p>
        <label class="field-label">URL
          <input id="setting-navidrome-url" data-integ-url type="text" spellcheck="false" placeholder="http://navidrome:4533" /></label>
        <label class="field-label">User
          <input id="setting-navidrome-user" data-integ-user type="text" spellcheck="false" autocomplete="off" /></label>
        <label class="field-label">Password
          <span class="secret-row"><input id="setting-navidrome-password" data-secret="navidrome_password" type="password" autocomplete="off" placeholder="Navidrome password…" data-placeholder="Navidrome password…" /><button type="button" class="btn btn-ghost btn-sm" data-secret-remove hidden>Remove</button><button type="button" class="btn btn-ghost btn-sm" data-source-test="navidrome" title="Check the connection (what you typed, else the saved values)">Test</button></span>
        </label>
        <div class="source-test-result" data-test-result="navidrome" hidden></div>
        <label class="field-label">Scan just the changed folders <span class="ma-dim">(one per line: tggr folder = library id:folder in it; blank: full scans)</span>
          <textarea id="setting-navidrome-folders" rows="2" spellcheck="false" placeholder="/music = 1:"></textarea></label>
        <p class="settings-hint">Test lists the library ids. <code>/music = 1:</code> means tggr's <code>/music</code> is the root of library 1. A change outside these folders, or more than 50 folders at once, scans everything.</p>
        <div class="settings-hint" data-rescan-status="navidrome"></div>
      </div>
      <div class="settings-section">
        <div class="settings-section-title">Music Assistant</div>
        <p class="settings-hint">Optional. Music Assistant syncs 30 s after tggr last changes a file. Token: an <strong>admin</strong>'s long-lived token (Settings → Profile). Test lists the file providers to sync.</p>
        <label class="field-label">URL
          <input id="setting-ma-url" data-integ-url type="text" spellcheck="false" placeholder="http://music-assistant:8095" /></label>
        <label class="field-label">Token
          <span class="secret-row"><input id="setting-ma-token" data-secret="ma_token" type="password" autocomplete="off" placeholder="Paste a long-lived token…" data-placeholder="Paste a long-lived token…" /><button type="button" class="btn btn-ghost btn-sm" data-secret-remove hidden>Remove</button><button type="button" class="btn btn-ghost btn-sm" data-source-test="music_assistant" title="Check the connection (what you typed, else the saved values)">Test</button></span>
        </label>
        <div class="source-test-result" data-test-result="music_assistant" hidden></div>
        <label class="field-label">Providers to sync <span class="ma-dim">(instance ids, comma-separated; blank: all)</span>
          <input id="setting-ma-providers" type="text" spellcheck="false" placeholder="filesystem_local--ab12cd34" /></label>
        <label class="field-label">Sync just the changed providers <span class="ma-dim">(one per line: tggr folder = provider instance id; blank: the list above)</span>
          <textarea id="setting-ma-folders" rows="2" spellcheck="false" placeholder="/music/Shared = filesystem_local--ab12cd34"></textarea></label>
        <p class="settings-hint">Music Assistant can't sync a single folder, only whole providers — this helps once each library is its own provider. A change outside these folders syncs the list above.</p>
        <div class="settings-hint" data-rescan-status="music_assistant"></div>
      </div>
      <div class="settings-section">
        <div class="settings-section-title">Player rescans</div>
        <p class="settings-hint">When Navidrome and Music Assistant are asked to rescan after tggr changes files (tags, moves, covers, ReplayGain). A big write is always one rescan.</p>
        <label class="field-label">Rescan
          <select id="setting-rescan-mode">
            <option value="quiet">After the last change — each change restarts the wait</option>
            <option value="delay">After a change — later changes don't push it back</option>
            <option value="off">Off — only "Rescan now"</option>
          </select></label>
        <label class="field-label" id="rescan-wait-wrap">Wait
          <span class="secret-row"><input id="setting-rescan-wait" type="number" min="1" max="1440" step="1" /> <span id="rescan-wait-unit">minutes</span></span></label>
        <div id="rescan-pending" class="settings-hint"></div>
        <button type="button" id="rescan-now" class="btn btn-ghost btn-sm" title="Ask Navidrome and Music Assistant to rescan now (saved settings)">Rescan now</button>
      </div>
      </div>
      <div class="settings-sect" data-sect="search" hidden>
      <div class="settings-section">
        <div class="settings-section-title">Search Box</div>
        <p class="settings-hint">The tags the search box looks in, in every mode (words, <code>*</code> glob, <code>.*</code> regex). Every tag but Lyrics is indexed; with Lyrics on, words search goes track by track, slower on a big library.</p>
        <div id="search-fields" class="search-fields">
          <button type="button" class="tog" data-search-field="title" aria-pressed="false" title="Click to search this tag, or to stop">Title</button>
          <button type="button" class="tog" data-search-field="artist" aria-pressed="false" title="Click to search this tag, or to stop">Artist</button>
          <button type="button" class="tog" data-search-field="album" aria-pressed="false" title="Click to search this tag, or to stop">Album</button>
          <button type="button" class="tog" data-search-field="album_artist" aria-pressed="false" title="Click to search this tag, or to stop">Album Artist</button>
          <button type="button" class="tog" data-search-field="year" aria-pressed="false" title="Click to search this tag, or to stop">Year</button>
          <button type="button" class="tog" data-search-field="genre" aria-pressed="false" title="Click to search this tag, or to stop">Genre</button>
          <button type="button" class="tog" data-search-field="composer" aria-pressed="false" title="Click to search this tag, or to stop">Composer</button>
          <button type="button" class="tog" data-search-field="comment" aria-pressed="false" title="Click to search this tag, or to stop">Comment</button>
          <button type="button" class="tog" data-search-field="lyrics" aria-pressed="false" title="Click to search this tag, or to stop">Lyrics</button>
          <button type="button" class="tog" data-search-field="filename" aria-pressed="false" title="Click to search this tag, or to stop">File name</button>
        </div>
      </div>
      </div>
      <div class="settings-sect" data-sect="writing" hidden>
      <div class="settings-section">
        <div class="settings-section-title">ReplayGain</div>
        <p class="settings-hint">Scan volume levels and write ReplayGain tags, so players that read them play tracks at an even volume. Run it from the selection toolbar.</p>
        <div id="replaygain-status" class="acoustid-status"></div>
      </div>
      <div class="settings-section">
        <div class="settings-section-title">Writing Changes</div>
        <label class="settings-toggle">
          <input id="setting-stage-changes" type="checkbox" />
          <span>Review changes before writing</span>
        </label>
        <p class="settings-hint">Edits, organizing and lookups are held as staged changes until you write them from <strong>Review</strong>. Off: each edit is written straight away.</p>
      </div>
      <div class="settings-section">
        <div class="settings-section-title">Cover Art</div>
        <label class="field-label">New cover art goes to
          <select id="setting-cover-target">
            <option value="folder">The album folder (cover.jpg)</option>
            <option value="tracks">Each track (embedded)</option>
            <option value="both">Both</option>
          </select></label>
        <label class="field-label">Folder cover: shrink to
          <select id="setting-cover-folder-size">
            <option value="500">500 px</option><option value="800">800 px</option><option value="1000">1000 px</option>
            <option value="1200">1200 px</option><option value="1500">1500 px</option><option value="0">Don't resize</option>
          </select></label>
        <label class="field-label">Track (embedded) art: shrink to
          <select id="setting-cover-size">
            <option value="250">250 px</option><option value="500">500 px</option><option value="800">800 px</option>
            <option value="1200">1200 px</option><option value="0">Don't resize</option>
          </select></label>
        <p class="settings-hint">Plex, Jellyfin, Navidrome and Music Assistant read the folder's cover.jpg; embedded art is a copy in every track, for files that leave the folder. Any art written (Match album, Covers…, an uploaded cover) is shrunk to these sizes on its longest side, never enlarged. To move existing art: select tracks → Covers….</p>
      </div>
      <div class="settings-section">
        <div class="settings-section-title">Trash</div>
        <p class="settings-hint">Deleted files are moved to a trash folder and can be restored with Undo. Emptying trash frees that space permanently.</p>
        <div id="trash-status" class="acoustid-status"></div>
        <button id="empty-trash-btn" class="btn btn-ghost btn-sm">Empty trash</button>
      </div>
      </div>
      <div class="settings-sect" data-sect="backup" hidden>
      <div class="settings-section">
        <div class="settings-section-title">Back up</div>
        <p class="settings-hint">One zip with the parts you pick (struck: left out).</p>
        <div class="tog-row backup-parts" id="backup-parts">
          <button type="button" class="tog" data-part="data" aria-pressed="true" title="The library database (tracks, staged changes, history, groups, Quality results) and the trash Undo restores from">Data</button>
          <button type="button" class="tog" data-part="settings" aria-pressed="true" title="Everything in Settings. API keys stay encrypted: restoring needs the same TGGR_SECRET_KEY">Settings</button>
          <button type="button" class="tog" data-part="prefs" aria-pressed="true" title="This browser's columns, widths, page size and views">Interface</button>
          <button type="button" class="tog" data-part="environment" aria-pressed="false" title="tggr.env: the TGGR_* settings the server runs with, to set on a new container">Environment</button>
        </div>
        <p class="settings-hint" id="backup-secrets-row" hidden><button type="button" class="tog" id="backup-secrets" aria-pressed="false">Include secrets</button>
          Puts <code>TGGR_SECRET_KEY</code> (and a login password, if set) in the file as plain text: anyone with the file can read your API keys. Keep it somewhere safe.</p>
        <button id="backup-download-btn" class="btn btn-sm">Download backup</button>
      </div>
      <div class="settings-section">
        <div class="settings-section-title">Restore</div>
        <p class="settings-hint">Replaces the parts you pick (struck: left as they are) with the backup's, when it has them. To move tggr to a new config volume: back up, start tggr on the new volume, restore. Restoring Data needs no scan running. An Environment file is shown, to set on the container yourself.</p>
        <div class="tog-row backup-parts" id="restore-parts">
          <button type="button" class="tog" data-part="data" aria-pressed="true">Data</button>
          <button type="button" class="tog" data-part="settings" aria-pressed="true">Settings</button>
          <button type="button" class="tog" data-part="prefs" aria-pressed="true">Interface</button>
          <button type="button" class="tog" data-part="environment" aria-pressed="true">Environment</button>
        </div>
        <input id="backup-file" type="file" accept=".zip,application/zip" hidden>
        <button id="backup-restore-btn" class="btn btn-sm btn-danger">Restore from a backup…</button>
        <div id="backup-status" class="acoustid-status"></div>
        <pre id="restore-env" class="restore-env" hidden></pre>
      </div>
      </div>
    </div>
    <div class="settings-sidebar-footer" id="settings-footer">
      <span id="settings-unsaved" class="settings-unsaved"></span>
      <button id="settings-logout" class="btn btn-ghost" hidden>Log out</button>
      <button id="settings-cancel" class="btn btn-ghost" title="Discard your changes" hidden>Cancel</button>
      <button id="settings-save" class="btn btn-primary">Save</button>
    </div>
  </aside>

  <div class="workspace">
    <aside class="sidebar">
      <div class="sidebar-tabs">
        <button class="stab active" data-mode="tags">Tags</button>
        <button class="stab" data-mode="files">Files</button>
        <button class="stab" data-mode="quality">Quality</button>
        <button class="stab" data-mode="groups">Groups</button>
      </div>
      <nav id="panel-tags" class="sidebar-panel">
        <div class="nav-toolbar">
          <button id="expand-all-btn" class="btn btn-ghost btn-sm">Expand all</button>
          <button id="collapse-all-btn" class="btn btn-ghost btn-sm">Collapse all</button>
        </div>
        <ul id="artist-list" class="nav-list"></ul>
      </nav>
      <nav id="panel-files" class="sidebar-panel" hidden>
        <div class="nav-toolbar">
          <button id="move-folder-btn" class="btn btn-ghost btn-sm" style="flex:1" title="Move the selected folder (and everything in it) — staged for review" disabled>Move…</button>
          <button id="rename-folder-btn" class="btn btn-ghost btn-sm" style="flex:1" title="Rename the selected folder — staged for review" disabled>Rename…</button>
        </div>
        <div id="dir-tree" class="dir-tree"></div>
      </nav>
      <nav id="panel-groups" class="sidebar-panel" hidden>
        <ul id="group-list" class="nav-list"></ul>
      </nav>
      <nav id="panel-quality" class="sidebar-panel" hidden>
        <div class="nav-toolbar" id="quality-toolbar" hidden>
          <button id="fix-all-btn" class="btn btn-ghost btn-sm" style="flex:1">Fix All</button>
          <button id="dedupe-btn" class="btn btn-ghost btn-sm" style="flex:1" title="Review each group: pick the copy to keep, then remove the rest from the library or move their files to the trash (undoable)" hidden>Review duplicates…</button>
          <button id="refile-btn" class="btn btn-ghost btn-sm" style="flex:1" title="Stage moving the selected tracks to the path their library layout gives — reviewed before anything moves" hidden>Re-file selected</button>
          <button id="lyrics-lookup-btn" class="btn btn-ghost btn-sm" style="flex:1" title="Look up lyrics for every track listed (or the selected ones) in the background — what's found is staged for review" hidden>Look up all…</button>
        </div>
        <ul id="quality-list" class="nav-list"></ul>
      </nav>
    </aside>

    <div class="pane-resizer" data-resize="sidebar" role="separator" aria-orientation="vertical"
         title="Drag to resize · double-click to reset"></div>

    <main class="track-pane">
      <div id="home-pane" class="home-pane" hidden></div>
      <div class="track-pane-toolbar">
        <div class="toolbar-line">
          <span id="track-count" class="track-count"></span>
          <span id="selection-bar" class="selection-bar" hidden>
            <button type="button" id="selection-count" class="selection-count" title="Show only what's selected"></button>
            <button id="select-view-btn" class="btn btn-link btn-sm" hidden></button>
            <button id="clear-selection" class="btn btn-ghost btn-sm" title="Deselect" aria-label="Deselect">✕</button>
          </span>
          <span class="toolbar-spacer"></span>
          <div id="bulk-actions" class="ibar" role="toolbar" aria-label="Selection actions" hidden>
            <button id="mb-album-btn" class="ib ib-prim" type="button">${ICON.match}</button>
            <div class="ib-wrap">
              <button class="ib" type="button" data-ib-menu="tags-menu" title="Tags" aria-haspopup="menu" aria-expanded="false">${ICON.tag}${ICON.caret}</button>
              <div id="tags-menu" class="ib-menu" role="menu" hidden>
                <button id="normalize-case-btn" class="ib-mi" type="button" role="menuitem">Normalize case</button>
                <button id="autonumber-btn" class="ib-mi" type="button" role="menuitem" title="Number selected tracks 1…N in filename order">Auto-number</button>
                <button id="find-replace-btn" class="ib-mi" type="button" role="menuitem" title="Find and replace in one tag across the selection — plain text or regex with capture groups, previewed">Find / replace…</button>
                <button id="parse-names-btn" class="ib-mi" type="button" role="menuitem" title="Read tags from the file and folder names with a pattern like %artist%/%album%/%track% - %title% — previewed, then staged">Tags from names…</button>
                <hr>
                <button id="lyrics-btn" class="ib-mi" type="button" role="menuitem" title="Fetch lyrics (synced when available) from LRCLIB — reviewed, then staged">Lyrics…</button>
                <hr>
                <button id="mb-add-btn" class="ib-mi" type="button" role="menuitem" title="Open MusicBrainz's Add release page filled in from this album (titles, lengths, artist, year, barcode): you check it and submit there, then attach the disc ID">Add to MusicBrainz…</button>
                <button id="disc-ids-btn" class="ib-mi" type="button" role="menuitem" title="Work out each disc's MusicBrainz disc ID from its tracks' exact lengths (rips made before the ripper tagged it), checked against MusicBrainz, then staged">Disc IDs from track lengths</button>
                <button id="replaygain-btn" class="ib-mi" type="button" role="menuitem" title="Measure loudness and stage ReplayGain tags: each album on its own, with album gain when the whole album is selected" hidden>ReplayGain…</button>
              </div>
            </div>
            <div class="ib-wrap">
              <button class="ib" type="button" data-ib-menu="files-menu" title="Files" aria-haspopup="menu" aria-expanded="false">${ICON.folder}${ICON.caret}</button>
              <div id="files-menu" class="ib-menu" role="menu" hidden>
                <button id="covers-btn" class="ib-mi" type="button" role="menuitem" title="Move, copy or delete cover art between the album folder (cover.jpg) and the tracks">Covers…</button>
                <button id="merge-albums-btn" class="ib-mi" type="button" role="menuitem" title="Make the selected tracks one album: tags, disc numbers, optionally one folder — previewed, then staged">Merge albums…</button>
                <button id="layout-move-btn" class="ib-mi" type="button" role="menuitem" title="Move the selected files to where their layout puts them — shows the final folders and names first">Move to layout…</button>
                <button id="bulk-rename-btn" class="ib-mi" type="button" role="menuitem" title="Rename the selected files with search &amp; replace (regex, captures, counters) — previewed, then staged">Rename files…</button>
                <button id="lyrics-group-btn" class="ib-mi" type="button" role="menuitem" title="Put the selection in groups, or take it out (a group can set a layout and turn Quality checks off)">Groups…</button>
                <hr>
                <button id="remove-tracks-btn" class="ib-mi ib-danger" type="button" role="menuitem" title="Remove from the library index (leaves files on disk)">Remove from library</button>
                <button id="delete-files-btn" class="ib-mi ib-danger" type="button" role="menuitem" title="Move the selected files to trash (undoable)">Delete files…</button>
              </div>
            </div>
            <button id="export-m3u-btn" class="ib" type="button" title="Export the selection as an .m3u playlist" aria-label="Export M3U">${ICON.export}</button>
          </div>
          <div class="seg" role="group" aria-label="Tracks or albums">
            <button id="view-list-btn" class="seg-b active" type="button" title="Tracks" aria-label="Tracks">${ICON.track}</button>
            <button id="view-albums-btn" class="seg-b" type="button" title="Albums" aria-label="Albums">${ICON.album}</button>
          </div>
          <span id="album-style" class="seg" role="group" aria-label="List or tiles" hidden><button class="seg-b" type="button" data-style="list" title="Album list" aria-label="Album list">${ICON.list}</button><button class="seg-b" type="button" data-style="tiles" title="Album tiles" aria-label="Album tiles">${ICON.tiles}</button></span>
          <button id="grid-edit-btn" class="btn btn-ghost btn-sm grid-edit-btn" aria-pressed="false">✎</button>
          <button id="grid-discard-btn" class="btn btn-ghost btn-sm" hidden>✕</button>
          <div class="col-picker-wrap">
            <button id="col-picker-btn" class="ib-solo" type="button" title="Columns" aria-label="Columns">${ICON.cols}</button>
            <div id="col-picker" class="col-picker" hidden></div>
          </div>
          <button id="editor-toggle" class="ib-solo" type="button" aria-pressed="true" hidden>${ICON.panel}</button>
        </div>
        <div class="toolbar-line filter-line">
          <div class="filter-wrap">
            <button id="filter-btn" class="ib-solo" type="button" title="Add a filter" aria-label="Add a filter" aria-haspopup="menu" aria-expanded="false">${ICON.funnel}</button>
            <div id="filter-menu" class="filter-menu" role="menu" hidden></div>
          </div>
          <span id="sel-chip" class="fchip sel-chip" hidden>Selected only<button type="button" class="fchip-x" id="sel-chip-x" aria-label="Show everything again">✕</button></span>
          <span id="filter-chips" class="filter-chips"><span class="filter-none">No filters</span></span>
          <button id="filter-clear" class="btn btn-link btn-sm" type="button" hidden>Clear</button>
        </div>
      </div>
      <div class="table-wrap">
        <table class="track-table">
          <thead><tr id="track-thead-row"></tr></thead>
          <tbody id="track-tbody"></tbody>
        </table>
        <div id="track-empty" class="track-empty" hidden>No tracks found.</div>
        <div id="track-loading" class="track-loading" hidden>Loading…</div>
      </div>
      <div id="album-grid" class="album-grid" style="display:none"></div>
      <div id="album-list" class="album-list" style="display:none"></div>
      <div id="pagination" class="pagination">
        <span class="page-controls">
        <span id="page-nav" class="page-nav">
          <button type="button" id="page-prev" class="btn btn-ghost btn-sm" title="Previous page">‹</button>
          <span id="page-unit">rows</span> <input id="page-top" class="page-top" type="number" min="1" title="The top row: type a row number to start the page there">–<span id="page-end"></span>
          of <span id="page-total"></span>
          <button type="button" id="page-next" class="btn btn-ghost btn-sm" title="Next page">›</button>
          <span class="page-of">page <span id="page-num"></span> of <span id="page-count"></span></span>
        </span>
        <span id="page-size-wrap" class="page-size-wrap"><select id="page-size" class="page-size" title="Rows per page"></select> per page</span>
        </span>
      </div>
    </main>

    <div class="pane-resizer" id="editor-resizer" data-resize="editor" role="separator" aria-orientation="vertical"
         title="Drag to resize · double-click to reset" hidden></div>

    <aside id="tag-editor" class="tag-editor" hidden>
      <div class="tag-editor-header">
        <span id="editor-title" class="editor-title"></span>
        <div class="editor-header-actions">
          <button id="auto-fix-btn" class="btn btn-ghost btn-sm" title="Auto-fix: look up and save the best match">Auto-fix</button>
          <button id="infer-btn" class="btn btn-ghost btn-sm" title="Guess tags from the file name and folders">From filename</button>
          <button id="lookup-btn" class="btn btn-ghost btn-sm" title="Search MusicBrainz">Lookup</button>
          <button id="close-editor" class="btn btn-ghost btn-icon" title="Close" aria-label="Close editor">✕</button>
        </div>
      </div>
      <div id="lookup-panel" class="lookup-panel" hidden>
        <div class="lookup-header">
          <span class="lookup-title">MusicBrainz results</span>
          <button id="lookup-close" class="btn btn-ghost btn-icon btn-sm">✕</button>
        </div>
        <ul id="lookup-results" class="lookup-results"></ul>
      </div>
      <div id="editor-file" class="editor-file" hidden></div>
      <form id="tag-form" class="tag-form" autocomplete="off">
        <div class="cover-section">
          <div class="cover-preview" id="cover-preview">
            <img id="cover-img" alt="Cover art" />
            <div id="cover-placeholder" class="cover-placeholder">♪</div>
          </div>
          <button type="button" id="change-cover-btn" class="btn btn-ghost btn-sm" title="From disk, the Cover Art Archive or a URL">Change Cover…</button>
        </div>
        <audio id="player" class="editor-player" controls preload="none" hidden></audio>
        <div id="spectro-section" class="spectro-section" hidden>
          <button type="button" id="spectro-btn" class="btn btn-ghost btn-sm">Spectrogram ▾</button>
          <div id="spectro-wrap" class="spectro-wrap" hidden>
            <div class="spectro-frame">
              <img id="spectro-img" class="spectro-img" alt="Frequency spectrogram" title="Click to open full size" />
              <button type="button" id="spectro-popout" class="spectro-popout" title="Open full size" aria-label="Open spectrogram full size">⤢</button>
            </div>
            <div id="spectro-status" class="spectro-status"></div>
          </div>
        </div>
        <label class="field-label">Title<input name="title" type="text" /></label>
        <label class="field-label">Artist<input name="artist" type="text" /></label>
        <label class="field-label">Album<input name="album" type="text" /></label>
        <label class="field-label">Album Artist<input name="album_artist" type="text" /></label>
        <label class="field-label">Year<input name="year" type="text" maxlength="4" /></label>
        <label class="field-label">Track #<input name="track_number" type="text" /></label>
        <label class="field-label">Disc #<input name="disc_number" type="text" /></label>
        <label class="field-label">Genre<input name="genre" type="text" /></label>
        <label class="field-label">Composer<input name="composer" type="text" /></label>
        <label class="field-label">BPM<input name="bpm" type="text" inputmode="numeric" /></label>
        <label class="field-check"><input name="compilation" type="checkbox" /><span>Part of a compilation</span></label>
        <label class="field-label">Comment<textarea name="comment" rows="3"></textarea></label>
        <label class="field-label"><span class="field-label-row">Lyrics <button type="button" id="lyrics-search-btn" class="btn btn-link btn-sm" title="Search LRCLIB for this track by hand">Search…</button></span><textarea name="lyrics" rows="4"></textarea></label>
        <div id="editor-rename-preview" class="rename-preview" hidden></div>
        <div class="tag-form-actions">
          <button type="submit" class="btn btn-primary">Save</button>
          <button type="button" id="revert-btn" class="btn btn-ghost">Revert</button>
        </div>
      </form>
    </aside>
  </div>

  <footer id="statusbar" class="statusbar">
    <span id="status-where" class="status-where"></span>
    <span id="status-count" class="status-count"></span>
    <span id="status-sel" class="status-sel"></span>
  </footer>
`
