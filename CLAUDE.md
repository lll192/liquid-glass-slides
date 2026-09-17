# liquid-glass-slides

Build Apple iOS 26 "Liquid Glass" style animated HTML slide decks from an outline JSON.

- **To build, read `references/INSTRUCTIONS.md` and follow it exactly.**
- Entry point (zero dependencies, no network):
  `python scripts/build.py --outline <outline.json> --out <deck.html>`
- Output: one self-contained `.html` file (engine + ECharts + Three.js inlined).
- Use when: the user wants a PPT / 幻灯片 / 演示 / pitch deck / keynote with a translucent glass aesthetic, optionally with AI-generated hero/cover art.
- Not for editable PPTX or hand-drawn raster images.

See `README.md` and `references/` for full detail.
