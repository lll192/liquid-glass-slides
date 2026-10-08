# Quality Intelligence — 节奏规划与自动质检

`"quality_intelligence": true` is the default. It adds two complementary checks
without changing claims, deleting copy, or requiring screenshot review.

## 1. Build-time rhythm audit

The builder classifies each slide by semantic family (`opening`, `navigation`,
`break`, `visual`, `evidence`, `emphasis`, `structure`, `explain`, `closing`) and
visual weight (`light`, `medium`, `heavy`). These values are exposed as
`data-rhythm`, `data-weight`, `rhythm-*`, and `weight-*`.

The audit warns when:

- the same layout appears three or more times in a row;
- the same semantic family appears four or more times in a row;
- four or more consecutive pages have the same visual weight, or three heavy pages run together;
- a deck of six or more pages lacks a deliberate cover or closing;
- a long deck lacks visual evidence/emphasis or a breathing page.

Warnings require editorial revision of the outline. The deterministic builder
does not reorder pages automatically because narrative order may be intentional.

## 2. Runtime geometry audit

After fonts finish loading, the inlined browser engine checks the actual viewport:

- horizontal and vertical overflow;
- the main composition crossing slide boundaries;
- display titles wrapping beyond a conservative line limit;
- readable copy falling below 14 px.

Results are stored in `window.__LG_BUILD_REPORT__.runtime`. Run the check again
after live edits with:

```js
window.LiquidGlassQA.run()
```

Append `?qa=1` to the local HTML URL to show a compact status badge and outline
slides containing warnings/errors. Clicking the badge prints the issue table in
the browser console. The QA interface is invisible during normal presentation.

## 3. Response to findings

1. Fix factual/content problems first.
2. Shorten or split `overfull` pages; never keep shrinking type.
3. Break repeated heavy structures with a visual, quote, section divider, or
   evidence page only when it serves the narrative.
4. Rebuild and rerun the runtime audit at the intended presentation viewport.
5. Use screenshots only for a major visual-system change or a remaining anomaly.

Set `"quality_intelligence": false` only for exact legacy reproduction.
