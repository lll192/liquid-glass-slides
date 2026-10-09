# Visual Coverage Planner

Visual Coverage Planner gives each content slide a deliberate visual job. Its goal is
not to decorate every page. It balances human-readable text with evidence views,
explanatory diagrams, tables, images, and breathing room.

## Decision matrix

| Content need | Preferred visual |
|---|---|
| Real-world situation, person, place, object | AI-generated or sourced image |
| Quantitative trend, comparison, distribution, proportion | ECharts chart |
| Exact values the audience may need to read | `data-table` |
| Ordered steps, pipeline, lifecycle | `process-flow` |
| Relationships, system parts, taxonomy | `concept-map` |
| Two positions, choices, before/after | `comparison` |
| One decisive number | `stat-highlight` or `kpi-grid` |
| No trustworthy evidence or useful visual structure | concise text + ripple |

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
missing chart/table provenance, long text-only runs, and deck-level meaningful visual
coverage. For decks with at least six content slides, roughly 40–65% meaningful visual
coverage is a useful default range—not a quota. Dense technical reports may need more;
reflective or keynote-style decks may need less.

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
- Keep readable text in HTML. Do not ask image generation to render labels or paragraphs.
- If no meaningful visual is justified, use a concise editorial text composition and the
  automatic ripple background instead of filler imagery.

Top-level `"visual_coverage_planner": false` disables this audit for exact legacy
reproduction. It is enabled by default.
