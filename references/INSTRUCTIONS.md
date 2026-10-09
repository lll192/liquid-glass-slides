# Liquid Glass Slides — Instructions (model-agnostic core)

> This is the **single source of truth** for operating the `liquid-glass-slides`
> package. It is intentionally platform-neutral: it works the same whether the
> operator is a human, Claude Code, OpenAI Codex, Gemini CLI, Cursor, or any
> other agent that can read Markdown and run Python.
>
> Platform adapter files (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, and
> `.cursor/rules/*.mdc`) point here. `SKILL.md` is the installable skill
> entrypoint used by WorkBuddy, Codex-compatible skill loaders, and similar
> agents; keep its shared behavior consistent with this model-agnostic core.

---

## What this package does

Turn source material into an Apple iOS 26 **Liquid Glass** style animated HTML
slide deck. The aesthetic is a premium, light-reactive, translucent look: frosted
glass panels that blur and refract colorful content behind them, specular
highlights along edges, layered depth, and restrained motion — translated from
Apple's native Liquid Glass design language into pure CSS, no native Apple APIs.

The pipeline borrows a **planning-first workflow**
(intake → narrative → archetype mapping → style-lock → generate → verify), but
replaces image-raster generation with deterministic HTML/CSS so text (including
Chinese) is always real, selectable, and never garbled. AI image generation is
used only for decorative hero/cover/concept illustrations, never for baking text
into pixels.

## Operating Rule

Default production output is a **single self-contained HTML file** (inline
CSS/JS, zero external dependencies) that runs fullscreen in any modern browser.
Each slide is one viewport. When a cover or concept illustration is wanted,
generate it with an image model and reference it via `<img>`; keep all readable
text in HTML.

Editable PPTX / PDF export and hand-drawn raster images are out of scope. If the
user explicitly needs an editable `.pptx`, suggest a dedicated PPTX tool instead.

## Resource Map

Load only the references needed for the current task:

- `references/intake.md` — adaptive pre-generation form, gap diagnosis, and confirmation rules.
- `references/design-brief.md` — the stable `brief.json` contract between intake and slide planning.
- `references/source-intake.md` — conditional upload, source receipt, and content-coverage workflow for full or partial copy.
- `references/source-manifest.md` — the `source-manifest.json` provenance and handling contract.
- `references/narrative-planning.md` — deck-type selection and story structures.
- `references/narrative-director.md` — story roles, audience questions, speaker intent, emotional pacing, and transitions.
- `references/slide-archetypes.md` — semantic mapping from content to slide layouts.
- `references/visual-coverage-planner.md` — meaningful visual coverage, evidence rules, and structured visual layouts.
- `references/visual-dna.md` — Apple iOS 26 Liquid Glass visual system (CSS technique) and cross-page style-lock constants.
- `references/composition-system.md` — default constructivist-minimal layout system: asymmetric grid, edge alignment, quiet space, shared planes, and anti-dashboard rules.
- `references/layout-intelligence.md` — automatic composition variants, density classes, long-title handling, and overfull-warning response.
- `references/typography-system.md` — editorial Chinese/Latin/mixed-script hierarchy, semantic title length, line breaking, and long-title response.
- `references/visual-intelligence.md` — image orientation and chart-semantic profiling, adaptive visual ratios, alt-text checks, and chart takeaway rules.
- `references/quality-intelligence.md` — deck-level rhythm and visual-weight auditing plus runtime DOM fit inspection.
- `references/content-intelligence.md` — claim-led slide copy, long-block warnings, source fidelity, and presenter notes.
- `references/output-quality.md` — verification gates for the final deck.
- `references/prompt-patterns.md` — ImageGen prompt templates for liquid-glass hero/cover/concept images.
- `references/image-handling.md` — image intake & processing rules for BOTH AI-generated and user-provided images (transparency normalization, base64 embedding, sizing, placement patterns, optimization).
- `references/ai-imagery.md` — **when/what/where to add AI images**: per-layout guidance, prompt shape, the transparent-background trap + flood-fill cutout, and save+embed flow. Read this whenever you decide to generate imagery.
- `references/echarts-charts.md` — **when/what/where to add ECharts charts**: per-page decision rule (only where real quantitative data exists), chart-type selection, placement, and the auto-applied liquid-glass theme. Read this whenever a slide could benefit from a data visualization.
- `references/three-3d.md` — **when/what/where to add Three.js scenes**: cover-only particles plus restrained `petals`, `waves`, and semantic `network`. `object` and `orbs` are retired and render nothing.
- `references/ripple-textures.md` — **when/what/where to add ripple material**: water caustics, concentric rings, and cast-acrylic flow textures; quiet-zone composition, per-slide `surface` fields, static fallback, and dynamic shared-canvas behavior. Read this when water, propagation, resonance, flow, or transparent-material cues serve the topic.
- `references/theme-palettes.md` — **topic → color theme**: curated 3-color palettes by mood (tech / academic / finance / health / nature / creative / energetic / luxury / calm), the rule that the 3 background blobs and the Three.js particles share the theme, and that body text stays near-black. Read this whenever choosing a deck's color theme.
- `references/outline-schema.md` — the `outline.json` field spec for the one-click build path (`scripts/build.py`): every layout, its fields, and the `{{field}}` / `{{#items}}` placeholder contract.
- `references/deck-schema-v2.json` — the machine-readable v2 deck protocol shared by agents, validators, and future API/MCP clients.
- `references/production-pipeline.md` — the recoverable multi-stage CLI, artifact snapshots, status model, failure recovery, and delivery handoff.
- `references/pipeline-state-schema-v1.json` — the machine-readable job-state contract for CLI, Web, API, and MCP clients.
- `references/content-director.md` — deterministic narrative diagnosis, per-slide revision actions, deck metrics, and safe metadata completion.
- `references/agent-cli.md` — stable cross-platform command contract, JSON response envelope, exit codes, and integration rules for AI clients.
- `references/agent-response-schema-v1.json` — machine-readable JSON Schema for every Agent CLI response.
- `references/mcp-server.md` — local MCP stdio server, six presentation tools, workspace boundary, and client configuration.

**Layout snippet library** (`templates/single-page/*.html`): 18 drop-in
`<section class="slide">` fragments — `cover`, `toc`, `section-divider`,
`bullets`, `two-column`, `grid-cards`, `big-quote`, `stat-highlight`,
`kpi-grid`, `timeline`, `comparison`, `image-frame`, `object-float`, `closing`,
`chart`, `data-table`, `process-flow`, `concept-map`. Each ships with demo data and `{{field}}` placeholders; compose a deck
by listing them in an outline and running `scripts/build.py`.

**Engine** (`assets/engine.css`, `assets/engine.js`): the extracted viewport-fit
base, glass system, animations, and the keyboard/wheel/touch controller.
`templates/deck.html` is the shell skeleton (with `/*__ENGINE_CSS__*/`,
`<!--__SLIDES__-->`, `/*__ENGINE_JS__*/` markers). `scripts/build.py` inlines
the engine into a single self-contained file.

Use `assets/theme-tokens.json` as the compact token file when writing the deck.
Use `assets/template.html` as the starter scaffold: it already contains the
mandatory viewport-fit CSS base, the Apple theme variables, and the presentation
controller (keyboard/wheel/touch navigation, IntersectionObserver reveals,
progress bar, dots, page index, reduced-motion). Clone its
`<section class="slide">` blocks to add slides, then fill content.

## Workflow

1. **Ingest material**
   - Read the provided content or attached file (`.md`, `.txt`, `.docx`, `.pdf`, pasted text, or a rough idea).
   - For `.docx` / `.pdf`, extract text only; do not edit or package those files inside this package.

2. **Pass the Brief Gate**
   - Read `references/intake.md` and inventory information already present before asking anything.
   - If the request is usable, take the fast path: create `brief.json`, show one compact confirmation card, state non-obvious assumptions, and continue without forcing another reply.
   - If several consequential fields are missing, send the six-field compact form once. If only one decision blocks planning, ask only that focused question. Never ask the user to select ECharts, Three.js, or ripple technology.
   - Read `references/design-brief.md`, save the structured brief beside the future outline, and run `python scripts/validate_brief.py brief.json`.
   - Pause for explicit confirmation only when an unresolved choice materially changes claims, audience, brand, confidentiality, cost, or output scope. A completed form or “直接生成” instruction confirms the supplied fields.

3. **Pass the Source Gate when material is supplied**
   - If `content.mode` is `supplied` or `assisted`, read `references/source-intake.md`. Skip this gate for `agent-led` work unless the user also provides files.
   - Accept attached `.docx` / `.pdf` / `.md` / `.txt`, accessible local paths, pasted text, and separately uploaded visual assets. Text and images may map to the same section; never require the user to merge them first or bake readable copy into an image.
   - Classify one primary source plus any supporting, data, or visual sources; capture processing level, protected content, and requested AI additions.
   - Read `references/source-manifest.md`, create `source-manifest.json` and `content-map.md`, then run `python scripts/validate_source_manifest.py source-manifest.json`.
   - Do not start the outline while a required source is unreadable, source priority is ambiguous, or a material conflict remains hidden.

4. **Plan the deck narrative**
   - Read `references/narrative-planning.md` and `references/narrative-director.md`.
   - Classify the deck (teaching / persuasive / report / product / knowledge-card).
   - Build a slide-by-slide spine: each slide carries one `main_point` and a deliberate `story_role`; add `audience_question`, `speaker_intent`, `transition`, and `emotion` for important beats.
   - Read `references/content-intelligence.md`; separate the audience-facing claim and essential evidence from spoken detail stored in `speaker_notes`. For each substantive slide, write about 80–130 Chinese characters (target roughly 100) of natural, page-specific spoken language that refers to the visible content and leads into the transition.

5. **Map each slide to an archetype**
   - Read `references/slide-archetypes.md` and `references/visual-coverage-planner.md`.
   - Pick layouts from content semantics, not from a fixed template order. Vary archetypes for rhythm.
   - Add a `visual_plan` to content slides. Use meaningful visuals for explanation or evidence; do not count ripple or Three.js atmosphere as information coverage.
   - Read `references/layout-intelligence.md`. Keep `variant:auto` unless semantics require a fixed reading order. Revise or split every slide reported as `overfull`.

6. **Apply visual DNA (style-lock)**
   - Read `references/visual-dna.md`, `references/composition-system.md`, and `assets/theme-tokens.json`.
   - Read `references/typography-system.md`; use one-claim headings and resolve extra-long-title warnings unless wording is protected.
   - Lock background, glass material, title treatment, page number, accent, spacing, motion, dominant axis, and asymmetry ratio.
   - Default to `"composition":"constructivist"`: align to edges, prefer one shared glass plane over repeated cards, preserve 25–40% quiet space, and center only with a clear reason. Use `"classic"` for legacy compatibility or an explicit request.
   - Keep the outer shell fixed; vary only the central content area per slide.

7. **Build output**
   - For planning-only requests, deliver a blueprint with deck type, slide count, and per-slide title / main point / archetype / content blocks / visual brief.
   - For production, choose ONE of two paths:

     **Path A — hand-write (creative / exploratory).** Full control, best for bespoke layouts.
       a. **Decide AI imagery first** (see `references/ai-imagery.md`): cover almost always gets a floating hero; each `section-divider` usually gets a small floating motif; data-dense slides (timeline / comparison / bullets) usually get none. Generate with the image model, then **cut out the background** if the PNG came back as RGB (flood-fill, never naive white→alpha), and inline as base64 `<img>`. Never put required reading text into the image.
       b. Start from `assets/template.html`. Clone `<section class="slide">` blocks, apply `theme-tokens.json`, and fill each slide with real HTML text and semantic structure.
       c. Respect the mandatory viewport-fit base: every `.slide` is `height:100dvh; overflow:hidden`; all type/spacing use `clamp()`; no internal scroll.
       d. Keep image elements `object-fit:contain` with a `max-height` so they never break the viewport.
       e. **If an image needs to be inserted (user-supplied OR AI-generated)**, follow `references/image-handling.md`. First apply the one-line decision rule: **transparent / cut-out / white-bg-convertible image → floating transparent-object placement (`.hero-orb`, no frame, no radius, drop-shadow); image WITH a real/complex background (photo) → concentric-rounded glass frame (`height` cap + `width:auto` fit / `object-fit:cover` + `border-radius:calc(var(--r)*.64)`, see §4b).** For AI-generated images, decide (or proactively ask the user) the intended placement *before* generating, and request the matching background (transparent/white for floating, photographic/scene for framing). Then inline as base64 (no external URLs or local paths), size correctly, and pick the matching placement pattern.

     **Path B — one-click build (reproducible / batch).** Compose a v2 `outline.json` and run the generator.
       a. Read `references/outline-schema.md` and `references/deck-schema-v2.json`. Every deck requires stable `schema_version`, `deck_id`, and per-page `slide_id` values: `{ "schema_version":"2.0", "deck_id":"my-talk", "title":"...", "lang":"zh-CN", "slides":[ { "slide_id":"opening-question", "layout":"cover", ...fields } ] }`. Never derive identity from the current page number. Validate with `python scripts/slides.py --json validate my-talk.json`; migrate older outlines with `python scripts/migrate_outline.py old.json --out new.json`.
       b. **Add AI imagery**: `cover` and `section-divider` accept an optional `hero` field (image path or data URI) + `hero_alt`. Decide which slides need images per `references/ai-imagery.md`, generate + cut out the backgrounds, save the transparent files under `images/`, and put the **local path** (e.g. `"hero": "images/cover-hero.png"`) in the outline. `build.py` reads the file and **auto-inlines it as a base64 data URI**, so the output stays a single self-contained file while the image also lives on disk.
          > **Offline / sandbox note:** `build.py` inlines `echarts.min.js` and `three.min.js` from `assets/` — no network is required at build time. For images, prefer **local file paths** (relative to the outline) or `data:` URIs; avoid `http(s)://` URLs unless the build environment has network access.
       c. Run:
          ```bash
          python scripts/slides.py --json validate my-talk.json
          python scripts/slides.py --json build --outline my-talk.json --out my-talk.html
          ```
          For production or cross-agent work, prefer the recoverable pipeline described in `references/production-pipeline.md`:
          ```bash
          python scripts/slides.py --json run --outline my-talk.json --out dist/my-talk.html
          ```
          It materializes storyboard, visual-plan, QA-report, and pipeline-state JSON files beside the HTML. Continue from `needs_revision` by correcting the reported artifact and running the same command again.
          zero dependencies — only the Python standard library. Output is a single self-contained HTML file (engine CSS/JS inlined, same as Path A). Read `references/agent-cli.md` for the stable JSON contract and exit codes.
       d. Layouts auto-handle repetition: pass a list under `items` and the snippet repeats it with staggered reveal; `grid-cards` / `kpi-grid` auto-pick `g2`/`g3`/`g4` by item count. `image-frame` and `object-float` take an image `src` (base64 or local path — build.py inlines it) and apply the concentric-rounded / floating rules above.
       e. **Add ECharts charts where the data earns it**: for any slide carrying a `"chart": { "option": {...} }` field (use layout `chart`), `build.py` inlines `assets/echarts.min.js` automatically and applies the liquid-glass theme (transparent canvas, iOS palette, frosted tooltip). Per `references/echarts-charts.md`, add a chart **only** where the page has real, comparable, quantitative data — never fabricate numbers, and never chart a page that is already text-only or visually complete (timeline, bullets, dividers). The `option` must be pure JSON (no JS functions).
       f. To iterate, edit the JSON and re-run — identical outline always yields an identical deck.
       g. **Ripple fallback is automatic**: when a slide has no Three.js scene, ECharts chart, image, or explicit `surface`, `build.py` adds a deterministic ripple layer. Dense reading pages receive a subtle static texture localized away from text; sparse pages may drift gently. Use top-level or per-slide `"auto_ripple": false` to opt out. Explicit `surface` settings always win. See `references/ripple-textures.md`.
       h. **Layout intelligence is automatic**: content shape selects split direction, list rhythm, grid hierarchy, and media side; density classes tune spacing within safe limits. `overfull` requires copy revision or a slide split, not unlimited font shrinking.
       i. **Visual intelligence is automatic**: image dimensions and ECharts series semantics adjust visual ratios and chart height. Resolve missing-asset, alt-text, and chart-takeaway warnings before delivery.
       j. **Quality intelligence is automatic**: resolve build-time rhythm warnings, then inspect `window.__LG_BUILD_REPORT__.runtime` at the delivery viewport. Add `?qa=1` only for the visible inspection badge.
       k. **Content intelligence is automatic**: resolve generic-title and long-display-block warnings. Use `main_point` for planning and `speaker_notes` for presenter-only explanation; press `N` to edit notes, which auto-save in the local browser.
       l. **Narrative Director is automatic**: explicit or inferred story roles and emotions shape the arc; the live presenter panel shows only the main point and transition while the full planning cues remain in reports. Resolve flat-role warnings intentionally.
       m. **Visual Coverage Planner is automatic**: it checks required visual plans, chart/table provenance, meaningful visual coverage, and text-only runs. Use `data-table`, `process-flow`, and `concept-map` where their semantics fit.
       n. **Content Director is automatic in the production pipeline**: inspect its per-slide findings before delivery. Safe completion may add only inferred structural metadata; visible copy, speaker prose, facts, and evidence still require editorial judgment.

8. **Verify**
   - Read `references/output-quality.md`.
   - Check content accuracy, slide rhythm, visual consistency, Liquid Glass aesthetic match, and no overflow at 1920×1080, 1280×720, 768×1024, and 375×667.
   - Because text is real HTML, Chinese rendering is reliable; still confirm fonts fall back to PingFang SC / Microsoft YaHei on the user's machine.

9. **Deliver**
   - Report the HTML file path, companion brief path, source manifest/content map when created, slide count, deck type, any assumptions, and verification performed.
   - Remind the user the deck is editable: text lives in the HTML, and the theme can be retuned by editing the `:root` variables.

## Defaults

- Language: Simplified Chinese (unless the user asks otherwise).
- Intake: adaptive Brief Gate; never repeat questions already answered in the request or source material.
- Brief: save a validated `brief.json` before outline planning; keep assumptions and unresolved factual dependencies explicit.
- Sources: for full or partial user copy, pass the Source Gate and preserve provenance; skip it for pure `agent-led` work without files.
- Audience: general or professionally curious; avoid expert-only jargon unless requested.
- Deck length: 8–12 slides for a talk, 12–20 for a course module, 5–8 for a short idea.
- Output: single self-contained `.html` file.
- Visual fallback: slides without Three.js, ECharts, images, or an explicit surface automatically receive a restrained ripple background; disable with `auto_ripple:false` globally or per slide.
- Aesthetic: Apple iOS 26 Liquid Glass — translucent frosted panels with backdrop blur/refraction, specular edge highlights, and light-reactive depth over a vivid blurred backdrop.
- Composition: constructivist minimalism by default — asymmetric 12-column logic, strict edge alignment, decisive scale contrast, restrained geometry, and fewer independent cards. Preserve the topic palette; never force Soviet red/black or propaganda clichés.
- Layout intelligence: enabled by default; use automatic variants and resolve every `overfull` warning before delivery.
- Typography: editorial by default; the builder adds title-length and script classes, while the operator preserves semantic phrase boundaries and concise headings.
- Visual intelligence: enabled by default; orientation-aware image placement and semantic chart sizing remain subordinate to narrative order and factual accuracy.
- Quality intelligence: enabled by default; build-time rhythm warnings and runtime geometry checks replace routine screenshot loops, but not editorial judgment.
- Content intelligence: enabled by default; titles carry claims, screen copy stays concise, and detailed explanation belongs in hidden presenter notes.
- Narrative Director: enabled by default; direct important slides with a story role, audience question, speaker intent, emotional cue, and transition.
- Visual Coverage Planner: enabled by default; balance meaningful visuals with quiet pages, require chart/table provenance, and never use decorative motion as fake evidence.
- Accent: vivid system tint (default iOS blue `#0A84FF`); allow a single brand tint on request.
- Illustrations: **proactively add AI-generated images** where they break monotony — a floating hero on the `cover` and a small floating motif on each `section-divider` by default; data-dense layouts (timeline / comparison / bullets) stay text/CSS-only. Decide placement *before* generating and cut out backgrounds when the model ignores transparency (see `references/ai-imagery.md`).
- Charts: **proactively add ECharts visualizations only where a slide carries real, comparable, quantitative data** (trends, category comparisons, proportions, multi-dimension ability radar). Scan every page; add charts selectively, never on every slide. All charts auto-inherit the liquid-glass theme. Do not invent numbers to fill a chart (see `references/echarts-charts.md`). **This is fully automatic for the user: the operator does the scanning, decides placement, writes the `chart` fields into the outline, and runs build.py — the user never writes code or fields.**
- 3D / Three.js: **add live backgrounds only where they carry meaning** — `petals` for literary atmosphere, `waves` for flow/time, `network` only for an actual relationship network, and `field` / `nebula` on the cover only. `object` and `orbs` are retired and render nothing. Non-cover misuse of particle storms also renders no 3D scene. Never add motion merely to fill empty space (see `references/three-3d.md`).
- 3D scenes: reserve motion for a few atmosphere or concept pages. Never use them on pure-information slides or on every slide. All supported scenes render behind text through one shared canvas.
- Theme (auto color system): **every deck gets a coherent color theme derived from its topic.** Pick a palette of 3 best-fit colors (`colors`) for the three blurred background blobs AND the Three.js particle field, plus one accent (`accent`) for headings / eyebrows / links / glows; body text stays near-black for readability. Write the `theme` object into the outline and `build.py` derives every CSS variable and forwards the 3 colors to Three.js. See `references/theme-palettes.md` for curated palettes by topic mood. **Fully automatic for the user: the operator chooses the palette, writes the `theme` field, and builds — the user never picks colors or writes code.**

## Final Response

When finished, report:

- The created HTML file path.
- The validated brief path when production created one.
- The source manifest and content map paths when user material was ingested.
- Page count and deck type.
- Any important assumptions.
- Verification performed and any remaining risks.

For planning-only outputs, provide the blueprint directly and list the critical questions to answer before production.
