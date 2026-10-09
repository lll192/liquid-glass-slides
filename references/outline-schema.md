# Outline Schema — one-click build path (`scripts/build.py`)

`build.py` reads a single JSON file (`outline.json`) and emits one **self-contained HTML**
deck. No external assets, no build step. Same engine as the hand-write path.

```bash
python scripts/build.py --outline my-talk.json --out my-talk.html
# or positional:  python scripts/build.py my-talk.json
```

## Top-level object

| Key | Type | Required | Meaning |
|---|---|---|---|
| `lang` | string | no | HTML `lang` attr. Default `zh-CN`. |
| `title` | string | no | Browser tab title. Default `Liquid Glass Deck`. |
| `composition` | string | no | `constructivist` (default) or `classic`. The default uses an asymmetric editorial grid, strict alignment, shared glass planes, and restrained geometry. |
| `layout_intelligence` | boolean | no | Default `true`. Automatically selects a content-aware variant and density class per slide. Disable only for exact legacy reproduction. |
| `typography` | string | no | `editorial` (default) or `classic`. Editorial mode adds visual-length title classes, CJK-aware wrapping, script-aware tracking, and tabular figures. |
| `visual_intelligence` | boolean | no | Default `true`. Profiles local/data-URI image orientation and ECharts series semantics, then adjusts visual ratios and chart height while emitting accessibility/editorial warnings. |
| `quality_intelligence` | boolean | no | Default `true`. Audits deck rhythm at build time and embeds a runtime DOM geometry report. Disable only for exact legacy reproduction. |
| `content_intelligence` | boolean | no | Default `true`. Checks generic titles and oversized display blocks, and embeds presenter notes without adding them to slide density. |
| `narrative_director` | boolean | no | Default `true`. Infers or reads story roles/emotions, exposes presenter cues, and audits flat narrative runs. |
| `visual_coverage_planner` | boolean | no | Default `true`. Audits meaningful visual coverage, required visual plans, text-only runs, and chart/table provenance. |
| `theme` | object | no | Topic color theme — see below. `build.py` derives the 3 background blobs, the Three.js particle palette, the accent text color, and every glow/shadow from it. **Fully automatic: the AI picks the palette from the topic; the user never sets colors.** |
| `auto_ripple` | boolean | no | Default `true`. Automatically adds a restrained ripple surface to slides that have no Three.js, ECharts, image, or explicit `surface`. |
| `slides` | array | **yes** | Ordered list of slide objects. Each needs a `layout`. |

`constructivist` changes composition, not topic color. It does not force red/black,
historic motifs, or diagonal decoration. Use `classic` only to reproduce the older
centered, card-forward layout treatment.

## Fields available on every slide

- `main_point` — optional planning-only statement of the one audience takeaway;
  it is included in the build report but not rendered.
- `speaker_notes` — optional string or string array. Notes are HTML-escaped,
  excluded from density calculations, hidden from the audience, and available
  through the `N` presenter panel or `?notes=1`.
- `story_role` — optional narrative role: `hook`, `orient`, `question`, `context`,
  `conflict`, `explain`, `example`, `evidence`, `contrast`, `reveal`, `synthesis`,
  `transition`, `resolution`, or `pause`.
- `audience_question`, `speaker_intent`, `transition`, `emotion` — optional
  Narrative Director cues shown only in the presenter panel.
- `visual_plan` — optional object with `type`, `purpose`, `priority`
  (`required`/`optional`), and `source`. See `visual-coverage-planner.md`.

## Theme (auto color system)

`build.py` reads an optional top-level `theme` object and turns it into a coherent
deck palette. You only need `colors` (3 hex) and `accent` (1 hex); everything else
is derived. If `theme` is omitted, a balanced blue / red / green default is used.

```json
{
  "theme": {
    "name": "scholarly",                       // optional label for reference
    "colors": ["#0A84FF", "#5E5CE6", "#30D158"], // exactly 3: the 3 blurred blobs + particles
    "accent": "#0A84FF"                        // the one best color for text emphasis (defaults to colors[0])
  },
  "slides": [ ... ]
}
```

What each field drives:
- `colors[0..2]` → the three blurred background blobs **and** the Three.js particle palette.
- `accent` → `--accent`: eyebrows, headings emphasis, links, chip/dot/glow color. Defaults to `colors[0]`.
- Body text stays near-black (`--ink`) for readability — only *emphasis* uses the accent.
- Any other `--key:value` pairs in `theme` are also merged into `:root` (legacy escape hatch).

Curated palettes by topic mood: `references/theme-palettes.md`.

## Placeholder contract (used inside `templates/single-page/*.html`)

- `{{field}}` — scalar substitution. Missing field → empty string.
- `{{#items}} ... {{/items}}` — repeat block. Inside, use `{{item.x}}` for each list
  element's field, and `{{i}}` for its 0-based index (for staggered reveal).
- `{{#hero}} ... {{/hero}}` — optional block: renders once if the field is truthy
  (e.g. an image data URI or a caption string), else omitted entirely.

HTML is allowed inside field values (e.g. `two-column` `left`/`right`). Keep required
reading text in HTML — never bake text into an image.

Every slide also accepts optional `variant`. Omit it or use `"auto"` by default.
Supported values depend on layout; see `references/layout-intelligence.md`. The
builder emits `data-variant` and `data-density` on each slide. An `overfull` build
warning means the outline should be shortened or split before delivery.

## Layouts

### `cover`
`eyebrow`, `title`, `subtitle`; optional `hero` (image src) + `hero_alt`.

### `toc`
`eyebrow`, `title`; `items: [{ label, desc }]`. Renders as one indexed composition
field with separators and auto zero-padded numbers (01, 02, …).

### `section-divider`
`num`, `title`, `subtitle`.

### `bullets`
`eyebrow`, `title`; `items: [{ text, desc? }]`. Renders as flat rows inside one
shared glass plane (index + title + description). Best with 3–6 items;
with more, consider splitting the page.

### `two-column`
`eyebrow`, `title`; `left` and `right` (HTML strings). Right renders inside a glass card.

### `grid-cards`
`eyebrow`, `title`; `items: [{ num, title, desc }]`. Columns auto: 2→`g2`, 3→`g3`, 4→`g4`.

### `big-quote`
`quote`, `by`.

### `stat-highlight`
`eyebrow`, `num`, `unit`, `title`, `desc`.

### `kpi-grid`
`eyebrow`, `title`; `items: [{ num, label }]`. Columns auto like `grid-cards`.

### `timeline`
`eyebrow`, `title`; `items: [{ year, head, desc }]` (animated growth).

### `comparison`
`eyebrow`, `title`; `left_title` + `left_items:[{text}]`; `right_title` + `right_items:[{text}]`.
A `VS` badge sits between two glass panels.

### `image-frame`  (concentric-rounded glass photo frame)
`eyebrow`, `title`, `image` (src), `alt`; optional `caption`.
Use for photos / images WITH a background. The frame applies the concentric-radius rule
automatically — do **not** also float it.

### `object-float`  (transparent object, no frame)
`eyebrow`, `title`, `subtitle`; `image` (src) + `alt` (optional block).
Use for transparent / cut-out / white-bg-convertible objects — they float via `.hero-orb`.

### `closing`  (Closing A — large gradient title)
`eyebrow`, `title`, `subtitle`; `contacts: [{ icon, text }]`.

### `chart`  (ECharts visualization)
Renders the `chart` layout. `eyebrow`, `title`; optional `note` (one-line lead) and
`caption` (footnote). The chart itself comes from:
```json
"chart": {
  "height": "min(44vh,400px)",          // optional, default min(46vh,420px)
  "option": { "xAxis":{...}, "yAxis":{...}, "series":[...] }   // a PURE JSON ECharts option
}
```
`build.py` reads `option`, inlines `assets/echarts.min.js` automatically, and applies the
liquid-glass theme (transparent canvas, iOS palette, frosted tooltip). The chart container gets
a unique id (`echart-0`, `echart-1`, …) — you never write it by hand.

**Rules (see `references/echarts-charts.md`):**
- Add a chart **only** where the page has real, comparable, quantitative data. Do not fabricate numbers.
- `option` must be pure JSON — no JS functions (`formatter` must be a string template like `'{b}: {c}'`).
- Use `chart` for trends (line/area), category comparison (grouped bar), proportion (pie/doughnut),
  multi-dimension (radar), correlation (scatter).

### `data-table`  (exact values / evidence)

`eyebrow`, `title`; `columns` (string array), `rows` (array of row arrays);
optional `highlight_rows` (zero-based row indexes), `caption`, and `source`.
Keep to five columns and seven visible rows. Use a chart for pattern recognition and
a table when the audience needs exact values.

### `process-flow`  (ordered mechanism)

`eyebrow`, `title`; `items: [{ label, desc }]`; optional `caption`.
Best with three to five concise steps. The builder supplies sequence numbers and a
horizontal/compact variant.

### `concept-map`  (relationships / system model)

`eyebrow`, `title`, `center`; `items: [{ label, desc }]`; optional `caption`.
Best with three to six nodes around one central concept. Use the spoken explanation to
name the relationships rather than filling nodes with paragraphs.

### `three`  (Three.js 3D background — optional per-slide)
Add a live 3D scene **behind any existing slide** by adding a `three` field to that slide object.
It does NOT need its own layout — the 3D plays behind the slide's own text.
```json
"three": { "scene": "field" }     // field | nebula | object | network
```
- `field`   — calm floating colored bokeh (good for cover / opening / closing).
- `nebula`  — denser, faster particles (energy / scale / ecosystem).
- `object`  — slow-rotating wireframe icosahedron (structure / mechanism / core idea).
- `network` — connected nodes + links (community / relations / ecosystem / comparison).
Only ONE shared WebGL canvas is ever created; `build.py` swaps the active scene by visible slide
and inlines `assets/three.min.js` automatically (dependency-free decks stay small). If WebGL is
unavailable, the slide silently falls back to the static light gradient — no error.

**Rules (see `references/three-3d.md`):**
- Add 3D **only** where it strengthens the theme or visual impact. Do **not** put it on every slide.
- Best hosts: `cover`, `section-divider`, `stat-highlight`, `closing`. Avoid text-dense slides
  (`bullets`, `grid-cards`, `comparison`, `timeline`) — the motion distracts from reading.
- Style is auto-tuned to the light liquid-glass theme (soft bokeh, iOS palette, low opacity) — no skinning needed.

### `surface` (optional ripple material per slide)

Add an opt-in water/acrylic material layer without changing the slide layout:

```json
"surface": {
  "kind": "ripple",
  "pattern": "flow",
  "zone": "bottom",
  "intensity": "hero",
  "motion": "drift",
  "seed": 11
}
```

- `pattern`: `rings` | `flow` | `caustic`.
- `zone`: `bottom` | `bottom-right` | `edge` | `full`; use a localized zone to protect text.
- `intensity`: `subtle` | `hero`.
- `motion`: `static` | `drift` | `pulse`.
- `seed`: integer stored in the outline for deterministic output.

All modes receive a CSS fallback. Dynamic modes use the existing shared Three.js canvas and
therefore trigger Three.js inlining. If the same slide also declares `three`, the explicit
3D scene wins and the ripple remains static. See `references/ripple-textures.md` for selection
rules, allowed host layouts, and verification.

If `surface` is omitted, `build.py` automatically supplies a subtle deterministic ripple
when the slide also has no `three`, `chart`, `hero`, `image`, or inline `<img>`.
Dense layouts use a static localized texture; sparse layouts may use gentle drift.
Set `"auto_ripple": false` at the top level or on an individual slide to opt out.
An explicit `surface` declaration always takes precedence.

## Image rule (critical)

Decide placement **before** you have the image:

- background **transparent / cut-out / white** → use `object-float` (floating).
- background **complex / photographic** → use `image-frame` (glass frame, concentric radius).

For AI-generated images, request the matching background up front (see `image-handling.md`
§2 one-line decision rule). Inline as base64/data URI — never an external URL or local path.

## Tips

- Deterministic: same outline → same HTML. Great for re-runs and version control.
- For a one-off bespoke layout, fall back to Path A (hand-write from `assets/template.html`).
- See `examples/sample-outline.json` + `examples/sample-deck.html` for the core layout tour, and `examples/narrative-visual-outline.json` for Narrative Director plus the three structured visual layouts (18 layouts total).
