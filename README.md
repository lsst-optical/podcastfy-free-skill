# podcastfy-free

Codex skill for creating free Chinese dialogue-style audio blogs from Markdown, PDFs, Office files, images, notes, URLs, or plain text.

The default workflow is:

1. Convert source files to Markdown when needed.
2. Have Codex write a two-person Podcastfy-style transcript.
3. Use Microsoft Edge TTS to synthesize MP3 audio without paid API keys.

## Install

Copy this folder to your Codex skills directory:

```powershell
Copy-Item -Recurse . C:\Users\lsst\.codex\skills\podcastfy-free
```

## Optional Dependencies

For free audio synthesis:

```powershell
python -m pip install edge-tts
```

For document-to-Markdown conversion with Marker:

```powershell
python -m pip install marker-pdf
```

For broader Office/HTML/EPUB support:

```powershell
python -m pip install "marker-pdf[full]"
```

## Notes

- The skill does not call external LLM APIs by default.
- Podcastfy itself is optional; the bundled direct Edge TTS script works without Podcastfy.
- Marker is optional; searchable PDFs can use the fallback extractor.
