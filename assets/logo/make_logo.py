"""Draw the Sprite logo family as SVG.

The mark is the burst of dust alone: seven grains of light in seven
directions drawn by hand. The wordmark is "Sprite" in Nunito ExtraBold as
outlines, with a wand, a slender twig carrying the same burst, in place of
the i. The lockup sets the burst, large, beside the wordmark. Palette: forest
letters, muted gold dust, a brown twig, a pale mint ground. Run with fontTools on the path and the Nunito variable font in
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

# 1. The mark: the burst alone in a 100-unit square.
write('mark.svg', svg(200, 200, dust(50, 50, 1.0, GOLD), 'Sprite: a burst of gold dust', (0, 0, 100, 100)))
write('mark-white.svg', svg(200, 200, dust(50, 50, 1.0, WHITE), 'Sprite: a burst of white dust, for the mint ground', (0, 0, 100, 100)))
write('mark-forest.svg', svg(200, 200, dust(50, 50, 1.0, FOREST), 'Sprite: a burst of forest dust, for one-color uses', (0, 0, 100, 100)))
write('wand.svg', svg(200, 200, wand(50, 96, 0.58, BROWN, GOLD), 'Sprite: the twig wand of the wordmark', (0, 0, 100, 100)))

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

# 3. The lockup, the duo: the burst at 1.5 cap heights beside the wordmark.
def lockup(dust_color, letters, twig_color):
  mh = 1.5 * cap
  sc = mh / 100.0
  gap = 0.3 * cap
  my = -cap / 2
  body = '<g transform="translate(0 %.3f) scale(%.4f)">\n%s\n</g>\n' % (my - 50 * sc, sc, dust(50, 50, 1.0, dust_color))
  shift = mh + gap
  body += '<g transform="translate(%.3f 0)">\n%s\n</g>' % (shift, wordmark(letters, twig_color, dust_color))
  width = shift + total_w
  y_top = min(vb[1], my - mh / 2 - 6)
  lvb = (-6, y_top, width + 12, max(desc, my + mh / 2 + 6) - y_top)
  return svg(int(round(lvb[2] * 2)), int(round(lvb[3] * 2)), body, 'Sprite', lvb), lvb
LOCKUP, LVB = lockup(GOLD, FOREST, BROWN)
write('lockup.svg', LOCKUP)
write('lockup-dark.svg', lockup(GOLD, WHITE, WOOD)[0])

# 4. Icons: the burst alone on a forest rounded square, the grains enlarged for small sizes.
def icon(size, boost):
  body = '<rect x="0" y="0" width="100" height="100" rx="22" fill="%s"></rect>\n%s' % (FOREST, dust(50, 50, 0.9, GOLD, boost))
  return svg(size, size, body, 'Sprite', (0, 0, 100, 100))
write('favicon.svg', icon(64, 1.6))
write('icon.svg', icon(512, 1.25))

# 5. The social preview, 1280 by 640: the lockup on the mint field.
def place(inner_svg, inner_vb, box_x, box_y, box_w, box_h):
  """The body of an SVG scaled to fit a box, centred."""
  inner = inner_svg.split('>', 1)[1].rsplit('</svg>', 1)[0]
  sc = min(box_w / inner_vb[2], box_h / inner_vb[3])
  tx = box_x + (box_w - inner_vb[2] * sc) / 2 - inner_vb[0] * sc
  ty = box_y + (box_h - inner_vb[3] * sc) / 2 - inner_vb[1] * sc
  return '<g transform="translate(%.3f %.3f) scale(%.5f)">\n%s\n</g>' % (tx, ty, sc, inner)
body = '<rect width="1280" height="640" fill="%s"></rect>\n%s' % (MINT, place(LOCKUP, LVB, 240, 170, 800, 300))
write('social-preview.svg', svg(1280, 640, body, 'Sprite, a Curry system', (0, 0, 1280, 640)))

# 6. The specimen sheet: every asset on one image.
def caption(x, y, text, color='#4A6382', size=15, weight='normal'):
  return '<text x="%.1f" y="%.1f" font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="%d" font-weight="%s" fill="%s">%s</text>' % (x, y, size, weight, color, text)
W, H = 1600, 1180
parts = ['<rect width="%d" height="%d" fill="#FFFFFF"></rect>' % (W, H)]
parts.append(caption(40, 50, 'Sprite: the logo family', '#2F5D3A', 28, 'bold'))
parts.append(caption(40, 78, 'The burst of dust is the mark and the icon; the wordmark carries a twig wand in place of the i; the lockup sets the two side by side.'))
# Row 1: the lockup on white, on mint, on forest.
tiles = [('#FFFFFF', '#E3EEF6', LOCKUP, LVB, 'lockup.svg on white'), (MINT, MINT, LOCKUP, LVB, 'lockup.svg on mint'), (FOREST, FOREST, lockup(GOLD, WHITE, WOOD)[0], LVB, 'lockup-dark.svg on forest')]
for i, (bg, border, body_svg, bvb, label) in enumerate(tiles):
  x = 40 + i * 510; y = 100
  parts.append('<rect x="%d" y="%d" width="490" height="220" rx="14" fill="%s" stroke="%s"></rect>' % (x, y, bg, border))
  parts.append(place(body_svg, bvb, x + 30, y + 30, 430, 160))
  parts.append(caption(x, y + 245, label))
# Row 2: the wordmark alone, the mark alone in three colors, the wand.
y = 370
parts.append('<rect x="40" y="%d" width="760" height="200" rx="14" fill="#FFFFFF" stroke="#E3EEF6"></rect>' % y)
parts.append(place(open(os.path.join(OUT, 'wordmark.svg')).read(), vb, 70, y + 30, 700, 140))
parts.append(caption(40, y + 225, 'wordmark.svg (wordmark-dark.svg for dark grounds)'))
for i, (bg, fname, label) in enumerate([('#FFFFFF', 'mark.svg', 'mark.svg'), (MINT, 'mark-white.svg', 'mark-white.svg on mint'), (FOREST, 'mark.svg', 'mark.svg on forest'), ('#FFFFFF', 'wand.svg', 'wand.svg')]):
  x = 830 + i * 185
  parts.append('<rect x="%d" y="%d" width="170" height="200" rx="14" fill="%s" stroke="%s"></rect>' % (x, y, bg, '#E3EEF6' if bg == '#FFFFFF' else bg))
  parts.append(place(open(os.path.join(OUT, fname)).read(), (0, 0, 100, 100), x + 25, y + 25, 120, 150))
  parts.append(caption(x, y + 225, label, size=13))
# Row 3: icons at sizes, the social preview, the palette.
y = 640
parts.append(caption(40, y + 20, 'favicon.ico and the icons: the burst on forest', '#2F5D3A', 16, 'bold'))
x = 40
for s in (16, 32, 48, 96, 180):
  parts.append(place(open(os.path.join(OUT, 'favicon.svg' if s <= 48 else 'icon.svg')).read(), (0, 0, 100, 100), x, y + 40 + (180 - s), s, s))
  parts.append(caption(x, y + 245, '%d' % s, size=12))
  x += s + 30
parts.append(caption(560, y + 20, 'social-preview.png, 1280 by 640', '#2F5D3A', 16, 'bold'))
parts.append('<g transform="translate(560 %d) scale(0.3125)">%s</g>' % (y + 40, open(os.path.join(OUT, 'social-preview.svg')).read().split('>', 1)[1].rsplit('</svg>', 1)[0]))
parts.append(caption(1000, y + 20, 'The palette', '#2F5D3A', 16, 'bold'))
for i, (name, hexv, use) in enumerate([('Forest', FOREST, 'letters, icon ground'), ('Gold', GOLD, 'the dust'), ('Twig', BROWN, 'the twig on light grounds'), ('Light wood', WOOD, 'the twig on dark grounds'), ('Mint', MINT, 'light grounds'), ('White', WHITE, 'letters on dark grounds')]):
  yy = y + 40 + i * 48
  parts.append('<rect x="1000" y="%d" width="36" height="36" rx="9" fill="%s" stroke="#E3EEF6"></rect>' % (yy, hexv))
  parts.append(caption(1048, yy + 16, '%s  %s' % (name, hexv), '#2F5D3A', 14, 'bold'))
  parts.append(caption(1048, yy + 33, use, size=12))
parts.append(caption(40, H - 30, 'Nunito ExtraBold (SIL OFL 1.1) as outlines; drawings and layout generated by assets/logo/make_logo.py.', size=12))
write('specimen.svg', svg(W, H, '\n'.join(parts), 'The Sprite logo family on one sheet', (0, 0, W, H)))
