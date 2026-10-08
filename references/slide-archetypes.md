# Slide Archetypes

Map each slide's content to a layout by semantics, not by a fixed order.

| Archetype | Best for | Layout hint |
|---|---|---|
| cover | title / opening | left-anchored 7:5 composition, optional hero field, eyebrow + subtitle |
| single-concept | one idea | one oversized statement against deliberate quiet space |
| two-column | explanation + example / summary | asymmetric 7:5 split; only the smaller anchor needs glass |
| process | steps / how-it-works | horizontal numbered steps |
| grid-cards | 3–6 related items | one shared glass plane with ruled cells; avoid detached cards |
| timeline | chronology / evolution | one vertical sequence inside a shared plane |
| stat-row | key numbers | one dominant number or one ruled KPI field |
| quote | citation / emphasis | large left-aligned quote with one accent rule |
| image-feature | one hero visual | 4:8 text/image field; let the image carry real area |
| takeaway / closing | ending | big gradient title (2.5–3× content size) + halo ring + contact capsules; optional recap — see CLOSING spec below |

## Rhythm guidance
- Avoid two heavy grid slides in a row.
- Alternate statement slides with visual slides.
- Keep title slides short; let the cover and takeaway breathe.
- Use one dominant axis and one visual anchor per slide.
- Prefer one shared glass plane with internal rules; do not make every paragraph a card.
- Preserve 25–40% quiet space whenever the content allows it.

## Component library (template.html v2) — vary the art form, never repeat one visual for 10+ slides

| Component | Class | Use for |
|---|---|---|
| Glass plane | `.glass.construct-plane` | one organizing field with sheen + border; divide internally with rules |
| Composition shell | `.composition-shell` | shared left edge and maximum editorial measure |
| Asymmetric split | `.construct-split` | default 7:5 text/anchor relationship |
| Ruled grid | `.construct-grid` + `.construct-grid-item` | related items inside one plane, not detached cards |
| Explicit grids | `.g2` / `.g3` / `.g4` | **NEVER use `auto-fit`/`minmax` — it collapses to 1 column in narrow preview panes and overflows the viewport** |
| Glass timeline | `.tline` + `.titem` (with `--i`) | chronology, challenge lists; line grows + nodes pop on slide activation |
| SVG ring | `.rings` / `.ring` (`.val` with `--off`) | stats/progress; `stroke-dasharray:283`, `--off = 283×(1−pct)`; always mark 示意 unless data is sourced |
| Step flow | `.flow` (`.step` + `.arrow`) | process/roadmap with nudging arrows |
| Section index | `.qbadge` | rectangular chapter coordinate in constructivist mode |
| Comparison field | `.construct-compare` + `.vs` | one divided plane; `VS` is a small coordinate label |
| Chips | `.chip` | keywords, tags; shimmer sweep |
| Floating glyphs | `.glyphs span` | optional topic-specific symbol only when explicitly useful; empty by default |
| Mouse parallax | built-in JS | background blobs follow the cursor with restrained depth |

## Anti-crowding / anti-overflow rules (from real feedback)
1. Grids must be explicit columns (`.g2/.g3/.g4`) with media-query collapse — see above.
2. Repeated items share one plane. Internal cell padding ≤ `clamp(.9rem,2.1vw,1.55rem)`; item text ≤ 2 lines.
3. Total content height must fit `100dvh` at 1280×720 and ~1080×620 preview panes.
4. `slide-content` top/bottom padding ≥ `clamp(2.6rem,7vh,4.5rem)` to clear the fixed chrome (brand/counter).
5. Cover hero occupies the right 5 columns and may reach `520px`; it collapses below copy on narrow screens.
6. No more than 3 consecutive slides using the same primary component.

## CLOSING (ending page) — archetype spec (default: 方案 A 大字排版型)
The closing page is the most-skipped and most-ugly page. Enforce these so it never looks like "one tiny line floating in empty space":

- **Big title, always.** Title size `clamp(2.6rem, 7.5vw, 5.6rem)` (≈2.5–3× the content-page title). Gradient text fill (`#1D1D1F → #0A84FF → #5AC8FA`).
- **Visual anchor.** A centered translucent halo ring (`.closing .halo`) provides the final visual release. Decorative orbs are suppressed by default in constructivist mode.
- **Contact zone is mandatory.** 3 contact capsules max (email / site / name-team), glass pills (`.closing .contact`), centered below the lead line.
- **Lead line** under the title: one short closing sentence (≤ 1 line on desktop).
- **Reveal stagger**: eyebrow (i:0) → title (i:1) → lead (i:2) → contacts (i:3).
- **No tiny type, no empty page.** If the user wants a recap, add a glass card of 3 takeaway points above the contacts — do not shrink the title to fit it.
- Placeholder contact text (`your@email.com` etc.) is fine; tell the user to swap in real info.
- Alternatives (only if the user asks): B = glass panel recap + CTA button; C = thanks + "take-away 3 points" split.
