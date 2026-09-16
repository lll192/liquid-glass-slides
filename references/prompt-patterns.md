# Image Prompt Patterns (Liquid Glass Hero / Cover / Concept)

Use the image model only for decorative visuals (cover hero, section concept art, abstract backgrounds). Keep all readable text in HTML — never request text to be baked into the image.

## General style lock (append to every prompt)
"Apple iOS 26 Liquid Glass style, translucent frosted glass panels, soft backdrop blur and refraction, specular edge highlights, light premium studio, pastel + vivid accent gradient background, minimal, no text, no words, no letters, no watermark."

## Cover hero (concept, not literal)
Pattern:
"[SUBJECT as an elegant abstract glass object / metaphor], floating frosted-glass form with refraction and rim light, over a soft pastel-to-vivid gradient backdrop, Apple keynote light, premium minimal, no text."
Example (AI & math):
"A translucent frosted-glass polyhedron floating above a soft gradient of blue and magenta, light refracting through its edges, faint equations reflected on the surface, Apple iOS 26 Liquid Glass style, premium minimal, no text, no words."

### Floating hero — transparent background (PREFERRED for light pages)
A hero image with a baked-in dark/colored backdrop looks like a heavy card and clashes with the light page. Instead make the object float frameless:

1. Generate on a white/transparent background. Prompt pattern:
   "A single translucent crystal glass [OBJECT] floating in mid-air, clear refractive glass with subtle blue and soft pink iridescence, delicate bright edges, soft studio light, centered composition, isolated on a fully transparent background, no ground, no shadow, no backdrop, Apple Liquid Glass aesthetic, premium minimal, no text, no words, no watermark."
2. Image models often return RGB with a PURE WHITE background even when asked for transparency — verify corners with Pillow (`mode` + corner pixels).
3. Convert white → true alpha in Python (per pixel): `a = 255 - min(r,g,b)`; unblend color `c' = (c - (255-a)) / a * 255` (clamp 0-255). Transparent glass interiors become see-through naturally.
4. Embed as base64, style with `.hero-orb` (see template.html): `drop-shadow` follows the object shape, slow `heroFloat` bob animation. No border, no border-radius, no box-shadow rectangle — the object must look like it floats on the page.

## Section concept illustration
"[CONCEPT] rendered as a glossy glass diorama on a light gradient, soft shadow, one accent tint, editorial, no text."

## Abstract background
"Soft mesh gradient in white to pastel, faint floating glass shards with refraction, lots of negative space, premium, no text."

## Rules
- Always include "no text, no words, no letters" — image models still try to add text.
- Generate one image per distinct visual brief.
- Place via `<img>` with `object-fit:contain` and a `max-height`; never rely on the image for required reading content.
- If the image direction is right but you wanted a label, add the label in an HTML glass caption instead of regenerating.
