# Narrative Director

Narrative Director turns a slide list into a paced talk. It does not invent facts or
rewrite protected source text. It records the job of each slide, the audience question
being answered, the speaker's intent, and the hand-off to the next page.

## Per-slide contract

```json
{
  "story_role": "evidence",
  "main_point": "优先级决定爬虫把有限带宽用在哪里",
  "audience_question": "为什么不能把所有网页都抓下来？",
  "speaker_intent": "用容量约束建立问题意识",
  "transition": "既然资源有限，下一页看选择策略",
  "emotion": "tension"
}
```

- `story_role`: `hook`, `orient`, `question`, `context`, `conflict`, `explain`,
  `example`, `evidence`, `contrast`, `reveal`, `synthesis`, `transition`,
  `resolution`, or `pause`.
- `main_point`: the one retained audience takeaway. It remains hidden from the slide.
- `audience_question`: the question this page resolves.
- `speaker_intent`: what should change in the audience's understanding or feeling.
- `transition`: a natural spoken bridge to the next page.
- `emotion`: a restrained pacing cue such as `curiosity`, `clarity`, `tension`,
  `confidence`, `relief`, or `reflection`.

All fields are optional. When `story_role` or `emotion` is absent, the builder infers a
conservative default from the layout. Explicit direction is recommended for important
beats. The presenter panel (`N` or `?notes=1`) docks in a separate right rail and shows
only the two cues needed during delivery: `main_point` and `transition`. The other fields
still guide planning and narrative audits, but do not clutter the live panel. The slide
narrows to remain fully visible. Audience mode contains no presenter button, label, or
cue.

## Speaker-note voice

Write `speaker_notes` for every substantive slide as a short piece of spoken language,
normally **80–130 Chinese characters (target about 100)** or roughly 45–80 English
words. It should sound like something a person would naturally say, not metadata or a
second slide.

- Refer to the visible diagram, table, example, or contrast on that page.
- Explain one concrete relationship, implication, caveat, or example instead of merely
  repeating the title and labels.
- Lead naturally toward the recorded `transition`; avoid canned “首先、其次、最后”
  patterns, slogans, and unexplained jargon.
- Use only facts supported by the user material or traceable sources. Never invent a
  number or detail to make the note sound more specific.

The presenter can edit notes directly in the panel. Edits are automatically stored in
that browser on that device (with an in-session fallback when local storage is blocked).
They do not rewrite the source outline or generated HTML; update the outline and rebuild
when an edit must travel with the deck.

## Directing the arc

1. Open with a question, tension, or promise—not a table of contents disguised as a
   story.
2. Alternate explanation with evidence, example, contrast, or reveal.
3. Use `pause` or a section divider as a reset after a dense sequence.
4. End with synthesis and resolution: what should the audience now believe, remember,
   or do?
5. Keep one main point per slide. Split pages that need two incompatible intents.

The builder warns when four or more consecutive slides repeat the same role, and when a
long deck has no evidence, example, contrast, or reveal beat. Warnings are editorial
signals, not a license to add unsupported claims.

## Source fidelity

- Protected wording remains verbatim.
- Missing evidence stays marked as a dependency; never fabricate it for a stronger arc.
- Speaker intent may change framing, not factual meaning.
- Transitions should connect existing claims rather than imply causality the source does
  not establish.

Top-level `"narrative_director": false` disables the audit and cue layer for exact legacy
reproduction. It is enabled by default.
