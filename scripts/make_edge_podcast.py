#!/usr/bin/env python
"""Create a free dialogue podcast from a Podcastfy-style transcript.

The preferred path uses Podcastfy's transcript input with Edge TTS. The direct
path uses edge-tts and ffmpeg/pydub as a lightweight fallback.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple


DEFAULT_VOICE1 = "zh-CN-XiaoxiaoNeural"
DEFAULT_VOICE2 = "zh-CN-YunxiNeural"
EN_VOICE1 = "en-US-JennyNeural"
EN_VOICE2 = "en-US-EricNeural"


Segment = Tuple[str, str]


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def normalize_transcript(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:text|xml|markdown)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)

    if re.search(r"<Person[12]>", text):
        segments = parse_segments(text)
        return "\n".join(f"<{speaker}>{content}</{speaker}>" for speaker, content in segments)

    converted: List[str] = []
    label_pattern = re.compile(
        r"^\s*(?:Person\s*([12])|主持人\s*([AB])|嘉宾\s*([AB])|([AB]))\s*[：:]\s*(.+?)\s*$",
        flags=re.I,
    )
    for line in text.splitlines():
        match = label_pattern.match(line)
        if not match:
            continue
        person_digit, host_letter, guest_letter, bare_letter, content = match.groups()
        letter = (host_letter or guest_letter or bare_letter or "").upper()
        speaker = "Person1" if person_digit == "1" or letter == "A" else "Person2"
        converted.append(f"<{speaker}>{content.strip()}</{speaker}>")

    if not converted:
        raise ValueError(
            "Transcript has no Person tags. Use <Person1>...</Person1> and <Person2>...</Person2>."
        )
    return "\n".join(converted)


def parse_segments(text: str) -> List[Segment]:
    pattern = re.compile(r"<(Person[12])>(.*?)</\1>", flags=re.DOTALL | re.I)
    segments: List[Segment] = []
    for match in pattern.finditer(text):
        speaker = "Person1" if match.group(1).lower() == "person1" else "Person2"
        content = " ".join(match.group(2).split()).strip()
        if content:
            segments.append((speaker, content))
    if not segments:
        raise ValueError("No non-empty <Person1>/<Person2> segments found.")
    return segments


def validate_segments(segments: Sequence[Segment]) -> List[str]:
    warnings: List[str] = []
    for index in range(1, len(segments)):
        if segments[index][0] == segments[index - 1][0]:
            warnings.append(
                f"Adjacent turns {index} and {index + 1} both use {segments[index][0]}."
            )
    for index, (_, content) in enumerate(segments, 1):
        if len(content) > 260:
            warnings.append(f"Turn {index} is long for TTS ({len(content)} characters).")
    return warnings


def write_normalized_transcript(transcript: Path, output: Path | None) -> Tuple[Path, List[Segment]]:
    normalized = normalize_transcript(transcript.read_text(encoding="utf-8"))
    segments = parse_segments(normalized)
    target = output or transcript.with_suffix(".normalized.txt")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(normalized + "\n", encoding="utf-8")
    return target, segments


def voice_defaults(language: str) -> Tuple[str, str]:
    if language.lower().startswith("en"):
        return EN_VOICE1, EN_VOICE2
    return DEFAULT_VOICE1, DEFAULT_VOICE2


def preflight() -> int:
    checks = [
        ("python", sys.version.split()[0], True),
        ("podcastfy", "installed" if module_available("podcastfy") else "missing", module_available("podcastfy")),
        ("edge_tts", "installed" if module_available("edge_tts") else "missing", module_available("edge_tts")),
        ("pydub", "installed" if module_available("pydub") else "missing", module_available("pydub")),
        ("ffmpeg", shutil.which("ffmpeg") or "missing", shutil.which("ffmpeg") is not None),
    ]
    for name, value, ok in checks:
        status = "OK" if ok else "MISSING"
        print(f"{status:7} {name}: {value}")

    print("\nFree path requirements:")
    print("- Direct Edge synthesis needs edge_tts.")
    print("- pydub or ffmpeg is recommended for cleaner multi-turn MP3 merging; otherwise byte-append fallback is used.")
    print("- Podcastfy engine needs podcastfy installed; no API key is required for --tts-model edge with an existing transcript.")
    print("\nInstall hints:")
    print("python -m pip install podcastfy edge-tts pydub")
    print("winget install Gyan.FFmpeg")
    return 0


def synthesize_with_podcastfy(
    transcript: Path,
    output: Path,
    voice1: str,
    voice2: str,
    language: str,
) -> Path:
    from podcastfy.client import process_content

    work_dir = output.parent
    config = {
        "conversation_style": ["engaging", "clear", "conversational"],
        "roles_person1": "main explainer",
        "roles_person2": "curious listener",
        "dialogue_structure": ["Introduction", "Main Content", "Closing"],
        "podcast_name": "Audio Blog",
        "podcast_tagline": "",
        "output_language": language,
        "engagement_techniques": ["questions", "analogies", "short transitions"],
        "creativity": 0.7,
        "user_instructions": "",
        "text_to_speech": {
            "default_tts_model": "edge",
            "output_directories": {
                "transcripts": str(work_dir / "transcripts"),
                "audio": str(work_dir / "audio"),
            },
            "edge": {
                "default_voices": {
                    "question": voice1,
                    "answer": voice2,
                }
            },
            "audio_format": "mp3",
            "ending_message": "",
        },
    }
    result = process_content(
        transcript_file=str(transcript),
        tts_model="edge",
        generate_audio=True,
        conversation_config=config,
    )
    if not result:
        raise RuntimeError("Podcastfy did not return an audio path.")
    result_path = Path(result)
    output.parent.mkdir(parents=True, exist_ok=True)
    if result_path.resolve() != output.resolve():
        shutil.move(str(result_path), str(output))
    return output


async def edge_save(text: str, voice: str, target: Path) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(target))


def merge_with_pydub(files: Sequence[Path], output: Path) -> None:
    from pydub import AudioSegment

    combined = AudioSegment.empty()
    for file_path in files:
        combined += AudioSegment.from_file(str(file_path), format="mp3")
    output.parent.mkdir(parents=True, exist_ok=True)
    combined.export(str(output), format="mp3")


def quote_for_ffmpeg_list(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace("'", "'\\''")


def merge_with_ffmpeg(files: Sequence[Path], output: Path, tmp_dir: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is not available.")
    list_file = tmp_dir / "concat.txt"
    list_file.write_text(
        "".join(f"file '{quote_for_ffmpeg_list(path)}'\n" for path in files),
        encoding="utf-8",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-c",
        "copy",
        str(output),
    ]
    subprocess.run(cmd, check=True)


def merge_by_byte_append(files: Sequence[Path], output: Path) -> None:
    """Last-resort MP3 concatenation.

    Most players tolerate sequential MP3 frame appends. Prefer pydub or ffmpeg
    when available because they produce cleaner duration metadata.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as out_file:
        for file_path in files:
            out_file.write(file_path.read_bytes())


def synthesize_direct(
    segments: Sequence[Segment],
    output: Path,
    voice1: str,
    voice2: str,
) -> Path:
    if not module_available("edge_tts"):
        raise RuntimeError("edge_tts is missing. Install with: python -m pip install edge-tts")

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="podcastfy_free_") as temp:
        tmp_dir = Path(temp)
        audio_files: List[Path] = []
        for index, (speaker, content) in enumerate(segments, 1):
            voice = voice1 if speaker == "Person1" else voice2
            target = tmp_dir / f"{index:04d}_{speaker}_{uuid.uuid4().hex}.mp3"
            asyncio.run(edge_save(content, voice, target))
            audio_files.append(target)

        if len(audio_files) == 1:
            shutil.copyfile(audio_files[0], output)
        elif module_available("pydub"):
            merge_with_pydub(audio_files, output)
        elif shutil.which("ffmpeg"):
            merge_with_ffmpeg(audio_files, output, tmp_dir)
        else:
            print(
                "WARNING pydub and ffmpeg are unavailable; using last-resort MP3 byte append.",
                file=sys.stderr,
            )
            merge_by_byte_append(audio_files, output)
    return output


def synthesize(args: argparse.Namespace) -> int:
    transcript = Path(args.transcript).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    if not transcript.exists():
        raise FileNotFoundError(f"Transcript not found: {transcript}")

    default_voice1, default_voice2 = voice_defaults(args.language)
    voice1 = args.voice1 or default_voice1
    voice2 = args.voice2 or default_voice2
    normalized_path = Path(args.normalized_transcript).expanduser().resolve() if args.normalized_transcript else None
    normalized, segments = write_normalized_transcript(transcript, normalized_path)

    warnings = validate_segments(segments)
    for warning in warnings:
        print(f"WARNING {warning}", file=sys.stderr)

    engine = args.engine
    if engine == "auto":
        engine = "podcastfy" if module_available("podcastfy") else "direct"

    try:
        if engine == "podcastfy":
            result = synthesize_with_podcastfy(normalized, output, voice1, voice2, args.language)
        elif engine == "direct":
            result = synthesize_direct(segments, output, voice1, voice2)
        else:
            raise ValueError(f"Unknown engine: {engine}")
    except Exception as exc:
        if args.engine == "auto" and engine == "podcastfy":
            print(f"WARNING Podcastfy engine failed: {exc}", file=sys.stderr)
            print("Falling back to direct Edge TTS.", file=sys.stderr)
            result = synthesize_direct(segments, output, voice1, voice2)
        else:
            raise

    print(f"Transcript: {normalized}")
    print(f"Audio: {result}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create free Edge TTS podcasts from Podcastfy transcripts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("preflight", help="Check local dependencies and print install hints.")

    synth = subparsers.add_parser("synthesize", help="Synthesize an MP3 from a transcript.")
    synth.add_argument("--transcript", required=True, help="Path to a Person1/Person2 transcript.")
    synth.add_argument("--output", required=True, help="Path to the MP3 output file.")
    synth.add_argument("--engine", choices=["auto", "podcastfy", "direct"], default="auto")
    synth.add_argument("--language", default="zh-CN", help="Language hint for default voices.")
    synth.add_argument("--voice1", default=None, help="Edge voice for Person1.")
    synth.add_argument("--voice2", default=None, help="Edge voice for Person2.")
    synth.add_argument("--normalized-transcript", default=None, help="Optional path for normalized transcript output.")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "preflight":
        return preflight()
    if args.command == "synthesize":
        return synthesize(args)
    parser.error(f"Unhandled command: {args.command}")
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        raise SystemExit(1)
