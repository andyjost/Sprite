# The Sprite logo

The mark is a burst of dust: seven grains of light thrown in seven
directions drawn by hand. The wordmark is "Sprite" in Nunito ExtraBold
with a wand, a slender twig carrying the same burst, in place of the i.
The lockup sets the burst, large, beside the wordmark. The letters are
outlines, so no font needs to be installed to render them.
`specimen.png` shows every file of the family on one sheet.

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

- `lockup.svg`: the burst beside the wordmark, forest letters, for white
  and mint grounds; `lockup-dark.svg`: white letters and a light-wood
  twig, for forest and other dark grounds. The README of the
  distribution shows the first and, to a viewer in dark mode, the second.
- `wordmark.svg`, `wordmark-dark.svg`: the name with the wand alone.
- `mark.svg`: the burst in gold, for white and dark grounds;
  `mark-white.svg`: in white, for the mint ground; `mark-forest.svg`: in
  forest, for one-color uses. `wand.svg`: the twig wand of the wordmark,
  for a place that wants it alone.
- `favicon.svg`, `favicon.ico` (16, 32 and 48 px), `icon.svg`,
  `icon-180.png`, `icon-192.png`, `icon-512.png`: the burst on a forest
  rounded square, the grains enlarged for small sizes. The docs use the
  favicon.
- `social-preview.png` (1280 by 640) and its source: the lockup on mint,
  for the link card of the repository (uploaded once in the repository's
  settings).
- `specimen.svg`, `specimen.png`: the whole family on one sheet, with the
  palette.

## Rules

The dust stays gold and keeps its seven directions; the twig stays
slender, about half a letter stem, with its one stub, and lives only in
the wordmark. Give the burst clear space of half its width on every
side. Do not add a dot or a star to the wand's tip.
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
rsvg-convert -w 1600 out/specimen.svg -o out/specimen.png
```

Nunito is by Vernon Adams, Cyreal and Jacques Le Bailly, under the SIL
Open Font License 1.1 (`NUNITO-OFL.txt`); the outlines in these files are
derived from it. The drawings themselves carry the license of this
repository.
