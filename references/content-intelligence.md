# Content Intelligence — 屏幕文案与演讲备注

`"content_intelligence": true` is the default. This layer helps the producing
agent edit for presentation instead of shrinking document prose into a slide.
The deterministic builder reports problems but never paraphrases protected or
user-authored text by itself.

## 1. One audience-facing claim per page

Use `main_point` to record the claim that the audience should retain. It is
planning metadata and is not rendered. If `main_point` is absent, an informative
title may carry the claim. Generic labels such as “基本概念”, “现状分析”,
“相关介绍”, “Overview”, or “Conclusion” do not count as claims and trigger a
`[copy]` warning on content pages.

Prefer:

- “爬虫从种子 URL 出发，沿链接不断扩展边界”
- “页面变化越快，重新访问策略越重要”

Avoid:

- “基本概念”
- “问题分析”

Section dividers, covers, quotes, navigation, and closing pages may use short
labels because their role is structural rather than argumentative.

## 2. Separate display copy from spoken explanation

Keep only the claim, evidence, labels, and indispensable context on screen. Put
examples, transitions, caveats, definitions, and delivery cues in
`speaker_notes`:

```json
{
  "layout": "bullets",
  "title": "礼貌策略决定爬虫能否长期运行",
  "main_point": "限速与 robots.txt 是可持续抓取的基本边界",
  "speaker_notes": [
    "先解释 robots.txt 是站点声明，不等同于法律许可。",
    "用校园图书馆检索作类比，再进入限速示例。"
  ]
}
```

For each substantive page, combine the explanation into natural spoken prose of about
80–130 Chinese characters (target roughly 100). Mention the visual evidence or example
on that page, add one useful interpretation or caveat, and connect naturally to the next
idea. Do not turn planning labels into a script, repeat the title verbatim, or invent
facts. The presenter panel is directly editable and auto-saves browser-local revisions;
those revisions do not modify the outline file.

The builder escapes notes and embeds them as hidden content. Press `N` during
playback, or append `?notes=1`, to open the presenter panel and edit the current page's
note. Notes never affect slide density or appear in the audience view by default.

## 3. Long-block warnings

The builder checks individual display fields and repeated item descriptions.
When it reports a long block:

1. preserve mandatory wording and citations;
2. remove repetition;
3. move explanation to `speaker_notes`;
4. split the page if two claims remain;
5. rebuild instead of reducing text below readable size.

## 4. Source fidelity

- `main_point` may summarize, but must not add unsupported causality or certainty.
- Text marked `must_preserve` in the source manifest remains verbatim.
- AI additions remain traceable in `content-map.md`.
- Do not convert source prose into fabricated numbers, quotes, or chart data.

Set `"content_intelligence": false` only for exact legacy reproduction.
