# Intake & Brief Gate

Goal: convert whatever the user provides into a usable presentation brief without
making a well-specified request answer a redundant questionnaire.

## 1. Inventory the request before asking

Extract what is already known from the conversation and attached material:

- topic and desired outcome;
- audience and use scenario;
- page count or speaking time;
- content ownership (`supplied`, `assisted`, or `agent-led`);
- visual direction, color or brand constraints;
- required facts, assets, sections, and things to avoid.

Do not ask for information that is already stated or safely implied. Do not ask
the user to choose implementation technologies such as ECharts, Three.js, or a
ripple preset. Ask about the intended communication effect; the agent selects the
medium.

## 2. Choose the intake depth

### Fast path — the request is already usable

Use when topic, audience/use, and approximate scope are clear. Create the brief,
state any non-obvious assumptions in one compact confirmation card, and continue
in the same turn. Do not force an extra reply.

### Compact form — several consequential fields are missing

Send the following as one grouped form. The user may answer in prose, paste
source material, or reply with one pipe-separated line. Mark inferred defaults;
do not make every field mandatory.

```text
生成简报（已有内容可直接粘贴；不确定的项目留空，我会自动决定）

1. 主题与目标：
2. 受众与场景：
3. 页数或演讲时长：
4. 内容来源：完整文案 / 部分素材，由 AI 整理 / 只给主题，由 AI 策划
5. 视觉方向：极简专业 / 学术清晰 / 科技未来 / 温暖叙事 / 高级品牌 / 自动匹配
6. 配色与特殊要求：品牌色、必须包含或避免的内容（可选）
```

Also accept this compact answer shape:

```text
大学生心理健康科普｜大一课堂｜12页｜AI策划｜温暖清晰｜蓝绿色
```

### Focused question — only one decision is blocking

Ask only that question. Examples: the same topic could be either a sales pitch
or a classroom lesson; supplied figures conflict; the requested page count is
incompatible with mandatory content.

## 3. Build the design brief

Read `references/design-brief.md`. Create a `brief.json` next to the future
`outline.json`, using defaults only where the user left room for judgment. Record
those defaults in `assumptions` instead of silently presenting them as user
choices.

The brief is a planning contract, not renderer input. It should remain stable
while the outline and visual execution iterate.

Run the zero-dependency validator when a brief file is created:

```bash
python scripts/validate_brief.py brief.json
```

If `content.mode` is `supplied` or `assisted`, continue to
`references/source-intake.md` before narrative planning. If it is `agent-led`
and the user supplied no files, skip the Source Gate.

## 4. Confirm proportionally

Present a compact card before planning:

```text
生成简报
主题 / 目标：……
受众 / 场景：……
规模：12 页 · 约 10 分钟
内容：AI 策划，用户审核
视觉：温暖叙事 · 蓝绿色 · 动效克制
关键约束：……
假设：……
```

- **Soft confirmation:** if the request is ordinary and the brief follows the
  user's stated intent, show the card and continue. The user can correct it while
  generation is underway.
- **Explicit confirmation:** pause only when a choice materially changes claims,
  audience, brand, confidentiality, cost, or output scope.
- A direct instruction such as “直接生成” or a completed form counts as
  confirmation of the supplied fields.

## Defaults

Use defaults only after inventorying the request:

- language: Simplified Chinese;
- audience: general professional;
- scenario: conference-style talk;
- length: 8–12 slides;
- content mode: `agent-led` when no source material is supplied;
- visual direction: `auto`;
- density: `balanced`;
- motion: `subtle`;
- media intensity: `balanced`;
- palette: derive from topic, with accessible near-black body text;
- output: self-contained 16:9 HTML deck.
- production profile: `balanced`; use `fast` when the user prioritizes rapid iteration.

Never invent facts, quotations, sources, or quantitative data to complete a
brief. Put unresolved factual dependencies in `open_questions`.
