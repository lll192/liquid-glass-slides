# Visual Intelligence — 图片与图表编排

The default one-click build uses `"visual_intelligence": true`. It inspects
available image metadata and ECharts options before choosing layout proportions.
It never invents data, crops a source destructively, or replaces factual copy.

## Image profiling

For local files and base64 data URIs, the builder reads dimensions for PNG, JPEG,
GIF, extended WebP, and dimensioned SVG without external libraries. It classifies:

- `media-landscape` — ratio ≥ 1.30 (including common 4:3 imagery); grant the visual about 8 of 12 columns;
- `media-portrait` — ratio ≤ 0.78; keep a narrower visual field and use `contain`;
- `media-square` — everything between; use a 5:7 or 7:5 relationship;
- `media-unknown` — remote, missing, unsupported, or dimensionless asset; retain the
  safe default layout.

Every image slide exposes `data-media`. Missing local assets and missing `alt` /
`hero_alt` text produce build warnings.

The profile complements, rather than replaces, the placement decision in
`image-handling.md`: transparent cut-outs still float; real-background images still
use a frame.

## Chart profiling

The builder reads the pure-JSON ECharts `series` list and classifies the page:

- `chart-trend` — line/area;
- `chart-comparison` — bar;
- `chart-proportion` — pie/doughnut;
- `chart-radar` — multidimensional radar;
- `chart-distribution` — scatter;
- `chart-generic` — other supported types.

Four or more series, or 28+ data points, adds `chart-data-dense`. Dense charts
receive more canvas area and a taller bounded container. Proportion/radar charts
use a more balanced text/visual split. Pages expose `data-chart-profile`.

## Required editorial judgment

- A chart must have a factual `takeaway` or at least a `note`; the builder warns
  when both are missing.
- The takeaway states the pattern visible in the data, not an unsupported cause.
- A caption records source, scope, date, and whether values are illustrative.
- If labels remain crowded, reduce categories or split the analysis; do not rely on
  tiny axis text.
- Image orientation should not override narrative reading order. Set an explicit
  slide `variant` when the visual must appear on a particular side.

Set `"visual_intelligence": false` only for exact legacy reproduction.
