# Theme Palettes — auto color system for liquid-glass-slides

**What it is.** Every deck gets one coherent color theme chosen from its topic.
The AI (not the user) writes a `theme` object into the outline:

```json
"theme": { "colors": ["#0A84FF","#5E5CE6","#30D158"], "accent": "#0A84FF" }
```

`build.py` then derives everything:
- `colors[0..2]` → the **three blurred background blobs** *and* the **Three.js
  particle palette** (so 3D and backdrop always match).
- `accent` → `--accent`: eyebrows, emphasis, links, dots, chips, glows.
- Body text stays near-black (`--ink`) — only *emphasis* uses the accent. This keeps
  readability high on the light liquid-glass backdrop.

If `theme` is omitted, a balanced blue / red / green default is applied.

> **Fully automatic for the user.** The AI scans the topic, picks the best palette
> below (or a bespoke one), writes the `theme` field, and runs `build.py`. The user
> never chooses colors and never writes code.

---

## Rules for picking a palette

1. **Three distinct, sufficiently-saturated colors.** They must read clearly on a
   *light* backdrop — avoid three near-greys or three pastels that blur into white.
2. **The accent should be the most "anchor" color** — usually a confident blue/
   indigo/green. It carries the smallest amount of text, so it can be the boldest.
3. **Match the topic mood**, not the literal subject. A "security" talk and a
   "wellness" talk should feel different even if both are "tech".
4. Prefer the curated palettes below; only deviate when the brand demands a specific hue.

---

## Curated palettes (3 colors + suggested accent)

| Mood / topic | colors[0] | colors[1] | colors[2] | accent (suggested) |
|---|---|---|---|---|
| Tech / product | `#0A84FF` | `#64D2FF` | `#30D158` | `#0A84FF` |
| Academic / math / proof | `#0A84FF` | `#5E5CE6` | `#30D158` | `#0A84FF` |
| Finance / data | `#0A84FF` | `#30D158` | `#FF9F0A` | `#0A84FF` |
| Health / medical | `#30D158` | `#64D2FF` | `#0A84FF` | `#30D158` |
| Nature / sustainability | `#30D158` | `#0BD1A0` | `#64D2FF` | `#30D158` |
| Creative / design | `#FF375F` | `#BF5AF2` | `#0A84FF` | `#BF5AF2` |
| Energetic / marketing | `#FF9F0A` | `#FF375F` | `#FFD60A` | `#FF9F0A` |
| Luxury / premium | `#1D1D1F` | `#B58A2E` | `#8E8E93` | `#B58A2E` |
| Calm / editorial | `#5E5CE6` | `#64D2FF` | `#BF5AF2` | `#5E5CE6` |

> For the **Luxury** palette the three blobs are dark/neutral; the gold accent still
> pops against the light glass. If a brand color is required, drop it into `colors[0]`
> and set `accent` to it.

---

## Self-check before building

- [ ] Exactly 3 colors provided (more/fewer → build.py pads/truncates, but don't rely on it).
- [ ] All three read clearly on white.
- [ ] Accent is the strongest/most "anchor" hue and is used sparingly (emphasis only).
- [ ] Body text is near-black, not colored.
- [ ] Particles (if any `three` field exists) visibly share the blob colors.
