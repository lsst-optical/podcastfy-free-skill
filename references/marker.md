# Marker Document Conversion

Marker is an optional preprocessing layer for `podcastfy-free`. Use it to convert source documents into Markdown before Codex reads, outlines, and writes the dialogue script.

## What Marker Supports

Marker converts PDF, image, PPTX, DOCX, XLSX, HTML, and EPUB files to Markdown, JSON, chunks, or HTML. It can OCR scanned pages, preserve tables/equations/code blocks, extract images, and remove common headers and footers.

## Installation

For PDF and image conversion:

```powershell
python -m pip install marker-pdf
```

For Office documents, HTML, EPUB, and broader file support:

```powershell
python -m pip install "marker-pdf[full]"
```

Marker needs Python 3.10+ and PyTorch. It can run on CPU, GPU, or MPS. First runs may download model weights and take longer.

## Default Command

```powershell
python C:\Users\lsst\.codex\skills\podcastfy-free\scripts\prepare_markdown.py convert `
  --input F:\path\source.pdf `
  --output G:\podcast\podcasts\topic\source.md
```

For scanned PDFs:

```powershell
python C:\Users\lsst\.codex\skills\podcastfy-free\scripts\prepare_markdown.py convert `
  --engine marker `
  --force-ocr `
  --input F:\path\scan.pdf `
  --output G:\podcast\podcasts\topic\source.md
```

## Rules for This Skill

- Use Markdown as the main understanding artifact and report its path with final outputs.
- Do not pass Marker's `--use_llm` by default; that would require a separate LLM backend and is outside the free workflow.
- Use `--page-range` for very large books when the user only wants selected chapters.
- If Marker is missing and the file is a searchable PDF, `prepare_markdown.py` can use a local PDF text fallback.
- If the fallback finds no text, treat the file as scanned and ask to install Marker or run with `--force-ocr`.
