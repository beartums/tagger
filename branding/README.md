# Tagger branding

The mark: curly braces (a tag) around lines of text (metadata) and a waveform
(the audio). The name isn't final, so the mark is used without a wordmark in
the app; the social preview sets "Tagger" beside it.

| File | Use |
|---|---|
| `logo-dark.svg` | The mark on dark backgrounds (white ink). Same as `frontend/public/logo.svg`. |
| `logo-light.svg` | The mark on light backgrounds (dark ink). |
| `favicon.svg` | Browser tab icon; ink follows the browser's light/dark setting. Same as `frontend/public/favicon.svg`. |
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
