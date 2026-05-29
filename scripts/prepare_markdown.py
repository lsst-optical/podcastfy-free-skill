#!/usr/bin/env python
"""Prepare source documents as Markdown for podcastfy-free.

Marker is preferred when available. A lightweight PDF text fallback is included
so searchable PDFs can still be converted without installing Marker.
"""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable, List, Optional


MARKER_INSTALL = "python -m pip install marker-pdf"
MARKER_FULL_INSTALL = 'python -m pip install "marker-pdf[full]"'


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def marker_command() -> Optional[str]:
    return shutil.which("marker_single")


def preflight() -> int:
    cmd = marker_command()
    checks = [
        ("marker_single", cmd or "missing", cmd is not None),
        ("marker module", "installed" if module_available("marker") else "missing", module_available("marker")),
        ("PyMuPDF fallback", "installed" if module_available("fitz") else "missing", module_available("fitz")),
        ("pypdf fallback", "installed" if module_available("pypdf") else "missing", module_available("pypdf")),
        ("pdfplumber fallback", "installed" if module_available("pdfplumber") else "missing", module_available("pdfplumber")),
    ]
    for name, value, ok in checks:
        print(f"{'OK' if ok else 'MISSING':7} {name}: {value}")

    print("\nInstall hints:")
    print(f"- PDFs/images: {MARKER_INSTALL}")
    print(f"- Office/HTML/EPUB and broader file support: {MARKER_FULL_INSTALL}")
    print("- This skill does not use Marker's --use_llm path by default, so no LLM API key is required.")
    return 0


def markdown_header(source: Path, engine: str) -> str:
    return f"# Source Extract\n\n- Source: `{source}`\n- Engine: `{engine}`\n\n"


def run_marker(
    source: Path,
    output: Path,
    force_ocr: bool = False,
    page_range: Optional[str] = None,
    keep_images: bool = False,
) -> Path:
    cmd = marker_command()
    if not cmd:
        raise RuntimeError(f"marker_single is missing. Install Marker with: {MARKER_INSTALL}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="podcastfy_marker_") as tmp:
        tmp_dir = Path(tmp)
        command = [
            cmd,
            str(source),
            "--output_format",
            "markdown",
            "--output_dir",
            str(tmp_dir),
        ]
        if force_ocr:
            command.append("--force_ocr")
        if page_range:
            command.extend(["--page_range", page_range])
        if not keep_images:
            command.append("--disable_image_extraction")

        subprocess.run(command, check=True)
        candidates = sorted(
            [p for p in tmp_dir.rglob("*.md") if p.is_file() and p.stat().st_size > 0],
            key=lambda p: (p.stem.lower() != source.stem.lower(), -p.stat().st_size, len(str(p))),
        )
        if not candidates:
            produced = "\n".join(str(p.relative_to(tmp_dir)) for p in tmp_dir.rglob("*") if p.is_file())
            raise RuntimeError(f"Marker did not produce a Markdown file. Produced files:\n{produced}")

        text = candidates[0].read_text(encoding="utf-8", errors="replace").strip()
        output.write_text(markdown_header(source, "marker") + text + "\n", encoding="utf-8")
    return output


def extract_pdf_with_pymupdf(source: Path) -> List[str]:
    import fitz

    doc = fitz.open(source)
    pages: List[str] = []
    for index, page in enumerate(doc, 1):
        text = (page.get_text("text") or "").strip()
        pages.append(f"## Page {index}\n\n{text}\n")
    return pages


def extract_pdf_with_pypdf(source: Path) -> List[str]:
    from pypdf import PdfReader

    reader = PdfReader(str(source))
    pages: List[str] = []
    for index, page in enumerate(reader.pages, 1):
        text = (page.extract_text() or "").strip()
        pages.append(f"## Page {index}\n\n{text}\n")
    return pages


def run_pdf_fallback(source: Path, output: Path) -> Path:
    if source.suffix.lower() != ".pdf":
        raise RuntimeError(
            "Fallback conversion only supports searchable PDFs. Install marker-pdf[full] for this file type."
        )

    if module_available("fitz"):
        pages = extract_pdf_with_pymupdf(source)
        engine = "pymupdf-fallback"
    elif module_available("pypdf"):
        pages = extract_pdf_with_pypdf(source)
        engine = "pypdf-fallback"
    else:
        raise RuntimeError(f"No PDF fallback library is installed. Install Marker with: {MARKER_INSTALL}")

    nonempty = sum(1 for page in pages if len(page.strip()) > len("## Page 1"))
    text_body = "\n".join(pages).strip()
    if not text_body or nonempty == 0:
        raise RuntimeError(
            "No extractable text found. This is probably a scanned document; install Marker and rerun with --force-ocr."
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown_header(source, engine) + text_body + "\n", encoding="utf-8")
    return output


def convert(args: argparse.Namespace) -> int:
    source = Path(args.input).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"Input file not found: {source}")

    engine = args.engine
    if engine == "auto":
        engine = "marker" if marker_command() else "fallback"

    try:
        if engine == "marker":
            result = run_marker(
                source=source,
                output=output,
                force_ocr=args.force_ocr,
                page_range=args.page_range,
                keep_images=args.keep_images,
            )
        elif engine == "fallback":
            result = run_pdf_fallback(source, output)
        else:
            raise ValueError(f"Unknown engine: {engine}")
    except Exception as exc:
        if args.engine == "auto" and engine == "marker":
            print(f"WARNING Marker failed: {exc}", file=sys.stderr)
            print("Falling back to searchable-PDF text extraction.", file=sys.stderr)
            result = run_pdf_fallback(source, output)
        else:
            raise

    print(f"Markdown: {result}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert source documents to Markdown for podcastfy-free.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("preflight", help="Check Marker and fallback document extraction dependencies.")

    conv = subparsers.add_parser("convert", help="Convert a document to Markdown.")
    conv.add_argument("--input", required=True, help="Source file path.")
    conv.add_argument("--output", required=True, help="Markdown output path.")
    conv.add_argument("--engine", choices=["auto", "marker", "fallback"], default="auto")
    conv.add_argument("--force-ocr", action="store_true", help="Pass --force_ocr to Marker.")
    conv.add_argument("--page-range", default=None, help='Marker page range, for example "0,5-10,20".')
    conv.add_argument("--keep-images", action="store_true", help="Keep Marker's image extraction enabled.")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "preflight":
        return preflight()
    if args.command == "convert":
        return convert(args)
    parser.error(f"Unhandled command: {args.command}")
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        raise SystemExit(1)
