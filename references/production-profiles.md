# Production Profiles

Production profiles control time and media spend without changing content quality or
the deterministic HTML build. The profile belongs in `brief.json` under `production`.

| Profile | AI image budget | Sourced-image target | Visual QA |
|---|---:|---:|---|
| `fast` | 0–1 | 2–4 | reports first, one final browser check only when needed |
| `balanced` | 1–2 | 2–4 | reports first, inspect the cover and any warned page |
| `premium` | 2–4 | 3–6 | selective multi-page visual review |

Use `balanced` by default. Choose `fast` when the user prioritizes speed, iteration, or
testing. Choose `premium` only when the user explicitly values bespoke art enough to
accept longer generation time.

```json
"production": {
  "profile": "balanced",
  "ai_image_budget": 1,
  "web_image_target": 3
}
```

## Time-saving rules

1. Finish the brief, narrative spine, and image search plan before starting image work.
2. Use one batch of focused web-image queries for multiple slides. Generate an AI image
   only when a sourced image cannot express the required concept or art direction.
3. If the environment permits concurrency, run independent fact research, web-image
   search, and the first AI image request together. Never start several speculative image
   generations and decide their use afterward.
4. Build once after the outline and local assets are ready. Use build reports and the
   runtime DOM report before screenshots.
5. Do not capture every slide routinely. Inspect the cover, pages named by warnings, and
   one representative dense page. Expand inspection only when a defect appears.
6. Reuse the same image only as a deliberate full-deck background. Content images and
   decorative motifs should not repeat across slides.

The HTML build normally takes seconds. Long runs usually come from serial image
generation, broad browsing, or screenshot loops, so reduce those activities before
weakening content or typography checks.
