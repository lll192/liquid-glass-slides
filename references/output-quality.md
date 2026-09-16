# Output Quality Gates

Verify before delivery.

## Content
- Each slide has exactly one clear main point.
- Chinese text is accurate; no invented facts or fake statistics (label illustrative charts as 示意).
- Spelling / terminology consistent.

## Structure & rhythm
- Cover present; takeaway present.
- Archetype variety; no two heavy grids back-to-back.

## Visual consistency (Liquid Glass)
- Background, glass parameters, accent, specular highlight, and edge-light treatment identical across slides.
- Title treatment consistent.
- Glass panels actually sit over the vivid blurred backdrop — never over a flat opaque fill (that kills the refraction).

## Viewport fit (critical)
Test at: 1920×1080, 1280×720, 768×1024, 375×667.
- Every `.slide` fits one viewport, no internal scroll.
- No horizontal scrollbar.
- Type scales via `clamp()`; never shrunk below readable size to force a fit — split the slide instead.

## Technical
- Single self-contained HTML, inline CSS/JS, zero external deps (Google/Fontshare fonts allowed via `<link>`).
- Keyboard / wheel / touch navigation works.
- Reduced-motion respected.
- Images `object-fit:contain` with `max-height`.
