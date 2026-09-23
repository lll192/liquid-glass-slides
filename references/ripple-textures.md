# Ripple Materials — 涟漪、焦散与水波浮雕

Use this reference when a deck needs water, propagation, resonance, flow, calm,
transparency, or cast-acrylic material cues. Ripple material is an **optional
surface treatment**, not a deck-wide default.

## Visual model

The system translates three related physical effects into a slide-safe form:

- `rings` — concentric waves and restrained interference; best for propagation,
  influence, ecosystems, cause-and-effect, and section transitions.
- `flow` — horizontal undulating relief with a tinted lower field; closest to a
  cast acrylic/resin sign and best for cover, flow, narrative, and closing pages.
- `caustic` — irregular focused-light cells produced by a moving water surface;
  best for premium product, ocean, spatial, optical, and technology themes.

The defining composition rule is **quiet reading zone + active material zone**.
Never place high-contrast ripples directly behind dense text.

## Where to use it

Good hosts: `cover`, `section-divider`, `stat-highlight`, `big-quote`, `closing`.

Avoid by default: `bullets`, `grid-cards`, `comparison`, `timeline`, `chart`, and
other dense reading layouts. A normal 8–14 slide deck should use ripple material
on about 2–4 slides and no more than two patterns.

## Outline interface

```json
"surface": {
  "kind": "ripple",
  "pattern": "rings",
  "zone": "bottom-right",
  "intensity": "hero",
  "motion": "pulse",
  "seed": 17
}
```

- `pattern`: `rings` | `flow` | `caustic`
- `zone`: `bottom` | `bottom-right` | `edge` | `full`
- `intensity`: `subtle` | `hero`
- `motion`: `static` | `drift` | `pulse`
- `seed`: integer; keep it in the outline so repeated builds remain identical.

Every ripple slide receives a CSS fallback. `drift` and `pulse` also use the
shared Three.js canvas for a procedural shader. If the slide already declares a
`three` scene, that scene wins and the ripple remains static; do not combine two
hero motion systems on one page.

## Selection guidance

- Use `rings` with `bottom-right` for a single conceptual focal point.
- Use `flow` with `bottom` to reproduce the calm-top / active-bottom acrylic
  composition while protecting headings and lead text.
- Use `caustic` with `edge` for an optical material halo around a central quote
  or statistic.
- Use `full` only on sparse cover or closing pages, normally at `subtle` intensity.

## Hard constraints

1. Required text remains real HTML and sits above the material layer.
2. Texture colors inherit the deck theme; do not introduce an unrelated water-blue palette.
3. Respect `prefers-reduced-motion`; the CSS layer freezes and Three.js renders one frame.
4. Mobile keeps lower opacity and must still fit the four viewport QA sizes.
5. Do not embed the photographic reference images as production textures unless their license is known.
6. Do not use ripple motion merely to fill empty space; the material must reinforce the page meaning.
7. Omit large background `glyphs` by default on ripple slides. The water field already supplies rhythm;
   if a deck identity truly needs a symbol, use at most one restrained geometric mark such as `◌` or `≈`.
8. Template glass orbs are hidden on ripple slides. Ripple and caustic light already provide depth;
   ordinary non-ripple slides retain their existing orbs.

## Verification

- Check that the main reading zone is visibly calmer than the material zone.
- Confirm `ripple-surface`, the expected `ripple-*` classes, and `data-three="ripple:..."`
  appear in the generated HTML for a dynamic page.
- Build the same outline twice and compare hashes.
- Test reduced-motion and a 375×667 viewport before delivery.
