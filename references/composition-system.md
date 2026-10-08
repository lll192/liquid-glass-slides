# Composition System — 构成主义简约版式

This reference controls **spatial composition**, while `visual-dna.md` controls
material, color, and motion. The default generated deck uses this system through
top-level `"composition": "constructivist"`.

## Intent

Use the discipline of constructivism—clear hierarchy, asymmetric balance,
geometric order, and purposeful tension—without copying historical propaganda
graphics. The result should feel editorial, modern, quiet, and premium.

## Non-negotiable rules

1. **One visual argument per slide.** Give every slide one dominant title, number,
   image, diagram, or quotation. Supporting elements must be visibly subordinate.
2. **Use a 12-column mental grid.** Default splits are 7:5, 8:4, or 5:7. Avoid
   1:1 symmetry unless the content is a genuine comparison.
3. **Align edges, not centers.** Titles, eyebrow labels, body copy, and panels share
   a strong left edge. Centering is reserved for a deliberate cover, quote, or close.
4. **Build with planes and rules.** Prefer one glass plane containing several
   sections separated by thin rules. Do not turn every idea into its own floating card.
5. **Protect negative space.** Keep roughly 25–40% of the canvas visually quiet.
   Empty space is structural; do not fill it with decorative bubbles or extra copy.
6. **Create controlled contrast.** Pair large/small, dense/empty, opaque/transparent,
   or horizontal/vertical. Use only one such contrast as the page's main tension.
7. **Keep geometry decisive.** Lines, square markers, and rectangular fields are
   preferred. Rounded glass remains the material, not the organizing metaphor.
8. **Limit repeated units.** Three to five items per page is ideal. If more are
   necessary, group them inside one plane or split the slide.

## Typography

- Headlines are short, large, left-aligned, and limited to about 12–16 CJK
  characters per line when possible.
- Eyebrows act as coordinates: small uppercase text followed by a horizontal rule.
- Body copy should normally occupy no more than 42–56 characters per line.
- Numbers can become visual anchors, but must never compete with the title and image
  at the same time.

## Layout patterns

- **Cover:** 7:5 text/image split; without imagery, keep the title in the left 7
  columns and preserve the right side as breathing room.
- **Contents:** one indexed field, not a dashboard of cards. Use rules and sequence.
- **Bullets / timeline:** one glass plane with flat rows and visible rhythm.
- **Grid / KPI:** one shared plane; vary item span or typographic scale rather than
  repeating identical cards.
- **Two-column:** default to 7:5. The smaller side is the visual anchor or summary.
- **Comparison:** one shared comparison plane with a central rule; avoid circular
  “VS” badges and two disconnected cards.
- **Stat / quote / divider:** use one oversized anchor aligned against a compact text
  block. Keep the remainder of the slide quiet.
- **Image / chart:** treat the visual as a large compositional field, not a thumbnail.

## Color and historical restraint

- Preserve the topic-derived palette. Do **not** force red/black, cream paper, or
  other Soviet-era clichés.
- Do not use fake Cyrillic, propaganda symbols, distressed textures, or arbitrary
  diagonal bars.
- One accent rule or block is enough. Geometry should clarify the hierarchy, not
  become decoration.

## Responsive behavior

- Desktop/tablet: retain asymmetric ratios and edge alignment.
- Narrow/mobile: collapse to one column, keep text left-aligned, reduce decorative
  geometry, and preserve order: eyebrow → title → main visual/anchor → explanation.
- Never allow the constructivist treatment to introduce scrolling inside a slide.

## Classic opt-out

Set top-level `"composition": "classic"` to keep the legacy centered/card-forward
treatment. Use this only when matching an older deck or an explicit user request.
