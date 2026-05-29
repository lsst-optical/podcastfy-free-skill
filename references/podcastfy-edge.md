# Podcastfy and Edge TTS Notes

Podcastfy can generate audio from an existing transcript:

```powershell
python -m podcastfy.client --transcript path\to\script.txt --tts-model edge
```

That path does not need Gemini, OpenAI, ElevenLabs, or DeepSeek keys because the transcript already exists and Edge TTS does not use an API key.

## Why This Skill Avoids Podcastfy LLM Generation

Podcastfy's normal source-to-podcast flow is:

```text
source material -> LLM transcript generation -> TTS audio generation
```

The LLM transcript generation step needs an external LLM provider unless a local model is configured. For this free skill, Codex writes the transcript in the conversation, then Podcastfy or direct Edge TTS only performs transcript-to-audio.

## Voices

Default Chinese voices:

- `Person1`: `zh-CN-XiaoxiaoNeural`
- `Person2`: `zh-CN-YunxiNeural`

Useful English voices:

- `Person1`: `en-US-JennyNeural`
- `Person2`: `en-US-EricNeural`

## Engine Choice

- `auto`: try Podcastfy first when installed; fall back to direct Edge TTS if Podcastfy fails.
- `podcastfy`: use the Podcastfy `process_content(..., transcript_file=..., tts_model="edge")` path.
- `direct`: parse `Person1`/`Person2` tags, synthesize each turn with `edge_tts`, then merge segments.

Use `direct` when Podcastfy's dependency set is not installed or when a minimal no-key path is more important than matching Podcastfy exactly.
