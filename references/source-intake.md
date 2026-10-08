# Source Gate

Use this gate after `brief.json` selects `content.mode = supplied` or
`content.mode = assisted`. Skip it for `agent-led` work unless the user also
provides reference or visual files.

The goal is to preserve source intent, make AI additions visible, and prevent a
pile of attachments from silently becoming an unreliable outline.

## 1. Accept material through portable channels

Offer all channels supported by the current client:

- attach `.docx`, `.pdf`, `.md`, or `.txt` files to the conversation;
- provide an accessible local project path;
- paste text directly into the conversation.

Visual assets may be attached separately and classified as `visual`; do not
treat an image as factual copy unless the user explicitly asks for extraction.
If an attachment or path cannot be read, say which item is unavailable and ask
the user to attach it again or paste the relevant text. Never pretend to have
read an inaccessible source.

Keep original files unchanged. Work from extracted text or a task-local copy;
do not overwrite, rename, move, or delete user sources merely to organize a
deck.

## 2. Collect only the choices that change treatment

### Full copy (`supplied`)

After the user selects “完整文案”, request the material and one processing level:

```text
请附加 .docx / .pdf / .md / .txt，提供本地路径，或直接粘贴文案。

处理方式：
○ 原文优先：只做分页、排版和必要的短句化
○ 轻度优化：允许精简重复内容和调整局部顺序
○ 重新策划：保留核心事实与观点，重新组织叙事

必须原样保留的内容（可选）：数据、引用、固定表述、署名或参考文献
```

Map the choices to `preserve`, `light-edit`, or `restructure`. If the user has
already described the desired treatment, do not ask again.

For several files, identify exactly one `primary` document. Classify the rest as
`supporting`, `data`, or `visual`. If no priority is obvious and different choices
would change the narrative, ask one focused question.

### Partial material (`assisted`)

After the user selects “部分素材，由 AI 整理”, request the material and ask only:

```text
这些素材主要用于：必须出现 / 背景参考 / 数据证据 / 视觉素材
希望 AI 补充什么：概念、案例、过渡、总结或其他缺口
必须保留或不能改写的内容（可选）：……
```

Do not ask users to manually label every paragraph. Infer coverage after reading
the material, then show the result in the content map.

## 3. Produce a source receipt

Before storyboarding, show a compact receipt:

```text
素材清单
主文案：《网页爬虫介绍.docx》 · 完整可读
辅助材料：《课堂要求.pdf》第 2–4 页 · 完整可读
处理方式：轻度优化

识别结构：定义 / 工作流程 / 使用场景 / 合规边界
计划处理：合并重复段落；保留原始引用；补充一页入门实践
待确认：无
```

If any required source is missing, unreadable, contradictory, or ambiguously
prioritized, stop before the outline and request the smallest necessary fix.

## 4. Save the source manifest

Read `references/source-manifest.md`. Save `source-manifest.json` next to
`brief.json`, then validate it:

```bash
python scripts/validate_source_manifest.py source-manifest.json
```

The manifest records file roles and coverage. It must never contain the user's
entire document text, credentials, or unrelated personal data.

## 5. Build the content map

Create `content-map.md` as a human-readable planning artifact. Use one row per
planned section:

```markdown
| Section | Coverage | Sources | Treatment |
|---|---|---|---|
| 爬虫定义 | provided | src-01 §1 | 精简，保留原意 |
| 工作流程 | partial | src-01 §2 | 重组步骤，补充连接说明 |
| 合规边界 | missing | — | AI 起草基础说明，避免法律结论 |
```

Coverage values:

- `provided`: the user supplied enough material;
- `partial`: user material exists, but needs organization or clearly identified
  additions;
- `missing`: the agent must draft the section or ask for it.

For `supplied` mode, do not silently turn a missing section into new authorial
content. Follow the selected processing level and list any proposed addition.
For `assisted` mode, AI additions are expected, but must remain traceable in the
content map and must not invent facts, quotes, sources, or numbers.

## 6. Handoff to narrative planning

Continue only when:

- every `must-use` source is readable;
- the primary source is unambiguous when `mode = supplied`;
- protected wording and citations are recorded;
- each planned section has a coverage status and treatment;
- material conflicts that affect claims are resolved or explicitly surfaced.

Carry `must_preserve`, `ai_fill`, conflicts, and section coverage into the
outline and final quality review.
