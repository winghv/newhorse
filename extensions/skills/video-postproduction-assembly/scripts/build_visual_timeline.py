#!/usr/bin/env python3
"""Build a deterministic base cut from graphics, proof assets, and approved footage."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm"}
IMAGE_RATIO_WARNING_THRESHOLD = 0.72
VIDEO_RATIO_WARNING_THRESHOLD = 0.2
MAX_IMAGE_SLOT_DURATION_SECONDS = 8.0
MAX_AVERAGE_SLOT_DURATION_SECONDS = 6.5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", help="Media package root directory.")
    parser.add_argument("--content-id", help="Content package id under the media-ops root.")
    parser.add_argument(
        "--media-ops-root",
        help="Root directory containing media packages. Defaults to repo-local data/media-ops.",
    )
    parser.add_argument(
        "--voiceover-audio",
        help="Merged voiceover audio path, relative to project root. Defaults to voiceover-profile render target.",
    )
    parser.add_argument(
        "--subtitles",
        help="Subtitle path, relative to project root. Used to derive visual change cadence when present.",
    )
    parser.add_argument(
        "--output-video",
        default="content/postproduction/auto-base-cut.mp4",
        help="Base cut output path, relative to project root.",
    )
    parser.add_argument(
        "--plan-output",
        default="content/postproduction/auto-base-cut-plan.json",
        help="Plan output path, relative to project root.",
    )
    parser.add_argument("--width", type=int, default=1920, help="Output width.")
    parser.add_argument("--height", type=int, default=1080, help="Output height.")
    parser.add_argument("--fps", type=int, default=30, help="Output fps.")
    parser.add_argument("--crf", type=int, default=22, help="Output CRF.")
    parser.add_argument("--preset", default="ultrafast", help="Output encoding preset.")
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


def relative_to_project(path: Path, project_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_root.resolve()))
    except ValueError:
        return str(path.resolve())


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


def run_command(command: list[str]) -> None:
    subprocess.run(command, check=True, capture_output=True, text=True)


def ffprobe_json(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def media_duration(path: Path) -> float:
    payload = ffprobe_json(path)
    duration = payload.get("format", {}).get("duration")
    if duration is None:
        raise ValueError(f"Unable to read duration from {path}")
    return float(duration)


def parse_timestamp(value: str) -> float:
    hours, minutes, rest = value.split(":")
    seconds, milliseconds = rest.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000


def parse_srt(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []

    blocks = re.split(r"\n\s*\n", text)
    cues: list[dict[str, Any]] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3 or "-->" not in lines[1]:
            continue
        start_raw, end_raw = [part.strip() for part in lines[1].split("-->")]
        start = parse_timestamp(start_raw)
        end = parse_timestamp(end_raw)
        cues.append(
            {
                "start": start,
                "end": end,
                "duration": max(end - start, 0.0),
                "text": " ".join(lines[2:]),
            }
        )
    return cues


def build_slots(cues: list[dict[str, Any]], total_duration: float) -> list[dict[str, float]]:
    if cues:
        slots: list[dict[str, float]] = []
        current_start = cues[0]["start"]
        current_end = cues[0]["end"]
        for cue in cues[1:]:
            proposed_duration = cue["end"] - current_start
            current_duration = current_end - current_start
            if current_duration >= 4.0 and proposed_duration > 7.5:
                slots.append(
                    {
                        "start": current_start,
                        "end": current_end,
                        "duration": max(current_end - current_start, 0.1),
                    }
                )
                current_start = cue["start"]
            current_end = cue["end"]
        slots.append({"start": current_start, "end": current_end, "duration": max(current_end - current_start, 0.1)})
        if len(slots) >= 2 and slots[-1]["duration"] < 2.0:
            slots[-2]["end"] = slots[-1]["end"]
            slots[-2]["duration"] = slots[-2]["end"] - slots[-2]["start"]
            slots.pop()
        return slots

    slots = []
    cursor = 0.0
    target_slot = 4.5
    while cursor < total_duration:
        remaining = total_duration - cursor
        duration = min(target_slot, remaining)
        slots.append({"start": cursor, "end": cursor + duration, "duration": duration})
        cursor += duration
    return slots


def infer_chapter_from_text(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"Chapter\s*(\d+)", value, flags=re.IGNORECASE)
    if not match:
        return None
    return f"ch{match.group(1)}"


def parse_card_order(path: Path) -> int:
    match = re.search(r"card-(\d+)", path.name)
    return int(match.group(1)) if match else 999


def collect_graphic_assets(project_root: Path) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    graphics_brief = load_json(project_root / "assets" / "graphics" / "graphics-asset-brief.json")
    cards = graphics_brief.get("cards") if isinstance(graphics_brief.get("cards"), list) else []

    for card in cards:
        if not isinstance(card, dict):
            continue
        output_path = resolve_candidate(project_root, card.get("output_path"))
        if output_path is None or not output_path.exists() or output_path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        assets.append(
            {
                "type": "image",
                "path": output_path,
                "chapter_id": infer_chapter_from_text(card.get("evidence")),
                "order": int(card.get("card", parse_card_order(output_path))),
                "role": card.get("role"),
                "source": "graphics-asset-brief",
            }
        )

    if assets:
        return sorted(assets, key=lambda item: (item.get("order", 999), str(item["path"])))

    graphics_dir = project_root / "assets" / "graphics"
    fallback = [
        {
            "type": "image",
            "path": path.resolve(),
            "chapter_id": None,
            "order": parse_card_order(path),
            "role": None,
            "source": "graphics-dir",
        }
        for path in sorted(graphics_dir.glob("card-*.png"))
        if path.is_file()
    ]
    return fallback


def collect_cover_asset(project_root: Path) -> dict[str, Any] | None:
    root_assets = project_root / "assets"
    candidates = sorted(
        path for path in root_assets.glob("*") if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES and "cover" in path.name.lower()
    )
    if not candidates:
        return None
    return {
        "type": "image",
        "path": candidates[0].resolve(),
        "chapter_id": "opening",
        "order": -1,
        "role": "cover",
        "source": "cover",
    }


def collect_proof_assets(project_root: Path) -> list[dict[str, Any]]:
    proof_pack = load_json(project_root / "sources" / "prompt-proof-pack.json")
    prioritized: list[dict[str, Any]] = []
    raw_paths: list[tuple[str, str | None]] = []
    for raw_path in proof_pack.get("primary_render_assets", []):
        if isinstance(raw_path, str):
            raw_paths.append((raw_path, "ch3"))
    for item in proof_pack.get("proof_items", []):
        if isinstance(item, dict) and isinstance(item.get("graphic_binding"), str):
            raw_paths.append((item["graphic_binding"], item.get("chapter_id")))

    seen: set[Path] = set()
    for raw_path, chapter_id in raw_paths:
        candidate = resolve_candidate(project_root, raw_path)
        if candidate is None or not candidate.exists() or candidate.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        prioritized.append(
            {
                "type": "image",
                "path": candidate,
                "chapter_id": chapter_id,
                "order": parse_card_order(candidate),
                "role": "proof",
                "source": "prompt-proof-pack",
            }
        )
    return prioritized


def collect_video_assets(project_root: Path) -> list[dict[str, Any]]:
    source_manifest = load_json(project_root / "sources" / "source-manifest.json")
    manifest_items = source_manifest.get("source_manifest") if isinstance(source_manifest.get("source_manifest"), list) else []
    assets: list[dict[str, Any]] = []
    for item in manifest_items:
        if not isinstance(item, dict) or item.get("license_status") != "approved":
            continue
        candidate = resolve_candidate(project_root, item.get("local_asset_path"))
        if candidate is None or not candidate.exists() or candidate.suffix.lower() not in VIDEO_SUFFIXES:
            continue
        duration_seconds = item.get("duration_seconds")
        assets.append(
            {
                "type": "video",
                "path": candidate,
                "chapter_id": item.get("chapter_id"),
                "clip_id": item.get("clip_id"),
                "duration_seconds": float(duration_seconds) if isinstance(duration_seconds, (int, float)) else media_duration(candidate),
                "source": "source-manifest",
            }
        )
    return sorted(assets, key=lambda item: (item.get("chapter_id") or "zz", item.get("clip_id") or item["path"].name))


def resolve_chapter_order(project_root: Path, assets: list[dict[str, Any]]) -> list[str]:
    content_packet_path = detect_content_packet(project_root)
    content_packet = primary_packet(load_json(content_packet_path))
    chapter_outline = content_packet.get("chapter_outline")
    ordered: list[str] = []
    if isinstance(chapter_outline, list):
        for item in chapter_outline:
            if not isinstance(item, dict):
                continue
            chapter_id = item.get("chapter_id")
            if isinstance(chapter_id, str) and chapter_id and chapter_id not in ordered:
                ordered.append(chapter_id)

    if ordered:
        return ordered

    for asset in assets:
        chapter_id = asset.get("chapter_id")
        if isinstance(chapter_id, str) and chapter_id.startswith("ch") and chapter_id not in ordered:
            ordered.append(chapter_id)
    return ordered


def build_chapter_targets(
    slots: list[dict[str, float]],
    chapter_order: list[str],
    assets: list[dict[str, Any]],
    has_cover: bool,
) -> list[str | None]:
    if not slots:
        return []

    targets: list[str | None] = []
    if has_cover:
        targets.append("opening")

    remaining_slots = len(slots) - len(targets)
    if remaining_slots <= 0:
        return targets[: len(slots)]
    if not chapter_order:
        targets.extend([None] * remaining_slots)
        return targets

    weights = {chapter_id: 1 for chapter_id in chapter_order}
    for asset in assets:
        chapter_id = asset.get("chapter_id")
        if chapter_id not in weights:
            continue
        weights[chapter_id] += 1
        if asset.get("type") == "video":
            weights[chapter_id] += 1
        if asset.get("role") == "proof":
            weights[chapter_id] += 2
        if asset.get("role") == "running-example":
            weights[chapter_id] += 1

    quotas = {chapter_id: 0 for chapter_id in chapter_order}
    if remaining_slots >= len(chapter_order):
        for chapter_id in chapter_order:
            quotas[chapter_id] = 1
        remaining_slots -= len(chapter_order)

    total_weight = sum(weights.values()) or 1
    fractional: list[tuple[float, str]] = []
    for chapter_id in chapter_order:
        raw = remaining_slots * (weights[chapter_id] / total_weight)
        whole = int(raw)
        quotas[chapter_id] += whole
        fractional.append((raw - whole, chapter_id))

    distributed = sum(quotas.values())
    remainder = len(slots) - len(targets) - distributed
    for _, chapter_id in sorted(fractional, reverse=True):
        if remainder <= 0:
            break
        quotas[chapter_id] += 1
        remainder -= 1

    for chapter_id in chapter_order:
        targets.extend([chapter_id] * quotas[chapter_id])

    if len(targets) < len(slots):
        targets.extend([chapter_order[-1]] * (len(slots) - len(targets)))
    return targets[: len(slots)]


def interleave_assets(
    *,
    cover_asset: dict[str, Any] | None,
    proof_assets: list[dict[str, Any]],
    graphic_assets: list[dict[str, Any]],
    video_assets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    ordered: list[dict[str, Any]] = []
    seen: set[Path] = set()

    def append_asset(asset: dict[str, Any] | None) -> None:
        if asset is None:
            return
        path = asset["path"]
        if path in seen:
            return
        seen.add(path)
        ordered.append(asset)

    append_asset(cover_asset)
    for index in range(max(len(graphic_assets), len(video_assets))):
        if index < len(graphic_assets):
            append_asset(graphic_assets[index])
        if index < len(video_assets):
            append_asset(video_assets[index])
    for asset in proof_assets:
        append_asset(asset)
    return ordered


def motion_profile(slot_index: int, role: str | None, duration: float) -> dict[str, Any]:
    if role == "cover":
        preset = "push_right"
        zoom_ratio = 1.12
    elif role == "proof":
        preset = "push_left"
        zoom_ratio = 1.12
    else:
        presets = ("push_right", "push_left", "tilt_down", "tilt_up", "diagonal_down", "diagonal_up")
        preset = presets[slot_index % len(presets)]
        zoom_ratio = 1.08

    if duration >= 7.0:
        zoom_ratio += 0.02

    return {
        "preset": preset,
        "zoom_ratio": round(zoom_ratio, 3),
    }


def assign_assets(
    slots: list[dict[str, float]],
    assets: list[dict[str, Any]],
    chapter_targets: list[str | None],
) -> list[dict[str, Any]]:
    if not assets:
        raise FileNotFoundError("No visual assets available for rebuild_timeline source generation.")

    sequence: list[dict[str, Any]] = []
    use_counts: dict[Path, int] = defaultdict(int)
    last_used_slot: dict[Path, int] = {}

    def can_cover(asset: dict[str, Any], duration: float) -> bool:
        if asset["type"] == "image":
            return True
        return float(asset.get("duration_seconds", 0.0)) + 0.05 >= duration

    def consecutive_type_count(asset_type: str) -> int:
        count = 0
        for item in reversed(sequence):
            if item["asset_type"] != asset_type:
                break
            count += 1
        return count

    def choose_asset(index: int, duration: float, target_chapter: str | None) -> dict[str, Any]:
        consecutive_images = consecutive_type_count("image")
        previous_type = sequence[-1]["asset_type"] if sequence else None
        previous_target = sequence[-1].get("target_chapter") if sequence else None

        best_asset: dict[str, Any] | None = None
        best_score: tuple[float, float, float, float] | None = None

        for order_index, candidate in enumerate(assets):
            if not can_cover(candidate, duration):
                continue

            score = 0.0
            candidate_chapter = candidate.get("chapter_id")
            candidate_role = candidate.get("role")
            candidate_type = candidate["type"]
            previous_distance = index - last_used_slot[candidate["path"]] if candidate["path"] in last_used_slot else 99

            if target_chapter == "opening":
                score += 120 if candidate_role == "cover" else -80
            elif target_chapter and candidate_chapter == target_chapter:
                score += 60
            elif target_chapter and candidate_chapter is None:
                score += 6
            elif target_chapter and candidate_chapter == previous_target:
                score += 4
            elif target_chapter and candidate_chapter not in {None, target_chapter}:
                score -= 10

            if target_chapter == "ch3":
                if candidate_role == "proof" and use_counts[candidate["path"]] == 0:
                    score += 45
                elif candidate_role == "running-example":
                    score += 30

            if target_chapter == "ch4":
                if candidate_role == "framework-overview":
                    score += 24
                elif candidate_role == "walkthrough":
                    score += 20
                elif candidate_role == "step-card":
                    score += 16

            if candidate_type == "video":
                score += 16
                if consecutive_images >= 2:
                    score += 22
                if previous_type == "video":
                    score -= 8
                coverage_margin = float(candidate.get("duration_seconds", duration)) - duration
                score += min(max(coverage_margin, 0.0), 6.0)
            else:
                if consecutive_images >= 2:
                    score -= 18
                elif consecutive_images == 1:
                    score -= 6
                if candidate_role == "proof":
                    score += 12

            if previous_type == candidate_type:
                score -= 10

            if previous_distance < 4:
                score -= (4 - previous_distance) * 10
            else:
                score += min(previous_distance, 8)

            score -= use_counts[candidate["path"]] * 4

            tie_breaker = (
                score,
                1.0 if candidate_type == "video" else 0.0,
                1.0 if candidate_role == "proof" else 0.0,
                -float(order_index),
            )
            if best_score is None or tie_breaker > best_score:
                best_score = tie_breaker
                best_asset = candidate

        if best_asset is not None:
            return best_asset

        for candidate in assets:
            if candidate["type"] == "image":
                return candidate
        return assets[0]

    for index, slot in enumerate(slots):
        target_chapter = chapter_targets[index] if index < len(chapter_targets) else None
        asset = choose_asset(index, slot["duration"], target_chapter)
        use_count = use_counts[asset["path"]]
        use_counts[asset["path"]] += 1
        last_used_slot[asset["path"]] = index

        clip_start = 0.0
        if asset["type"] == "video":
            duration_seconds = float(asset.get("duration_seconds", slot["duration"]))
            max_offset = max(duration_seconds - slot["duration"], 0.0)
            if max_offset > 0:
                clip_start = round(min((use_count * 1.618) % max_offset, max_offset), 3)

        sequence.append(
            {
                "slot_index": index,
                "slot_start": round(slot["start"], 3),
                "slot_end": round(slot["end"], 3),
                "slot_duration": round(slot["duration"], 3),
                "asset_type": asset["type"],
                "asset_path": asset["path"],
                "clip_start": clip_start,
                "chapter_id": asset.get("chapter_id"),
                "target_chapter": target_chapter,
                "asset_source": asset.get("source"),
                "role": asset.get("role"),
                "clip_id": asset.get("clip_id"),
                "motion_preset": None,
                "motion_zoom_ratio": None,
            }
        )
        if asset["type"] == "image":
            motion = motion_profile(index, asset.get("role"), slot["duration"])
            sequence[-1]["motion_preset"] = motion["preset"]
            sequence[-1]["motion_zoom_ratio"] = motion["zoom_ratio"]

    return sequence


def quote_concat_path(path: Path) -> str:
    return str(path).replace("'", "'\\''")


def even_int(value: float) -> int:
    rounded = int(round(value))
    return rounded if rounded % 2 == 0 else rounded + 1


def image_filter(
    *,
    width: int,
    height: int,
    fps: int,
    duration: float,
    motion_preset: str | None,
    motion_zoom_ratio: float | None,
) -> str:
    fade_out_start = max(duration - 0.2, 0.0)
    zoom_ratio = motion_zoom_ratio or 1.08
    overscan_width = even_int(width * zoom_ratio)
    overscan_height = even_int(height * zoom_ratio)
    spare_x = max(overscan_width - width, 2)
    spare_y = max(overscan_height - height, 2)
    frame_denominator = max(int(round(duration * fps)) - 1, 1)

    if motion_preset == "push_left":
        x_expr = f"({spare_x}*(1-n/{frame_denominator}))"
        y_expr = f"{spare_y}/2"
    elif motion_preset == "tilt_down":
        x_expr = f"{spare_x}/2"
        y_expr = f"({spare_y}*n/{frame_denominator})"
    elif motion_preset == "tilt_up":
        x_expr = f"{spare_x}/2"
        y_expr = f"({spare_y}*(1-n/{frame_denominator}))"
    elif motion_preset == "diagonal_down":
        x_expr = f"({spare_x}*n/{frame_denominator})"
        y_expr = f"({spare_y}*n/{frame_denominator})"
    elif motion_preset == "diagonal_up":
        x_expr = f"({spare_x}*(1-n/{frame_denominator}))"
        y_expr = f"({spare_y}*(1-n/{frame_denominator}))"
    else:
        x_expr = f"({spare_x}*n/{frame_denominator})"
        y_expr = f"{spare_y}/2"

    return (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,"
        f"setsar=1,"
        f"scale={overscan_width}:{overscan_height},"
        f"crop={width}:{height}:x={x_expr}:y={y_expr},"
        f"fps={fps},format=yuv420p,"
        f"fade=t=in:st=0:d=0.2,fade=t=out:st={fade_out_start:.3f}:d=0.2"
    )


def video_filter(*, width: int, height: int, fps: int, duration: float) -> str:
    fade_out_start = max(duration - 0.2, 0.0)
    return (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},setsar=1,fps={fps},format=yuv420p,"
        f"fade=t=in:st=0:d=0.2,fade=t=out:st={fade_out_start:.3f}:d=0.2"
    )


def render_sequence(
    *,
    sequence: list[dict[str, Any]],
    output_video: Path,
    width: int,
    height: int,
    fps: int,
    crf: int,
    preset: str,
) -> None:
    output_video.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="auto-base-cut-") as temp_dir_raw:
        temp_dir = Path(temp_dir_raw)
        clip_paths: list[Path] = []

        for item in sequence:
            clip_path = temp_dir / f"clip-{item['slot_index']:04d}.mp4"
            duration = float(item["slot_duration"])
            asset_path = Path(item["asset_path"])
            if item["asset_type"] == "image":
                command = [
                    "ffmpeg",
                    "-y",
                    "-loop",
                    "1",
                    "-i",
                    str(asset_path),
                    "-t",
                    f"{duration:.3f}",
                    "-vf",
                    image_filter(
                        width=width,
                        height=height,
                        fps=fps,
                        duration=duration,
                        motion_preset=item.get("motion_preset"),
                        motion_zoom_ratio=item.get("motion_zoom_ratio"),
                    ),
                    "-an",
                    "-c:v",
                    "libx264",
                    "-preset",
                    preset,
                    "-crf",
                    str(crf),
                    "-pix_fmt",
                    "yuv420p",
                    str(clip_path),
                ]
            else:
                command = [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    f"{float(item['clip_start']):.3f}",
                    "-t",
                    f"{duration:.3f}",
                    "-i",
                    str(asset_path),
                    "-vf",
                    video_filter(width=width, height=height, fps=fps, duration=duration),
                    "-an",
                    "-c:v",
                    "libx264",
                    "-preset",
                    preset,
                    "-crf",
                    str(crf),
                    "-pix_fmt",
                    "yuv420p",
                    str(clip_path),
                ]
            run_command(command)
            clip_paths.append(clip_path)

        concat_file = temp_dir / "concat.txt"
        concat_file.write_text(
            "\n".join(f"file '{quote_concat_path(path)}'" for path in clip_paths) + "\n",
            encoding="utf-8",
        )
        run_command(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                preset,
                "-crf",
                str(crf),
                "-pix_fmt",
                "yuv420p",
                str(output_video),
            ]
        )


def build_quality_report(sequence: list[dict[str, Any]], *, proof_assets_available: bool) -> dict[str, Any]:
    slot_count = len(sequence)
    image_slots = [item for item in sequence if item["asset_type"] == "image"]
    video_slots = [item for item in sequence if item["asset_type"] == "video"]
    proof_slots = [item for item in sequence if item.get("role") == "proof"]
    image_slot_ratio = (len(image_slots) / slot_count) if slot_count else 0.0
    video_slot_ratio = (len(video_slots) / slot_count) if slot_count else 0.0
    average_slot_duration = (sum(float(item["slot_duration"]) for item in sequence) / slot_count) if slot_count else 0.0
    max_image_slot_duration = max((float(item["slot_duration"]) for item in image_slots), default=0.0)
    image_motion_enabled_count = sum(1 for item in image_slots if item.get("motion_preset"))
    longest_consecutive_image_slots = 0
    current_image_run = 0
    target_aligned_slots = 0
    chapter_targeted_slots = 0
    for item in sequence:
        if item["asset_type"] == "image":
            current_image_run += 1
            longest_consecutive_image_slots = max(longest_consecutive_image_slots, current_image_run)
        else:
            current_image_run = 0

        target_chapter = item.get("target_chapter")
        if isinstance(target_chapter, str) and target_chapter.startswith("ch"):
            chapter_targeted_slots += 1
            if item.get("chapter_id") in {target_chapter, None}:
                target_aligned_slots += 1
    longform_gate_enabled = slot_count >= 6
    warnings: list[str] = []
    status = "pass"

    if longform_gate_enabled and image_slot_ratio > IMAGE_RATIO_WARNING_THRESHOLD:
        warnings.append("image_ratio_high")
        status = "revise"
    if max_image_slot_duration > MAX_IMAGE_SLOT_DURATION_SECONDS:
        warnings.append("image_hold_too_long")
        status = "revise"
    if average_slot_duration > MAX_AVERAGE_SLOT_DURATION_SECONDS:
        warnings.append("average_slot_too_long")
        status = "revise"
    if image_slots and image_motion_enabled_count != len(image_slots):
        warnings.append("image_motion_missing")
        status = "revise"
    if longform_gate_enabled and slot_count and video_slot_ratio < VIDEO_RATIO_WARNING_THRESHOLD:
        warnings.append("video_ratio_low")
    if proof_assets_available and proof_slots == []:
        warnings.append("proof_slots_missing")
    if longform_gate_enabled and longest_consecutive_image_slots > 5:
        warnings.append("consecutive_image_run_too_long")
        status = "revise"

    return {
        "status": status,
        "metrics": {
            "slot_count": slot_count,
            "image_slot_count": len(image_slots),
            "video_slot_count": len(video_slots),
            "proof_slot_count": len(proof_slots),
            "image_slot_ratio": round(image_slot_ratio, 3),
            "video_slot_ratio": round(video_slot_ratio, 3),
            "average_slot_duration_seconds": round(average_slot_duration, 3),
            "max_image_slot_duration_seconds": round(max_image_slot_duration, 3),
            "image_motion_enabled_count": image_motion_enabled_count,
            "longest_consecutive_image_slots": longest_consecutive_image_slots,
            "chapter_target_alignment_ratio": round(
                (target_aligned_slots / chapter_targeted_slots) if chapter_targeted_slots else 1.0,
                3,
            ),
            "longform_gate_enabled": longform_gate_enabled,
        },
        "thresholds": {
            "image_slot_ratio_warning": IMAGE_RATIO_WARNING_THRESHOLD,
            "video_slot_ratio_warning": VIDEO_RATIO_WARNING_THRESHOLD,
            "max_image_slot_duration_seconds": MAX_IMAGE_SLOT_DURATION_SECONDS,
            "max_average_slot_duration_seconds": MAX_AVERAGE_SLOT_DURATION_SECONDS,
        },
        "warnings": warnings,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)
    voiceover_profile = load_json(project_root / "content" / "postproduction" / "voiceover-profile.json")
    render_targets = voiceover_profile.get("render_targets") if isinstance(voiceover_profile.get("render_targets"), dict) else {}

    voiceover_audio = resolve_candidate(project_root, args.voiceover_audio or render_targets.get("voiceover_audio"))
    if voiceover_audio is None or not voiceover_audio.exists():
        raise FileNotFoundError("voiceover audio is required to build a rebuild_timeline source video")
    subtitles = resolve_candidate(project_root, args.subtitles or render_targets.get("subtitle_draft"))
    output_video = resolve_candidate(project_root, args.output_video)
    plan_output = resolve_candidate(project_root, args.plan_output)
    if output_video is None or plan_output is None:
        raise ValueError("output_video and plan_output must resolve to concrete filesystem paths")

    cover_asset = collect_cover_asset(project_root)
    proof_assets = collect_proof_assets(project_root)
    graphic_assets = collect_graphic_assets(project_root)
    video_assets = collect_video_assets(project_root)
    assets = interleave_assets(
        cover_asset=cover_asset,
        proof_assets=proof_assets,
        graphic_assets=graphic_assets,
        video_assets=video_assets,
    )

    total_duration = media_duration(voiceover_audio)
    cues = parse_srt(subtitles)
    slots = build_slots(cues, total_duration)
    chapter_order = resolve_chapter_order(project_root, assets)
    chapter_targets = build_chapter_targets(slots, chapter_order, assets, has_cover=cover_asset is not None)
    sequence = assign_assets(slots, assets, chapter_targets)
    quality = build_quality_report(sequence, proof_assets_available=bool(proof_assets))
    render_sequence(
        sequence=sequence,
        output_video=output_video,
        width=args.width,
        height=args.height,
        fps=args.fps,
        crf=args.crf,
        preset=args.preset,
    )

    payload = {
        "project_root": str(project_root),
        "voiceover_audio": relative_to_project(voiceover_audio, project_root),
        "subtitles": relative_to_project(subtitles, project_root) if subtitles and subtitles.exists() else None,
        "output_video": relative_to_project(output_video, project_root),
        "slot_count": len(sequence),
        "asset_count": len(assets),
        "duration_seconds": round(total_duration, 3),
        "chapter_order": chapter_order,
        "quality": quality,
        "sequence": [
            {
                **{key: value for key, value in item.items() if key != "asset_path"},
                "asset_path": relative_to_project(Path(item["asset_path"]), project_root),
            }
            for item in sequence
        ],
    }
    write_json(plan_output, payload)
    print(
        json.dumps(
            {
                "output_video": str(output_video),
                "plan_output": str(plan_output),
                "slot_count": len(sequence),
                "asset_count": len(assets),
                "quality_status": payload["quality"]["status"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
