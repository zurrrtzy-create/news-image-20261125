#!/usr/bin/env python3
"""Render the make.fun news-image-20261125 entry: a newspaper front page
summing up the world news of Wednesday 25 November 2026.

Written from scratch in this session. Pillow + real fonts only (EB Garamond
for body text, Playfair Display for the masthead and headlines), no network,
no wall-clock time; all randomness uses fixed seeds, so the output is fully
deterministic.

Run:  python3 render.py            (writes entry.png next to this file)
"""

import math
import os
import random
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
OUT = os.path.join(HERE, "entry.png")

W, H = 1024, 1024
MARGIN = 24
COLW = 312
GAP = 20
COLX = [MARGIN, MARGIN + COLW + GAP, MARGIN + 2 * (COLW + GAP)]

PAPER = (247, 243, 232)
INK = (26, 26, 24)
MUTED = (92, 86, 74)
RED = (168, 32, 26)
DARKRED = (120, 20, 16)
RULE = (60, 56, 48)
GOLD = (176, 132, 52)


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


F_TITLE = lambda s: font("PlayfairDisplay.ttf", s)
F_BODY = lambda s: font("EBGaramond.ttf", s)
F_ITAL = lambda s: font("EBGaramond-Italic.ttf", s)


def wrap(draw, text, fnt, max_w):
    """Greedy word wrap; returns a list of lines that fit max_w."""
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def text_block(draw, x, y, text, fnt, max_w, leading, color=INK, max_lines=None):
    """Draw wrapped text; returns the y just below the last line."""
    lines = wrap(draw, text, fnt, max_w)
    if max_lines:
        lines = lines[:max_lines]
    for line in lines:
        draw.text((x, y), line, font=fnt, fill=color)
        y += leading
    return y


def vgrad(img, box, top, bottom):
    """Vertical gradient fill inside box (x0, y0, x1, y1)."""
    x0, y0, x1, y1 = box
    h = max(1, y1 - y0)
    for i in range(h):
        t = i / h
        c = tuple(int(top[j] + (bottom[j] - top[j]) * t) for j in range(3))
        img.paste(c, (x0, y0 + i, x1, y0 + i + 1))


def rrect(d, box, rad, **kw):
    d.rounded_rectangle(box, radius=rad, **kw)


def blur_overlay(img, fn, radius=4):
    """Draw fn() onto a transparent RGBA overlay, Gaussian-blur it, and
    composite it over img. Used for soft glows, volumetric smoke, blurred
    shadows and water reflections — the main 3D depth device. Deterministic
    (fixed radius, no randomness). Returns an RGB image."""
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    fn(ImageDraw.Draw(ov))
    ov = ov.filter(ImageFilter.GaussianBlur(radius))
    base = img.convert("RGBA")
    base.alpha_composite(ov)
    return base.convert("RGB")


# ------------------------------------------------------- texture toolkit
# Third revision: the flat vector look itself reads as AI. Every image now
# gets a realistic, hand-crafted treatment — grain, mottling, rough edges,
# real materials — all with fixed seeds so the render stays deterministic.
def mottle(d, box, seed, colors, n, rmin=6, rmax=18, alpha=40):
    """Soft translucent blotches inside box: mottled colour variation so
    large flat areas stop reading as one clean fill. d is an RGBA draw."""
    rnd = random.Random(seed)
    x0, y0, x1, y1 = box
    for _ in range(n):
        cx = rnd.randint(x0, x1)
        cy = rnd.randint(y0, y1)
        rx = rnd.randint(rmin, rmax)
        ry = rnd.randint(max(3, rmin // 2), rmax)
        col = colors[rnd.randrange(len(colors))]
        d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=col + (alpha,))


def wobble(pts, seed, amp=2):
    """Jitter polygon points by up to amp px: hand-drawn irregular edges
    instead of perfect geometry. Deterministic (fixed seed)."""
    rnd = random.Random(seed)
    return [(x + rnd.randint(-amp, amp), y + rnd.randint(-amp, amp))
            for (x, y) in pts]


def streaks(d, box, seed, color, n, vertical=False, alpha=50):
    """Thin semi-transparent streaks: brushed metal, rust runs, grime."""
    rnd = random.Random(seed)
    x0, y0, x1, y1 = box
    for _ in range(n):
        if vertical:
            x = rnd.randint(x0, x1)
            y = rnd.randint(y0, y1)
            ln = rnd.randint(4, 14)
            d.line([(x, y), (x, y + ln)], fill=color + (alpha,), width=1)
        else:
            x = rnd.randint(x0, x1)
            y = rnd.randint(y0, y1)
            ln = rnd.randint(6, 22)
            d.line([(x, y), (x + ln, y)], fill=color + (alpha,), width=1)


def grain_region(img, box, seed, amount=11, exclude=()):
    """Deterministic film grain over a box of an RGB image: per-pixel
    black/white speckle at low alpha, breaking up flat colour blocks.
    exclude: rectangles (same coords as box) left untouched — used for
    the '%'-badge and '-4%' label inside scenes, which must stay
    pixel-identical. Returns a new RGB image."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    rnd = random.Random(seed)
    px = []
    for yy in range(h):
        gy = y0 + yy
        for xx in range(w):
            gx = x0 + xx
            if any(ex0 <= gx < ex1 and ey0 <= gy < ey1
                   for (ex0, ey0, ex1, ey1) in exclude):
                px.append((0, 0, 0, 0))
            else:
                a = rnd.randint(0, amount)
                px.append((255, 255, 255, a) if rnd.random() < 0.5
                          else (0, 0, 0, a))
    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ov.putdata(px)
    base = img.convert("RGBA")
    base.alpha_composite(ov, (x0, y0))
    return base.convert("RGB")


def grain_panel(img, x, y, w, h, seed, amount=11):
    """Film grain clipped to an icon panel's rounded rect, so it can never
    spill onto the paper, the number badge or the tile text. Applied
    in place on img."""
    rnd = random.Random(seed)
    px = []
    for _ in range(w * h):
        a = rnd.randint(0, amount)
        px.append((255, 255, 255, a) if rnd.random() < 0.5 else (0, 0, 0, a))
    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ov.putdata(px)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w, h), 9, fill=255)
    ov.putalpha(ImageChops.multiply(ov.split()[3], mask))
    base = img.convert("RGBA")
    base.alpha_composite(ov, (x, y))
    img.paste(base.convert("RGB"), (0, 0))


def hgrad_band(img, y0, y1, top, bottom):
    """Horizontal-ish vertical gradient band across the full image width."""
    vgrad(img, (0, y0, img.size[0], y1), top, bottom)


# ---------------------------------------------------------------- stories
BIG = [
    dict(
        kicker="STRAIT OF HORMUZ",
        head="Two tankers hit mines and burn in the Strait of Hormuz",
        summ=("IRGC says two tankers struck mines on an unauthorised route; "
              "Brent jumps to $91."),
        scene="hormuz",
    ),
    dict(
        kicker="TRADE WAR",
        head="US proposes tariffs on 14 partners; China hit hardest",
        summ=("Washington proposes an extra 20% on China; EU, Japan and "
              "Korea capped at 15%."),
        scene="tariffs",
    ),
    dict(
        kicker="WALL STREET",
        head="Nasdaq plunges 4% as AI rout rattles Wall Street",
        summ=("Nvidia fell 8.7% at one point; the VIX hit 35 before losses "
              "eased to 0.62%."),
        scene="nasdaq",
    ),
]

# (number, icon kind, hue, headline, summary)
TILES = [
    (4, "rocket", (38, 84, 124), "Shenzhou-24 docks at Tiangong",
     "Pakistan's first astronaut reaches orbit with two taikonauts."),
    (5, "jet", (90, 60, 60), "Ukraine hits five Russian jets",
     "Three MiG-31s and two Su-34s struck at Savasleyka airbase."),
    (6, "blast", (120, 60, 40), "Hamas security chief killed",
     "Israeli strike in Gaza City kills Abuelouf, wife and children."),
    (7, "flame", (150, 70, 20), "Houthis claim refinery strike",
     "Ras Tanura targeted; coalition says four drones intercepted."),
    (8, "truck", (140, 40, 30), "Cairo tanker fire kills 31",
     "Fuel tanker overturns and burns on a ring road; 15 injured."),
    (9, "treaty", (40, 96, 84), "Solomons picks Australia",
     "Security treaty bars foreign bases; a setback for Beijing."),
    (10, "gavel", (70, 70, 90), "Huawei convicted in US trial",
     "Guilty on 10 of 12 counts; verdict came on Tuesday."),
    (11, "chart_up", (30, 110, 60), "US growth beats forecasts",
     "Q3 GDP 4.3%; core PCE 3.3%, hotter than expected."),
    (12, "scales", (96, 74, 110), "Netanyahu bribery case in doubt",
     "Judges urge prosecutors to drop Case 4000."),
    (13, "store", (160, 110, 40), "Colombia siege ends",
     "Hostages freed in Cartagena supermarket; one captor killed."),
    (14, "ball", (50, 110, 50), "Liverpool 3-0 Brugge",
     "Lille stun Bayern 2-1 in the Champions League."),
    (15, "trophy", (176, 132, 52), "Sporting 2-2 Man Utd",
     "Fernandes brace; Tielemans sent off late in Lisbon."),
    (16, "goal", (40, 100, 130), "Barcelona 4-1 Sabah",
     "Gordon scores twice; Inter beat Stuttgart 2-0."),
    (17, "tag", (150, 90, 30), "Australia inflation hot",
     "October CPI 4.9% tops forecasts; Asia stocks slide."),
    (18, "columns", (80, 90, 110), "France passes 2026 budget",
     "Assembly approves 135-64; Airtel Money joins the FTSE 100."),
]

ALSO = [
    "Poundland collapses into administration; 12,000 jobs at risk",
    "EU unveils EUR 50bn Quantum Act and Sovereign Tech Fund",
    "Iran-linked hackers hit Saudi hospitals using N-able software",
    "Nollywood legend Pete Edochie dies at 79",
    "Copernicus: 22 Nov the hottest day on record, 2.23C above pre-industrial",
    "Macy\u2019s Thanksgiving parade postponed over storm forecast",
    "Persib Bandung 3-1 FC Seoul in the AFC Champions League Two",
    "ESA\u2019s Hera sees stadium-size crater on asteroid Dimorphos",
    "South Pole Telescope maps the distant universe in record detail",
    "Gaza declares meningitis epidemic alert as cases surge",
    "Carbon Budget: 1.5C likely passed regularly by 2031",
    "Trump: Iran war funded to January; ending the republic \u2018probably doable\u2019",
]

# ------------------------------------------------------------------- icons
def _shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


# Per-icon stage: (backdrop tone, light direction). Light direction is a
# (dx, dy) offset: (-1,-1) top-left, (1,-1) top-right, (0,-1) top.
STAGE = {
    "rocket": ((18, 32, 52), (-1, -1)),
    "jet": ((196, 208, 218), (1, -1)),
    "blast": ((30, 24, 22), (0, -1)),
    "flame": ((44, 26, 18), (0, -1)),
    "truck": ((190, 196, 200), (-1, -1)),
    "treaty": ((232, 224, 204), (-1, -1)),
    "gavel": ((196, 164, 120), (1, -1)),
    "chart_up": ((204, 228, 208), (-1, -1)),
    "scales": ((214, 206, 224), (1, -1)),
    "store": ((238, 226, 198), (0, -1)),
    "ball": ((206, 228, 200), (-1, -1)),
    "trophy": ((20, 30, 56), (-1, -1)),
    "goal": ((200, 218, 230), (1, -1)),
    "tag": ((232, 214, 182), (-1, -1)),
    "columns": ((220, 216, 206), (0, -1)),
}


def _backdrop(pd, w, h, kind, kseed):
    """Per-kind backdrop scene behind the icon subject — the fifth
    revision kills the identical soft white light-wash every panel used
    to share. Each panel now gets its own scene (night sky, dusty yard,
    warm interior, dusk...) with its own coloured light, direction and
    texture, all mottled and grainy, so no two panels share a backdrop.
    Drawn on the temp panel with the texture toolkit (fixed seeds), so
    the rounded-rect mask clips everything. Subjects are drawn on top
    afterwards; light subjects get a soft darker pool behind them and
    dark subjects a soft glow, so every subject stays readable against
    its own backdrop."""
    rnd = random.Random(5000 + kseed * 41)
    cx, cy = w // 2, h // 2
    _, (ldx, ldy) = STAGE[kind]

    def glow(gx, gy, rx, ry, col, a):
        pd.ellipse((gx - rx, gy - ry, gx + rx, gy + ry), fill=col + (a,))
        pd.ellipse((gx - rx // 2, gy - ry // 2, gx + rx // 2, gy + ry // 2),
                   fill=col + (min(255, a + 16),))

    def pool(col, a):
        # soft readability pool/glow behind the subject, offset towards
        # the light so it reads as light falling on the scene, not a wash
        glow(cx + ldx * 5, cy + ldy * 4, 20, 15, col, a)

    if kind == "rocket":
        # night sky: dim stars low and at the sides, faint nebula
        for _ in range(3):
            sx = rnd.randint(6, w - 6)
            sy = rnd.randint(4, 12)
            r = rnd.choice([1, 1, 2])
            pd.ellipse((sx - r, sy - r, sx + r, sy + r),
                       fill=(200, 220, 255, rnd.randint(90, 160)))
        for _ in range(4):
            sx = rnd.choice([rnd.randint(4, 9), rnd.randint(w - 9, w - 4)])
            sy = rnd.randint(22, h - 6)
            pd.ellipse((sx - 1, sy - 1, sx + 1, sy + 1),
                       fill=(200, 220, 255, rnd.randint(70, 140)))
        mottle(pd, (2, 2, w - 2, 22), 5100 + kseed,
               [(40, 60, 110), (70, 50, 100)], 4, 4, 12, 30)
        glow(12, 10, 18, 12, (150, 180, 230), 22)  # cool moonlight top-left
        pool((150, 180, 230), 14)
    elif kind == "jet":
        # hazy sky: cloud wisps up top, darker haze band low, warm sun
        for (wx, wy, wr) in ((12, 8, 10), (42, 6, 12), (26, 13, 8)):
            pd.ellipse((wx - wr, wy - 3, wx + wr, wy + 3),
                       fill=(255, 255, 255, 42))
        pd.rectangle((0, h - 12, w, h), fill=(140, 158, 180, 70))
        glow(50, 8, 16, 10, (255, 240, 200), 26)
        pool((120, 135, 155), 26)
    elif kind == "blast":
        # charcoal room: ember glow rising from the floor, drifting embers
        glow(30, 52, 22, 12, (255, 140, 50), 30)
        glow(30, 52, 12, 7, (255, 180, 90), 34)
        for _ in range(5):
            ex = rnd.randint(6, w - 6)
            ey = rnd.randint(8, 30)
            pd.ellipse((ex - 1, ey - 1, ex + 1, ey + 1),
                       fill=(255, 160, 70, rnd.randint(90, 170)))
        pd.ellipse((4, 2, 14, 10), fill=(0, 0, 0, 40))  # dark top-left corner
        pool((255, 150, 60), 24)
    elif kind == "flame":
        # dark hearth: warm glow from below, smoke wisps curling up top
        glow(30, 52, 22, 12, (255, 170, 70), 30)
        for (wx, wy, wr) in ((10, 8, 7), (46, 6, 8), (52, 14, 6)):
            pd.ellipse((wx - wr, wy - 2, wx + wr, wy + 2),
                       fill=(120, 110, 105, 50))
        pool((255, 160, 70), 24)
    elif kind == "truck":
        # dusty yard: haze band low, sun glare top-left, dust specks
        pd.rectangle((0, h - 14, w, h), fill=(170, 155, 130, 70))
        glow(10, 8, 16, 10, (255, 235, 200), 24)
        for _ in range(6):
            dx = rnd.randint(4, w - 4)
            dy = rnd.randint(h - 16, h - 4)
            pd.ellipse((dx - 1, dy - 1, dx + 1, dy + 1),
                       fill=(120, 105, 80, 90))
        pool((140, 150, 160), 24)
    elif kind == "treaty":
        # warm room: lamp glow top-left, shadow pooling bottom-right
        glow(10, 8, 18, 12, (255, 225, 170), 26)
        pd.ellipse((w - 16, h - 12, w + 6, h + 6), fill=(120, 100, 70, 45))
        pd.line([(0, h - 6), (w, h - 6)], fill=(150, 130, 95, 60), width=1)
        pool((200, 185, 150), 24)
    elif kind == "gavel":
        # wood-toned gloom: warm light top-right, dark corners, wood streaks
        glow(50, 8, 16, 10, (255, 210, 150), 26)
        pd.ellipse((0, 0, 12, 10), fill=(60, 40, 20, 50))
        pd.ellipse((0, h - 10, 12, h), fill=(60, 40, 20, 50))
        streaks(pd, (2, 2, w - 2, h - 2), 5200 + kseed, (90, 60, 30), 6,
                alpha=40)
        pool((150, 115, 75), 22)
    elif kind == "chart_up":
        # office: cool window light top-left, soft shadow bottom-right
        glow(10, 8, 18, 12, (210, 235, 255), 26)
        pd.rectangle((0, 0, 14, h), fill=(255, 255, 255, 18))
        pd.ellipse((w - 14, h - 10, w + 6, h + 6), fill=(90, 110, 105, 40))
        pool((160, 190, 165), 24)
    elif kind == "scales":
        # lavender dusk: darker band up top, low warm sun top-right
        pd.rectangle((0, 0, w, 10), fill=(150, 140, 180, 70))
        glow(50, 10, 16, 10, (255, 215, 170), 26)
        for (sx, sy) in ((8, 6), (20, 4)):
            pd.ellipse((sx - 1, sy - 1, sx + 1, sy + 1),
                       fill=(255, 255, 255, 130))
        pool((175, 165, 195), 24)
    elif kind == "store":
        # warm shop interior: lamp glow from above, shadow at the floor
        glow(30, 6, 22, 10, (255, 220, 160), 28)
        pd.rectangle((0, h - 8, w, h), fill=(120, 95, 60, 55))
        pd.line([(0, 10), (w, 10)], fill=(150, 120, 80, 50), width=1)
        pool((200, 185, 150), 24)
    elif kind == "ball":
        # pitch at dusk: pale sky band up top, floodlight top-left
        pd.rectangle((0, 0, w, 12), fill=(170, 190, 200, 70))
        glow(10, 8, 16, 10, (255, 245, 210), 26)
        pd.rectangle((0, h - 10, w, h), fill=(90, 140, 95, 60))
        pool((160, 190, 160), 24)
    elif kind == "trophy":
        # deep navy hall: warm spotlight top-left, sparkles, dark corners
        glow(12, 10, 18, 12, (255, 205, 120), 30)
        for _ in range(4):
            sx = rnd.randint(40, w - 6)
            sy = rnd.randint(4, 20)
            pd.ellipse((sx - 1, sy - 1, sx + 1, sy + 1),
                       fill=(255, 220, 150, 150))
        pd.ellipse((w - 12, h - 10, w, h), fill=(0, 0, 0, 50))
        pool((255, 200, 110), 24)
    elif kind == "goal":
        # pale sky: cloud wisps, warm sun top-right, horizon band low
        for (wx, wy, wr) in ((12, 8, 9), (36, 5, 11)):
            pd.ellipse((wx - wr, wy - 3, wx + wr, wy + 3),
                       fill=(255, 255, 255, 45))
        pd.rectangle((0, h - 10, w, h), fill=(150, 175, 150, 60))
        glow(50, 8, 15, 10, (255, 240, 200), 26)
        pool((160, 180, 195), 24)
    elif kind == "tag":
        # tan desk: wood streaks, warm lamp top-left, shadow bottom-right
        streaks(pd, (2, 2, w - 2, h - 2), 5300 + kseed, (150, 115, 70), 7,
                alpha=45)
        glow(10, 8, 17, 11, (255, 225, 170), 26)
        pd.ellipse((w - 14, h - 10, w + 6, h + 6), fill=(110, 85, 50, 45))
        pool((195, 170, 130), 24)
    elif kind == "columns":
        # stone at dusk: slate band up top, low warm sun from the right
        pd.rectangle((0, 0, w, 10), fill=(140, 140, 150, 70))
        glow(52, 30, 14, 12, (255, 210, 150), 26)
        pd.rectangle((0, h - 8, w, h), fill=(110, 105, 95, 55))
        pool((180, 175, 160), 24)


def draw_icon(img, d, x, y, w, h, kind, hue):
    """A small realistic 3D illustration, not a glossy app tile: a muted
    per-kind backdrop scene with its own coloured light and direction
    (no identical white wash, no diagonal gloss, no uniform gradient),
    and the subject drawn as a dimensional mini-scene — faceted shading,
    cast shadows, highlights that follow the form. The panel + backdrop
    are built on a temp image and pasted through a rounded-rect mask so
    nothing can spill onto the paper, the number badge or the tile text.
    Everything stays inside the 60x56 box, so the tile text, the number
    badges and the big scenes are untouched."""
    back = STAGE[kind][0]
    # panel + per-kind backdrop scene on a temp image, clipped to the
    # rounded rect
    panel = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    pd = ImageDraw.Draw(panel)
    pd.rounded_rectangle((0, 0, w, h), 9, fill=back + (255,))
    # mottled backdrop: dark/light blotches so the panel is never one
    # clean flat fill
    kseed = list(STAGE).index(kind)
    mottle(pd, (2, 2, w - 2, h - 2), 1000 + kseed * 17,
           [(0, 0, 0), (255, 255, 255)], 6, 5, 14, 26)
    # per-kind backdrop scene (fifth revision): the identical soft white
    # light-wash is gone — each panel gets its own mottled, grainy scene
    # with its own coloured light and direction
    _backdrop(pd, w, h, kind, kseed)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w, h), 9, fill=255)
    img.paste(panel, (x, y), mask)
    rrect(d, (x, y, x + w, y + h), 9, outline=(0, 0, 0, 70), width=1)
    cx, cy = x + w // 2, y + h // 2
    _mini_scene(img, x, y, w, h, kind, hue)
    # texture pass over the mini-scene: a few dark/light speckles, then
    # film grain clipped to the rounded panel — the subject stops looking
    # stamped out, and nothing can spill onto the badge or tile text
    rnd = random.Random(2000 + kseed * 31)
    for _ in range(5):
        sx = rnd.randint(x + 5, x + w - 5)
        sy = rnd.randint(y + 5, y + h - 5)
        col = (0, 0, 0, 46) if rnd.random() < 0.5 else (255, 255, 255, 46)
        d.ellipse((sx, sy, sx + 1, sy + 1), fill=col)
    grain_panel(img, x, y, w, h, 3000 + kseed * 31)


def _mini_scene(img, x, y, w, h, kind, hue):
    """One subject redrawn as a realistic textured mini-scene, in the same
    visual language as the big scenes: brushed metal, wood grain, fibre
    paper, rust, scuffs, ragged edges and mottled colour — no clean flat
    glyphs. The subject is drawn on a temp panel image with the texture
    toolkit (mottle, wobble, streaks; all fixed seeds) and alpha-
    composited through the rounded-rect mask, so nothing can spill onto
    the badge, the tile text or the paper. Colours are art-directed per
    kind; hue is kept for the call signature."""
    temp = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(temp, "RGBA")
    cx, cy = w // 2, h // 2
    kseed = list(STAGE).index(kind)
    S = 4000 + kseed * 37  # base seed for this icon's texture

    if kind == "rocket":
        # stars of varied brightness + two cross sparkles
        rnd = random.Random(S + 1)
        for _ in range(7):
            sx = rnd.randint(6, w - 6)
            sy = rnd.randint(6, 20)
            r = rnd.choice([1, 1, 2])
            a = rnd.randint(120, 230)
            d.ellipse((sx - r, sy - r, sx + r, sy + r), fill=(255, 255, 255, a))
        for (sx, sy) in ((9, 10), (51, 16)):
            d.line([(sx - 2, sy), (sx + 2, sy)], fill=(255, 255, 255, 180), width=1)
            d.line([(sx, sy - 2), (sx, sy + 2)], fill=(255, 255, 255, 180), width=1)
        # ground shadow, smoke puffs, ragged layered flame
        d.ellipse((cx - 13, cy + 22, cx + 13, cy + 26), fill=(0, 0, 0, 80))
        for (px, py, pr, al) in ((cx - 9, cy + 20, 5, 70), (cx + 8, cy + 22, 4, 60),
                                 (cx - 2, cy + 24, 4, 55)):
            d.ellipse((px - pr, py - pr, px + pr, py + pr), fill=(200, 200, 210, al))
        d.ellipse((cx - 9, cy + 10, cx + 9, cy + 26), fill=(255, 150, 50, 70))
        d.polygon(wobble([(cx - 5, cy + 11), (cx + 5, cy + 11), (cx + 3, cy + 20),
                          (cx, cy + 25), (cx - 3, cy + 20)], S + 2, 2),
                  fill=(230, 120, 30))
        d.polygon(wobble([(cx - 3, cy + 12), (cx + 3, cy + 12), (cx + 1, cy + 19),
                          (cx, cy + 22), (cx - 1, cy + 19)], S + 3, 1),
                  fill=(245, 190, 60))
        d.polygon([(cx - 1, cy + 13), (cx + 1, cy + 13), (cx, cy + 19)],
                  fill=(255, 240, 180))
        for (ex, ey) in ((cx - 8, cy + 16), (cx + 9, cy + 18), (cx - 4, cy + 24)):
            d.ellipse((ex - 1, ey - 1, ex + 1, ey + 1), fill=(255, 200, 90, 220))
        # body: light left facet, mid right facet, brushed steel + grime
        d.polygon([(cx - 7, cy - 13), (cx, cy - 13), (cx, cy + 12), (cx - 7, cy + 12)],
                  fill=(200, 214, 226))
        d.polygon([(cx, cy - 13), (cx + 7, cy - 13), (cx + 7, cy + 12), (cx, cy + 12)],
                  fill=(120, 140, 160))
        streaks(d, (cx - 7, cy - 13, cx + 7, cy + 12), S + 4, (255, 255, 255), 5,
                vertical=True, alpha=50)
        streaks(d, (cx - 7, cy - 13, cx + 7, cy + 12), S + 5, (60, 70, 80), 4,
                vertical=True, alpha=45)
        mottle(d, (cx - 7, cy - 13, cx + 7, cy + 12), S + 6,
               [(90, 100, 110), (70, 80, 90)], 3, 2, 4, 40)
        # nose cone: light left half, mid right half
        d.polygon([(cx - 7, cy - 13), (cx, cy - 20), (cx, cy - 13)], fill=(225, 232, 238))
        d.polygon([(cx, cy - 20), (cx + 7, cy - 13), (cx, cy - 13)], fill=(140, 158, 176))
        # fins with wobbly edges: shaded, darker on the far side
        d.polygon(wobble([(cx - 7, cy + 4), (cx - 13, cy + 14), (cx - 7, cy + 12)],
                         S + 7, 1), fill=(150, 168, 186))
        d.polygon(wobble([(cx + 7, cy + 4), (cx + 13, cy + 14), (cx + 7, cy + 12)],
                         S + 8, 1), fill=(90, 108, 128))
        # window: dark glass with an uneven glint
        d.ellipse((cx - 4, cy - 7, cx + 4, cy + 1), fill=(28, 52, 78))
        d.polygon(wobble([(cx - 3, cy - 6), (cx, cy - 6), (cx - 1, cy - 3),
                          (cx - 3, cy - 3)], S + 9, 1), fill=(255, 255, 255, 220))
        d.line([(cx - 7, cy - 12), (cx - 7, cy + 11)], fill=(255, 255, 255, 170), width=1)
    elif kind == "jet":
        # hazy horizon band + ragged contrail puffs
        d.rectangle((2, cy + 12, w - 2, cy + 16), fill=(255, 255, 255, 40))
        d.line([(cx - 22, cy + 13), (cx + 22, cy + 13)], fill=(150, 160, 170), width=1)
        rnd = random.Random(S + 1)
        for _ in range(5):
            px = cx - 26 + rnd.randint(0, 12)
            py = cy - 4 + rnd.randint(-2, 2)
            pr = rnd.randint(2, 4)
            d.ellipse((px - pr, py - pr, px + pr, py + pr),
                      fill=(255, 255, 255, rnd.randint(60, 120)))
        # tail fin + fuselage with panel lines and wear
        d.polygon(wobble([(cx - 14, cy - 1), (cx - 10, cy - 13), (cx - 5, cy - 1)],
                         S + 2, 1), fill=(70, 46, 46))
        d.polygon([(cx - 16, cy + 1), (cx + 14, cy - 4), (cx + 18, cy),
                   (cx + 14, cy + 4), (cx - 16, cy + 5)], fill=(110, 72, 72))
        mottle(d, (cx - 16, cy - 4, cx + 18, cy + 5), S + 3,
               [(140, 95, 95), (80, 55, 55)], 4, 2, 5, 40)
        for ly in (cy - 1, cy + 2):
            d.line([(cx - 12, ly), (cx + 12, ly - 1)], fill=(80, 52, 52), width=1)
        d.line([(cx - 12, cy - 2), (cx + 12, cy - 4)], fill=(190, 150, 140), width=2)
        d.line([(cx - 12, cy + 4), (cx + 12, cy + 3)], fill=(60, 40, 40), width=1)
        # wings: light top face, dark underside, wobbled edges
        d.polygon(wobble([(cx - 2, cy - 2), (cx + 6, cy - 15), (cx + 10, cy - 2)],
                         S + 4, 1), fill=(140, 95, 95))
        d.polygon(wobble([(cx - 6, cy + 4), (cx - 2, cy + 15), (cx + 2, cy + 4)],
                         S + 5, 1), fill=(60, 40, 40))
        # cockpit glass with an irregular glint
        d.ellipse((cx + 8, cy - 4, cx + 14, cy), fill=(40, 60, 80))
        d.polygon([(cx + 9, cy - 4), (cx + 11, cy - 4), (cx + 10, cy - 2)],
                  fill=(255, 255, 255, 200))
        d.ellipse((cx - 6, cy + 16, cx + 16, cy + 20), fill=(0, 0, 0, 55))
    elif kind == "blast":
        # ground glow with falloff: concentric translucent ellipses
        for (r, al) in ((16, 40), (12, 60), (8, 80)):
            d.ellipse((cx - r, cy + 14 - r // 2, cx + r, cy + 14 + r // 2),
                      fill=(255, 140, 40, al))
        # layered starburst with wobbly edges so the spikes look organic
        for (r_out, r_in, col, rot, sd) in ((17, 8, (160, 60, 20), 0.0, S + 1),
                                            (13, 6, (220, 100, 30), 0.20, S + 2),
                                            (9, 4, (250, 190, 60), 0.42, S + 3)):
            pts = []
            for i in range(16):
                ang = math.pi * i / 8 + rot
                r = r_out if i % 2 == 0 else r_in
                pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
            d.polygon(wobble(pts, sd, 2), fill=col)
        # mottled core + debris flecks of varied size + smoke wisps
        mottle(d, (cx - 6, cy - 6, cx + 6, cy + 6), S + 4,
               [(255, 235, 160), (255, 255, 255)], 4, 2, 4, 90)
        d.ellipse((cx - 2, cy - 2, cx + 2, cy + 2), fill=(255, 255, 255))
        rnd = random.Random(S + 5)
        for _ in range(7):
            dx = cx + rnd.randint(-24, 24)
            dy = cy + rnd.randint(-18, 16)
            r = rnd.choice([1, 1, 2])
            d.ellipse((dx - r, dy - r, dx + r, dy + r), fill=(200, 90, 30))
        for (wx, wy) in ((cx - 18, cy - 12), (cx + 19, cy - 10)):
            d.line(wobble([(wx, wy), (wx + 6, wy + 3), (wx + 10, wy + 1)], S + 6, 1),
                   fill=(120, 110, 105, 120), width=1)
        d.ellipse((cx - 12, cy + 16, cx + 12, cy + 20), fill=(255, 140, 40, 70))
    elif kind == "flame":
        # glow behind the flame, then nested teardrops with wobbly edges
        d.ellipse((cx - 14, cy - 14, cx + 14, cy + 18), fill=(255, 140, 40, 55))
        d.polygon(wobble([(cx, cy - 18), (cx + 10, cy - 4), (cx + 11, cy + 8),
                          (cx + 5, cy + 16), (cx - 5, cy + 16), (cx - 11, cy + 8),
                          (cx - 10, cy - 4)], S + 1, 2), fill=(200, 70, 20))
        mottle(d, (cx - 8, cy - 6, cx + 8, cy + 12), S + 2,
               [(230, 100, 30), (170, 55, 15)], 5, 2, 5, 60)
        d.polygon(wobble([(cx + 1, cy - 10), (cx + 7, cy), (cx + 6, cy + 10),
                          (cx - 3, cy + 12), (cx - 6, cy + 2)], S + 3, 2),
                  fill=(245, 140, 40))
        d.polygon(wobble([(cx, cy - 4), (cx + 4, cy + 3), (cx + 3, cy + 11),
                          (cx - 3, cy + 11), (cx - 4, cy + 3)], S + 4, 1),
                  fill=(255, 205, 80))
        d.ellipse((cx - 2, cy + 7, cx + 2, cy + 12), fill=(255, 240, 180))
        # embers rising off the flame
        for (ex, ey) in ((cx - 7, cy - 12), (cx + 6, cy - 14), (cx + 2, cy - 18)):
            d.ellipse((ex - 1, ey - 1, ex + 1, ey + 1), fill=(255, 190, 80, 220))
        d.ellipse((cx - 10, cy + 16, cx + 10, cy + 20), fill=(0, 0, 0, 90))
    elif kind == "truck":
        # ground line + wheel shadows first
        d.line([(cx - 24, cy + 15), (cx + 24, cy + 15)], fill=(120, 128, 134), width=1)
        for wx in (cx - 10, cx + 11):
            d.ellipse((wx - 6, cy + 12, wx + 6, cy + 17), fill=(0, 0, 0, 80))
        # tank: brushed streaks + rust patches, bright top band, dark end cap
        d.rectangle((cx - 16, cy - 6, cx + 6, cy + 8), fill=(150, 50, 35))
        streaks(d, (cx - 16, cy - 6, cx + 6, cy + 8), S + 1, (220, 130, 95), 6,
                alpha=55)
        mottle(d, (cx - 16, cy + 2, cx + 6, cy + 8), S + 2,
               [(120, 60, 30), (90, 45, 25)], 3, 2, 4, 70)
        d.rectangle((cx - 16, cy - 6, cx + 6, cy - 1), fill=(205, 95, 65))
        d.line([(cx - 16, cy - 6), (cx + 6, cy - 6)], fill=(240, 150, 110), width=1)
        d.ellipse((cx + 4, cy - 6, cx + 10, cy + 8), fill=(105, 35, 25))
        d.line([(cx - 16, cy + 8), (cx + 6, cy + 8)], fill=(90, 30, 22), width=1)
        # cab: dark body, glass window with a glare streak, headlight glare
        d.polygon([(cx + 6, cy - 6), (cx + 15, cy - 6), (cx + 17, cy + 8),
                   (cx + 6, cy + 8)], fill=(90, 30, 25))
        d.polygon([(cx + 9, cy - 4), (cx + 14, cy - 4), (cx + 14, cy + 1),
                   (cx + 9, cy + 1)], fill=(140, 170, 190))
        d.line([(cx + 10, cy - 4), (cx + 12, cy + 1)], fill=(255, 255, 255, 220),
               width=1)
        d.ellipse((cx + 15, cy + 4, cx + 17, cy + 6), fill=(255, 220, 120))
        d.ellipse((cx + 14, cy + 3, cx + 18, cy + 7), fill=(255, 220, 120, 60))
        # wheels: dark tyres with tread ticks, hubs with a highlight
        for wx in (cx - 10, cx + 11):
            d.ellipse((wx - 5, cy + 5, wx + 5, cy + 15), fill=(25, 25, 25))
            for ang in range(0, 360, 60):
                a = math.radians(ang)
                d.line([(wx + 3 * math.cos(a), cy + 10 + 3 * math.sin(a)),
                        (wx + 5 * math.cos(a), cy + 10 + 5 * math.sin(a))],
                       fill=(70, 70, 70), width=1)
            d.ellipse((wx - 2, cy + 8, wx + 2, cy + 12), fill=(130, 130, 130))
            d.ellipse((wx - 2, cy + 8, wx, cy + 10), fill=(200, 200, 200, 180))
    elif kind == "treaty":
        # sheet shadow, then the sheet with wobbly uneven edges + fibre
        d.ellipse((cx - 12, cy + 12, cx + 14, cy + 18), fill=(0, 0, 0, 55))
        d.polygon(wobble([(cx - 11, cy - 14), (cx + 9, cy - 14), (cx + 11, cy - 12),
                          (cx + 11, cy + 14), (cx - 11, cy + 14), (cx - 11, cy - 12)],
                         S + 1, 1), fill=(250, 248, 240))
        streaks(d, (cx - 10, cy - 12, cx + 10, cy + 13), S + 2, (200, 195, 180), 8,
                alpha=45)
        d.rectangle((cx + 8, cy - 12, cx + 11, cy + 14), fill=(210, 205, 190))
        # folded corner, top right
        d.polygon([(cx + 11, cy - 12), (cx + 4, cy - 12), (cx + 11, cy - 5)],
                  fill=(225, 220, 205))
        d.line([(cx + 4, cy - 12), (cx + 11, cy - 5)], fill=(180, 175, 160), width=1)
        # handwritten-style wavy lines
        for (ly, ln) in ((cy - 6, 14), (cy, 14), (cy + 6, 8)):
            d.line(wobble([(cx - 7, ly), (cx - 7 + ln // 2, ly), (cx - 7 + ln, ly)],
                          S + 3 + ly, 1), fill=(90, 90, 80), width=2)
        # wax seal with an irregular edge + ribbon folds
        d.polygon(wobble([(cx + 3, cy + 8), (cx + 7, cy + 8), (cx + 11, cy + 11),
                          (cx + 12, cy + 14), (cx + 9, cy + 17), (cx + 5, cy + 17),
                          (cx + 3, cy + 13)], S + 4, 1), fill=(190, 50, 35))
        mottle(d, (cx + 4, cy + 9, cx + 11, cy + 16), S + 5,
               [(220, 90, 60), (150, 35, 25)], 3, 1, 3, 70)
        d.ellipse((cx + 5, cy + 9, cx + 8, cy + 12), fill=(235, 120, 95))
        d.polygon([(cx + 6, cy + 16), (cx + 10, cy + 16), (cx + 8, cy + 21)],
                  fill=(160, 40, 30))
        d.line([(cx + 7, cy + 16), (cx + 8, cy + 21)], fill=(120, 30, 22), width=1)
    elif kind == "gavel":
        # sound block with wear, then handle, then head
        d.ellipse((cx - 12, cy + 17, cx + 12, cy + 21), fill=(0, 0, 0, 70))
        d.rectangle((cx - 12, cy + 11, cx + 12, cy + 16), fill=(120, 80, 45))
        streaks(d, (cx - 12, cy + 11, cx + 12, cy + 16), S + 1, (160, 115, 65), 5,
                alpha=60)
        mottle(d, (cx - 12, cy + 11, cx + 12, cy + 16), S + 2, [(90, 60, 30)],
               2, 2, 4, 60)
        d.line([(cx - 12, cy + 11), (cx + 12, cy + 11)], fill=(195, 145, 85), width=1)
        # handle: wood grain along its length with a light edge
        d.line([(cx - 1, cy - 1), (cx - 12, cy + 11)], fill=(110, 75, 45), width=5)
        d.line([(cx - 3, cy - 3), (cx - 13, cy + 9)], fill=(140, 95, 55), width=1)
        d.line([(cx - 2, cy - 2), (cx - 12, cy + 10)], fill=(175, 130, 80), width=1)
        # head: three facets with wood-grain streaks + worn edges
        d.polygon([(cx - 12, cy - 11), (cx + 2, cy - 15), (cx + 14, cy - 1),
                   (cx, cy + 3)], fill=(140, 100, 60))
        d.polygon([(cx - 12, cy - 11), (cx + 2, cy - 15), (cx + 5, cy - 12),
                   (cx - 9, cy - 8)], fill=(180, 138, 88))
        d.polygon([(cx, cy + 3), (cx + 14, cy - 1), (cx + 12, cy + 2),
                   (cx - 1, cy + 5)], fill=(95, 65, 35))
        streaks(d, (cx - 12, cy - 15, cx + 14, cy + 3), S + 3, (200, 160, 100), 6,
                alpha=50)
        mottle(d, (cx - 10, cy - 12, cx + 12, cy + 2), S + 4,
               [(110, 75, 40), (160, 120, 70)], 3, 2, 4, 50)
        d.line(wobble([(cx - 12, cy - 11), (cx + 2, cy - 15)], S + 5, 1),
               fill=(210, 170, 110), width=1)
    elif kind == "chart_up":
        # three bars with textured faces + irregular top edges
        for (bx, bh, sd) in ((cx - 13, 8, S + 1), (cx - 3, 13, S + 2),
                             (cx + 7, 18, S + 3)):
            d.rectangle((bx, cy + 14 - bh, bx + 7, cy + 14), fill=(40, 130, 75))
            mottle(d, (bx, cy + 14 - bh, bx + 7, cy + 14), sd,
                   [(60, 160, 95), (25, 90, 55)], 3, 1, 3, 60)
            d.rectangle((bx, cy + 14 - bh, bx + 7, cy + 14 - bh + 3),
                        fill=(125, 205, 155))
            d.rectangle((bx + 5, cy + 14 - bh, bx + 7, cy + 14), fill=(25, 85, 50))
            d.line(wobble([(bx, cy + 14 - bh), (bx + 7, cy + 14 - bh)], sd + 10, 1),
                   fill=(90, 170, 120), width=1)
        # axes with a light top edge
        d.line([(cx - 16, cy + 14), (cx + 16, cy + 14)], fill=(60, 80, 65), width=2)
        d.line([(cx - 16, cy - 14), (cx - 16, cy + 14)], fill=(60, 80, 65), width=2)
        d.line([(cx - 16, cy - 14), (cx - 16, cy + 13)], fill=(150, 175, 155), width=1)
        # trend line: hand-wobbled, soft glow underlay, arrowhead
        pts = [(cx - 13, cy + 6), (cx - 4, cy - 3), (cx + 4, cy + 2), (cx + 14, cy - 11)]
        wpts = [pts[0]] + wobble(pts[1:-1], S + 4, 2) + [pts[-1]]
        d.line(wpts, fill=(120, 220, 160, 110), width=5, joint="curve")
        d.line(wpts, fill=(20, 110, 55), width=2, joint="curve")
        d.polygon([(cx + 14, cy - 11), (cx + 8, cy - 11), (cx + 14, cy - 5)],
                  fill=(20, 110, 55))
        d.ellipse((cx - 12, cy + 15, cx + 12, cy + 19), fill=(0, 0, 0, 45))
    elif kind == "scales":
        # base slab with wear + pillar with brushed streaks, brass finial
        d.ellipse((cx - 11, cy + 16, cx + 11, cy + 20), fill=(0, 0, 0, 60))
        d.rectangle((cx - 9, cy + 12, cx + 9, cy + 16), fill=(110, 95, 130))
        streaks(d, (cx - 9, cy + 12, cx + 9, cy + 16), S + 1, (170, 155, 190), 4,
                alpha=50)
        d.line([(cx - 9, cy + 12), (cx + 9, cy + 12)], fill=(175, 160, 195), width=1)
        d.rectangle((cx - 2, cy - 12, cx + 2, cy + 12), fill=(125, 105, 145))
        streaks(d, (cx - 2, cy - 12, cx + 2, cy + 12), S + 2, (190, 175, 210), 3,
                vertical=True, alpha=55)
        d.line([(cx - 2, cy - 12), (cx - 2, cy + 12)], fill=(185, 170, 205), width=1)
        d.ellipse((cx - 2, cy - 16, cx + 2, cy - 12), fill=(200, 175, 90))
        d.ellipse((cx - 2, cy - 16, cx, cy - 14), fill=(240, 220, 150))
        # beam with a light top edge
        d.rectangle((cx - 15, cy - 12, cx + 15, cy - 10), fill=(125, 105, 145))
        d.line([(cx - 15, cy - 12), (cx + 15, cy - 12)], fill=(185, 170, 205), width=1)
        # pans: chain links as small rings + bowls with worn rims
        for px in (cx - 13, cx + 13):
            for (lx, ly) in ((px - 3, cy - 7), (px + 3, cy - 7),
                             (px - 2, cy - 3), (px + 2, cy - 3)):
                d.ellipse((lx - 1, ly - 1, lx + 1, ly + 1),
                          outline=(150, 135, 170), width=1)
            d.line([(px - 4, cy - 10), (px, cy + 2)], fill=(100, 85, 120), width=1)
            d.line([(px + 4, cy - 10), (px, cy + 2)], fill=(100, 85, 120), width=1)
            d.ellipse((px - 6, cy - 1, px + 6, cy + 7), fill=(90, 75, 110))
            mottle(d, (px - 6, cy - 1, px + 6, cy + 7), S + 3 + px,
                   [(120, 100, 140), (70, 58, 90)], 2, 1, 3, 60)
            d.ellipse((px - 5, cy - 2, px + 5, cy + 5), fill=(175, 160, 195))
            d.ellipse((px - 3, cy - 2, px + 1, cy), fill=(220, 210, 230))
            d.arc((px - 6, cy - 1, px + 6, cy + 7), 200, 340,
                  fill=(60, 50, 75), width=1)
    elif kind == "store":
        # body with mottled wall texture + door + window with reflections
        d.rectangle((cx - 13, cy, cx + 13, cy + 14), fill=(205, 170, 115))
        mottle(d, (cx - 13, cy, cx + 13, cy + 14), S + 1,
               [(220, 190, 135), (180, 145, 95)], 4, 2, 5, 50)
        d.rectangle((cx + 10, cy, cx + 13, cy + 14), fill=(165, 130, 80))
        d.rectangle((cx - 3, cy + 4, cx + 3, cy + 14), fill=(90, 60, 35))
        d.line([(cx - 3, cy + 4), (cx - 3, cy + 14)], fill=(140, 100, 60), width=1)
        d.ellipse((cx - 2, cy + 5, cx, cy + 7), fill=(255, 255, 255, 200))
        d.rectangle((cx - 11, cy + 4, cx - 6, cy + 10), fill=(150, 185, 200))
        d.line([(cx - 10, cy + 4), (cx - 8, cy + 10)], fill=(255, 255, 255, 200),
               width=1)
        d.line([(cx - 8, cy + 4), (cx - 6, cy + 10)], fill=(255, 255, 255, 120),
               width=1)
        d.ellipse((cx - 13, cy + 15, cx + 13, cy + 19), fill=(0, 0, 0, 60))
        # awning: fabric folds (vertical streaks) + uneven scalloped edge
        for k in range(4):
            x0 = cx - 16 + k * 8
            col = (238, 232, 214) if k % 2 == 0 else (180, 60, 45)
            d.polygon([(x0, cy - 8), (x0 + 8, cy - 8), (x0 + 6, cy), (x0 - 2, cy)],
                      fill=col)
            streaks(d, (x0, cy - 8, x0 + 8, cy), S + 2 + k, (0, 0, 0), 2,
                    vertical=True, alpha=35)
        for k in range(4):
            sx = cx - 12 + k * 8 + (1 if k % 2 else -1)
            d.ellipse((sx - 3, cy - 2, sx + 3, cy + 3),
                      fill=(180, 60, 45) if k % 2 else (238, 232, 214))
    elif kind == "ball":
        # grass blades + cast shadow
        rnd = random.Random(S + 1)
        for _ in range(8):
            gx = cx - 20 + rnd.randint(0, 40)
            d.line([(gx, cy + 16), (gx + rnd.randint(-1, 1), cy + 13)],
                   fill=(110, 150, 100), width=1)
        d.line([(cx - 22, cy + 16), (cx + 22, cy + 16)], fill=(140, 175, 130), width=1)
        d.ellipse((cx - 12, cy + 15, cx + 12, cy + 19), fill=(0, 0, 0, 65))
        # ball: mottled leather, shade crescent, curved specular highlight
        d.ellipse((cx - 15, cy - 15, cx + 15, cy + 15), fill=(245, 245, 240))
        mottle(d, (cx - 14, cy - 14, cx + 14, cy + 14), S + 2,
               [(225, 225, 215), (210, 210, 200)], 6, 2, 5, 40)
        d.ellipse((cx - 2, cy + 1, cx + 15, cy + 15), fill=(200, 205, 200, 120))
        d.ellipse((cx - 12, cy - 13, cx - 2, cy - 3), fill=(255, 255, 255, 200))
        d.arc((cx - 13, cy - 14, cx - 1, cy - 2), 200, 320,
              fill=(255, 255, 255, 160), width=2)
        d.ellipse((cx - 15, cy - 15, cx + 15, cy + 15), outline=(40, 40, 40), width=2)
        # centre pentagon + partial patches + seams + scuff marks
        d.polygon([(cx, cy - 7), (cx + 7, cy - 2), (cx + 4, cy + 6), (cx - 4, cy + 6),
                   (cx - 7, cy - 2)], fill=(35, 35, 35))
        d.polygon([(cx - 4, cy - 15), (cx + 4, cy - 15), (cx + 2, cy - 9),
                   (cx - 2, cy - 9)], fill=(35, 35, 35))
        d.polygon([(cx - 15, cy - 2), (cx - 9, cy - 2), (cx - 9, cy + 4),
                   (cx - 15, cy + 4)], fill=(35, 35, 35))
        d.polygon([(cx + 10, cy + 9), (cx + 15, cy + 12), (cx + 12, cy + 15),
                   (cx + 8, cy + 13)], fill=(35, 35, 35))
        for (x1, y1, x2, y2) in ((cx, cy - 7, cx, cy - 15), (cx + 7, cy - 2, cx + 15, cy),
                                 (cx - 7, cy - 2, cx - 15, cy - 4),
                                 (cx + 4, cy + 6, cx + 10, cy + 12),
                                 (cx - 4, cy + 6, cx - 10, cy + 12)):
            d.line([(x1, y1), (x2, y2)], fill=(60, 60, 60), width=1)
        for (sx, sy, sl) in ((cx - 10, cy + 8, 4), (cx + 9, cy - 8, 3),
                             (cx - 2, cy + 12, 3)):
            d.line([(sx, sy), (sx + sl, sy + 1)], fill=(150, 150, 145, 160), width=1)
    elif kind == "trophy":
        # warm glow behind the cup
        d.ellipse((cx - 14, cy - 14, cx + 14, cy + 12), fill=(255, 200, 90, 45))
        # handles first (behind the cup body)
        d.arc((cx - 17, cy - 16, cx - 7, cy - 2), 90, 270, fill=(170, 130, 45),
              width=3)
        d.arc((cx + 7, cy - 16, cx + 17, cy - 2), 270, 90, fill=(170, 130, 45),
              width=3)
        # cup body: brushed gold streaks + tarnish variation, then facets
        d.polygon([(cx - 10, cy - 16), (cx + 10, cy - 16), (cx + 6, cy + 2),
                   (cx - 6, cy + 2)], fill=(200, 155, 55))
        streaks(d, (cx - 10, cy - 16, cx + 10, cy + 2), S + 1, (240, 200, 100), 5,
                vertical=True, alpha=55)
        streaks(d, (cx - 10, cy - 16, cx + 10, cy + 2), S + 2, (120, 85, 25), 4,
                vertical=True, alpha=50)
        mottle(d, (cx - 10, cy - 16, cx + 10, cy + 2), S + 3,
               [(160, 115, 35), (220, 175, 70)], 3, 2, 4, 55)
        d.polygon([(cx - 10, cy - 16), (cx - 3, cy - 16), (cx - 4, cy + 2),
                   (cx - 6, cy + 2)], fill=(240, 195, 90))
        d.polygon([(cx + 4, cy - 16), (cx + 10, cy - 16), (cx + 6, cy + 2),
                   (cx + 4, cy + 2)], fill=(140, 100, 30))
        # rim: bright band + white top edge
        d.rectangle((cx - 10, cy - 16, cx + 10, cy - 13), fill=(245, 205, 100))
        d.line([(cx - 10, cy - 16), (cx + 10, cy - 16)], fill=(255, 240, 190), width=1)
        # stem + base slab with brushed streaks and a bright top edge
        d.rectangle((cx - 2, cy + 2, cx + 2, cy + 10), fill=(170, 130, 45))
        d.line([(cx - 2, cy + 2), (cx - 2, cy + 10)], fill=(240, 195, 90), width=1)
        d.rectangle((cx - 9, cy + 10, cx + 9, cy + 15), fill=(140, 100, 30))
        streaks(d, (cx - 9, cy + 10, cx + 9, cy + 15), S + 4, (200, 160, 80), 3,
                alpha=50)
        d.line([(cx - 9, cy + 10), (cx + 9, cy + 10)], fill=(240, 195, 90), width=1)
        # sparkles of varied size + ground shadow
        for (sx, sy, sr) in ((cx + 16, cy - 12, 3), (cx - 18, cy + 2, 3),
                             (cx + 14, cy + 6, 2)):
            d.line([(sx - sr, sy), (sx + sr, sy)], fill=(255, 255, 255, 230), width=1)
            d.line([(sx, sy - sr), (sx, sy + sr)], fill=(255, 255, 255, 230), width=1)
        d.ellipse((cx - 11, cy + 16, cx + 11, cy + 19), fill=(0, 0, 0, 85))
    elif kind == "goal":
        # grass blades + ground line + shadow
        rnd = random.Random(S + 1)
        for _ in range(8):
            gx = cx - 20 + rnd.randint(0, 40)
            d.line([(gx, cy + 16), (gx + rnd.randint(-1, 1), cy + 13)],
                   fill=(110, 150, 110), width=1)
        d.line([(cx - 22, cy + 15), (cx + 22, cy + 15)], fill=(140, 170, 150), width=1)
        d.ellipse((cx - 12, cy + 14, cx + 12, cy + 18), fill=(0, 0, 0, 55))
        # net backing with mottled tone
        d.rectangle((cx - 16, cy - 12, cx + 16, cy + 14), fill=(185, 200, 214))
        mottle(d, (cx - 16, cy - 12, cx + 16, cy + 14), S + 2,
               [(200, 212, 226), (165, 180, 198)], 4, 3, 7, 40)
        # net grid: uneven mesh, slight sag on the horizontals
        for gx in range(cx - 16, cx + 17, 6):
            d.line(wobble([(gx, cy - 12), (gx, cy + 14)], S + 3 + gx, 1),
                   fill=(150, 165, 180), width=1)
        for gy in range(cy - 12, cy + 15, 6):
            d.line(wobble([(cx - 16, gy), (cx, gy + 1), (cx + 16, gy)], S + 4 + gy, 1),
                   fill=(150, 165, 180), width=1)
        # posts + crossbar: white with wear, light top edge, grey far edge
        d.rectangle((cx - 16, cy - 12, cx - 13, cy + 14), fill=(250, 250, 248))
        d.rectangle((cx + 13, cy - 12, cx + 16, cy + 14), fill=(250, 250, 248))
        d.rectangle((cx - 16, cy - 12, cx + 16, cy - 9), fill=(250, 250, 248))
        mottle(d, (cx - 16, cy - 12, cx + 16, cy + 14), S + 5,
               [(235, 235, 230), (200, 205, 210)], 3, 2, 4, 35)
        d.line([(cx - 16, cy - 12), (cx + 16, cy - 12)], fill=(255, 255, 255), width=1)
        d.line([(cx + 14, cy - 9), (cx + 14, cy + 14)], fill=(170, 180, 190), width=1)
        # ball inside the net with its own little shadow + a scuff
        d.ellipse((cx + 2, cy + 9, cx + 10, cy + 13), fill=(0, 0, 0, 60))
        d.ellipse((cx + 2, cy + 3, cx + 10, cy + 11), fill=(245, 245, 240))
        d.ellipse((cx + 2, cy + 3, cx + 10, cy + 11), outline=(40, 40, 40), width=1)
        d.polygon([(cx + 6, cy + 5), (cx + 8, cy + 7), (cx + 6, cy + 9),
                   (cx + 4, cy + 7)], fill=(35, 35, 35))
        d.line([(cx + 3, cy + 4), (cx + 5, cy + 5)], fill=(150, 150, 145, 160), width=1)
    elif kind == "tag":
        # string loop curving up-right, with a lighter inner strand
        d.arc((cx - 2, cy - 20, cx + 18, cy - 2), 200, 340, fill=(120, 90, 60),
              width=2)
        d.arc((cx - 2, cy - 20, cx + 18, cy - 2), 200, 340, fill=(150, 115, 75),
              width=1)
        # tag body: wobbly worn edges, fibre texture, worn corners
        d.polygon(wobble([(cx - 12, cy - 4), (cx + 2, cy - 14), (cx + 14, cy - 10),
                          (cx + 14, cy + 8), (cx - 2, cy + 14), (cx - 12, cy + 6)],
                         S + 1, 1), fill=(200, 140, 55))
        streaks(d, (cx - 12, cy - 14, cx + 14, cy + 14), S + 2, (230, 180, 100), 6,
                alpha=45)
        mottle(d, (cx - 12, cy - 14, cx + 14, cy + 14), S + 3,
               [(170, 110, 40), (220, 165, 80)], 3, 2, 4, 50)
        d.polygon([(cx - 12, cy - 4), (cx + 2, cy - 14), (cx + 6, cy - 12),
                   (cx - 8, cy - 2)], fill=(235, 185, 105))
        d.polygon([(cx - 12, cy + 6), (cx - 2, cy + 14), (cx + 2, cy + 12),
                   (cx - 10, cy + 9)], fill=(140, 90, 30))
        for (wx, wy) in ((cx - 11, cy + 5), (cx + 13, cy + 7), (cx + 1, cy - 13)):
            d.ellipse((wx - 2, wy - 2, wx + 2, wy + 2), fill=(120, 75, 25, 110))
        # hole with an irregular edge + bright ring, wavy price line
        d.polygon(wobble([(cx - 9, cy - 3), (cx - 6, cy - 3), (cx - 3, cy),
                          (cx - 6, cy + 3), (cx - 9, cy + 3), (cx - 9, cy)],
                         S + 4, 1), fill=(120, 75, 25))
        d.ellipse((cx - 9, cy - 3, cx - 3, cy + 3), outline=(245, 210, 150), width=1)
        d.line(wobble([(cx - 1, cy + 3), (cx + 4, cy + 3), (cx + 9, cy + 3)], S + 5, 1),
               fill=(120, 75, 25), width=2)
        d.ellipse((cx - 10, cy + 14, cx + 12, cy + 18), fill=(0, 0, 0, 60))
    elif kind == "columns":
        # steps with wear + shadow
        d.ellipse((cx - 14, cy + 16, cx + 14, cy + 20), fill=(0, 0, 0, 55))
        d.rectangle((cx - 16, cy + 12, cx + 16, cy + 16), fill=(150, 145, 135))
        mottle(d, (cx - 16, cy + 12, cx + 16, cy + 16), S + 1,
               [(170, 165, 155), (130, 125, 115)], 3, 2, 4, 55)
        d.line([(cx - 16, cy + 12), (cx + 16, cy + 12)], fill=(200, 195, 185), width=1)
        d.rectangle((cx - 13, cy + 8, cx + 13, cy + 12), fill=(180, 175, 165))
        d.line([(cx - 13, cy + 8), (cx + 13, cy + 8)], fill=(215, 210, 200), width=1)
        # pediment: mottled stone with a hairline crack
        d.polygon([(cx - 16, cy - 6), (cx + 16, cy - 6), (cx, cy - 15)],
                  fill=(175, 170, 160))
        mottle(d, (cx - 14, cy - 14, cx + 14, cy - 7), S + 2,
               [(190, 185, 175), (150, 145, 135)], 3, 2, 4, 50)
        d.line([(cx - 16, cy - 6), (cx, cy - 15)], fill=(220, 215, 205), width=1)
        d.line([(cx, cy - 15), (cx + 16, cy - 6)], fill=(220, 215, 205), width=1)
        d.polygon([(cx - 11, cy - 7), (cx + 11, cy - 7), (cx, cy - 12)],
                  fill=(140, 135, 125))
        d.line(wobble([(cx + 4, cy - 13), (cx + 6, cy - 10), (cx + 5, cy - 7)],
                      S + 3, 1), fill=(110, 105, 95), width=1)
        # three columns: fluted shafts with worn capitals
        for bx in (cx - 11, cx - 2, cx + 7):
            d.rectangle((bx, cy - 6, bx + 5, cy + 8), fill=(165, 160, 150))
            mottle(d, (bx, cy - 6, bx + 5, cy + 8), S + 4 + bx,
                   [(180, 175, 165), (145, 140, 130)], 2, 1, 3, 55)
            d.line([(bx + 2, cy - 6), (bx + 2, cy + 8)], fill=(140, 135, 125),
                   width=1)
            d.line([(bx, cy - 6), (bx, cy + 8)], fill=(225, 220, 210), width=1)
            d.line([(bx + 5, cy - 6), (bx + 5, cy + 8)], fill=(120, 115, 105),
                   width=1)
            d.rectangle((bx - 1, cy - 8, bx + 6, cy - 6), fill=(190, 185, 175))
            d.line([(bx - 1, cy - 8), (bx + 6, cy - 8)], fill=(220, 215, 205), width=1)
        # crack down the middle column
        d.line(wobble([(cx + 1, cy - 6), (cx, cy - 1), (cx + 2, cy + 4)], S + 5, 1),
               fill=(110, 105, 95), width=1)

    # clip to the panel's rounded rect and composite onto the page
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w, h), 9, fill=255)
    temp.putalpha(ImageChops.multiply(temp.split()[3], mask))
    base = img.convert("RGBA")
    base.alpha_composite(temp, (x, y))
    img.paste(base.convert("RGB"), (0, 0))


# ------------------------------------------------------------------ scenes
def scene_hormuz():
    """Dusk over the strait: two tankers burning, mines in the water.
    3D treatment: multi-stop sky, blurred sun glow, volumetric smoke,
    lit windows, deck highlights and blurred fire reflections on the sea."""
    img = Image.new("RGB", (COLW, 170))
    # three-stop dusk sky: indigo -> mauve -> burning horizon
    vgrad(img, (0, 0, COLW, 62), (16, 26, 48), (74, 52, 62))
    vgrad(img, (0, 62, COLW, 104), (74, 52, 62), (224, 112, 48))
    # soft sun glow low on the horizon + hazy clouds
    def _glow(o):
        for (gx, gy, gr, col) in ((92, 98, 64, (255, 170, 70, 90)),
                                  (92, 96, 40, (255, 200, 110, 110)),
                                  (40, 34, 34, (120, 90, 120, 70)),
                                  (250, 26, 30, (110, 80, 110, 70))):
            o.ellipse((gx - gr, gy - gr // 2, gx + gr, gy + gr // 2), fill=col)
    img = blur_overlay(img, _glow, radius=9)
    d = ImageDraw.Draw(img, "RGBA")
    # mottled dusk clouds: blotchy dark mauve + ember-orange, never a
    # clean gradient band; a few distant birds for scale
    mottle(d, (0, 0, COLW, 100), 501, [(40, 30, 44), (90, 60, 70),
                                        (150, 95, 80)], 14, 8, 26, 36)
    for (bx, by) in ((200, 30), (230, 22), (262, 40)):
        d.line([(bx - 4, by + 2), (bx, by), (bx + 4, by + 2)],
               fill=(20, 16, 22, 200), width=1)
    # sea: dark base with a lighter band under the horizon
    d.rectangle((0, 104, COLW, 170), fill=(14, 40, 56))
    vgrad(img, (0, 104, COLW, 116), (52, 100, 118), (14, 40, 56))
    d = ImageDraw.Draw(img, "RGBA")
    # distant ships on the horizon in the gaps between the two tankers
    for (dx, dw) in ((2, 12), (130, 16)):
        d.polygon([(dx, 104), (dx + dw, 104), (dx + dw - 2, 100), (dx + 2, 100)],
                  fill=(24, 30, 40))
        d.rectangle((dx + dw // 2 - 1, 96, dx + dw // 2 + 1, 100),
                    fill=(24, 30, 40))
    # far tanker (left), hull with lit deck edge and windows
    d.polygon([(18, 104), (128, 104), (118, 88), (28, 88)], fill=(16, 20, 26))
    d.line([(28, 88), (118, 88)], fill=(220, 130, 60), width=2)
    d.rectangle((44, 76, 66, 88), fill=(22, 28, 36))
    d.rectangle((84, 80, 104, 88), fill=(22, 28, 36))
    for wx in (48, 56, 88, 96):
        d.rectangle((wx, 80, wx + 3, 84), fill=(255, 200, 110))
    # near tanker (right), hull with deck highlight + waterline stripe
    d.polygon([(150, 118), (296, 118), (284, 100), (162, 100)], fill=(12, 16, 22))
    d.polygon([(150, 118), (296, 118), (292, 112), (154, 112)], fill=(44, 56, 70))
    d.line([(162, 100), (284, 100)], fill=(230, 140, 70), width=2)
    d.rectangle((196, 86, 224, 100), fill=(18, 24, 32))
    d.rectangle((240, 90, 262, 100), fill=(18, 24, 32))
    for wx in (200, 210, 244, 252):
        d.rectangle((wx, 90, wx + 3, 94), fill=(255, 205, 115))
    # hull wear: rust runs down to the waterline, brushed horizontal
    # streaks, and small deck fittings (vents, a container) in varied tones
    streaks(d, (18, 88, 128, 104), 502, (120, 60, 30), 10, vertical=True, alpha=60)
    streaks(d, (150, 100, 296, 118), 503, (120, 60, 30), 12, vertical=True, alpha=60)
    streaks(d, (18, 92, 128, 100), 504, (150, 170, 190), 8, alpha=36)
    d.rectangle((70, 78, 80, 88), fill=(30, 36, 44))
    d.rectangle((70, 78, 80, 81), fill=(90, 100, 112))
    d.rectangle((108, 82, 116, 88), fill=(26, 32, 40))
    d.rectangle((168, 92, 184, 100), fill=(28, 34, 42))
    d.rectangle((168, 92, 184, 95), fill=(80, 92, 104))
    # blurred fire reflections on the water under both blazes
    def _refl(o):
        for (rx, ry, rw, rh, col) in ((62, 106, 34, 46, (255, 130, 40, 110)),
                                      (84, 106, 16, 34, (255, 180, 80, 90)),
                                      (240, 120, 30, 40, (255, 130, 40, 110)),
                                      (258, 120, 14, 28, (255, 180, 80, 90))):
            o.ellipse((rx, ry, rx + rw, ry + rh), fill=col)
    img = blur_overlay(img, _refl, radius=4)
    d = ImageDraw.Draw(img, "RGBA")
    # choppy sea: irregular wavelets of varied length + foam flecks,
    # never a regular repeating arc pattern
    rnd = random.Random(505)
    for yy in (116, 130, 146, 160):
        xx = 0
        while xx < COLW:
            wl = rnd.randint(14, 30)
            d.arc((xx, yy + rnd.randint(-2, 2), xx + wl, yy + 10), 200, 340,
                  fill=(130, 180, 200), width=2)
            if rnd.random() < 0.6:
                d.arc((xx + 2, yy + 3, xx + wl - 2, yy + 13), 200, 340,
                      fill=(8, 26, 38), width=1)
            if rnd.random() < 0.4:
                fx = xx + rnd.randint(2, max(3, wl - 2))
                fy = yy + rnd.randint(0, 6)
                d.ellipse((fx, fy, fx + 3, fy + 1), fill=(220, 235, 240, 160))
            xx += wl + rnd.randint(4, 14)
    # volumetric smoke: blurred grey puffs with darker cores
    def _smoke(o):
        for (sx, sy, sr, col) in ((64, 36, 16, (80, 78, 84, 200)),
                                  (78, 22, 19, (70, 68, 74, 200)),
                                  (94, 32, 13, (84, 82, 88, 190)),
                                  (212, 62, 15, (78, 76, 82, 200)),
                                  (224, 48, 17, (68, 66, 72, 200)),
                                  (240, 58, 11, (86, 84, 90, 190))):
            o.ellipse((sx - sr, sy - sr, sx + sr, sy + sr), fill=col)
        # irregular billows: wobbly-edged puffs so the smoke has ragged,
        # varied-density layers instead of clean circles
        for (bx, by, br, sd) in ((70, 30, 14, 506), (90, 24, 12, 507),
                                 (220, 54, 12, 508)):
            pts = [(bx + br * math.cos(i * math.pi / 6),
                    by + br * 0.8 * math.sin(i * math.pi / 6))
                   for i in range(12)]
            o.polygon(wobble(pts, sd, 3), fill=(60, 58, 64, 190))
    img = blur_overlay(img, _smoke, radius=6)
    d = ImageDraw.Draw(img, "RGBA")
    # explosion over the far tanker: blurred halo + layered flame core
    def _halo(o):
        o.ellipse((48, 34, 118, 96), fill=(255, 120, 30, 120))
        o.ellipse((228, 66, 282, 112), fill=(255, 120, 30, 110))
    img = blur_overlay(img, _halo, radius=10)
    d = ImageDraw.Draw(img, "RGBA")
    for (ex, ey, er, col) in ((76, 62, 26, (255, 90, 20, 220)),
                              (88, 54, 18, (255, 160, 40, 230)),
                              (70, 52, 12, (255, 220, 120, 240)),
                              (96, 66, 10, (255, 120, 30, 220)),
                              (76, 58, 6, (255, 240, 180, 250))):
        d.ellipse((ex - er, ey - er, ex + er, ey + er), fill=col)
    # embers drifting up from the far blaze
    for (ex, ey) in ((60, 40), (92, 36), (104, 46), (70, 28), (110, 56)):
        d.ellipse((ex - 2, ey - 2, ex + 2, ey + 2), fill=(255, 200, 90))
    # fire on the near tanker deck: layered flame + bright core
    for (ex, ey, er, col) in ((250, 88, 14, (255, 110, 25, 230)),
                              (258, 82, 9, (255, 190, 60, 240)),
                              (254, 86, 5, (255, 240, 180, 250))):
        d.ellipse((ex - er, ey - er, ex + er, ey + er), fill=col)
    # flame tongues: wobbly-edged licks rising off both blazes
    d.polygon(wobble([(76, 30), (84, 44), (80, 58), (72, 58), (68, 44)], 509, 2),
              fill=(255, 150, 40, 220))
    d.polygon(wobble([(252, 66), (258, 76), (256, 86), (250, 86), (248, 76)], 510, 2),
              fill=(255, 170, 60, 220))
    # mines in the foreground water: sphere + specular dot + soft shadow
    for (mx, my) in ((40, 152), (150, 158), (270, 150)):
        d.ellipse((mx - 9, my + 6, mx + 9, my + 11), fill=(8, 22, 32))
        d.ellipse((mx - 7, my - 7, mx + 7, my + 7), fill=(10, 12, 14))
        d.ellipse((mx - 4, my - 5, mx - 1, my - 2), fill=(150, 160, 170))
        d.ellipse((mx - 3, my + 2, mx + 1, my + 5), fill=(120, 70, 40, 120))
        for ang in range(0, 360, 45):
            a = math.radians(ang)
            d.line([(mx, my), (mx + 11 * math.cos(a), my + 11 * math.sin(a))],
                   fill=(10, 12, 14), width=2)
    # film grain over the whole scene: breaks every flat colour block
    img = grain_region(img, (0, 0, COLW, 170), 511, amount=11)
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle((0, 0, COLW - 1, 169), outline=(0, 0, 0, 120), width=1)
    return img


def scene_tariffs():
    """A container ship under a big tariff badge, red arrows pointing down.
    3D treatment: gradient hull side, shaded 3D containers, soft sun glow,
    hazy background crane, blurred hull reflection, badge drop shadow."""
    img = Image.new("RGB", (COLW, 170))
    vgrad(img, (0, 0, COLW, 170), (198, 216, 228), (126, 156, 176))
    # soft sun glow top-left + hazy clouds
    def _sky(o):
        o.ellipse((10, 4, 110, 54), fill=(255, 250, 230, 90))
        for (cx, cy, r) in ((60, 30, 18), (120, 22, 14), (240, 34, 16)):
            o.ellipse((cx - r, cy - r // 2, cx + r, cy + r // 2),
                      fill=(255, 255, 255, 120))
    img = blur_overlay(img, _sky, radius=7)
    d = ImageDraw.Draw(img, "RGBA")
    # mottled sky: blotchy pale cloud, never a clean gradient; gulls.
    # The mottle stays clear of the '%' badge box (x>=232, y<80) so the
    # badge and the sky corners around it stay pixel-identical.
    mottle(d, (0, 0, 200, 56), 601, [(255, 255, 255), (200, 210, 220)],
           8, 10, 18, 30)
    for (bx, by) in ((150, 24), (180, 16), (120, 40)):
        d.line([(bx - 4, by + 2), (bx, by), (bx + 4, by + 2)],
               fill=(90, 100, 110, 220), width=1)
    # hazy background crane (far, lighter) for depth
    d.line([(210, 52), (210, 118)], fill=(120, 135, 150), width=3)
    d.line([(210, 52), (268, 52)], fill=(120, 135, 150), width=3)
    d.line([(268, 52), (268, 70)], fill=(120, 135, 150), width=2)
    # dock crane (near) with a light left edge
    d.line([(30, 40), (30, 120)], fill=(70, 80, 90), width=4)
    d.line([(28, 40), (28, 120)], fill=(150, 165, 180), width=1)
    d.line([(30, 40), (96, 40)], fill=(70, 80, 90), width=4)
    d.line([(96, 40), (96, 62)], fill=(70, 80, 90), width=2)
    d.line([(96, 62), (88, 62)], fill=(70, 80, 90), width=2)
    # crane cables: thin diagonals from the jib, and a dockside container
    # stack (muted, hazy) left of the near crane
    d.line([(30, 40), (60, 62)], fill=(60, 70, 80), width=1)
    d.line([(96, 40), (70, 62)], fill=(60, 70, 80), width=1)
    d.rectangle((2, 100, 14, 112), fill=(110, 125, 140))
    d.rectangle((2, 100, 14, 103), fill=(150, 165, 180))
    d.rectangle((14, 104, 24, 116), fill=(90, 105, 120))
    d.rectangle((14, 104, 24, 107), fill=(130, 145, 160))
    # ship hull: trapezoid side shaded top-light to bottom-dark, row by row
    for yy in range(118, 143):
        t = (yy - 118) / 24
        c = tuple(int((40, 62, 82)[j] + ((16, 26, 38)[j] - (40, 62, 82)[j]) * t)
                  for j in range(3))
        xl = int(20 + 20 * t)
        xr = int(292 - 20 * t)
        d.line([(xl, yy), (xr, yy)], fill=c)
    # deck stripe: red with a bright top edge
    d.rectangle((20, 118, 292, 124), fill=(180, 40, 30))
    d.line([(20, 118), (292, 118)], fill=(240, 110, 90), width=1)
    # hull wear: brushed horizontal streaks, rust patches at the
    # waterline, white draft ticks
    streaks(d, (20, 118, 292, 142), 602, (120, 150, 170), 14, alpha=40)
    mottle(d, (20, 134, 292, 143), 603, [(120, 70, 40), (90, 55, 30)],
           8, 4, 10, 60)
    for tx in (40, 60, 80):
        d.line([(tx, 138), (tx, 142)], fill=(220, 225, 230), width=1)
    # containers: each a 3D box — light top face, dark right side, rib lines
    cols = [(200, 70, 50), (60, 120, 160), (220, 160, 60),
            (90, 150, 80), (180, 90, 120), (70, 90, 130)]
    k = 0
    for row in range(2):
        for col in range(4):
            x0 = 44 + col * 56
            y0 = 62 + row * 28
            c = cols[k % len(cols)]
            k += 1
            # soft shadow of the box onto the deck / box below
            d.rectangle((x0 + 2, y0 + 24, x0 + 54, y0 + 27), fill=(0, 0, 0, 70))
            d.rectangle((x0, y0, x0 + 52, y0 + 26), fill=c, outline=(0, 0, 0, 80))
            d.rectangle((x0, y0, x0 + 52, y0 + 5),
                        fill=tuple(min(255, int(v * 1.35) + 18) for v in c))
            d.rectangle((x0 + 47, y0, x0 + 52, y0 + 26),
                        fill=tuple(int(v * 0.55) for v in c))
            d.line([(x0, y0 + 12), (x0 + 52, y0 + 12)], fill=(0, 0, 0, 60), width=1)
            d.line([(x0, y0 + 19), (x0 + 52, y0 + 19)], fill=(0, 0, 0, 60), width=1)
            # container wear: rust runs, a grime blotch on every third
            # box, and a slightly irregular top edge — skipped for the
            # top-right box (k==4), which sits partly behind the '%'
            # badge: its worn pixels would show in the badge box corners
            # and the badge area must stay pixel-identical
            if k != 4:
                streaks(d, (x0, y0, x0 + 52, y0 + 26), 610 + k, (120, 70, 40), 3,
                        vertical=True, alpha=70)
                if k % 3 == 0:
                    mottle(d, (x0, y0, x0 + 52, y0 + 26), 620 + k, [(0, 0, 0)],
                           2, 4, 10, 40)
                d.line(wobble([(x0, y0), (x0 + 52, y0)], 630 + k, 1),
                       fill=(0, 0, 0, 40), width=1)
    # sea with a lighter band at the waterline
    d.rectangle((0, 142, COLW, 170), fill=(22, 66, 92))
    vgrad(img, (0, 142, COLW, 150), (48, 104, 134), (22, 66, 92))
    d = ImageDraw.Draw(img, "RGBA")
    # blurred reflection of the hull + container colours
    def _refl(o):
        o.polygon([(40, 142), (272, 142), (256, 168), (56, 168)],
                  fill=(16, 30, 44, 130))
        for (rx, col) in ((60, (200, 70, 50, 70)), (120, (60, 120, 160, 70)),
                          (180, (220, 160, 60, 70)), (236, (90, 150, 80, 70))):
            o.rectangle((rx, 144, rx + 34, 162), fill=col)
    img = blur_overlay(img, _refl, radius=3)
    d = ImageDraw.Draw(img, "RGBA")
    # wave arcs: choppy wavelets of varied length + foam flecks, plus
    # broken reflection streaks under the hull
    rnd = random.Random(604)
    for yy in (152, 162):
        xx = 0
        while xx < COLW:
            wl = rnd.randint(14, 30)
            d.arc((xx, yy + rnd.randint(-2, 2), xx + wl, yy + 10), 200, 340,
                  fill=(150, 200, 220), width=2)
            if rnd.random() < 0.5:
                d.arc((xx + 2, yy + 3, xx + wl - 2, yy + 13), 200, 340,
                      fill=(10, 40, 60), width=1)
            if rnd.random() < 0.4:
                fx = xx + rnd.randint(2, max(3, wl - 2))
                fy = yy + rnd.randint(0, 6)
                d.ellipse((fx, fy, fx + 3, fy + 1), fill=(220, 235, 240, 160))
            xx += wl + rnd.randint(4, 14)
    streaks(d, (30, 146, 282, 168), 605, (200, 220, 230), 10, alpha=50)
    # tariff badge: blurred drop shadow, red disc, glossy top arc, white ring
    def _badge_shadow(o):
        o.ellipse((238, 14, 310, 86), fill=(0, 0, 0, 110))
    img = blur_overlay(img, _badge_shadow, radius=4)
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse((232, 8, 304, 80), fill=(168, 32, 26))
    # glossy arc across the very top of the badge (stays above the % glyph)
    d.arc((235, 11, 301, 77), 250, 290, fill=(255, 255, 255, 150), width=3)
    d.ellipse((232, 8, 304, 80), outline=(255, 255, 255), width=3)
    f = F_TITLE(44)
    d.text((268, 18), "%", font=f, fill=(255, 255, 255), anchor="ma")
    # down arrows with a dark offset shadow and a light top edge
    for ax in (150, 178, 206):
        d.polygon([(ax + 2, 94), (ax + 12, 94), (ax + 7, 106)], fill=(90, 16, 12))
        d.rectangle((ax + 4, 82, ax + 10, 96), fill=(90, 16, 12))
        d.polygon([(ax, 92), (ax + 10, 92), (ax + 5, 104)], fill=(168, 32, 26))
        d.rectangle((ax + 2, 80, ax + 8, 94), fill=(168, 32, 26))
        d.line([(ax + 2, 80), (ax + 8, 80)], fill=(230, 110, 95), width=1)
    # film grain over the scene — the '%' badge box is excluded, so the
    # badge disc, ring and '%' glyph stay pixel-identical
    img = grain_region(img, (0, 0, COLW, 170), 606, amount=11,
                       exclude=[(232, 8, 304, 80)])
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle((0, 0, COLW - 1, 169), outline=(0, 0, 0, 120), width=1)
    return img


def scene_nasdaq():
    """Night skyline with a plunging red chart and candlesticks.
    3D treatment: moon glow and stars, faint grid, two-layer skyline
    (hazy back towers, dark front towers with lit windows), glowing
    candlesticks and a glowing plunging chart line."""
    img = Image.new("RGB", (COLW, 170))
    vgrad(img, (0, 0, COLW, 170), (16, 22, 44), (44, 60, 96))
    # moon glow + stars (stars kept clear of the -4% label box, x>=234 y<36)
    def _sky(o):
        o.ellipse((30, 8, 58, 36), fill=(240, 240, 220, 160))
        o.ellipse((22, 0, 66, 44), fill=(220, 225, 240, 60))
    img = blur_overlay(img, _sky, radius=6)
    d = ImageDraw.Draw(img, "RGBA")
    # moon craters: small darker mottled circles on the moon disc
    for (mx, my, mr) in ((40, 18, 3), (47, 25, 2), (41, 27, 2)):
        d.ellipse((mx - mr, my - mr, mx + mr, my + mr),
                  fill=(200, 200, 190, 120))
    # stars of varied size + two cross sparkles (kept clear of the -4%
    # label box, x>=234 y<36)
    for i, (sx, sy) in enumerate(((18, 14), (60, 8), (120, 18), (170, 10),
                                 (205, 26), (150, 40), (90, 52), (300, 60),
                                 (16, 70), (280, 90))):
        r = 2 if i % 4 == 0 else 1
        d.ellipse((sx - r, sy - r, sx + r, sy + r),
                  fill=(255, 255, 255, 200))
    for (sx, sy) in ((100, 30), (230, 60)):
        d.line([(sx - 3, sy), (sx + 3, sy)], fill=(255, 255, 255, 180), width=1)
        d.line([(sx, sy - 3), (sx, sy + 3)], fill=(255, 255, 255, 180), width=1)
    # faint horizontal grid for depth
    for gy in (40, 70, 100, 130, 160):
        d.line([(0, gy), (COLW, gy)], fill=(140, 170, 220, 28), width=1)
    # back skyline: hazy blue-grey towers with faint windows of varied
    # size and tone — some warm, some cool
    rnd = random.Random(77)
    x = -6
    while x < COLW:
        bw = rnd.randint(26, 48)
        bh = rnd.randint(64, 118)
        d.rectangle((x, 170 - bh, x + bw, 170), fill=(62, 82, 122))
        d.line([(x, 170 - bh), (x + bw, 170 - bh)], fill=(110, 135, 175), width=1)
        for wy in range(170 - bh + 10, 162, 16):
            for wx in range(x + 6, x + bw - 4, 12):
                if rnd.random() < 0.3:
                    ww = rnd.randint(3, 5)
                    col = ((255, 210, 140, 100) if rnd.random() < 0.25
                           else (200, 210, 230, 110))
                    d.rectangle((wx, wy, wx + ww, wy + 6), fill=col)
        x += bw + 6
    # atmospheric haze between the two skyline layers: the back towers
    # sit further away, so they wash out towards the horizon
    d.rectangle((0, 96, COLW, 124), fill=(140, 160, 200, 26))
    # front skyline: dark towers, warm lit windows of varied size, some
    # dark unlit ones, rooftop clutter (AC boxes, water towers, antennas)
    rnd = random.Random(25)
    x = 0
    while x < COLW:
        bw = rnd.randint(22, 44)
        bh = rnd.randint(50, 110)
        d.rectangle((x, 170 - bh, x + bw, 170), fill=(10, 14, 28))
        d.line([(x, 170 - bh), (x + bw, 170 - bh)], fill=(70, 90, 130), width=1)
        for wy in range(170 - bh + 8, 162, 14):
            for wx in range(x + 5, x + bw - 4, 10):
                if rnd.random() < 0.4:
                    ww = rnd.randint(3, 5)
                    d.rectangle((wx, wy, wx + ww, wy + 6),
                                fill=(255, 210, 110, 200))
                elif rnd.random() < 0.12:
                    d.rectangle((wx, wy, wx + 4, wy + 6),
                                fill=(30, 34, 48, 160))
        if rnd.random() < 0.4:
            d.rectangle((x + 6, 170 - bh - 6, x + 14, 170 - bh),
                        fill=(16, 20, 34))
        if rnd.random() < 0.3:
            wx = x + bw - 10
            d.rectangle((wx, 170 - bh - 9, wx + 6, 170 - bh), fill=(14, 18, 30))
            d.polygon([(wx - 1, 170 - bh - 9), (wx + 7, 170 - bh - 9),
                       (wx + 3, 170 - bh - 13)], fill=(14, 18, 30))
        if rnd.random() < 0.5:
            ax = x + bw // 2
            d.line([(ax, 170 - bh), (ax, 170 - bh - 10)], fill=(10, 14, 28), width=2)
            d.ellipse((ax - 2, 170 - bh - 13, ax + 2, 170 - bh - 9),
                      fill=(255, 70, 60))
        x += bw + 4
    # candlesticks: blurred red glow under each, then body + light edge
    def _candle_glow(o):
        for (cx, o_y, c_y) in ((36, 60, 74), (66, 52, 70), (96, 48, 62),
                               (126, 58, 44), (156, 66, 40)):
            o.rectangle((cx - 7, min(o_y, c_y) - 8, cx + 7, max(o_y, c_y) + 8),
                        fill=(220, 60, 50, 130))
    img = blur_overlay(img, _candle_glow, radius=3)
    d = ImageDraw.Draw(img, "RGBA")
    for i, (cx, o, c, col) in enumerate(((36, 60, 74, (220, 60, 50)),
                                        (66, 52, 70, (220, 60, 50)),
                                        (96, 48, 62, (220, 60, 50)),
                                        (126, 58, 44, (220, 60, 50)),
                                        (156, 66, 40, (220, 60, 50)))):
        wd = 4 + (i % 3)
        d.line([(cx, o - 8), (cx, c + 8)], fill=col, width=2)
        d.rectangle((cx - wd, min(o, c), cx + wd, max(o, c)), fill=col)
        d.line([(cx - wd, min(o, c)), (cx - wd, max(o, c))],
               fill=(255, 130, 110), width=1)
    # plunging chart line, hand-drawn: middle points wobbled a touch, ends
    # kept exact so the arrowhead still sits on the line
    raw = [(20, 46), (70, 54), (110, 50), (160, 66), (210, 78), (262, 108),
           (296, 128)]
    pts = [raw[0]] + wobble(raw[1:-1], 701, 2) + [raw[-1]]

    def _chart_glow(o):
        o.line(pts, fill=(255, 70, 50, 120), width=10, joint="curve")
    img = blur_overlay(img, _chart_glow, radius=3)
    d = ImageDraw.Draw(img, "RGBA")
    d.line(pts, fill=(255, 70, 50), width=5, joint="curve")
    d.polygon([(298, 130), (280, 122), (284, 138)], fill=(150, 30, 20))
    d.polygon([(296, 128), (278, 120), (282, 136)], fill=(255, 70, 50))
    # -4% label, top-right in clear sky above the chart line (unchanged)
    f = F_TITLE(30)
    d.text((236, 2), "-4%", font=f, fill=(255, 90, 70))
    # film grain over the scene — the '-4%' label box is excluded, so the
    # label and the sky behind it stay pixel-identical
    img = grain_region(img, (0, 0, COLW, 170), 702, amount=11,
                       exclude=[(236, 2, 312, 36)])
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle((0, 0, COLW - 1, 169), outline=(0, 0, 0, 120), width=1)
    return img


SCENES = {"hormuz": scene_hormuz, "tariffs": scene_tariffs, "nasdaq": scene_nasdaq}

# ------------------------------------------------------------------ layout
def draw_masthead(d):
    d.rectangle((MARGIN, 14, W - MARGIN, 16), fill=RULE)
    title = "THE WORLD IN ONE DAY"
    f = F_TITLE(56)
    while d.textlength(title, font=f) > W - 2 * MARGIN:
        f = F_TITLE(f.size - 2)
    d.text((W // 2, 22), title, font=f, fill=INK, anchor="ma")
    d.text((W // 2, 84), "WEDNESDAY  25  NOVEMBER  2026",
           font=F_BODY(21), fill=INK, anchor="ma")
    d.text((W // 2, 108),
           "Thirty stories from one day \u2014 reported by Reuters, AP, BBC and others",
           font=F_ITAL(15), fill=MUTED, anchor="ma")
    d.rectangle((MARGIN, 128, W - MARGIN, 130), fill=RULE)


def draw_big(d, img, i, story):
    x = COLX[i]
    y = 142
    img.paste(SCENES[story["scene"]](), (x, y))
    y = 142 + 170 + 10
    d.text((x, y), story["kicker"], font=F_BODY(13), fill=RED)
    y += 20
    y = text_block(d, x, y, story["head"], F_TITLE(23), COLW, 26, max_lines=2)
    y += 4
    text_block(d, x, y, story["summ"], F_BODY(15), COLW, 19, max_lines=2)


def draw_tiles(img, d):
    y0 = 452
    d.text((MARGIN, y0), "MORE FROM WEDNESDAY", font=F_BODY(16), fill=INK)
    d.line([(MARGIN + 190, y0 + 10), (W - MARGIN, y0 + 10)], fill=RULE, width=1)
    top = y0 + 26
    for r in range(5):
        for c in range(3):
            idx = r * 3 + c
            num, kind, hue, head, summ = TILES[idx]
            tx = COLX[c]
            ty = top + r * 64
            # number badge
            d.ellipse((tx + 1, ty + 20, tx + 23, ty + 42), fill=RED)
            nf = F_BODY(14)
            d.text((tx + 12, ty + 21), str(num), font=nf, fill=(255, 255, 255),
                   anchor="ma")
            # 3D icon
            draw_icon(img, d, tx + 28, ty + 3, 60, 56, kind, hue)
            # text
            x = tx + 96
            w = COLW - 96 - 2
            y = ty + 1
            y = text_block(d, x, y, head, F_BODY(16), w, 17, max_lines=2)
            text_block(d, x, y + 1, summ, F_BODY(13), w, 14, color=MUTED,
                       max_lines=2)


def _fit_line(d, text, x, y, max_w, sizes=(13, 12)):
    for s in sizes:
        f = F_BODY(s)
        if d.textlength(text, font=f) <= max_w:
            d.text((x, y), text, font=f, fill=INK)
            return
    f = F_BODY(sizes[-1])
    while d.textlength(text + "\u2026", font=f) > max_w and len(text) > 10:
        text = text[:-1]
    d.text((x, y), text + "\u2026", font=f, fill=INK)


def draw_also(d):
    y0 = 806
    d.text((MARGIN, y0), "ALSO TODAY", font=F_BODY(16), fill=INK)
    d.line([(MARGIN + 108, y0 + 10), (W - MARGIN, y0 + 10)], fill=RULE, width=1)
    colw = (W - 2 * MARGIN - 24) // 2
    for i, line in enumerate(ALSO):
        col = i // 6
        row = i % 6
        x = MARGIN if col == 0 else MARGIN + colw + 24
        y = y0 + 28 + row * 17
        d.ellipse((x, y + 5, x + 5, y + 10), fill=RED)
        _fit_line(d, line, x + 11, y, colw - 11)


def draw_footer(d):
    d.rectangle((MARGIN, 940, W - MARGIN, 942), fill=RULE)
    d.text((MARGIN, 950),
           "Sources: Reuters, AP, BBC, Newsquawk, Sky Sports, NBC Sports, "
           "Copernicus, The Hacker News.",
           font=F_BODY(12), fill=MUTED)
    d.text((MARGIN, 968),
           "Scenes are illustrations drawn for this page, not photographs.",
           font=F_ITAL(12), fill=MUTED)
    d.text((MARGIN, 986),
           "DATE CHECK: Huawei\u2019s verdict was Tue 24 Nov and the heat "
           "record Sun 22 Nov \u2014 everything else happened Wed 25 Nov 2026.",
           font=F_BODY(12), fill=RED)


def main():
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img, "RGBA")
    draw_masthead(d)
    for i, story in enumerate(BIG):
        draw_big(d, img, i, story)
    d.rectangle((MARGIN, 440, W - MARGIN, 441), fill=RULE)
    draw_tiles(img, d)
    draw_also(d)
    draw_footer(d)
    img.save(OUT, format="PNG", optimize=True)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
