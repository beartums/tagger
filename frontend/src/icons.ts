// Line icons for the track pane's toolbar (stroke = currentColor).
const svg = (body: string) =>
  `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${body}</svg>`

export const ICON = {
  funnel: svg('<path d="M3 4h18l-7 8.5V19l-4 2v-8.5z"/>'),
  brain:  svg('<path d="M12 5a3 3 0 1 0-6 .1 4 4 0 0 0-2.5 5.8 4 4 0 0 0 .6 6.6A4 4 0 1 0 12 18z"/><path d="M12 5a3 3 0 1 1 6 .1 4 4 0 0 1 2.5 5.8 4 4 0 0 1-.6 6.6A4 4 0 1 1 12 18z"/><path d="M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4"/><path d="M17.6 6.5a3 3 0 0 0 .4-1.4M6 5.1a3 3 0 0 0 .4 1.4"/>'),
  tag:    svg('<path d="M3 12V3h9l9 9-9 9z"/><circle cx="7.5" cy="7.5" r="1.2"/>'),
  file:   svg('<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/>'),
  folder: svg('<path d="M3 6.5A1.5 1.5 0 0 1 4.5 5H9l2 2.5h8.5A1.5 1.5 0 0 1 21 9v9.5a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 18.5z"/>'),
  image:  svg('<rect x="3" y="4" width="18" height="16" rx="2"/><path d="m3 17 5-5 4 4 3-3 6 6"/>'),
  star:   svg('<path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/>'),
  check:  svg('<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>'),
  match:  svg('<circle cx="10.5" cy="10.5" r="6"/><path d="m15 15 6 6"/><path d="m8 10.5 2 2 3.5-4"/>'),
  export: svg('<path d="M12 3v12M7 8l5-5 5 5"/><path d="M5 14v5a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-5"/>'),
  cols:   svg('<rect x="3" y="4" width="18" height="16" rx="1.5"/><path d="M9 4v16M15 4v16"/>'),
  track:  svg('<path d="M9 18V5l11-2v13"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="17.5" cy="16" r="2.5"/>'),
  album:  svg('<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="2.5"/>'),
  list:   svg('<path d="M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01"/>'),
  tiles:  svg('<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>'),
  pencil: svg('<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="m13.5 6.5 4 4"/>'),
  group:  svg('<rect x="7" y="3" width="14" height="10" rx="1.5"/><path d="M4 7v12a1 1 0 0 0 1 1h12"/>'),
  panel:  svg('<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M15 4v16"/><path d="M17.5 8.5h1M17.5 11.5h1M17.5 14.5h1"/>'),
  bell:   svg('<path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15z"/><path d="M10 20.5a2 2 0 0 0 4 0"/>'),
  lock:   svg('<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>'),
  caret:  '<span class="ib-caret" aria-hidden="true">▾</span>',
}
