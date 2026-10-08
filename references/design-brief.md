# Design Brief Contract

The design brief is the stable handoff between intake and slide planning. It
captures communication intent, not slide markup. Save it as `brief.json`; keep
the renderer-specific structure in `outline.json`.

## Canonical shape

```json
{
  "schema_version": "1.0",
  "topic": "常见心理疾病介绍",
  "objective": "帮助大学生建立基础识别意识，并知道何时寻求专业帮助",
  "audience": "大学一年级学生",
  "scenario": "teaching",
  "language": "zh-CN",
  "slide_count": 12,
  "duration_minutes": 10,
  "content": {
    "mode": "agent-led",
    "source_files": [],
    "must_include": ["常见类型", "典型表现", "求助渠道"],
    "avoid": ["污名化表达", "替代专业诊断的自测结论"]
  },
  "visual": {
    "direction": "warm",
    "palette_preference": "低饱和蓝绿色",
    "density": "balanced",
    "motion": "subtle",
    "media_intensity": "balanced"
  },
  "delivery": {
    "format": "html",
    "aspect_ratio": "16:9"
  },
  "assumptions": ["未提供完整文案，由 Agent 策划初稿并标记需核验的医学表述"],
  "open_questions": [],
  "confirmed": true
}
```

## Field rules

### Required meaning

- `topic`: a concrete subject, not a filename or generic “做个 PPT”.
- `objective`: what the audience should understand, believe, decide, or do after
  the presentation.
- `audience`: the real viewers; include experience level when it affects tone.
- `scenario`: one of `teaching`, `report`, `pitch`, `interview`, `keynote`,
  `internal`, or `general`.
- `slide_count`: intended slide count, normally 3–40.

### Content

`content.mode` controls authorship:

- `supplied`: preserve the user's text and structure unless asked to edit it;
- `assisted`: reorganize, tighten, and fill clearly identified gaps;
- `agent-led`: plan a draft from the topic, without inventing unsupported facts.

Paths in `source_files` should remain local project paths or user-provided
references. `must_include` and `avoid` are presentation constraints, not visual
keywords.

### Visual intent

- `direction`: `auto`, `minimal`, `academic`, `technology`, `warm`, or `brand`.
- `density`: `airy`, `balanced`, or `dense`.
- `motion`: `none`, `subtle`, or `expressive`.
- `media_intensity`: `restrained`, `balanced`, or `rich`.

These are communication preferences. They do not prescribe ECharts, Three.js,
AI imagery, or ripple material. The visual-planning step chooses one dominant
medium per slide based on content.

### Delivery

The current package supports `html` and defaults to `16:9`. Keep these values
explicit so future exporters can consume the same brief without redesigning the
intake contract.

### Assumptions and open questions

- Put agent-selected defaults in `assumptions`.
- Put unresolved factual or scope dependencies in `open_questions`.
- `confirmed` means the supplied fields reflect the user's intent. It may be
  `true` after a completed form or a direct “直接生成” instruction. It is not a
  claim that every generated fact has been verified.

## Conversion into an outline

Before writing `outline.json`:

1. translate the objective into one audience takeaway;
2. select a narrative structure appropriate to `scenario`;
3. assign one main point to each slide;
4. use visual preferences to set a deck-level style lock;
5. choose imagery, chart, 3D, or ripple per slide only after its content role is
   known;
6. carry `must_include`, `avoid`, assumptions, and open questions into the
   planning and quality checks.

Do not rewrite the brief merely because a layout is inconvenient. Change the
outline or split a slide instead.
