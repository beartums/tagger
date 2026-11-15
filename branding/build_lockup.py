"""
Build the full logo (mark + "Tagger" wordmark) as crisp SVGs for the README:
logo-full-light.svg and logo-full-dark.svg.

The mark is logo-dark.svg without its glow: the waveform bars are drawn at the
width of its white backing, in the gradient alone, so nothing is blurred. The
wordmark is Inter Bold (SIL Open Font License), shaped with HarfBuzz and
converted to outlines, so it renders the same without the font installed.

    pip install fonttools uharfbuzz
    curl -sL -o Inter-Bold.ttf <Inter 700 .ttf, e.g. from fonts.google.com>
    python build_lockup.py Inter-Bold.ttf
"""
import re
import sys
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

HERE = Path(__file__).parent
INK = {"light": "#1f2328", "dark": "#ffffff"}
TRACK = -30          # font units between letters (Inter is set a little tight at display size)
CAP = 172            # wordmark cap height, in mark units (the mark is 424 tall)
GAP = 60             # mark to wordmark
PAD = 16             # around the whole logo


def wordmark(font_path: str, text: str = "Tagger") -> tuple[str, float, int, int]:
    data = Path(font_path).read_bytes()
    buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties()
    hb.shape(hb.Font(hb.Face(data)), buf, {"kern": True, "liga": True})
    f = TTFont(font_path); gs = f.getGlyphSet(); order = f.getGlyphOrder()
    x, parts = 0, []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        pen = SVGPathPen(gs)
        gs[order[info.codepoint]].draw(TransformPen(pen, (1, 0, 0, -1, x + pos.x_offset, -pos.y_offset)))
        parts.append(pen.getCommands())
        x += pos.x_advance + TRACK
    return " ".join(parts), x - TRACK, f["OS/2"].sCapHeight, -f["hhea"].descent


def crisp_mark(ink: str) -> str:
    """The mark's drawing (inside its translate group), ink recoloured, no glow."""
    src = (HERE / "logo-dark.svg").read_text()
    defs = re.search(r"<linearGradient.*?</linearGradient>", src).group(0)
    body = re.search(r'<g transform="translate\(-196 -252\)">(.*)</g></svg>', src, re.S).group(1)
    backing = re.search(r'<g stroke="#fff" stroke-linecap="round" opacity=".9">(.*?)</g>', body, re.S).group(1)
    body = re.sub(r'<g stroke="#fff" stroke-linecap="round" opacity=".9">.*?</g>', "", body, flags=re.S)
    body = re.sub(r'<g stroke="url\(#tg-wave\)"[^>]*>.*?</g>',
                  f'<g stroke="url(#tg-wave)" stroke-linecap="round">{backing}</g>', body, flags=re.S)
    return defs, body.replace('"#fff"', f'"{ink}"')


def main(font_path: str) -> None:
    path, width, cap, desc = wordmark(font_path)
    s = CAP / cap
    baseline = 211 + CAP / 2               # cap height centred on the waveform's line
    x0 = 632 + GAP
    total_w = x0 + width * s
    bottom = max(424, baseline + desc * s)
    for mode, ink in INK.items():
        defs, mark = crisp_mark(ink)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-PAD} {-PAD} {total_w + 2 * PAD:.0f} {bottom + 2 * PAD:.0f}" role="img" aria-label="Tagger">'
               f"<defs>{defs}</defs>"
               f'<g transform="translate(-196 -252)">{mark}</g>'
               f'<path fill="{ink}" transform="translate({x0} {baseline:.1f}) scale({s:.6f})" d="{path}"/>'
               "</svg>\n")
        (HERE / f"logo-full-{mode}.svg").write_text(svg)
        print(f"logo-full-{mode}.svg", f"{total_w + 2 * PAD:.0f}x{bottom + 2 * PAD:.0f}", len(svg), "bytes")


if __name__ == "__main__":
    main(sys.argv[1])
