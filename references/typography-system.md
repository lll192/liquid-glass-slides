# Typography System — 中文与中英混排

Typography is part of composition, not a final decoration pass. The default
top-level setting is `"typography": "editorial"`.

## Automatic title profiles

The builder measures visual length rather than raw character count: a CJK glyph
counts as one unit, while Latin letters and digits count as narrower units. Every
slide receives:

- `title-size-short`, `title-size-medium`, `title-size-long`, or `title-size-xlong`;
- `script-cjk`, `script-latin`, or `script-mixed`.

These classes tune display size, line measure, and tracking without changing the
copy. Extra-long titles also print a build warning.

## Writing rules

- Prefer one claim per title. A title should normally fit in one or two lines.
- Break by meaning, not by filling a rectangle. Keep a verb with its object and
  keep product names, proper nouns, percentages, and number-unit pairs together.
- Chinese body copy should use full-width Chinese punctuation. Use a normal space
  between Chinese and inline English/Arabic tokens only when the chosen house style
  requires it; do not add spaces mechanically inside proper names.
- Keep headings concise instead of solving length with smaller type.
- Eyebrows are coordinates, not secondary titles: 2–6 words or a short section code.
- Body paragraphs should normally stay within 42–56 CJK characters per line and
  contain one idea each.

## CSS behavior

Editorial mode enables strict CJK line breaking, balanced headings, prettier body
wrapping, kerning/ligatures, script-aware tracking, and tabular lining figures for
KPI values and counters. Unsupported newer CSS properties degrade harmlessly.

## Long-title response

`title-size-xlong` is a safety net, not the target. When the builder reports an
extra-long title:

1. preserve protected or quoted wording;
2. otherwise rewrite it as one claim and move qualifications into the lead;
3. rebuild and confirm the warning is gone.

Set `"typography": "classic"` only to reproduce the earlier fixed type scale.
