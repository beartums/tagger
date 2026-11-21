# tggr branding

The mark: curly braces (a tag) around lines of text (metadata) and a waveform
(the audio). The name is **tggr**, always lowercase. The app header sets it
beside the mark in text; the full logo and the social preview draw it.

| File | Use |
|---|---|
| `logo-full-light.svg`, `logo-full-dark.svg` | The full logo: mark + "tggr", crisp (no glow), wordmark as outlines. Used in the README. Built by `build_lockup.py`. |
| `logo-dark.svg` | The mark on dark backgrounds (white ink). Same as `frontend/public/logo.svg`. |
| `logo-light.svg` | The mark on light backgrounds (dark ink). |
| `favicon.svg` | Browser tab icon; ink follows the browser's light/dark setting. Same as `frontend/public/favicon.svg`. A TALLER drawing than the logo mark (longer braces and wave bars, same stroke widths), so it fills a square tab instead of sitting in a 3:2 band. Its wave is simplified to 5 thick bars on the line (no glow): the logo's 8 thin bars smear at tab size (32 device px on a Retina screen, 16 on a regular one). |
| `favicon.ico` | 16, 32 and 48 px, for anything that can't use the SVG. |
| `app-icon.svg` | The mark on a rounded dark tile: home-screen and app icons. |
| `social-preview.svg` | 1280×640 card for GitHub's social preview and link unfurls. |
| `png/` | Renders of the above: `logo-{dark,light}-{512,1024}`, `favicon-{32,64}`, `app-icon-{180,192,512}`, `social-preview`. |

## Colours

| | |
|---|---|
| Waveform gradient | `#1f5fff` → `#1fb8e0` → `#5ee35a` (bottom-left to top-right), with a soft glow |
| Ink on dark | `#ffffff` |
| Ink on light | `#1f2328` |
| Tile / app background | `#0f1117` |

## Wordmark

Inter Bold (SIL Open Font License), kerned and tracked slightly tight, drawn
as outlines so it looks the same everywhere. To rebuild the full logo after
changing the mark: `pip install fonttools uharfbuzz`, download Inter Bold, then
`python build_lockup.py Inter-Bold.ttf`.

## Regenerating the PNGs

The SVGs are the source. With `rsvg-convert` and ImageMagick:

```sh
cd branding/png
for v in dark light; do for w in 512 1024; do rsvg-convert -w $w ../logo-$v.svg -o logo-$v-$w.png; done; done
for n in 32 64; do rsvg-convert -w $n -h $n ../favicon.svg -o favicon-$n.png; done
for n in 180 192 512; do rsvg-convert -w $n -h $n ../app-icon.svg -o app-icon-$n.png; done
rsvg-convert ../social-preview.svg -o social-preview.png
for n in 16 32 48; do rsvg-convert -w $n -h $n ../favicon.svg -o /tmp/fav-$n.png; done
magick /tmp/fav-16.png /tmp/fav-32.png /tmp/fav-48.png ../favicon.ico
```

The social preview uses Helvetica Neue (Arial as fallback); render it on a
machine that has it, or the type changes.

## Concepts (not adopted)

`concepts/` holds generated brand concepts kept as candidates for a possible future
rebrand. They are reference images only: nothing in the app uses them, and their
"TagTamer" name and palettes are not decisions.

| File | Idea |
|---|---|
| `concepts/tagtamer-tag-and-wave.png` | A price tag crossed by a sound wave; navy `#1E293B`, cyan `#06B6D4`, green `#10B981`; a 3-bar favicon variant |
| `concepts/tagtamer-network-grid.png` | A node-and-edge grid around a play button and waveform; navy, violet, cyan |
