# Visual Coverage Planner

Visual Coverage Planner gives each content slide a deliberate visual job. Opening and
closing pages may remain typographic; every interior page must have at least one reviewed
image, or a factual chart that replaces the image. It balances human-readable text with
evidence views, images, and breathing room without decorative-only assets.

## Decision matrix

| Content need | Preferred visual |
|---|---|
| Real-world situation, person, place, object | sourced image first; AI-generated when bespoke art is needed |
| Quantitative trend, comparison, distribution, proportion | ECharts chart |
| Exact values the audience may need to read | `data-table` |
| Ordered steps, pipeline, lifecycle | `process-flow` |
| Relationships, system parts, taxonomy | `concept-map` |
| Two positions, choices, before/after | `comparison` |
| One decisive number | `stat-highlight` or `kpi-grid` |
| No trustworthy evidence or useful visual structure | reviewed atmospheric photo + concise text |

Ripple and Three.js can create atmosphere, but they do not count as meaningful
information visuals. A meaningful visual must explain, compare, locate, quantify, or
make a concrete subject visible.

## Per-slide plan

```json
"visual_plan": {
  "type": "data-table",
  "purpose": "让观众比较三种调度策略的取舍",
  "priority": "required",
  "source": "课程资料，第 3 节"
}
```

- `type`: `auto`, `image`, `chart`, `data-table`, `process-flow`, `concept-map`,
  `comparison`, `kpi`, `stat`, `timeline`, `structured-grid`, `diagram`,
  `relationship`, or `data-visualization`.
- `purpose`: one sentence explaining why the visual earns its space.
- `priority`: `required` or `optional`.
- `source`: compact provenance for factual graphics.

The builder reports the planned and rendered visual type, required-visual mismatches,
missing chart/table provenance, text-only interior pages, and deck-level meaningful
visual coverage. Interior visual coverage should reach 100% when photography and factual
charts are counted together.

## Structured layouts

### `data-table`

Use `columns`, `rows`, optional `highlight_rows`, and `caption` or `source`. Keep to five
columns and seven visible rows; move detail to an appendix instead of shrinking type.

### `process-flow`

Use `items: [{"label":"抓取", "desc":"下载当前页面"}]`. Aim for three to five
steps. Each step should be a verb or short phase, not a paragraph.

### `concept-map`

Use `center` plus `items: [{"label":"调度器", "desc":"决定下一 URL"}]`. Aim for
three to six nodes and name actual relationships in the spoken explanation.

## Evidence and asset rules

- Never invent numbers to make a chart or table look complete.
- Charts and tables need a visible caption/source or `visual_plan.source`.
- The planner chooses the medium; the producing agent still generates an image with
  ImageGen, writes a valid ECharts option, or supplies structured layout data.
- For sourced images, read `web-imagery.md`, save assets locally, and validate a
  `media-manifest.json`. A search result URL by itself is not provenance.
- Keep readable text in HTML. Do not ask image generation to render labels or paragraphs.
- Use one background image or one to three content images. Do not add a decorative role.
- If no evidence image is justified, use a reviewed atmospheric image that matches the
  slide's place, object, or emotional context. Do not fabricate relevance.

Top-level `"visual_coverage_planner": false` disables this audit for exact legacy
reproduction. It is enabled by default.
