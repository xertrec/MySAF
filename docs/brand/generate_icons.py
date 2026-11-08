"""Generates the mySAF logo family (style: green tile, white ring, white glyph; no label).

Outputs, from one source of truth:
  docs/brand/icons/<name>.svg                       full icon (background + foreground), 108x108
  app/src/main/res/drawable/ic_logo_<name>.xml      adaptive-icon foreground (white, transparent bg)

Run from the repo root:  python docs/brand/generate_icons.py
All geometry is 108x108 (adaptive icon grid); content stays inside the 66dp safe zone.
"""
import math
import os

GREEN = "#0E6B3A"
WHITE = "#FFFFFF"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SVG_DIR = os.path.join(ROOT, "docs", "brand", "icons")
RES_DIR = os.path.join(ROOT, "app", "src", "main", "res", "drawable")

RING_C = (54.0, 45.0)
RING_R = 19.5
RING_W = 2.6
GLYPH_K = 1.3          # glyphs are authored in a frame of radius 10 around (0,0)
# Glyphs are authored around RING_C; the whole drawing is then scaled about it and moved so the
# ring is centred in the 108 grid with radius ~28 (outer edge 29.9, inside the 33dp safe zone).
FIT_SCALE = 1.44
FIT_DY = 54.0 - RING_C[1]


def f(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


class Path:
    """Path builder with an affine transform: p' = T + k * R(theta) * skew(p)."""

    def __init__(self, tx=0.0, ty=0.0, k=1.0, rot=0.0, skew=0.0, base=0.0):
        self.tx, self.ty, self.k, self.rot, self.skew, self.base = tx, ty, k, math.radians(rot), skew, base
        self.d = []

    def p(self, x, y):
        x = x - (y - self.base) * self.skew
        c, s = math.cos(self.rot), math.sin(self.rot)
        x, y = x * c - y * s, x * s + y * c
        return self.tx + self.k * x, self.ty + self.k * y

    def M(self, x, y):
        self.d.append("M%s,%s" % tuple(map(f, self.p(x, y))))
        return self

    def L(self, x, y):
        self.d.append("L%s,%s" % tuple(map(f, self.p(x, y))))
        return self

    def C(self, x1, y1, x2, y2, x, y):
        pts = [self.p(x1, y1), self.p(x2, y2), self.p(x, y)]
        self.d.append("C" + " ".join("%s,%s" % (f(a), f(b)) for a, b in pts))
        return self

    def Z(self):
        self.d.append("Z")
        return self

    def circle(self, cx, cy, r):
        (x, y), rr = self.p(cx, cy), r * self.k
        self.d.append(f"M{f(x - rr)},{f(y)}a{f(rr)},{f(rr)} 0 1,0 {f(2 * rr)},0a{f(rr)},{f(rr)} 0 1,0 {f(-2 * rr)},0Z")
        return self

    def ellipse(self, cx, cy, rx, ry):
        m = 0.5523
        self.M(cx + rx, cy)
        self.C(cx + rx, cy + ry * m, cx + rx * m, cy + ry, cx, cy + ry)
        self.C(cx - rx * m, cy + ry, cx - rx, cy + ry * m, cx - rx, cy)
        self.C(cx - rx, cy - ry * m, cx - rx * m, cy - ry, cx, cy - ry)
        self.C(cx + rx * m, cy - ry, cx + rx, cy - ry * m, cx + rx, cy)
        return self.Z()

    def rrect(self, x0, y0, x1, y1, r):
        m = 0.5523 * r
        self.M(x0 + r, y0).L(x1 - r, y0).C(x1 - r + m, y0, x1, y0 + r - m, x1, y0 + r)
        self.L(x1, y1 - r).C(x1, y1 - r + m, x1 - r + m, y1, x1 - r, y1)
        self.L(x0 + r, y1).C(x0 + r - m, y1, x0, y1 - r + m, x0, y1 - r)
        self.L(x0, y0 + r).C(x0, y0 + r - m, x0 + r - m, y0, x0 + r, y0)
        return self.Z()

    def wave(self, x0, x1, y, amp, periods):
        step = (x1 - x0) / (periods * 2)
        self.M(x0, y)
        x = x0
        for i in range(periods * 2):
            a = -amp if i % 2 == 0 else amp
            self.C(x + step * 0.35, y + a, x + step * 0.65, y + a, x + step, y)
            x += step
        return self

    def str(self):
        return "".join(self.d)


def stroke(path, w):
    return ("stroke", path.str(), w)


def fill(path, evenodd=False):
    return ("fill", path.str(), evenodd)


def G(rot=0.0):
    """Path in the glyph frame (radius 10 around the ring centre)."""
    return Path(RING_C[0], RING_C[1], GLYPH_K, rot)


# ---------------------------------------------------------------- lettering
# Upright letters, cap height 10, baseline y=0, y grows downwards. (path, advance width)
LETTERS = {
    "S": ("M6,-8.4C5,-10.3 0.7,-10.5 0.6,-7.4C0.5,-4.8 6.3,-5.6 6.3,-2.6C6.3,0.6 1.3,0.7 0.3,-1.4", 6.6),
    "A": ("M0.3,0L3.6,-10L6.9,0M1.6,-3.3L5.6,-3.3", 7.2),
    "F": ("M5.6,-10L0.8,-10L0.8,0M0.8,-5.3L4.8,-5.3", 5.8),
    "U": ("M0.8,-10L0.8,-3.8C0.8,1 6,1 6,-3.8L6,-10", 6.8),
    "B": ("M0.8,0L0.8,-10L3.5,-10C6.6,-10 6.6,-5.2 3.5,-5.2L0.8,-5.2M3.6,-5.2C7.2,-5.2 7.2,0 3.6,0L0.8,0", 6.7),
    "I": ("M0.8,0L0.8,-10", 1.6),
    "m": ("M0.8,0L0.8,-7M0.8,-4.3C0.8,-7.7 4.8,-7.7 4.8,-4.3L4.8,0M4.8,-4.3C4.8,-7.7 8.8,-7.7 8.8,-4.3L8.8,0", 9.6),
    "y": ("M0.3,-7L3.2,-0.3M6.2,-7L2.4,3.4", 6.5),
    " ": ("", 2.4),
}


def letter_path(d, path, dx):
    toks = d.replace("M", " M ").replace("L", " L ").replace("C", " C ").split()
    i = 0
    while i < len(toks):
        cmd = toks[i]
        n = {"M": 1, "L": 1, "C": 3}[cmd]
        pts = [tuple(map(float, toks[i + 1 + j].split(","))) for j in range(n)]
        pts = [(x + dx, y) for x, y in pts]
        if cmd == "M":
            path.M(*pts[0])
        elif cmd == "L":
            path.L(*pts[0])
        else:
            path.C(*pts[0], *pts[1], *pts[2])
        # C tokens may be "x1,y1 x2,y2 x,y" split by spaces
        i += 1 + n


def text(s, cx, baseline, cap, weight, skew=0.0, tracking=1.0):
    widths = [LETTERS[c][1] for c in s]
    total = sum(widths) + tracking * (len(s) - 1)
    k = cap / 10.0
    path = Path(cx - total * k / 2 + skew * 5 * k, baseline, k, 0, skew, 0)
    x = 0.0
    for c, w in zip(s, widths):
        if LETTERS[c][0]:
            letter_path(LETTERS[c][0], path, x)
        x += w + tracking
    return stroke(path, weight * k)


def ring():
    return stroke(Path().circle(*RING_C, RING_R), RING_W)


# ---------------------------------------------------------------- glyphs
def g_main():
    return [
        text("my", 54.5, 44.0, 9.6, 2.15, skew=0.22, tracking=0.6),
        text("SAF", 53.0, 56.5, 11.0, 2.15, skew=0.22, tracking=0.9),
    ]


def g_pool():
    return [
        fill(G().circle(6.0, -5.2, 2.4)),
        stroke(G().M(-8.5, -2.2).L(-2.0, -6.8).L(2.6, -1.6), 2.8),
        stroke(G().wave(-10, 10, 2.6, 1.5, 3), 2.3),
        stroke(G().wave(-10, 10, 7.0, 1.5, 3), 2.3),
    ]


def g_fitness_room():  # heart + pulse (cardio / fitness room)
    heart = (G().M(0, 8.2).C(-4.0, 5.0, -9.6, 1.0, -9.6, -3.6).C(-9.6, -7.4, -6.8, -9.0, -4.8, -9.0)
             .C(-2.6, -9.0, -0.9, -7.6, 0, -5.8).C(0.9, -7.6, 2.6, -9.0, 4.8, -9.0)
             .C(6.8, -9.0, 9.6, -7.4, 9.6, -3.6).C(9.6, 1.0, 4.0, 5.0, 0, 8.2).Z())
    pulse = G().M(-6.6, -1.6).L(-3.0, -1.6).L(-1.4, -4.8).L(1.0, 1.8).L(2.6, -1.6).L(6.6, -1.6)
    return [stroke(heart, 2.3), stroke(pulse, 1.8)]


def g_barbell():  # dumbbell, as in the reference image
    return [
        stroke(G().M(-4.5, 0).L(4.5, 0), 2.6),
        fill(G().rrect(-7.6, -6.6, -4.4, 6.6, 1.0)),
        fill(G().rrect(4.4, -6.6, 7.6, 6.6, 1.0)),
        fill(G().rrect(-10.0, -3.6, -8.4, 3.6, 0.7)),
        fill(G().rrect(8.4, -3.6, 10.0, 3.6, 0.7)),
    ]


def g_padel():
    head = G(35).ellipse(0, -3.0, 6.0, 7.0)
    for hx, hy in [(-2.4, -6.2), (2.4, -6.2), (0, -3.6), (-2.4, -1.0), (2.4, -1.0), (0, -8.6), (0, 1.6)]:
        head.circle(hx, hy, 0.9)
    return [
        fill(head, evenodd=True),
        stroke(G(35).M(0, 4.0).L(0, 9.6), 2.8),
        fill(G().circle(-7.2, -5.6, 2.0)),
    ]


def g_tennis():
    return [
        stroke(G().circle(0, 0, 9.2), 2.4),
        stroke(G().M(-6.5, -6.5).C(-2.6, -2.8, -2.6, 2.8, -6.5, 6.5), 2.1),
        stroke(G().M(6.5, -6.5).C(2.6, -2.8, 2.6, 2.8, 6.5, 6.5), 2.1),
    ]


def g_squash():
    rot = -35
    cx, cy, rx, ry = 0.0, -3.4, 4.6, 6.6
    strings = G(rot)
    for dx in (-2.3, 0, 2.3):
        h = ry * math.sqrt(1 - (dx / rx) ** 2)
        strings.M(cx + dx, cy - h).L(cx + dx, cy + h)
    for dy in (-3.3, 0, 3.3):
        w = rx * math.sqrt(1 - (dy / ry) ** 2)
        strings.M(cx - w, cy + dy).L(cx + w, cy + dy)
    return [
        stroke(G(rot).ellipse(cx, cy, rx, ry), 1.9),
        stroke(strings, 0.75),
        stroke(G(rot).M(0, 3.3).L(0, 9.8), 2.5),
        fill(G().circle(6.8, -6.0, 1.9)),
    ]


def g_sports_hall():  # basketball
    return [
        stroke(G().circle(0, 0, 9.2), 2.3),
        stroke(G().M(0, -9.2).L(0, 9.2).M(-9.2, 0).L(9.2, 0), 1.8),
        stroke(G().M(-6.3, -6.7).C(-2.4, -3.0, -2.4, 3.0, -6.3, 6.7), 1.8),
        stroke(G().M(6.3, -6.7).C(2.4, -3.0, 2.4, 3.0, 6.3, 6.7), 1.8),
    ]


def g_futsal():  # court, as in the reference image
    return [
        stroke(G().rrect(-10, -6.6, 10, 6.6, 0.8), 1.9),
        stroke(G().M(0, -6.6).L(0, 6.6), 1.6),
        stroke(G().circle(0, 0, 2.3), 1.6),
        stroke(G().M(-10, -3.2).C(-6.0, -3.2, -6.0, 3.2, -10, 3.2), 1.6),
        stroke(G().M(10, -3.2).C(6.0, -3.2, 6.0, 3.2, 10, 3.2), 1.6),
    ]


def g_football():  # soccer ball
    pent = G()
    seams = G()
    patches = []
    for i in range(5):
        a = math.radians(-90 + i * 72)
        x, y = 3.6 * math.cos(a), 3.6 * math.sin(a)
        (pent.M if i == 0 else pent.L)(x, y)
        ex, ey = 6.4 * math.cos(a), 6.4 * math.sin(a)
        seams.M(x, y).L(ex, ey)
        # seams from the spoke end to the rim, and a filled patch on the rim between spokes
        for s in (-1, 1):
            b = a + s * math.radians(26)
            seams.M(ex, ey).L(9.0 * math.cos(b), 9.0 * math.sin(b))
        m = a + math.radians(36)
        p = G()
        p.M(9.2 * math.cos(m - 0.30), 9.2 * math.sin(m - 0.30))
        p.L(7.0 * math.cos(m), 7.0 * math.sin(m))
        p.L(9.2 * math.cos(m + 0.30), 9.2 * math.sin(m + 0.30)).Z()
        patches.append(fill(p))
    pent.Z()
    return [stroke(G().circle(0, 0, 9.2), 2.3), fill(pent), stroke(seams, 1.5), *patches]


def g_calisthenics():  # pull-up
    return [
        stroke(G().M(-9.0, -8.2).L(9.0, -8.2), 2.4),
        stroke(G().M(-5.0, -8.2).L(-2.2, -1.6).M(5.0, -8.2).L(2.2, -1.6), 2.2),
        fill(G().circle(0, -4.6, 2.2)),
        stroke(G().M(0, -1.4).L(0, 4.0), 2.8),
        stroke(G().M(0, 4.0).L(-2.6, 9.2).M(0, 4.0).L(2.6, 9.2), 2.4),
    ]


def g_climbing():
    # Wall on the right, climber in profile facing it, rope from the top anchor to the harness.
    holds = G()
    for hx, hy, r in [(5.6, -7.4, 1.4), (6.2, 0.6, 1.3), (5.4, 6.6, 1.3)]:
        holds.circle(hx, hy, r)
    return [
        stroke(G().M(7.6, -9.6).L(7.6, 9.6), 2.2),                       # wall
        fill(holds),
        stroke(G().M(-4.0, -9.4).L(-2.6, 0.6), 1.2),                     # rope
        fill(G().circle(-0.4, -6.0, 2.1)),                               # head
        stroke(G().M(0.6, -3.4).L(3.6, -7.6), 2.0),                      # arm up to top hold
        stroke(G().M(0.6, -3.4).L(4.4, -0.4), 2.0),                      # arm to middle hold
        stroke(G().M(0.6, -3.4).L(-1.8, 1.8), 2.6),                      # torso
        stroke(G().M(-1.8, 1.8).L(1.0, 4.4).L(4.2, 6.6), 2.1),           # leg on bottom hold
        stroke(G().M(-1.8, 1.8).L(-3.0, 6.0).L(-0.6, 8.4), 2.1),         # free leg
    ]


def g_small_pool():  # pool ladder over the water (16 m pool)
    return [
        stroke(G().M(-6.0, 3.6).L(-6.0, -4.6).C(-6.0, -8.8, -0.6, -8.8, -0.6, -5.2), 2.3),
        stroke(G().M(1.6, 3.6).L(1.6, -4.6).C(1.6, -8.8, 7.0, -8.8, 7.0, -5.2), 2.3),
        stroke(G().M(-6.0, -1.6).L(1.6, -1.6).M(-6.0, 1.6).L(1.6, 1.6), 1.7),
        stroke(G().wave(-10, 10, 7.0, 1.5, 3), 2.3),
    ]


def g_beach_volley():  # volleyball over the sand
    return [
        stroke(G().circle(0, -2.6, 7.0), 2.2),
        stroke(G().M(-1.0, -9.5).C(-4.4, -6.0, -4.6, -0.8, -2.2, 3.9), 1.6),
        stroke(G().M(-6.6, -4.8).C(-2.2, -3.0, 3.0, -3.4, 6.4, -6.0), 1.6),
        stroke(G().M(6.8, -1.0).C(3.0, -0.6, 0.0, 1.2, -2.0, 4.0), 1.6),
        stroke(G().wave(-10, 10, 8.2, 1.0, 2), 2.0),
    ]


def g_outdoor_basketball():  # backboard, rim and net
    return [
        stroke(G().rrect(-8.0, -9.4, 8.0, -1.8, 1.0), 2.0),
        stroke(G().rrect(-2.8, -6.0, 2.8, -1.8, 0.3), 1.4),
        stroke(G().M(-4.6, -0.2).L(4.6, -0.2), 2.4),
        stroke(G().M(-4.2, -0.2).L(-2.6, 7.6).L(2.6, 7.6).L(4.2, -0.2)
               .M(-1.4, -0.2).L(-0.9, 7.6).M(1.4, -0.2).L(0.9, 7.6)
               .M(-3.5, 3.6).L(3.5, 3.6), 1.2),
    ]


def g_boxing():  # boxing glove
    return [
        stroke(G().M(-4.4, 2.6).L(-4.4, -4.0).C(-4.4, -9.6, 7.4, -9.6, 7.4, -3.2)
               .C(7.4, 0.4, 5.6, 2.6, 4.2, 2.6).L(-4.4, 2.6).Z(), 2.3),
        stroke(G().M(-4.4, -3.4).C(-8.6, -3.4, -8.6, 1.8, -4.4, 1.8), 2.1),
        fill(G().rrect(-4.0, 4.4, 4.6, 9.2, 1.0)),
    ]


def g_rhythm():  # beamed music notes (rhythm / dance rooms)
    return [
        fill(G().ellipse(-4.8, 6.0, 2.9, 2.2)),
        fill(G().ellipse(4.4, 4.0, 2.9, 2.2)),
        stroke(G().M(-2.0, 6.0).L(-2.0, -6.0).M(7.2, 4.0).L(7.2, -8.0), 1.9),
        fill(G().M(-2.95, -6.4).L(8.15, -8.8).L(8.15, -5.2).L(-2.95, -2.8).Z()),
    ]


def g_zen():  # seated figure in lotus pose (zen / yoga room)
    return [
        fill(G().circle(0, -7.4, 2.4)),
        fill(G().M(-2.4, -4.4).L(2.4, -4.4).L(3.4, 3.0).L(-3.4, 3.0).Z()),
        stroke(G().M(-2.0, -3.6).L(-5.6, -0.2).L(-7.2, 3.6).M(2.0, -3.6).L(5.6, -0.2).L(7.2, 3.6), 2.0),
        fill(G().M(-9.6, 5.0).C(-5.0, 2.2, 5.0, 2.2, 9.6, 5.0).C(5.0, 8.6, -5.0, 8.6, -9.6, 5.0).Z()),
    ]


def g_cycling():  # bicycle (indoor cycling room)
    return [
        stroke(G().circle(-5.6, 3.6, 4.0).circle(5.6, 3.6, 4.0), 1.9),
        stroke(G().M(-5.6, 3.6).L(-0.4, 3.6).L(-2.8, -3.2).M(-0.4, 3.6).L(4.0, -3.2).L(5.6, 3.6)
               .M(-2.8, -3.2).L(4.0, -3.2), 1.9),
        stroke(G().M(-4.6, -3.4).L(-1.2, -3.4).M(4.0, -3.2).L(3.0, -6.4).L(5.8, -6.4), 2.0),
    ]


# name -> glyph fn. Names match ActivityInfo ids (except "main").
ICONS = {
    "main": g_main,
    "piscina_25m": g_pool,
    "piscina_16m": g_small_pool,
    "sala_boxtraining": g_boxing,
    "sala_1_ritmes": g_rhythm,
    "sala_2_ritmes": g_rhythm,
    "sala_3_zen": g_zen,
    "sala_4_cycling": g_cycling,
    "basquet_exterior": g_outdoor_basketball,
    "volei_platja": g_beach_volley,
    "sala_fitness": g_fitness_room,
    "padel": g_padel,
    "tennis": g_tennis,
    "esquaix": g_squash,
    "pavello": g_sports_hall,
    "futbol_sala": g_futsal,
    "futbol_7_11": g_football,
    "barbell": g_barbell,
    "callistenia": g_calisthenics,
    "rocodrom": g_climbing,
}


def elements(name):
    return [ring(), *ICONS[name]()]


def to_svg(els, background=True):
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 108 108" width="108" height="108">']
    if background:
        out.append(f'<rect width="108" height="108" fill="{GREEN}"/>')
    cx, cy = RING_C
    out.append(f'<g transform="translate({f(cx)},{f(cy + FIT_DY)}) scale({f(FIT_SCALE)}) translate({f(-cx)},{f(-cy)})">')
    for kind, d, extra in els:
        if kind == "stroke":
            out.append(f'<path d="{d}" fill="none" stroke="{WHITE}" stroke-width="{f(extra)}" '
                       'stroke-linecap="round" stroke-linejoin="round"/>')
        else:
            rule = ' fill-rule="evenodd"' if extra else ""
            out.append(f'<path d="{d}" fill="{WHITE}"{rule}/>')
    out.append("</g>")
    out.append("</svg>")
    return "\n".join(out)


def to_vector(els):
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           "<!-- Generated by docs/brand/generate_icons.py. Do not edit by hand. -->",
           '<vector xmlns:android="http://schemas.android.com/apk/res/android"',
           '    android:width="108dp"', '    android:height="108dp"',
           '    android:viewportWidth="108"', '    android:viewportHeight="108">',
           f'    <group\n        android:pivotX="{f(RING_C[0])}"\n        android:pivotY="{f(RING_C[1])}"\n'
           f'        android:scaleX="{f(FIT_SCALE)}"\n        android:scaleY="{f(FIT_SCALE)}"\n'
           f'        android:translateY="{f(FIT_DY)}">']
    for kind, d, extra in els:
        if kind == "stroke":
            out.append(f'    <path\n        android:pathData="{d}"\n        android:strokeColor="{WHITE}"\n'
                       f'        android:strokeWidth="{f(extra)}"\n        android:strokeLineCap="round"\n'
                       '        android:strokeLineJoin="round" />')
        else:
            rule = '\n        android:fillType="evenOdd"' if extra else ""
            out.append(f'    <path\n        android:pathData="{d}"\n        android:fillColor="{WHITE}"{rule} />')
    out.append("    </group>")
    out.append("</vector>")
    return "\n".join(out) + "\n"


def main():
    os.makedirs(SVG_DIR, exist_ok=True)
    for name in ICONS:
        els = elements(name)
        with open(os.path.join(SVG_DIR, f"{name}.svg"), "w", encoding="utf-8") as fh:
            fh.write(to_svg(els) + "\n")
        with open(os.path.join(RES_DIR, f"ic_logo_{name}.xml"), "w", encoding="utf-8") as fh:
            fh.write(to_vector(els))
        if name != "main":  # main uses the hand-written ic_launcher / ic_launcher_round
            write_launcher(name)
            write_glyph(name)
    print(f"Generated {len(ICONS)} icons")


GLYPH_BOX = 30.0  # crop around RING_C: the glyph frame (radius 10 * GLYPH_K) plus stroke margin


def write_glyph(name):
    """Ring-less pictogram (`ic_sport_<name>`) for in-app lists; tinted by Compose's Icon."""
    els = ICONS[name]()
    ox, oy = RING_C[0] - GLYPH_BOX / 2, RING_C[1] - GLYPH_BOX / 2
    box = f(GLYPH_BOX)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{f(ox)} {f(oy)} {box} {box}" width="96" height="96">']
    vec = ['<?xml version="1.0" encoding="utf-8"?>',
           "<!-- Generated by docs/brand/generate_icons.py. Do not edit by hand. -->",
           '<vector xmlns:android="http://schemas.android.com/apk/res/android"',
           '    android:width="24dp"', '    android:height="24dp"',
           f'    android:viewportWidth="{box}"', f'    android:viewportHeight="{box}">',
           f'    <group\n        android:translateX="{f(-ox)}"\n        android:translateY="{f(-oy)}">']
    for kind, d, extra in els:
        if kind == "stroke":
            svg.append(f'<path d="{d}" fill="none" stroke="#000" stroke-width="{f(extra)}" '
                       'stroke-linecap="round" stroke-linejoin="round"/>')
            vec.append(f'        <path\n            android:pathData="{d}"\n            android:strokeColor="#FF000000"\n'
                       f'            android:strokeWidth="{f(extra)}"\n            android:strokeLineCap="round"\n'
                       '            android:strokeLineJoin="round" />')
        else:
            svg.append(f'<path d="{d}" fill="#000"{" fill-rule=\"evenodd\"" if extra else ""}/>')
            rule = '\n            android:fillType="evenOdd"' if extra else ""
            vec.append(f'        <path\n            android:pathData="{d}"\n            android:fillColor="#FF000000"{rule} />')
    svg.append("</svg>")
    vec += ["    </group>", "</vector>"]
    glyph_dir = os.path.join(os.path.dirname(SVG_DIR), "glyphs")
    os.makedirs(glyph_dir, exist_ok=True)
    with open(os.path.join(glyph_dir, f"{name}.svg"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(svg) + "\n")
    with open(os.path.join(RES_DIR, f"ic_sport_{name}.xml"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(vec) + "\n")


def write_launcher(name):
    """Launcher icon used by the `Launcher_<name>` activity-alias (adaptive on 26+, layered below)."""
    res = os.path.dirname(RES_DIR)
    adaptive = ('<?xml version="1.0" encoding="utf-8"?>\n'
                "<!-- Generated by docs/brand/generate_icons.py. -->\n"
                '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
                '    <background android:drawable="@drawable/ic_launcher_background" />\n'
                f'    <foreground android:drawable="@drawable/ic_logo_{name}" />\n'
                f'    <monochrome android:drawable="@drawable/ic_logo_{name}" />\n'
                "</adaptive-icon>\n")
    legacy = ('<?xml version="1.0" encoding="utf-8"?>\n'
              "<!-- Generated by docs/brand/generate_icons.py. -->\n"
              '<layer-list xmlns:android="http://schemas.android.com/apk/res/android">\n'
              '    <item android:drawable="@drawable/ic_launcher_background" />\n'
              f'    <item android:drawable="@drawable/ic_logo_{name}" />\n'
              "</layer-list>\n")
    for folder, body in (("mipmap-anydpi-v26", adaptive), ("mipmap-anydpi", legacy)):
        os.makedirs(os.path.join(res, folder), exist_ok=True)
        with open(os.path.join(res, folder, f"ic_launcher_{name}.xml"), "w", encoding="utf-8") as fh:
            fh.write(body)


if __name__ == "__main__":
    main()
