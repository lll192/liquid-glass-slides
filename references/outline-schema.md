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
| `theme` | object | no | Topic color theme — see below. `build.py` derives the 3 background blobs, the Three.js particle palette, the accent text color, and every glow/shadow from it. **Fully automatic: the AI picks the palette from the topic; the user never sets colors.** |
| `slides` | array | **yes** | Ordered list of slide objects. Each needs a `layout`. |

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

## Layouts

### `cover`
`eyebrow`, `title`, `subtitle`; optional `hero` (image src) + `hero_alt`.

### `toc`
`eyebrow`, `title`; `items: [{ label, desc }]`. Renders as a **numbered glass-card grid**:
auto zero-padded numbers (01, 02, …), ≤4 items → 2 columns, 5+ → 3 columns.

### `section-divider`
`num`, `title`, `subtitle`.

### `bullets`
`eyebrow`, `title`; `items: [{ text, desc? }]`. Renders as **full-width glass rows**
(accent dot + title + description), not a thin single-column list. Best with 3–6 items;
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

## Image rule (critical)

Decide placement **before** you have the image:

- background **transparent / cut-out / white** → use `object-float` (floating).
- background **complex / photographic** → use `image-frame` (glass frame, concentric radius).

For AI-generated images, request the matching background up front (see `image-handling.md`
§2 one-line decision rule). Inline as base64/data URI — never an external URL or local path.

## Tips

- Deterministic: same outline → same HTML. Great for re-runs and version control.
- For a one-off bespoke layout, fall back to Path A (hand-write from `assets/template.html`).
- See `examples/sample-outline.json` + the generated `examples/sample-deck.html` for a live tour of all 15 layouts.
