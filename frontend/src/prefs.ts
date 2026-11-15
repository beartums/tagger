// Interface preferences live in localStorage under "tggr." / "tggr_" keys.
// Imported first by main.ts: copies any older "tagger." / "tagger_" keys
// across once, so preferences survive the rename (the old keys are kept).
export const PREF_PREFIXES = ['tggr.', 'tggr_']

try {
  for (let i = 0; i < localStorage.length; i++) {
    const k = localStorage.key(i)!
    const m = /^tagger([._])(.*)$/.exec(k)
    if (!m) continue
    const nk = `tggr${m[1]}${m[2]}`
    if (localStorage.getItem(nk) === null) localStorage.setItem(nk, localStorage.getItem(k)!)
  }
} catch { /* storage blocked */ }

/** Every interface preference, for a backup. */
export function exportPrefs(): Record<string, string> {
  const out: Record<string, string> = {}
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i)!
      if (PREF_PREFIXES.some(p => k.startsWith(p))) out[k] = localStorage.getItem(k)!
    }
  } catch { /* storage blocked */ }
  return out
}

/** Replace the interface preferences with a backup's. */
export function importPrefs(prefs: Record<string, string>) {
  try {
    for (const k of Object.keys(exportPrefs())) localStorage.removeItem(k)
    for (const [k, v] of Object.entries(prefs)) {
      if (PREF_PREFIXES.some(p => k.startsWith(p)) && typeof v === 'string') localStorage.setItem(k, v)
    }
  } catch { /* storage blocked */ }
}
