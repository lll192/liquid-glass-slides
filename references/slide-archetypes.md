# Slide Archetypes

Map each slide's content to a layout by semantics, not by a fixed order.

| Archetype | Best for | Layout hint |
|---|---|---|
| cover | title / opening | centered big title, optional hero image behind, eyebrow + subtitle |
| single-concept | one idea | one large statement, minimal supporting line |
| two-column | comparison / pros-cons | two glass cards side by side |
| process | steps / how-it-works | horizontal numbered steps |
| grid-cards | 3–6 related items | responsive glass card grid |
| timeline | chronology / evolution | horizontal or 2×3 year grid |
| stat-row | key numbers | 3–4 big-number stats |
| quote | citation / emphasis | large quote, centered, on a glass panel |
| image-feature | one hero visual | full-bleed image with overlaid glass caption |
| takeaway / closing | ending | big gradient title (2.5–3× content size) + halo ring + contact capsules; optional recap — see CLOSING spec below |

## Rhythm guidance
- Avoid two heavy grid slides in a row.
- Alternate statement slides with visual slides.
- Keep title slides short; let the cover and takeaway breathe.
- Use the liquid-glass card style (see visual-dna.md) for floating panels; keep most text on glass over the vivid backdrop.

## Component library (template.html v2) — vary the art form, never repeat one visual for 10+ slides

| Component | Class | Use for |
|---|---|---|
| Glass panel | `.glass` | base card; has built-in sheen sweep + gradient border |
| Tilt card | `.glass.tilt` | grids; hover 3D tilt (JS) |
| Glass orb | `.orb` (`.sym` inside) | floating decorative spheres, split-layout right side, cover accents |
| Explicit grids | `.g2` / `.g3` / `.g4` | **NEVER use `auto-fit`/`minmax` — it collapses to 1 column in narrow preview panes and overflows the viewport** |
| Glass timeline | `.tline` + `.titem` (with `--i`) | chronology, challenge lists; line grows + nodes pop on slide activation |
| SVG ring | `.rings` / `.ring` (`.val` with `--off`) | stats/progress; `stroke-dasharray:283`, `--off = 283×(1−pct)`; always mark 示意 unless data is sourced |
| Step flow | `.flow` (`.step` + `.arrow`) | process/roadmap with nudging arrows |
| Pulse badge | `.qbadge` | open questions, attention items |
| VS badge | `.compare` + `.vs` | two-column comparison |
| Chips | `.chip` | keywords, tags; shimmer sweep |
| Floating glyphs | `.glyphs span` | large translucent symbols (π ∑ ∫ ∞) drifting in the background |
| Mouse parallax | built-in JS | blobs + glyphs + orbs follow the cursor with depth layers |

## Anti-crowding / anti-overflow rules (from real feedback)
1. Grids must be explicit columns (`.g2/.g3/.g4`) with media-query collapse — see above.
2. Card padding ≤ `clamp(.9rem,1.8vw,1.5rem)`; card text ≤ 2 lines.
3. Total content height must fit `100dvh` at 1280×720 and ~1080×620 preview panes.
4. `slide-content` top/bottom padding ≥ `clamp(2.6rem,7vh,4.5rem)` to clear the fixed chrome (brand/counter).
5. Hero images ≤ `min(38vw, 330px)` wide on covers so title + image fit together.
6. No more than 3 consecutive slides using the same primary component.

## CLOSING (ending page) — archetype spec (default: 方案 A 大字排版型)
The closing page is the most-skipped and most-ugly page. Enforce these so it never looks like "one tiny line floating in empty space":

- **Big title, always.** Title size `clamp(2.6rem, 7.5vw, 5.6rem)` (≈2.5–3× the content-page title). Gradient text fill (`#1D1D1F → #0A84FF → #5AC8FA`).
- **Visual anchor.** A centered translucent halo ring (`.closing .halo`) behind the title so the page is filled, not empty. Add 2 floating orbs (`.orb o1/o2`) for life.
- **Contact zone is mandatory.** 3 contact capsules max (email / site / name-team), glass pills (`.closing .contact`), centered below the lead line.
- **Lead line** under the title: one short closing sentence (≤ 1 line on desktop).
- **Reveal stagger**: eyebrow (i:0) → title (i:1) → lead (i:2) → contacts (i:3).
- **No tiny type, no empty page.** If the user wants a recap, add a glass card of 3 takeaway points above the contacts — do not shrink the title to fit it.
- Placeholder contact text (`your@email.com` etc.) is fine; tell the user to swap in real info.
- Alternatives (only if the user asks): B = glass panel recap + CTA button; C = thanks + "take-away 3 points" split.
