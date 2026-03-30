#!/usr/bin/env python3
"""Build an SRT subtitle draft from voiceover segments and generated audio."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any


SENTENCE_BREAKS = "。！？；"
CLAUSE_BREAKS = "，、："
TRAILING_PUNCTUATION = SENTENCE_BREAKS + CLAUSE_BREAKS + "…,.!?;:"
DEFAULT_SILENCE_NOISE_DB = "-35dB"
DEFAULT_MIN_SILENCE_SECONDS = 0.12
MIN_CUE_DURATION_SECONDS = 0.8


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", help="Media package root directory.")
    parser.add_argument("--content-id", help="Content package id under the media-ops root.")
    parser.add_argument(
        "--media-ops-root",
        help="Root directory containing media packages. Defaults to repo-local data/media-ops.",
    )
    parser.add_argument(
        "--segments-file",
        help="Segments JSON path, relative to project root. Defaults to voiceover-profile render target.",
    )
    parser.add_argument(
        "--segment-audio-dir",
        help="Per-segment audio directory, relative to project root. Defaults to minimax-output/tmp.",
    )
    parser.add_argument(
        "--voiceover-audio",
        help="Merged voiceover audio path, relative to project root. Defaults to voiceover-profile render target.",
    )
    parser.add_argument(
        "--output",
        help="Subtitle output path, relative to project root. Defaults to voiceover-profile render target.",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=20,
        help="Preferred maximum characters per subtitle cue.",
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


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def load_segments(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("segments file must contain a JSON array")
    return [item for item in payload if isinstance(item, dict) and isinstance(item.get("text"), str) and item["text"].strip()]


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


def detect_silence_ranges(
    path: Path,
    *,
    noise_db: str = DEFAULT_SILENCE_NOISE_DB,
    min_silence_seconds: float = DEFAULT_MIN_SILENCE_SECONDS,
) -> list[tuple[float, float]]:
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(path),
            "-af",
            f"silencedetect=noise={noise_db}:d={min_silence_seconds}",
            "-f",
            "null",
            "-",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    stderr = result.stderr or ""
    starts = [float(match.group(1)) for match in re.finditer(r"silence_start:\s*([0-9.]+)", stderr)]
    ends = [float(match.group(1)) for match in re.finditer(r"silence_end:\s*([0-9.]+)", stderr)]
    ranges: list[tuple[float, float]] = []
    for start, end in zip(starts, ends, strict=False):
        if end <= start:
            continue
        ranges.append((start, end))
    return ranges


def normalize_text(text: str) -> str:
    cleaned = text.replace("\n", " ")
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    cleaned = re.sub(r"\s+", "", cleaned)
    return cleaned.strip()


def split_long_fragment(fragment: str, max_chars: int) -> list[str]:
    fragment = fragment.strip()
    if not fragment:
        return []
    if len(fragment) <= max_chars:
        return [fragment]

    parts = re.findall(rf"[^{re.escape(CLAUSE_BREAKS)}]+(?:[{re.escape(CLAUSE_BREAKS)}]+|$)", fragment)
    refined_parts = [part.strip() for part in parts if part.strip()]
    if len(refined_parts) == 1 and len(refined_parts[0]) > max_chars:
        return [refined_parts[0][index : index + max_chars] for index in range(0, len(refined_parts[0]), max_chars)]

    chunks: list[str] = []
    current = ""
    for part in refined_parts:
        proposed = f"{current}{part}"
        if current and len(proposed) > max_chars:
            chunks.append(current)
            current = part
            continue
        current = proposed
    if current:
        chunks.append(current)
    return chunks


def build_cue_texts(text: str, max_chars: int) -> list[str]:
    cleaned = normalize_text(text)
    if not cleaned:
        return []

    fragments = re.findall(rf"[^{re.escape(SENTENCE_BREAKS)}]+(?:[{re.escape(SENTENCE_BREAKS)}]+|$)", cleaned)
    fragments = [fragment.strip() for fragment in fragments if fragment.strip()]

    cues: list[str] = []
    for fragment in fragments:
        cues.extend(split_long_fragment(fragment, max_chars))

    merged: list[str] = []
    current = ""
    for cue in cues:
        proposed = f"{current}{cue}"
        if current and len(proposed) > max_chars:
            merged.append(current)
            current = cue
            continue
        current = proposed
    if current:
        merged.append(current)

    return [cue.strip() for cue in merged if cue.strip()]


def cue_weight(text: str) -> int:
    stripped = re.sub(rf"[{re.escape(TRAILING_PUNCTUATION)}]", "", text)
    return max(len(stripped), 1)


def resolve_segment_audio_paths(
    *,
    segments: list[dict[str, Any]],
    segment_audio_dir: Path | None,
) -> list[Path | None]:
    if segment_audio_dir and segment_audio_dir.exists():
        audio_files = sorted(segment_audio_dir.glob("segment_*.mp3"))
        if len(audio_files) == len(segments):
            return [path.resolve() for path in audio_files]
    return [None] * len(segments)


def read_segment_durations(
    *,
    segments: list[dict[str, Any]],
    segment_audio_dir: Path | None,
    voiceover_audio: Path | None,
) -> list[float]:
    durations: list[float] | None = None

    if segment_audio_dir and segment_audio_dir.exists():
        audio_files = sorted(segment_audio_dir.glob("segment_*.mp3"))
        if len(audio_files) == len(segments):
            durations = [ffprobe_duration(path) for path in audio_files]

    if durations is None:
        explicit = [item.get("duration_seconds") for item in segments]
        if explicit and all(isinstance(item, (float, int)) for item in explicit):
            durations = [float(item) for item in explicit]

    if durations is None:
        weights = [cue_weight(normalize_text(segment["text"])) for segment in segments]
        total_weight = sum(weights) or 1
        total_duration = ffprobe_duration(voiceover_audio) if voiceover_audio and voiceover_audio.exists() else len(segments) * 4.0
        durations = [total_duration * weight / total_weight for weight in weights]

    if voiceover_audio and voiceover_audio.exists():
        total_duration = ffprobe_duration(voiceover_audio)
        measured_total = sum(durations)
        if measured_total > 0:
            scale = total_duration / measured_total
            durations = [duration * scale for duration in durations]

    return durations


def allocate_cue_durations(cues: list[str], segment_duration: float) -> list[float]:
    weights = [cue_weight(cue) for cue in cues]
    total_weight = sum(weights) or 1
    raw = [segment_duration * weight / total_weight for weight in weights]
    with_floor = [max(duration, MIN_CUE_DURATION_SECONDS) for duration in raw]
    total = sum(with_floor)
    if total <= 0:
        return []
    scale = segment_duration / total if segment_duration > 0 else 1.0
    return [duration * scale for duration in with_floor]


def target_boundaries_from_durations(cue_durations: list[float]) -> list[float]:
    cursor = 0.0
    boundaries: list[float] = []
    for duration in cue_durations[:-1]:
        cursor += duration
        boundaries.append(cursor)
    return boundaries


def silence_midpoints_for_segment(
    *,
    audio_path: Path | None,
    segment_duration: float,
    min_cue_duration_seconds: float = MIN_CUE_DURATION_SECONDS,
) -> list[float]:
    if audio_path is None or not audio_path.exists():
        return []

    raw_duration = ffprobe_duration(audio_path)
    if raw_duration <= 0:
        return []

    ranges = detect_silence_ranges(audio_path)
    if not ranges:
        return []

    scale = segment_duration / raw_duration if raw_duration > 0 else 1.0
    midpoints: list[float] = []
    for start, end in ranges:
        midpoint = ((start + end) / 2.0) * scale
        if midpoint < min_cue_duration_seconds:
            continue
        if midpoint > segment_duration - min_cue_duration_seconds:
            continue
        if midpoints and abs(midpoint - midpoints[-1]) < 0.05:
            continue
        midpoints.append(midpoint)
    return midpoints


def choose_silence_boundaries(
    *,
    candidate_boundaries: list[float],
    target_boundaries: list[float],
    segment_duration: float,
    min_cue_duration_seconds: float = MIN_CUE_DURATION_SECONDS,
) -> list[float]:
    boundary_count = len(target_boundaries)
    if boundary_count == 0:
        return []
    if len(candidate_boundaries) < boundary_count:
        return []

    infinity = float("inf")
    costs = [[infinity] * len(candidate_boundaries) for _ in range(boundary_count)]
    parents = [[-1] * len(candidate_boundaries) for _ in range(boundary_count)]

    for cue_index in range(boundary_count):
        remaining_slots = boundary_count - cue_index
        for candidate_index, boundary in enumerate(candidate_boundaries):
            if boundary < min_cue_duration_seconds:
                continue
            if segment_duration - boundary < min_cue_duration_seconds * remaining_slots:
                continue

            penalty = abs(boundary - target_boundaries[cue_index])
            if cue_index == 0:
                costs[cue_index][candidate_index] = penalty
                continue

            best_parent_cost = infinity
            best_parent_index = -1
            for parent_index in range(candidate_index):
                parent_boundary = candidate_boundaries[parent_index]
                if boundary - parent_boundary < min_cue_duration_seconds:
                    continue
                parent_cost = costs[cue_index - 1][parent_index]
                if parent_cost < best_parent_cost:
                    best_parent_cost = parent_cost
                    best_parent_index = parent_index

            if best_parent_index >= 0:
                costs[cue_index][candidate_index] = best_parent_cost + penalty
                parents[cue_index][candidate_index] = best_parent_index

    final_cost = infinity
    final_index = -1
    for candidate_index, cost in enumerate(costs[-1]):
        if cost < final_cost:
            final_cost = cost
            final_index = candidate_index

    if final_index < 0 or final_cost == infinity:
        return []

    selected = [0.0] * boundary_count
    cursor = final_index
    for cue_index in range(boundary_count - 1, -1, -1):
        selected[cue_index] = candidate_boundaries[cursor]
        cursor = parents[cue_index][cursor]
    return selected


def cue_durations_from_boundaries(boundaries: list[float], segment_duration: float) -> list[float]:
    if not boundaries:
        return [segment_duration] if segment_duration > 0 else []

    durations: list[float] = []
    cursor = 0.0
    for boundary in boundaries:
        durations.append(max(boundary - cursor, 0.0))
        cursor = boundary
    durations.append(max(segment_duration - cursor, 0.0))
    return durations


def allocate_cue_durations_with_audio(
    *,
    cues: list[str],
    segment_duration: float,
    audio_path: Path | None,
) -> list[float]:
    fallback = allocate_cue_durations(cues, segment_duration)
    if len(cues) <= 1:
        return fallback

    target_boundaries = target_boundaries_from_durations(fallback)
    candidate_boundaries = silence_midpoints_for_segment(
        audio_path=audio_path,
        segment_duration=segment_duration,
    )
    chosen_boundaries = choose_silence_boundaries(
        candidate_boundaries=candidate_boundaries,
        target_boundaries=target_boundaries,
        segment_duration=segment_duration,
    )
    if not chosen_boundaries:
        return fallback

    aligned = cue_durations_from_boundaries(chosen_boundaries, segment_duration)
    if len(aligned) != len(cues):
        return fallback
    return aligned


def format_timestamp(seconds: float) -> str:
    bounded = max(seconds, 0.0)
    total_milliseconds = int(round(bounded * 1000))
    hours, remainder = divmod(total_milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def relative_to_project(path: Path, project_root: Path) -> str:
    return str(path.resolve().relative_to(project_root.resolve()))


def build_srt_payload(
    segments: list[dict[str, Any]],
    segment_durations: list[float],
    max_chars: int,
    segment_audio_paths: list[Path | None] | None = None,
) -> tuple[str, int, float]:
    cursor = 0.0
    blocks: list[str] = []
    cue_index = 1

    for index, (segment, segment_duration) in enumerate(zip(segments, segment_durations, strict=True)):
        cue_texts = build_cue_texts(segment["text"], max_chars=max_chars)
        if not cue_texts:
            continue
        audio_path = segment_audio_paths[index] if segment_audio_paths and index < len(segment_audio_paths) else None
        cue_durations = allocate_cue_durations_with_audio(
            cues=cue_texts,
            segment_duration=segment_duration,
            audio_path=audio_path,
        )
        for cue_text, cue_duration in zip(cue_texts, cue_durations, strict=True):
            start = cursor
            end = cursor + cue_duration
            blocks.append(
                "\n".join(
                    [
                        str(cue_index),
                        f"{format_timestamp(start)} --> {format_timestamp(end)}",
                        cue_text,
                    ]
                )
            )
            cursor = end
            cue_index += 1

    return "\n\n".join(blocks) + ("\n" if blocks else ""), cue_index - 1, cursor


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)
    profile_path = project_root / "content" / "postproduction" / "voiceover-profile.json"
    voiceover_profile = load_json(profile_path)
    render_targets = voiceover_profile.get("render_targets") if isinstance(voiceover_profile.get("render_targets"), dict) else {}

    segments_path = resolve_candidate(project_root, args.segments_file or render_targets.get("segments_file"))
    if segments_path is None:
        segments_path = (project_root / "content" / "postproduction" / "voiceover-segments.json").resolve()
    if not segments_path.exists():
        raise FileNotFoundError(f"segments file missing: {segments_path}")

    voiceover_audio = resolve_candidate(project_root, args.voiceover_audio or render_targets.get("voiceover_audio"))
    segment_audio_dir = resolve_candidate(project_root, args.segment_audio_dir) or (
        voiceover_audio.parent / "tmp" if voiceover_audio is not None else (project_root / "content" / "postproduction" / "minimax-output" / "tmp")
    )
    output_path = resolve_candidate(project_root, args.output or render_targets.get("subtitle_draft"))
    if output_path is None:
        output_path = (project_root / "content" / "postproduction" / "subtitles.srt").resolve()

    segments = load_segments(segments_path)
    segment_audio_paths = resolve_segment_audio_paths(segments=segments, segment_audio_dir=segment_audio_dir)
    segment_durations = read_segment_durations(
        segments=segments,
        segment_audio_dir=segment_audio_dir,
        voiceover_audio=voiceover_audio if voiceover_audio and voiceover_audio.exists() else None,
    )
    srt_payload, cue_count, total_duration = build_srt_payload(
        segments,
        segment_durations,
        max_chars=args.max_chars,
        segment_audio_paths=segment_audio_paths,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(srt_payload, encoding="utf-8")

    print(
        json.dumps(
            {
                "segments_file": str(segments_path),
                "subtitle_output": str(output_path),
                "cue_count": cue_count,
                "duration_seconds": round(total_duration, 3),
                "voiceover_audio": str(voiceover_audio) if voiceover_audio else None,
                "segment_audio_dir": relative_to_project(segment_audio_dir, project_root)
                if segment_audio_dir.exists()
                else None,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
