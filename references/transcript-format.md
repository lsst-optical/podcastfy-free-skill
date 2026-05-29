# Transcript Format

Podcastfy's transcript-to-audio path expects `Person1` and `Person2` XML-like tags. The safest format is:

```text
<Person1>大家好，欢迎来到这期音频博客。今天我们聊一个具体问题。</Person1>
<Person2>我先问个直接的问题：这件事为什么值得听众花几分钟了解？</Person2>
<Person1>因为它影响了实际决策，而不只是一个概念。</Person1>
<Person2>明白了。那我们从核心背景开始。</Person2>
```

## Writing Rules

- Keep exactly two speakers unless the user asks otherwise.
- Use `Person1` as the main explainer and `Person2` as the curious listener or challenger.
- Alternate turns. Do not put two `Person1` blocks in a row unless there is a strong reason.
- Keep each turn under about 180 Chinese characters or 80 English words.
- Remove Markdown syntax, headings, bullets, tables, citations, raw URLs, and code fences from the spoken script.
- Use natural phrasing: short sentences, spoken transitions, and occasional clarifying questions.
- Preserve factual accuracy. If the source is uncertain, phrase it as uncertainty instead of inventing detail.

## Length Targets

- 1-2 minutes: 500-900 Chinese characters.
- 3-5 minutes: 1,200-2,000 Chinese characters.
- 8-10 minutes: 3,000-4,500 Chinese characters.

## Repair Checklist

Before synthesis, check:

- Matching opening and closing tags for every turn.
- No empty turns.
- No unsupported tags such as `<Host>`, `<Guest>`, or Markdown headings.
- No "as an AI" phrasing.
- No visible source-management language such as "according to the provided document" unless it should be spoken.
