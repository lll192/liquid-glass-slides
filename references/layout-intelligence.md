# Layout Intelligence — 构图变体与内容密度

The one-click builder analyzes each slide's content shape before rendering. This
layer chooses a composition variant and a density class; it never changes factual
meaning or silently deletes copy.

For cross-slide pacing and browser geometry checks, continue with
`quality-intelligence.md` after the per-slide composition is stable.

## Defaults

- Top-level `"layout_intelligence": true` is implicit.
- Per-slide `"variant": "auto"` is implicit.
- The chosen values are written to the slide as `data-variant`, `data-density`,
  `variant-*`, and `density-*` for inspection and CSS control.
- Set `"layout_intelligence": false` only for exact legacy reproduction.

## Automatic variants

| Layout | Auto choices | Decision signal |
|---|---|---|
| `toc` | `index-quadrant`, `index-matrix` | item count |
| `bullets` | `list-spread`, `list-vertical`, `list-compact` | item count |
| `two-column` | `split-left`, `split-right`, `split-balanced` | relative text volume |
| `grid-cards` | `feature-first`, `mosaic`, `matrix` | 3 / 4 / 5+ items |
| `kpi-grid` | `feature-first`, `kpi-strip`, `matrix` | 3 / 4 / 5+ metrics |
| `timeline` | `line-spacious`, `line-compact` | step count |
| `comparison` | `compare-left`, `compare-right`, `compare-balanced` | side density |
| `stat-highlight` | `number-left`, `number-right` | deterministic page rhythm |
| `image-frame`, `chart` | `visual-left`, `visual-right` | deterministic alternation |

Set a listed variant explicitly only when semantics demand a specific reading
order. Do not manually alternate every page just for decoration.

## Density classes

The builder measures visible copy, repeated items, and layout-specific capacity:

- `sparse` — permits more breathing room and stronger scale contrast.
- `standard` — normal composition.
- `dense` — tightens gaps and cell padding slightly while keeping readable type.
- `overfull` — applies a bounded compact treatment and prints a build warning.

An `overfull` warning is a planning failure, not an invitation to keep shrinking
text. The producing agent should, in order:

1. remove repetition and shorten supporting copy;
2. move secondary detail to speaker notes or a follow-up slide;
3. split the slide while preserving one main point per page;
4. rebuild and confirm the warning is gone.

The deterministic builder cannot safely paraphrase, summarize, or split user copy
without semantic judgment, so it never performs those destructive operations.

## Long titles

Long titles receive `title-long`, which expands line measure and reduces display
size within a bounded range. The agent should still rewrite titles to one clear
claim whenever source fidelity allows it.

## Verification

For routine edits, run only:

1. Python syntax compilation;
2. one representative build;
3. a DOM overflow check when layout CSS changed.

Use screenshot review only for a major visual-system change, a reported visual
defect, or a page that remains suspicious after automated checks.
