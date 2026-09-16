# Intake & Gap Diagnosis

Goal: turn a vague request into a concrete deck brief with minimal questions.

## Input types accepted
- Pasted text / Markdown / outline
- `.md`, `.txt` files
- `.docx`, `.pdf` (extract text only)
- A rough idea stated in chat

## Information to determine
1. **Topic** — what is the deck about?
2. **Audience** — who watches? (exec, peers, students, clients)
3. **Scenario** — talk, pitch, class, internal update, social post?
4. **Length** — short (5–8) / medium (8–12) / long (12–20+)
5. **Accent variant** — default Apple blue, or a neutral / brand accent
6. **Illustrations** — AI-generated hero/cover/concept images, or pure CSS visuals?

## Clarification rules
- Ask at most 1–3 questions, and only when the missing item materially changes the deck.
- Bundle questions into one message; never ask one at a time across multiple turns.
- If the user already gave a topic + length, proceed with defaults for the rest.
- When in doubt, default to: Chinese, medium length (8–12), iOS blue tint `#0A84FF`, one hero image on the cover.

## Missing-information fallbacks
- No audience → assume general professional.
- No scenario → assume a conference-style talk.
- No length → medium (8–12).
- No accent preference → vivid iOS tint `#0A84FF`.
- No illustration preference → one hero image on the cover only.
