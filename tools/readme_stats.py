"""Renders the stat strip (docs/stats.png), the top part of the README card.

Update STATS, then: python3 tools/readme_stats.py Fredoka.ttf docs/stats.png
and rebuild the card with tools/readme_card.py. Fredoka is the variable TTF from Google Fonts, and its
file is not in this repo: download it and pass the path of the copy you saved.
"""
import os
import sys

USAGE = ("usage: readme_stats.py <font.ttf> <out.png>\n"
         "  Fredoka, the variable TTF from Google Fonts, is not in this repo: download it and pass the\n"
         "  path of the file you saved.")


def font_and_out(argv):
    """The font and the picture, or a usage line that says where the font comes from.

    The font is the one argument a reader brings themselves: it is not in this repo, so a wrong path is
    the first thing that fails here, and Pillow's `OSError: cannot open resource` names neither the file
    it wanted nor where to get it.
    """
    if len(argv) != 3:
        sys.exit(USAGE)
    font, out = argv[1], argv[2]
    if not os.path.isfile(font):
        sys.exit(f"cannot open the font at {font}: Fredoka, the variable TTF from Google Fonts, is not in\n"
                 "this repo, so pass the path of the copy you downloaded")
    return font, out


FONT, OUT = font_and_out(sys.argv)

# Pillow is not in tools/requirements.txt: it is only needed to redraw the README card, so point at the
# optional file the way tools/flamechart.py does, instead of ending in a bare traceback.
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("readme_stats.py needs Pillow: tools/venv/bin/pip install -r tools/requirements-perf.txt")

STATS = [("293", "TV MODELS"), ("83", "BRANDS"), ("28", "LANGUAGES"), ("517 KB", "LAUNCHER")]
W, H = 1600, 240
img = Image.new("RGB", (W, H), "#15181e"); d = ImageDraw.Draw(img)
def f(size, wt):
    x = ImageFont.truetype(FONT, size); x.set_variation_by_axes([wt]); return x
num, lab = f(92, 600), f(30, 500)
PAD = 70
col = (W - 2 * PAD) / len(STATS)
for i, (n, l) in enumerate(STATS):
    cx = PAD + col * i + col / 2
    w = d.textlength(n, font=num); d.text((cx - w / 2, 40), n, font=num, fill="#cfffcf")
    sp = 5; w = sum(d.textlength(c, font=lab) for c in l) + sp * (len(l) - 1); x = cx - w / 2
    for c in l: d.text((x, 160), c, font=lab, fill="#aab3bd"); x += d.textlength(c, font=lab) + sp
    if i: d.line([(PAD + col * i, 56), (PAD + col * i, H - 56)], fill="#2c313a", width=3)
img.save(OUT, optimize=True)
