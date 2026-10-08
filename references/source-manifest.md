# Source Manifest Contract

`source-manifest.json` is the machine-readable record produced by the Source
Gate. It stores provenance and handling decisions, not the full source text.

## Canonical shape

```json
{
  "schema_version": "1.0",
  "mode": "assisted",
  "processing": "light-edit",
  "sources": [
    {
      "id": "src-01",
      "path": "sources/web-crawler-notes.docx",
      "role": "primary",
      "purpose": "must-use",
      "scope": "全文",
      "status": "available"
    },
    {
      "id": "src-02",
      "path": "sources/class-requirements.pdf",
      "role": "supporting",
      "purpose": "reference",
      "scope": "第 2–4 页",
      "status": "available"
    },
    {
      "id": "src-03",
      "path": "sources/crawler-flow.png",
      "role": "visual",
      "purpose": "visual",
      "scope": "整张图片",
      "status": "available",
      "intended_use": "工作流程",
      "treatment": "evidence",
      "fit": "contain",
      "caption": "用户提供的爬虫流程示意图",
      "credit": "用户提供"
    }
  ],
  "must_preserve": ["课程给出的学习目标原文"],
  "ai_fill": ["补充适合中学生的生活类比", "起草简短总结"],
  "conflicts": [],
  "content_map": [
    {
      "section": "网页爬虫的定义",
      "coverage": "provided",
      "source_ids": ["src-01"],
      "handling": "精简长句，保留原意"
    },
    {
      "section": "使用边界",
      "coverage": "partial",
      "source_ids": ["src-01", "src-02"],
      "handling": "合并两份材料，不扩展为法律结论"
    }
  ],
  "assumptions": [],
  "open_questions": [],
  "confirmed": true
}
```

## Field rules

### Mode and processing

- `mode`: `supplied` or `assisted`; it must match `brief.json`.
- `processing`: `preserve`, `light-edit`, or `restructure`.
- `supplied` requires exactly one `primary` source so the authoritative copy is
  unambiguous.
- `assisted` may use several `supporting` sources without a primary document.

### Sources

Each source needs:

- a unique `id`;
- a readable path or attachment label in `path`;
- `role`: `primary`, `supporting`, `data`, or `visual`;
- `purpose`: `must-use`, `reference`, `evidence`, or `visual`;
- `scope`: the part actually used, such as `全文`, `第 2–4 页`, or `表 1`;
- `status`: `available`, `missing`, or `unreadable`.

Every `must-use` and `evidence` source must be `available` before the Source Gate
passes. A missing optional reference may remain listed when its consequence is
recorded in `open_questions`.

For `role = visual`, also record:

- `intended_use`: cover, a named section, or `auto`;
- `treatment`: `evidence` or `decorative`;
- `fit`: `contain`, `cover`, `float`, or `no-crop`;
- optional `caption` and `credit` strings.

Visual evidence should normally use `contain` or `no-crop`. A transparent
decorative object may use `float`; a photographic decorative image may use
`cover`. Do not encode required slide copy into the image.

### Content map

Each item contains:

- `section`: a planned content section;
- `coverage`: `provided`, `partial`, or `missing`;
- `source_ids`: zero or more ids from `sources`;
- `handling`: a specific editing or filling plan.

`provided` and `partial` entries require at least one source id. `missing` entries
must have an empty `source_ids` list and a handling statement that makes the AI
addition visible.

### Protection and uncertainty

- `must_preserve`: exact wording, data, citations, attributions, or other content
  that the deck must retain.
- `ai_fill`: additions that the user requested or accepted.
- `conflicts`: disagreements among sources that affect the deck.
- `assumptions`: source-handling decisions inferred by the agent.
- `open_questions`: unresolved blockers or optional missing material.
- `confirmed`: whether the source receipt and treatment reflect the user's stated
  intent. It does not certify factual correctness.

Never store secret values, authentication data, or unrelated personal details in
the manifest.
