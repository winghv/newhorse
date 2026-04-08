#!/usr/bin/env python3
"""Generate timed voiceover audio from segments, respecting per-segment pause settings."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_TTS_CLI = Path("/Users/mac/.codex/skills/minimax-multimodal-toolkit/scripts/tts/generate_voice.sh")
DEFAULT_TTS_RETRY_ATTEMPTS = 3
DEFAULT_TTS_RETRY_BACKOFF_SECONDS = 2.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", help="Media package root directory.")
    parser.add_argument("--content-id", help="Content package id under the media-ops root.")
    parser.add_argument("--media-ops-root", help="Root directory containing media packages.")
    parser.add_argument("--segments-file", help="Segments JSON path, relative to project root.")
    parser.add_argument("--output", help="Merged voiceover output path, relative to project root.")
    parser.add_argument(
        "--temp-dir",
        help="Intermediate segment directory, relative to project root. Defaults to sibling tmp/ next to output.",
    )
    parser.add_argument(
        "--manifest-output",
        default="content/postproduction/voiceover-generation-manifest.json",
        help="Manifest output path, relative to project root.",
    )
    parser.add_argument(
        "--tts-cli",
        default=str(DEFAULT_TTS_CLI),
        help="Path to the TTS CLI used to synthesize each segment.",
    )
    parser.add_argument(
        "--force-segment-indexes",
        help="Comma-separated segment indexes to force-regenerate even when cached audio exists.",
    )
    args = parser.parse_args()
    if not args.project_root and not args.content_id:
        parser.error("one of --project-root or --content-id is required")
    return args


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def default_media_ops_root() -> Path:
    return repo_root() / "data" / "media-ops"


def resolve_project_root(args: argparse.Namespace) -> Path:
    if args.project_root:
        return Path(args.project_root).resolve()
    media_root = Path(args.media_ops_root).resolve() if args.media_ops_root else default_media_ops_root()
    return (media_root / args.content_id).resolve()


def resolve_candidate(project_root: Path, raw_path: str | None) -> Path | None:
    if not raw_path:
        return None
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = project_root / candidate
    return candidate.resolve()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def relative_to_project(path: Path, project_root: Path) -> str:
    return str(path.resolve().relative_to(project_root.resolve()))


def ffprobe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nk=1:nw=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def parse_force_segment_indexes(raw_value: str | None) -> set[int]:
    if not isinstance(raw_value, str) or not raw_value.strip():
        return set()
    indexes: set[int] = set()
    for token in raw_value.split(","):
        value = token.strip()
        if not value:
            continue
        indexes.add(int(value))
    return indexes


def segment_signature(segment: dict[str, Any], tts_cli: Path) -> str:
    payload = {
        "text": normalize_tts_text(segment.get("text") or ""),
        "voice_id": str(segment.get("voice_id") or "male-qn-qingse"),
        "speed": float(segment.get("speed", 1.0)),
        "volume": float(segment.get("volume", 1.0)),
        "pitch": normalize_pitch(segment.get("pitch", 0)),
        "emotion": str(segment.get("emotion") or "").strip(),
        "model": str(segment.get("model") or "").strip(),
        "tts_cli": str(tts_cli),
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(serialized.encode("utf-8")).hexdigest()


def load_segment_sidecar(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_segment_sidecar(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def segment_audio_ready(path: Path, *, sidecar_path: Path | None = None, expected_signature: str | None = None) -> bool:
    if not path.exists():
        return False
    if sidecar_path is not None and expected_signature:
        sidecar = load_segment_sidecar(sidecar_path)
        recorded_signature = str(sidecar.get("signature") or "").strip()
        if recorded_signature and recorded_signature != expected_signature:
            return False
    try:
        return ffprobe_duration(path) > 0
    except (subprocess.CalledProcessError, ValueError):
        return False


def normalize_pitch(raw_value: Any) -> str:
    try:
        numeric = float(raw_value)
    except (TypeError, ValueError):
        return str(raw_value if raw_value is not None else 0)
    if numeric.is_integer():
        return str(int(numeric))
    return str(numeric)


def normalize_tts_text(raw_text: Any) -> str:
    return re.sub(r"\s+", " ", str(raw_text or "")).strip()


def synthesize_segment(tts_cli: Path, segment: dict[str, Any], output_path: Path) -> None:
    text = normalize_tts_text(segment.get("text") or "")
    command = [
        "bash",
        str(tts_cli),
        "tts",
        text,
        "-v",
        str(segment.get("voice_id") or "male-qn-qingse"),
        "-o",
        str(output_path),
        "--speed",
        str(float(segment.get("speed", 1.0))),
        "--volume",
        str(float(segment.get("volume", 1.0))),
        "--pitch",
        normalize_pitch(segment.get("pitch", 0)),
    ]
    emotion = str(segment.get("emotion") or "").strip()
    if emotion:
        command.extend(["--emotion", emotion])
    model = str(segment.get("model") or "").strip()
    if model:
        command.extend(["--model", model])
    shell_command = " ".join(shlex.quote(part) for part in command)
    last_error: subprocess.CalledProcessError | None = None
    for attempt in range(1, DEFAULT_TTS_RETRY_ATTEMPTS + 1):
        try:
            subprocess.run(
                ["/bin/zsh", "-lc", shell_command],
                check=True,
                capture_output=True,
                text=True,
            )
            return
        except subprocess.CalledProcessError as error:
            last_error = error
            if attempt >= DEFAULT_TTS_RETRY_ATTEMPTS:
                raise
            time.sleep(DEFAULT_TTS_RETRY_BACKOFF_SECONDS * attempt)
    if last_error is not None:
        raise last_error


def create_silence(path: Path, duration_seconds: float) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=32000:cl=mono",
            "-t",
            f"{duration_seconds:.3f}",
            "-c:a",
            "mp3",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def merge_audio_sequence(input_files: list[Path], output_path: Path) -> None:
    command = ["ffmpeg", "-y"]
    filter_inputs: list[str] = []
    for index, input_file in enumerate(input_files):
        command.extend(["-i", str(input_file)])
        filter_inputs.append(f"[{index}:a]")
    filter_complex = "".join(filter_inputs) + f"concat=n={len(input_files)}:v=0:a=1[out]"
    command.extend(
        [
            "-filter_complex",
            filter_complex,
            "-map",
            "[out]",
            "-c:a",
            "mp3",
            str(output_path),
        ]
    )
    subprocess.run(command, check=True, capture_output=True, text=True)


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)
    profile_path = project_root / "content" / "postproduction" / "voiceover-profile.json"
    voiceover_profile = load_json(profile_path) if profile_path.exists() else {}
    render_targets = voiceover_profile.get("render_targets") if isinstance(voiceover_profile.get("render_targets"), dict) else {}

    segments_path = resolve_candidate(project_root, args.segments_file or render_targets.get("segments_file"))
    if segments_path is None or not segments_path.exists():
        raise FileNotFoundError("voiceover segments file is required")

    output_path = resolve_candidate(project_root, args.output or render_targets.get("voiceover_audio"))
    if output_path is None:
        output_path = (project_root / "content" / "postproduction" / "minimax-output" / "voiceover.mp3").resolve()
    temp_dir = resolve_candidate(project_root, args.temp_dir)
    if temp_dir is None:
        temp_dir = (output_path.parent / "tmp").resolve()
    manifest_output = resolve_candidate(project_root, args.manifest_output)
    if manifest_output is None:
        manifest_output = (project_root / "content" / "postproduction" / "voiceover-generation-manifest.json").resolve()

    tts_cli = Path(args.tts_cli).resolve()
    if not tts_cli.exists():
        raise FileNotFoundError(f"TTS CLI not found: {tts_cli}")
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise RuntimeError("ffmpeg and ffprobe are required")
    force_segment_indexes = parse_force_segment_indexes(args.force_segment_indexes)

    raw_segments = load_json(segments_path)
    segments = raw_segments if isinstance(raw_segments, list) else raw_segments.get("segments", [])
    if not isinstance(segments, list) or not segments:
        raise ValueError("segments file must contain a non-empty array")

    temp_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sequence_files: list[Path] = []
    manifest_segments: list[dict[str, Any]] = []
    total_pause_ms = 0

    for index, segment in enumerate(segments):
        if not isinstance(segment, dict) or not str(segment.get("text") or "").strip():
            continue
        segment_output = temp_dir / f"segment_{index:04d}.mp3"
        segment_sidecar = temp_dir / f"segment_{index:04d}.json"
        expected_signature = segment_signature(segment, tts_cli)
        if index in force_segment_indexes or not segment_audio_ready(
            segment_output,
            sidecar_path=segment_sidecar,
            expected_signature=expected_signature,
        ):
            synthesize_segment(tts_cli, segment, segment_output)
        if not segment_sidecar.exists() or str(load_segment_sidecar(segment_sidecar).get("signature") or "") != expected_signature:
            write_segment_sidecar(
                segment_sidecar,
                {
                    "signature": expected_signature,
                    "index": index,
                    "text": normalize_tts_text(segment.get("text") or ""),
                    "voice_id": str(segment.get("voice_id") or "male-qn-qingse"),
                },
            )
        sequence_files.append(segment_output)

        pause_after_ms = max(int(segment.get("pause_after_ms", 0) or 0), 0)
        total_pause_ms += pause_after_ms if index < len(segments) - 1 else 0
        if pause_after_ms > 0 and index < len(segments) - 1:
            silence_path = temp_dir / f"pause_{index:04d}.mp3"
            create_silence(silence_path, pause_after_ms / 1000.0)
            sequence_files.append(silence_path)

        manifest_segments.append(
            {
                "index": index,
                "text": str(segment.get("text") or ""),
                "segment_audio": relative_to_project(segment_output, project_root),
                "segment_duration_seconds": round(ffprobe_duration(segment_output), 3),
                "pause_after_ms": pause_after_ms,
                "signature": expected_signature,
            }
        )

    if not sequence_files:
        raise RuntimeError("no segment audio was generated")

    merge_audio_sequence(sequence_files, output_path)
    payload = {
        "content_id": voiceover_profile.get("content_id") or project_root.name,
        "segments_file": relative_to_project(segments_path, project_root),
        "output_audio": relative_to_project(output_path, project_root),
        "temp_dir": relative_to_project(temp_dir, project_root),
        "tts_cli": str(tts_cli),
        "segment_count": len(manifest_segments),
        "total_pause_ms": total_pause_ms,
        "output_duration_seconds": round(ffprobe_duration(output_path), 3),
        "segments": manifest_segments,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(manifest_output, payload)
    print(
        json.dumps(
            {
                "output_audio": str(output_path),
                "manifest_output": str(manifest_output),
                "segment_count": len(manifest_segments),
                "total_pause_ms": total_pause_ms,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
