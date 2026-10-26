# The Sprite logo

The mark is a wand: a slender twig with a burst of dust at its tip, seven
grains of light thrown in seven directions drawn by hand. The wordmark is
"Sprite" in Nunito ExtraBold with the wand in place of the i. The letters
are outlines, so no font needs to be installed to render them.

## Palette

| Role | Hex | Use |
|---|---|---|
| Forest | `#2F5D3A` | the letters; the ground of icons |
| Gold | `#D6B35A` | the dust, and nothing else |
| Twig | `#8B6A4E` | the twig on light grounds |
| Light wood | `#C9A27E` | the twig on dark grounds |
| Mint | `#D7F0E3` | the ground of the social preview and of light pages |
| White | `#FFFFFF` | the letters on dark grounds |

## Files

- `wordmark.svg`: the name with the wand, forest letters, for white and
  mint grounds. `wordmark-dark.svg`: white letters, the twig in light
  wood, for forest and other dark grounds. The README of the
  distribution shows the first and, to a viewer in dark mode, the second.
- `mark.svg`, `mark-dark.svg`: the wand alone, upright, for light and
  dark grounds; `mark-dust.svg`: the burst alone, for places too small
  for a twig.
- `favicon.svg`, `favicon.ico` (16, 32 and 48 px), `icon.svg`,
  `icon-180.png`, `icon-192.png`, `icon-512.png`: the wand tilted on a
  forest rounded square, the grains enlarged for small sizes. The docs
  use the favicon.
- `social-preview.png` (1280 by 640) and its source: the wordmark on
  mint, for the link card of the repository (uploaded once in the
  repository's settings).

## Rules

The twig stays slender, about half a letter stem, with its one stub; the
dust stays gold and keeps its seven directions. Give the wand clear
space of one burst on every side. Do not add a dot or a star to the tip.
No lime or yellow-green anywhere near the mark: the project shares its
name with a soft drink.

## Regenerating

`make_logo.py` draws every SVG from the geometry above and the Nunito
font. Fetch the variable font once, then run the script with
[fontTools](https://github.com/fonttools/fonttools) on the path; PNGs
come from `rsvg-convert`, and `favicon.ico` wraps the 16, 32 and 48 px
PNGs:

```sh
mkdir -p font && curl -sSL -o 'font/Nunito[wght].ttf' \
  'https://github.com/google/fonts/raw/main/ofl/nunito/Nunito%5Bwght%5D.ttf'
python make_logo.py
for s in 16 32 48; do rsvg-convert -w $s -h $s out/favicon.svg -o out/favicon-$s.png; done
```

Nunito is by Vernon Adams, Cyreal and Jacques Le Bailly, under the SIL
Open Font License 1.1 (`NUNITO-OFL.txt`); the outlines in these files are
derived from it. The drawings themselves carry the license of this
repository.
