---
name: podcastfy-free
description: Use when creating free dialogue-style audio blogs or podcasts from Markdown, PDFs, Office files, images, notes, URLs, or user-provided material using Codex-authored transcripts, optional Marker document-to-Markdown conversion, Podcastfy transcript input, and Microsoft Edge TTS without paid API keys. Triggers include podcastfy, marker, PDF to Markdown, free TTS, Edge TTS, audio blog, Chinese dialogue podcast, and transcript-to-audio workflows.
---

# Podcastfy Free

## Overview

Create occasional, zero-API-key dialogue podcasts by having Codex write the script and using Podcastfy or Edge TTS to synthesize it. Do not use Podcastfy's LLM generation path by default, because that requires external model API keys.

## Default Workflow

1. Gather source material from the user, local files, or URLs.
2. If the source is not already Markdown or plain text, convert it first with `scripts/prepare_markdown.py convert`.
3. Read the Markdown and build a source-grounded outline before writing the audio script.
4. Write a concise two-person transcript in the Podcastfy format from `references/transcript-format.md`.
5. Save the transcript in the workspace, usually under `podcasts/<topic>/script.txt`.
6. Run `scripts/make_edge_podcast.py preflight` if the audio environment is unknown.
7. Run `scripts/make_edge_podcast.py synthesize --transcript <script.txt> --output <podcast.mp3>`.
8. Verify that the MP3 exists and report the Markdown, transcript, and audio paths.

Use Chinese by default when the user writes in Chinese. Use Edge voices `zh-CN-XiaoxiaoNeural` for `Person1` and `zh-CN-YunxiNeural` for `Person2` unless the user asks for other voices.

## Script Commands

Document-to-Markdown preflight:

```powershell
python C:\Users\lsst\.codex\skills\podcastfy-free\scripts\prepare_markdown.py preflight
```

Convert a source file to Markdown:

```powershell
python C:\Users\lsst\.codex\skills\podcastfy-free\scripts\prepare_markdown.py convert `
  --input F:\path\source.pdf `
  --output G:\podcast\podcasts\example\source.md
```

For scanned PDFs, force OCR through Marker:

```powershell
python C:\Users\lsst\.codex\skills\podcastfy-free\scripts\prepare_markdown.py convert `
  --engine marker `
  --force-ocr `
  --input F:\path\scan.pdf `
  --output G:\podcast\podcasts\example\source.md
```

Run from any workspace:

```powershell
python C:\Users\lsst\.codex\skills\podcastfy-free\scripts\make_edge_podcast.py preflight
```

Synthesize with automatic engine selection:

```powershell
python C:\Users\lsst\.codex\skills\podcastfy-free\scripts\make_edge_podcast.py synthesize `
  --transcript G:\podcast\podcasts\example\script.txt `
  --output G:\podcast\podcasts\example\podcast.mp3
```

Force Podcastfy when it is installed and working:

```powershell
python C:\Users\lsst\.codex\skills\podcastfy-free\scripts\make_edge_podcast.py synthesize `
  --engine podcastfy `
  --transcript G:\podcast\podcasts\example\script.txt `
  --output G:\podcast\podcasts\example\podcast.mp3
```

Use direct Edge TTS when Podcastfy dependencies are not installed:

```powershell
python C:\Users\lsst\.codex\skills\podcastfy-free\scripts\make_edge_podcast.py synthesize `
  --engine direct `
  --transcript G:\podcast\podcasts\example\script.txt `
  --output G:\podcast\podcasts\example\podcast.mp3
```

## Environment Rules

- Prefer free mode: Codex writes the transcript, Edge TTS reads it.
- Do not request Gemini, OpenAI, ElevenLabs, or DeepSeek keys unless the user explicitly wants fully automated source-to-script generation.
- Prefer Markdown as the understanding layer. If the user gives PDF, DOCX, PPTX, XLSX, image, HTML, or EPUB, use Marker when installed; otherwise use the fallback only for searchable PDFs.
- If Marker is missing, install `python -m pip install marker-pdf` for PDF/image conversion or `python -m pip install "marker-pdf[full]"` for Office/HTML/EPUB support. Do not use Marker's `--use_llm` path unless the user explicitly asks for API-backed accuracy improvements.
- If `podcastfy` is missing, either install it with `python -m pip install podcastfy` or use `--engine direct`.
- If `edge_tts` is missing, install `python -m pip install edge-tts`.
- If merging metadata looks wrong, install FFmpeg or `pydub`. The direct engine can fall back to MP3 byte-append, but FFmpeg gives cleaner files. On Windows, `winget install Gyan.FFmpeg` is a common option.

## Transcript Requirements

Read `references/transcript-format.md` before writing or repairing a transcript. The short version:

- Use only `<Person1>...</Person1>` and `<Person2>...</Person2>` speaker blocks.
- Alternate speakers and keep each turn short enough for natural TTS.
- Avoid Markdown bullets, tables, code fences, footnotes, citations, and raw URLs inside the spoken transcript.
- Make the script sound spoken, not like a summary report.
- For a 3-5 minute Chinese audio blog, target roughly 1,200-2,000 Chinese characters.

## Troubleshooting

Use `references/marker.md` when converting documents to Markdown. Use `references/podcastfy-edge.md` when Podcastfy behavior matters, especially transcript input, Edge voices, and why this skill bypasses Podcastfy's LLM path.

If the user asks for a "free" workflow, keep using this pipeline even if higher-quality paid TTS options exist. Mention paid services only as an optional quality upgrade, not as the default solution.
