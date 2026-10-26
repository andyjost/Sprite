"""Draw the Sprite logo family as SVG.

The mark is a wand: a slender twig with a burst of dust at its tip. The
wordmark is "Sprite" in Nunito ExtraBold as outlines, the twig wand in place
of the i. Palette: forest letters, muted gold dust, a brown twig, a pale mint
ground. Run with fontTools on the path and the Nunito variable font in
``font/``; the SVG files land in ``out/``.
"""
import os, math
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
FOREST, GOLD, MINT, BROWN, WOOD, WHITE = '#2F5D3A', '#D6B35A', '#D7F0E3', '#8B6A4E', '#C9A27E', '#FFFFFF'

# The burst: seven directions drawn by hand (degrees, clockwise from the
# right, y down) and the reach of each in a 100-unit square about (50, 50);
# a near dot at radius 22 and a far dot sized by the reach.
BURST = [(-90, 46), (-45, 36), (0, 40), (50, 34), (110, 44), (160, 38), (230, 42)]

def dust(cx, cy, s, color, boost=1.0):
  out = ['<g fill="%s">' % color]
  for angle, reach in BURST:
    a = math.radians(angle); ux, uy = math.cos(a), math.sin(a)
    for r, dot in ((22, 3.2), (reach - 2, 3.5 + (reach - 34) / 4.0)):
      out.append('<circle cx="%.3f" cy="%.3f" r="%.3f"></circle>' % (cx + r * ux * s, cy + r * uy * s, dot * boost * s))
  out.append('</g>')
  return '\n'.join(out)

# The twig, in wand units: the base at (30, 190), the tip at (29, 100), a
# slightly bent spine of three rounded segments and a stub.
TWIG = [((30, 182), (28, 160), 16), ((28, 160), (32, 128), 14), ((32, 128), (29, 100), 12)]
STUB = ((29, 140), (18, 127), 7)

def twig(color, x0, y0, k):
  """The twig with its base at (x0, y0), one wand unit = k user units."""
  def pt(u, v): return (x0 + (u - 30) * k, y0 + (v - 190) * k)
  out = ['<g stroke="%s" stroke-linecap="round" fill="none">' % color]
  for (a, b, w) in TWIG + [STUB]:
    (x1, y1), (x2, y2) = pt(*a), pt(*b)
    out.append('<line x1="%.3f" y1="%.3f" x2="%.3f" y2="%.3f" stroke-width="%.3f"></line>' % (x1, y1, x2, y2, w * k))
  out.append('</g>')
  return '\n'.join(out)

def wand(x0, y0, k, twig_color, dust_color, boost=1.35):
  """A twig with the burst at its tip: the burst's centre sits 140 wand units above the base."""
  return twig(twig_color, x0, y0, k) + '\n' + dust(x0, y0 - 140 * k, 0.75 * k, dust_color, boost)

def svg(w, h, body, label, vb):
  return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%.3f %.3f %.3f %.3f" width="%d" height="%d" role="img" aria-label="%s">\n%s\n</svg>\n'
          % (vb[0], vb[1], vb[2], vb[3], w, h, label, body))

def write(name, text):
  os.makedirs(OUT, exist_ok=True)
  with open(os.path.join(OUT, name), 'w') as f: f.write(text)
  print('wrote', name)

# 1. The mark: the wand alone in a 100-unit square, the base near the bottom.
def mark_body(twig_color, dust_color, boost=1.35):
  return wand(50, 96, 0.58, twig_color, dust_color, boost)
write('mark.svg', svg(200, 200, mark_body(BROWN, GOLD), 'Sprite: a twig wand with a burst of dust', (0, 0, 100, 100)))
write('mark-dark.svg', svg(200, 200, mark_body(WOOD, GOLD), 'Sprite: a twig wand with a burst of dust, for dark grounds', (0, 0, 100, 100)))
write('mark-dust.svg', svg(200, 200, dust(50, 50, 1.0, GOLD), 'Sprite: the burst of dust alone', (0, 0, 100, 100)))

# 2. The wordmark: S p r [wand] t e, the letters as outlines.
font = instantiateVariableFont(TTFont(os.path.join(HERE, 'font', 'Nunito[wght].ttf')), {'wght': 800})
glyphset = font.getGlyphSet(); cmap = font.getBestCmap(); hmtx = font['hmtx']

def kerning_table():
  kern = {}
  if 'GPOS' not in font: return kern
  for lookup in font['GPOS'].table.LookupList.Lookup:
    for st in lookup.SubTable:
      if lookup.LookupType == 9: st = st.ExtSubTable
      if getattr(st, 'LookupType', lookup.LookupType) != 2: continue
      if st.Format == 1:
        for first, ps in zip(st.Coverage.glyphs, st.PairSet):
          for rec in ps.PairValueRecord:
            v = rec.Value1.XAdvance if rec.Value1 and hasattr(rec.Value1, 'XAdvance') else 0
            if v: kern.setdefault((first, rec.SecondGlyph), v)
      elif st.Format == 2:
        c1 = st.ClassDef1.classDefs; c2 = st.ClassDef2.classDefs
        for first in st.Coverage.glyphs:
          k1 = c1.get(first, 0)
          for second in glyphset.keys():
            rec = st.Class1Record[k1].Class2Record[c2.get(second, 0)]
            v = rec.Value1.XAdvance if rec.Value1 and hasattr(rec.Value1, 'XAdvance') else 0
            if v: kern.setdefault((first, second), v)
  return kern
KERN = kerning_table()

def layout(text):
  names = [cmap[ord(c)] for c in text]
  x = 0; placed = []
  for i, g in enumerate(names):
    if i: x += KERN.get((names[i-1], g), 0)
    placed.append((g, x)); x += hmtx[g][0]
  return placed, x

def glyph_path(g, dx, dy, s):
  pen = SVGPathPen(glyphset); glyphset[g].draw(TransformPen(pen, (s, 0, 0, -s, dx, dy))); return pen.getCommands()
def glyph_bounds(g):
  bp = BoundsPen(glyphset); glyphset[g].draw(bp); return bp.bounds

S = 0.1  # 1 font unit = 0.1 user unit: a cap height of about 72
placed, adv = layout('Sprıte')
dotless = cmap[ord('ı')]
paths = ['<path d="%s"></path>' % glyph_path(g, x * S, 0, S) for g, x in placed if g != dotless]
i_x = [x for g, x in placed if g == dotless][0]
ib = glyph_bounds(dotless)
wand_x = (i_x + (ib[0] + ib[2]) / 2) * S     # the stem's centre
xheight = ib[3] * S                            # the top of the dotless i
K = xheight / 90.0                             # the tip of the twig meets the x-height
cap = glyph_bounds(cmap[ord('S')])[3] * S
total_w = adv * S
top = -(140 * K + 52 * 0.75 * K * 1.35) - 6    # the highest grain
desc = max(-glyph_bounds(cmap[ord(c)])[1] * S for c in 'Sprte') + 6
vb = (-6, min(top, -cap - 6), total_w + 12, desc - min(top, -cap - 6))

def wordmark(letters, twig_color, dust_color):
  return '<g fill="%s">\n%s\n</g>\n%s' % (letters, '\n'.join(paths), wand(wand_x, 0, K, twig_color, dust_color))
write('wordmark.svg', svg(int(round(vb[2] * 2)), int(round(vb[3] * 2)), wordmark(FOREST, BROWN, GOLD), 'Sprite', vb))
write('wordmark-dark.svg', svg(int(round(vb[2] * 2)), int(round(vb[3] * 2)), wordmark(WHITE, WOOD, GOLD), 'Sprite', vb))
print('wordmark: width %.1f cap %.1f x-height %.1f wand at x=%.1f, k=%.3f' % (total_w, cap, xheight, wand_x, K))

# 3. Icons: a forest rounded square, the wand tilted, the grains enlarged for small sizes.
def icon(size, boost):
  body = ('<rect x="0" y="0" width="100" height="100" rx="22" fill="%s"></rect>\n<g transform="rotate(-25 50 60)">\n%s\n</g>'
          % (FOREST, wand(52, 97, 0.6, WOOD, GOLD, boost)))
  return svg(size, size, body, 'Sprite', (0, 0, 100, 100))
write('favicon.svg', icon(64, 1.7))
write('icon.svg', icon(512, 1.35))

# 4. The social preview, 1280 by 640: the wordmark on the mint field.
sc = 760.0 / vb[2]
tx = (1280 - vb[2] * sc) / 2 - vb[0] * sc
ty = (640 - vb[3] * sc) / 2 - vb[1] * sc
body = '<rect width="1280" height="640" fill="%s"></rect>\n<g transform="translate(%.3f %.3f) scale(%.5f)">\n%s\n</g>' % (MINT, tx, ty, sc, wordmark(FOREST, BROWN, GOLD))
write('social-preview.svg', svg(1280, 640, body, 'Sprite, a Curry system', (0, 0, 1280, 640)))
