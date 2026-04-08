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
TRANSLATION_SENTENCE_BREAKS = ".!?;"
TRANSLATION_CLAUSE_BREAKS = ",:;"


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


def detect_content_packet(project_root: Path) -> Path | None:
    content_dir = project_root / "content"
    if not content_dir.exists():
        return None
    prioritized = ["*video.json", "content-packet.json", "*.json"]
    for pattern in prioritized:
        matches = sorted(path for path in content_dir.glob(pattern) if path.is_file())
        if matches:
            return matches[0]
    return None


def primary_packet(payload: dict[str, Any]) -> dict[str, Any]:
    nested = payload.get("content_packet")
    return nested if isinstance(nested, dict) else payload


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
    for start, end in zip(starts, ends):
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


def normalize_translation_text(text: str) -> str:
    cleaned = text.replace("\n", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def resolve_translation_text(segment: dict[str, Any], translation_map: dict[str, str]) -> str:
    translation_payload = segment.get("subtitle_translation")
    if isinstance(translation_payload, dict):
        english = translation_payload.get("en")
        if isinstance(english, str) and english.strip():
            return normalize_translation_text(english)

    for key in ("translation_en", "english_text", "translation"):
        value = segment.get(key)
        if isinstance(value, str) and value.strip():
            return normalize_translation_text(value)

    segment_text = normalize_text(str(segment.get("text") or ""))
    mapped = translation_map.get(segment_text)
    return normalize_translation_text(mapped) if mapped else ""


def resolve_explicit_translation_cues(segment: dict[str, Any]) -> list[str] | None:
    for key in ("translation_cues", "translation_lines"):
        value = segment.get(key)
        if not isinstance(value, list):
            continue
        cues = [normalize_translation_text(str(item)) for item in value if str(item).strip()]
        if cues:
            return cues
    return None


def merge_translation_fragments(fragments: list[str], cue_count: int) -> list[str]:
    if cue_count <= 0:
        return []
    if not fragments:
        return [""] * cue_count
    if cue_count == 1:
        return [" ".join(fragment for fragment in fragments if fragment).strip()]

    chunk_count = min(max(cue_count, 1), len(fragments))
    merged: list[str] = []
    start_index = 0
    for index in range(chunk_count):
        end_index = round((index + 1) * len(fragments) / chunk_count)
        part = " ".join(fragment for fragment in fragments[start_index:end_index] if fragment).strip()
        merged.append(part)
        start_index = end_index

    while len(merged) < cue_count:
        merged.append("")
    return merged[:cue_count]


def split_translation_evenly(text: str, cue_count: int) -> list[str]:
    cleaned = normalize_translation_text(text)
    if cue_count <= 0:
        return []
    if not cleaned:
        return [""] * cue_count
    if cue_count == 1:
        return [cleaned]

    fragments = re.findall(
        rf"[^{re.escape(TRANSLATION_SENTENCE_BREAKS)}]+(?:[{re.escape(TRANSLATION_SENTENCE_BREAKS)}]+|$)",
        cleaned,
    )
    fragments = [fragment.strip() for fragment in fragments if fragment.strip()]
    if len(fragments) >= cue_count:
        return merge_translation_fragments(fragments, cue_count)

    clause_fragments = re.findall(
        rf"[^{re.escape(TRANSLATION_CLAUSE_BREAKS)}]+(?:[{re.escape(TRANSLATION_CLAUSE_BREAKS)}]+|$)",
        cleaned,
    )
    clause_fragments = [fragment.strip() for fragment in clause_fragments if fragment.strip()]
    if len(clause_fragments) >= cue_count:
        return merge_translation_fragments(clause_fragments, cue_count)

    words = cleaned.split()
    if not words:
        return [""] * cue_count
    chunks: list[str] = []
    start_index = 0
    for index in range(cue_count):
        end_index = round((index + 1) * len(words) / cue_count)
        if end_index <= start_index and start_index < len(words):
            end_index = start_index + 1
        chunks.append(" ".join(words[start_index:end_index]).strip())
        start_index = min(end_index, len(words))
    return chunks


def translation_cues_for_segment(
    segment: dict[str, Any],
    cue_count: int,
    translation_map: dict[str, str],
) -> list[str]:
    if cue_count <= 0:
        return []

    explicit_cues = resolve_explicit_translation_cues(segment)
    if explicit_cues:
        cues = explicit_cues[:cue_count]
        while len(cues) < cue_count:
            cues.append("")
        return cues

    translation_text = resolve_translation_text(segment, translation_map)
    return split_translation_evenly(translation_text, cue_count)


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


def read_raw_segment_durations(segment_audio_paths: list[Path | None]) -> list[float] | None:
    if not segment_audio_paths or any(path is None or not path.exists() for path in segment_audio_paths):
        return None
    return [ffprobe_duration(path) for path in segment_audio_paths if path is not None]


def infer_crossfade_seconds(raw_segment_durations: list[float], voiceover_audio: Path | None) -> float:
    if voiceover_audio is None or not voiceover_audio.exists() or len(raw_segment_durations) < 2:
        return 0.0

    merged_duration = ffprobe_duration(voiceover_audio)
    total_raw_duration = sum(raw_segment_durations)
    total_overlap = total_raw_duration - merged_duration
    if total_overlap <= 0:
        return 0.0

    inferred = total_overlap / max(len(raw_segment_durations) - 1, 1)
    # Guard against pathological inference from odd encodes.
    max_reasonable = min(raw_segment_durations) * 0.5
    return max(0.0, min(inferred, max_reasonable))


def build_segment_timeline_from_audio(
    *,
    segments: list[dict[str, Any]],
    segment_audio_paths: list[Path | None],
    voiceover_audio: Path | None,
) -> tuple[list[float], list[float], dict[str, Any]] | None:
    raw_segment_durations = read_raw_segment_durations(segment_audio_paths)
    if raw_segment_durations is None:
        return None

    inferred_crossfade_seconds = infer_crossfade_seconds(raw_segment_durations, voiceover_audio)
    pause_durations = [
        max(float(segment.get("pause_after_ms", 0) or 0), 0.0) / 1000.0 if index < len(raw_segment_durations) - 1 else 0.0
        for index, segment in enumerate(segments)
    ]
    starts: list[float] = []
    cursor = 0.0
    for index, duration in enumerate(raw_segment_durations):
        if index == 0:
            starts.append(0.0)
            cursor = duration + pause_durations[index]
            continue
        cursor -= inferred_crossfade_seconds
        starts.append(max(cursor, 0.0))
        cursor += duration + pause_durations[index]

    durations = list(raw_segment_durations)
    expected_total = starts[-1] + durations[-1] if starts and durations else 0.0
    merged_duration = ffprobe_duration(voiceover_audio) if voiceover_audio and voiceover_audio.exists() else expected_total
    if expected_total > 0 and merged_duration > 0:
        scale = merged_duration / expected_total
        starts = [start * scale for start in starts]
        durations = [duration * scale for duration in durations]

    return (
        starts,
        durations,
        {
            "alignment_mode": "segment_audio_forced",
            "inferred_crossfade_seconds": round(inferred_crossfade_seconds, 3),
            "total_pause_seconds": round(sum(pause_durations), 3),
            "merged_duration_seconds": round(merged_duration, 3),
        },
    )


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
    bilingual_enabled: bool,
    translation_map: dict[str, str],
    segment_audio_paths: list[Path | None] | None = None,
    segment_start_times: list[float] | None = None,
) -> tuple[str, int, float, int, int]:
    cursor = 0.0
    blocks: list[str] = []
    cue_index = 1
    translated_cue_count = 0
    missing_translation_segment_count = 0

    if len(segments) != len(segment_durations):
        raise ValueError("segments and segment_durations must have the same length")

    for index, (segment, segment_duration) in enumerate(zip(segments, segment_durations)):
        segment_start = segment_start_times[index] if segment_start_times and index < len(segment_start_times) else cursor
        cue_texts = build_cue_texts(segment["text"], max_chars=max_chars)
        if not cue_texts:
            continue
        translation_cues = translation_cues_for_segment(segment, len(cue_texts), translation_map) if bilingual_enabled else []
        if bilingual_enabled and not any(item.strip() for item in translation_cues):
            missing_translation_segment_count += 1
        audio_path = segment_audio_paths[index] if segment_audio_paths and index < len(segment_audio_paths) else None
        cue_durations = allocate_cue_durations_with_audio(
            cues=cue_texts,
            segment_duration=segment_duration,
            audio_path=audio_path,
        )
        if len(cue_texts) != len(cue_durations):
            raise ValueError("cue_texts and cue_durations must have the same length")
        cue_cursor = segment_start
        for cue_offset, (cue_text, cue_duration) in enumerate(zip(cue_texts, cue_durations)):
            start = cue_cursor
            end = cue_cursor + cue_duration
            translation_line = (
                translation_cues[cue_offset].strip()
                if cue_offset < len(translation_cues) and isinstance(translation_cues[cue_offset], str)
                else ""
            )
            subtitle_lines = [cue_text]
            if bilingual_enabled and translation_line:
                subtitle_lines.append(translation_line)
                translated_cue_count += 1
            blocks.append(
                "\n".join(
                    [
                        str(cue_index),
                        f"{format_timestamp(start)} --> {format_timestamp(end)}",
                        *subtitle_lines,
                    ]
                )
            )
            cue_cursor = end
            cue_index += 1
        cursor = max(cursor, cue_cursor)

    return (
        "\n\n".join(blocks) + ("\n" if blocks else ""),
        cue_index - 1,
        cursor,
        translated_cue_count,
        missing_translation_segment_count,
    )


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)
    content_packet_path = detect_content_packet(project_root)
    content_packet = primary_packet(load_json(content_packet_path)) if content_packet_path else {}
    subtitle_package = (
        content_packet.get("subtitle_package") if isinstance(content_packet.get("subtitle_package"), dict) else {}
    )
    style_pack = load_json(project_root / "content" / "postproduction" / "subtitle-style-pack.json")
    translation_map_raw = subtitle_package.get("translation_map") if isinstance(subtitle_package.get("translation_map"), dict) else {}
    translation_map = {
        normalize_text(str(key)): normalize_translation_text(str(value.get("en") if isinstance(value, dict) else value))
        for key, value in translation_map_raw.items()
        if str(key).strip() and str(value.get("en") if isinstance(value, dict) else value).strip()
    }
    bilingual_enabled = bool(
        subtitle_package.get("translation_required")
        or style_pack.get("translation_required")
        or content_packet.get("deliverable_type") == "midlong-video"
    )
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
    segment_timeline = build_segment_timeline_from_audio(
        segments=segments,
        segment_audio_paths=segment_audio_paths,
        voiceover_audio=voiceover_audio if voiceover_audio and voiceover_audio.exists() else None,
    )
    if segment_timeline is not None:
        segment_start_times, segment_durations, alignment_summary = segment_timeline
    else:
        segment_start_times = None
        segment_durations = read_segment_durations(
            segments=segments,
            segment_audio_dir=segment_audio_dir,
            voiceover_audio=voiceover_audio if voiceover_audio and voiceover_audio.exists() else None,
        )
        alignment_summary = {
            "alignment_mode": "duration_weighted",
            "inferred_crossfade_seconds": 0.0,
            "merged_duration_seconds": round(sum(segment_durations), 3),
        }
    srt_payload, cue_count, total_duration, translated_cue_count, missing_translation_segment_count = build_srt_payload(
        segments,
        segment_durations,
        max_chars=args.max_chars,
        bilingual_enabled=bilingual_enabled,
        translation_map=translation_map,
        segment_audio_paths=segment_audio_paths,
        segment_start_times=segment_start_times,
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
                "alignment_mode": alignment_summary["alignment_mode"],
                "inferred_crossfade_seconds": alignment_summary["inferred_crossfade_seconds"],
                "total_pause_seconds": alignment_summary.get("total_pause_seconds", 0.0),
                "bilingual_enabled": bilingual_enabled,
                "translated_cue_count": translated_cue_count,
                "missing_translation_segment_count": missing_translation_segment_count,
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
