# AI Imagery — when, what, where

This skill can proactively enrich a deck with AI-generated images instead of leaving every
slide text-only. This reference defines the **decision framework** so the result looks
intentional, not random. It applies to BOTH Path A (hand-write) and Path B (build.py).

## 0. First principles (order matters)

1. **Content first.** The image must be **semantically tied to the slide's actual topic**
   (a proof tree for a theorem-prover talk, a workshop scene for a craft talk, a data
   network for an infrastructure talk). **Never** generate generic "abstract geometry"
   filler that could sit on any deck — that reads as random decoration.
2. **Complete and beautiful.** Generate a **complete, well-composed scene or object** —
   one clear focal subject, finished edges, coherent lighting. Avoid prompts that produce
   fragmented / shattered / swarming elements.
3. **Images break monotony; they never carry required reading text.** All explanations
   stay in HTML. Ask for "no text / no letters" — models garble baked-in text, especially
   CJK.
4. **Default placement = concentric-rounded glass frame** (`.photo-frame`). Generate a
   scene with its own background and frame it. This is robust: no cutout, no alpha
   dependency, works for translucent and photographic content alike.
5. **Floating cutout (`hero-orb`) is the EXCEPTION**, not the default. Only use it when
   ALL hold: the object is solid/opaque with a simple silhouette, clearly separates from
   the background, and the cutout passes the sanity check in §3. If in doubt → frame it.

## 1. Which slides get an image (per-layout guidance)

| Layout | Add AI image? | Placement | What to generate |
|---|---|---|---|
| `cover` | **Almost always** | framed hero (`hero` field) | one signature scene/object **on-topic** |
| `section-divider` | **Usually (1 per divider)** | framed motif (`hero` field) | a scene echoing the section's specific theme |
| `bullets` / `two-column` | Rarely | — | only if a concrete visual aids the point |
| `grid-cards` | Optional | per-card icon (advanced) | skip unless asked; cards already vary rhythm |
| `stat-highlight` | Optional | small framed/decorative | a subtle on-topic visual; keep the number dominant |
| `timeline` / `comparison` | No | — | these are data-dense; images add clutter |
| `big-quote` | Optional | framed, low emphasis | an on-topic scene behind/beside the quote |
| `closing` | Optional | framed or none | a calm echo of the cover image |
| `image-frame` / `object-float` | By definition | framed / floating | the image IS the slide |

Rule of thumb: **cover + one motif per section divider** is the sweet spot for an 8–14
slide deck. Adding more risks clutter and burns generation credits.

## 2. What to generate (prompt shape)

- **Match the deck's topic in the prompt itself.** Name the concrete subject
  ("a glowing proof tree", "an open math notebook with compass constructions", "a server
  rack rendered as glass") — not just a style.
- Style: clean, minimal, Apple-keynote adjacent; light pastel background that harmonizes
  with the deck's `#F5F5F7` aesthetic; one focal subject; soft studio lighting;
  "no text, no letters, no words".
- Prefer **scene-with-background** compositions (framed later) over isolated objects.
- Keep it iconic, not literal clip-art.

### Worked examples (topic → prompt)

| Deck topic | Good prompt core |
|---|---|
| Lean / formal proofs | "glowing logical proof tree, luminous blue nodes connected by thin light branches, soft pastel studio background" |
| Geometry of design | "open notebook with compass-drawn circles and triangles in blue ink, brass drafting compass, white desk, morning light" |
| Data infrastructure | "translucent glass server towers with glowing data streams, pastel gradient background" |

## 3. If you really need a floating cutout (fragile — verify)

Most text-to-image models **ignore `background: "transparent"`** and return an **RGB image
with a light studio background**. Do NOT assume the PNG has an alpha channel — verify:

```python
from PIL import Image
im = Image.open(p)
print(im.mode)            # RGBA/LA => real alpha; RGB => background present
```

If it is RGB, a naive white→alpha (`a = 255 - min(r,g,b)`) **erodes translucent glass
objects**, and even edge flood-fill **leaks into semi-transparent bodies** (result: a
hollow shell of fragments — a known failure). Requirements for a usable cutout:

- object is **solid / opaque**, simple silhouette, clearly darker or more saturated
  than the background;
- after flood-fill, the kept silhouette is a **solid blob (≈25–40% of canvas)** — if it
  comes out as scattered fragments or <15%, **do not ship it**; fall back to the glass
  frame (§0.4) instead.

## 4. Save + embed (Path B — build.py handles embedding)

1. Generate → save the file under `images/` (e.g. `images/lean-cover.png`).
2. In `outline.json`, reference the **local path**: `"hero": "images/lean-cover.png"`.
3. `build.py` automatically reads the file and inlines it as a `data:image/...;base64,...`
   URI, so the final HTML is still a **single self-contained file** while the file also
   lives on disk. No manual base64 needed.

(Path A: inline the base64 `src` yourself, or reference the local path and accept that the
HTML is no longer portable without the folder.)

## 5. Cost note

Image generation consumes separate credits (≈ 5–10 per image). Default to **cover + one
motif per divider** unless the user asks for more.
