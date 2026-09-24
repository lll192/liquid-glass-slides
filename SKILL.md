---
name: liquid-glass-slides
description: Create Apple iOS 26 Liquid Glass style animated HTML slide decks (presentations) from articles, outlines, notes, Markdown, or rough ideas. Use when the user asks to make a PPT / 幻灯片 / 演示 / 演讲 / 路演 / pitch deck / 课件 / keynote with a liquid-glass / 液态玻璃 / frosted-glass / 玻璃质感 aesthetic (translucent material, backdrop blur and refraction, specular highlights, light-reactive depth), optionally with AI-generated hero or cover illustrations. Produces a single self-contained HTML file that plays fullscreen in a browser with keyboard/wheel/touch navigation and reveal animations. Not for editable PPTX or hand-drawn raster images.
agent_created: true
version: 1.1.0
author: lll192
license: MIT
homepage: https://github.com/lll192/liquid-glass-slides
---

# Liquid Glass Slides

Turn source material into an Apple iOS 26 Liquid Glass style animated HTML slide deck. Optimize for a premium, light-reactive, translucent look: frosted glass panels that blur and refract colorful content behind them, specular highlights along edges, layered depth, and restrained motion. The aesthetic is translated from Apple's native Liquid Glass design language (see the ECC `liquid-glass-design` skill, which targets SwiftUI/UIKit/WidgetKit) into pure CSS — no native Apple APIs are used.

This skill borrows a planning-first workflow (intake → narrative → archetype mapping → style-lock → generate → verify) adapted from the "ian-handdrawn-ppt" methodology, but replaces the image-raster engine with deterministic HTML/CSS so Chinese text is always real, editable, and never garbled. AI image generation is used only for decorative hero/cover/concept illustrations, never for baking text.

## Operating Rule

Default production output is a single self-contained HTML file (inline CSS/JS, zero external dependencies) that runs fullscreen in any modern browser. Each slide is one viewport. When the user asks for a cover or concept illustration, generate it with the image model and reference it via `<img>`; keep all readable text in HTML.

Editable PPTX / PDF export and hand-drawn raster images are out of scope. If the user explicitly needs an editable `.pptx`, suggest the built-in `pptx-generator` instead.

## Resource Map

Load only the references needed for the current task:

- `references/intake.md` — input types, gap diagnosis, clarification rules.
- `references/narrative-planning.md` — deck-type selection and story structures.
- `references/slide-archetypes.md` — semantic mapping from content to slide layouts.
- `references/visual-dna.md` — Apple iOS 26 Liquid Glass visual system (CSS technique) and cross-page style-lock constants.
- `references/output-quality.md` — verification gates for the final deck.
- `references/prompt-patterns.md` — ImageGen prompt templates for liquid-glass hero/cover/concept images.
- `references/image-handling.md` — image intake & processing rules for BOTH AI-generated and user-provided images (transparency normalization, base64 embedding, sizing, placement patterns, optimization).
- `references/ai-imagery.md` — **when/what/where to add AI images**: per-layout guidance, prompt shape, the transparent-background trap + flood-fill cutout, and save+embed flow. Read this whenever you decide to generate imagery.
- `references/echarts-charts.md` — **when/what/where to add ECharts charts**: per-page decision rule (only where real quantitative data exists), chart-type selection, placement, and the auto-applied liquid-glass theme. Read this whenever a slide could benefit from a data visualization.
- `references/three-3d.md` — **when/what/where to add Three.js 3D scenes**: per-page decision rule (only "atmosphere / key-concept" slides benefit), scene presets (`field` / `nebula` / `object`), placement behind content, single-shared-canvas mechanics, and style consistency. Read this whenever a slide could benefit from 3D depth.
- `references/ripple-textures.md` — **when/what/where to add ripple material**: water caustics, concentric rings, and cast-acrylic flow textures with protected reading zones. Read this only when water, propagation, resonance, flow, or transparent-material cues serve the topic.
- `references/theme-palettes.md` — **topic → color theme**: curated 3-color palettes by mood (tech / academic / finance / health / nature / creative / energetic / luxury / calm), the rule that the 3 background blobs and the Three.js particles share the theme, and that body text stays near-black. Read this whenever choosing a deck's color theme.
- `references/outline-schema.md` — the `outline.json` field spec for the one-click build path (`scripts/build.py`): every layout, its fields, and the `{{field}}` / `{{#items}}` placeholder contract.

**Layout snippet library** (`templates/single-page/*.html`): 15 drop-in `<section class="slide">` fragments — `cover`, `toc`, `section-divider`, `bullets`, `two-column`, `grid-cards`, `big-quote`, `stat-highlight`, `kpi-grid`, `timeline`, `comparison`, `image-frame`, `object-float`, `closing`, `chart`. Each ships with demo data and `{{field}}` placeholders; compose a deck by listing them in an outline and running `scripts/build.py`.

**Engine** (`assets/engine.css`, `assets/engine.js`): the extracted viewport-fit base, glass system, animations, and the keyboard/wheel/touch controller. `templates/deck.html` is the shell skeleton (with `/*__ENGINE_CSS__*/`, `<!--__SLIDES__-->`, `/*__ENGINE_JS__*/` markers). `scripts/build.py` inlines the engine into a single self-contained file.

Use `assets/theme-tokens.json` as the compact token file when writing the deck.
Use `assets/template.html` as the starter scaffold: it already contains the mandatory viewport-fit CSS base, the Apple theme variables, and the presentation controller (keyboard/wheel/touch navigation, IntersectionObserver reveals, progress bar, dots, page index, reduced-motion). Clone its `<section class="slide">` blocks to add slides, then fill content.

## Workflow

1. **Ingest material**
   - Read the provided content or attached file (`.md`, `.txt`, `.docx`, `.pdf`, pasted text, or a rough idea).
   - For `.docx` / `.pdf`, extract text only; do not edit or package those files inside this skill.

2. **Run intake and gap diagnosis**
   - Read `references/intake.md`.
   - Determine topic, audience, scenario, target length, and which accent variant to use.
   - Ask at most 1–3 questions only when missing information materially changes the deck. Otherwise proceed with sensible defaults.

3. **Plan the deck narrative**
   - Read `references/narrative-planning.md`.
   - Classify the deck (teaching / persuasive / report / product / knowledge-card).
   - Build a slide-by-slide spine: each slide must carry exactly one main point.

4. **Map each slide to an archetype**
   - Read `references/slide-archetypes.md`.
   - Pick layouts from content semantics, not from a fixed template order. Vary archetypes for rhythm.

5. **Apply visual DNA (style-lock)**
   - Read `references/visual-dna.md` and `assets/theme-tokens.json`.
   - Lock cross-page constants before writing: background tone, card style, glass parameters, title treatment, page-number position, accent color, spacing rhythm, and motion feel.
   - Keep the outer shell fixed; vary only the central content area per slide.

6. **Build output**
   - For planning-only requests, deliver a blueprint with deck type, slide count, and per-slide title / main point / archetype / content blocks / visual brief.
   - For production, choose ONE of two paths:

     **Path A — hand-write (creative / exploratory).** Full control, best for bespoke layouts.
       a. **Decide AI imagery first** (see `references/ai-imagery.md`): cover almost always gets a floating hero; each `section-divider` usually gets a small floating motif; data-dense slides (timeline / comparison / bullets) usually get none. Generate with the image model, then **cut out the background** if the PNG came back as RGB (flood-fill, never naive white→alpha), and inline as base64 `<img>`. Never put required reading text into the image.
       b. Start from `assets/template.html`. Clone `<section class="slide">` blocks, apply `theme-tokens.json`, and fill each slide with real HTML text and semantic structure.
       c. Respect the mandatory viewport-fit base: every `.slide` is `height:100dvh; overflow:hidden`; all type/spacing use `clamp()`; no internal scroll.
       d. Keep image elements `object-fit:contain` with a `max-height` so they never break the viewport.
       e. **If an image needs to be inserted (user-supplied OR AI-generated)**, follow `references/image-handling.md`. First apply the one-line decision rule: **transparent / cut-out / white-bg-convertible image → floating transparent-object placement (`.hero-orb`, no frame, no radius, drop-shadow); image WITH a real/complex background (photo) → concentric-rounded glass frame (`height` cap + `width:auto` fit / `object-fit:cover` + `border-radius:calc(var(--r)*.64)`, see §4b).** For AI-generated images, decide (or proactively ask the user) the intended placement *before* generating, and request the matching background (transparent/white for floating, photographic/scene for framing). Then inline as base64 (no external URLs or local paths), size correctly, and pick the matching placement pattern.

     **Path B — one-click build (reproducible / batch).** Compose an `outline.json` and run the generator.
       a. Read `references/outline-schema.md` for the full field spec. In short: a deck is `{ "title", "theme":{...}, "slides":[ { "layout":"<name>", ...fields } ] }`; each slide maps to a snippet in `templates/single-page/`.
       b. **Add AI imagery**: `cover` and `section-divider` accept an optional `hero` field (image path or data URI) + `hero_alt`. Decide which slides need images per `references/ai-imagery.md`, generate + cut out the backgrounds, save the transparent files under `images/`, and put the **local path** (e.g. `"hero": "images/cover-hero.png"`) in the outline. `build.py` reads the file and **auto-inlines it as a base64 data URI**, so the output stays a single self-contained file while the image also lives on disk.
       c. Run:
          ```bash
          python scripts/build.py --outline my-talk.json --out my-talk.html
          ```
          zero dependencies — only the Python standard library. Output is a single self-contained HTML file (engine CSS/JS inlined, same as Path A).
       d. Layouts auto-handle repetition: pass a list under `items` and the snippet repeats it with staggered reveal; `grid-cards` / `kpi-grid` auto-pick `g2`/`g3`/`g4` by item count. `image-frame` and `object-float` take an image `src` (base64 or local path — build.py inlines it) and apply the concentric-rounded / floating rules above.
       e. **Add ECharts charts where the data earns it**: for any slide carrying a `"chart": { "option": {...} }` field (use layout `chart`), `build.py` inlines `assets/echarts.min.js` automatically and applies the liquid-glass theme (transparent canvas, iOS palette, frosted tooltip). Per `references/echarts-charts.md`, add a chart **only** where the page has real, comparable, quantitative data — never fabricate numbers, and never chart a page that is already text-only or visually complete (timeline, bullets, dividers). The `option` must be pure JSON (no JS functions).
       f. To iterate, edit the JSON and re-run — identical outline always yields an identical deck.
       g. **Ripple fallback is automatic**: when a slide has no Three.js scene, ECharts chart, image, or explicit `surface`, `build.py` adds a deterministic, reading-safe ripple layer. Dense pages receive a subtle static texture; sparse pages may drift gently. Set top-level `"auto_ripple": false` to disable the deck-wide default, or `"auto_ripple": false` on one slide to opt that slide out. Explicit `surface` settings always win. See `references/ripple-textures.md`.

7. **Verify**
   - Read `references/output-quality.md`.
   - Check content accuracy, slide rhythm, visual consistency, Liquid Glass aesthetic match, and no overflow at 1920×1080, 1280×720, 768×1024, and 375×667.
   - Because text is real HTML, Chinese rendering is reliable; still confirm fonts fall back to PingFang SC / Microsoft YaHei on the user's machine.

8. **Deliver**
   - Report the HTML file path, slide count, deck type, any assumptions, and verification performed.
   - Remind the user the deck is editable: text lives in the HTML, and the theme can be retuned by editing the `:root` variables.

## Defaults

- Language: Simplified Chinese (unless the user asks otherwise).
- Audience: general or professionally curious; avoid expert-only jargon unless requested.
- Deck length: 8–12 slides for a talk, 12–20 for a course module, 5–8 for a short idea.
- Output: single self-contained `.html` file.
- Visual fallback: slides without Three.js, ECharts, images, or an explicit surface automatically receive a restrained ripple background; disable with `auto_ripple:false` globally or per slide.
- Aesthetic: Apple iOS 26 Liquid Glass — translucent frosted panels with backdrop blur/refraction, specular edge highlights, and light-reactive depth over a vivid blurred backdrop.
- Accent: vivid system tint (default iOS blue `#0A84FF`); allow a single brand tint on request.
- Illustrations: **proactively add AI-generated images** where they break monotony — a floating hero on the `cover` and a small floating motif on each `section-divider` by default; data-dense layouts (timeline / comparison / bullets) stay text/CSS-only. Decide placement *before* generating and cut out backgrounds when the model ignores transparency (see `references/ai-imagery.md`).
- Charts: **proactively add ECharts visualizations only where a slide carries real, comparable, quantitative data** (trends, category comparisons, proportions, multi-dimension ability radar). Scan every page; add charts selectively, never on every slide. All charts auto-inherit the liquid-glass theme. Do not invent numbers to fill a chart (see `references/echarts-charts.md`). **This is fully automatic for the user: the AI does the scanning, decides placement, writes the `chart` fields into the outline, and runs build.py — the user never writes code or fields.**
- 3D / Three.js: **proactively add live 3D backgrounds only where they strengthen the theme or visual impact** — `orbs` (glass bubbles), `petals` (drifting petals), `waves` (sine ribbons), `object` (rotating wireframe solid), `network` (nodes + links), and the **particle storm** `field` / `nebula` (dense drifting points, homepage only). Rule: **`field` / `nebula` are reserved for the `cover` slide**; every other slide uses the calm presets. Best hosts: `cover` (storm) / `section-divider` / `stat-highlight` / `closing` (calm); never on text-dense reading slides. One shared WebGL canvas swaps scenes by visible slide; the library inlines automatically only when a `three` field exists; style is auto-tuned to the light liquid-glass theme and degrades to a static gradient if WebGL is unavailable (see `references/three-3d.md`). **Also fully automatic for the user: the AI decides which pages, picks the scene type, writes the `three` fields, and builds — the user never writes code or fields.**
- 3D scenes: **proactively add Three.js 3D only on "atmosphere / key-concept" slides** — cover, section dividers, a key concept page, closing. **Particle storms `field` / `nebula` → cover ONLY** (build.py remaps them on other slides to a calm preset); non-cover pages use `orbs` / `petals` / `waves` / `object` (offset right) / `network`. Never on pure-info slides (bullets/grid-cards/timeline/comparison/two-column/chart); never on every slide. All scenes render BEHIND the text via one shared canvas and auto-inherit the iOS pastel palette. See `references/three-3d.md`. **Also fully automatic for the user: the AI scans, picks the scene, writes the `three` field, and builds — zero user code.**
- Theme (auto color system): **every deck gets a coherent color theme derived from its topic.** Pick a palette of 3 best-fit colors (`colors`) for the three blurred background blobs AND the Three.js particle field, plus one accent (`accent`) for headings / eyebrows / links / glows; body text stays near-black for readability. Write the `theme` object into the outline and `build.py` derives every CSS variable and forwards the 3 colors to Three.js. See `references/theme-palettes.md` for curated palettes by topic mood. **Fully automatic for the user: the AI chooses the palette, writes the `theme` field, and builds — the user never picks colors or writes code.**

## Final Response

When finished, report:

- The created HTML file path.
- Page count and deck type.
- Any important assumptions.
- Verification performed and any remaining risks.

For planning-only outputs, provide the blueprint directly and list the critical questions to answer before production.
