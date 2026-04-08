#!/usr/bin/env python3
"""Build a deterministic base cut from graphics, proof assets, and approved footage."""

from __future__ import annotations

import argparse
import functools
import hashlib
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
DISALLOWED_PLAIN_CARD_TYPES = {"graphics-card", "text-card", "text-only-card"}
IMAGE_MOTION_OVERSAMPLE_FACTOR = 2


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
    parser.add_argument("--fps", type=int, default=60, help="Output fps.")
    parser.add_argument("--crf", type=int, default=20, help="Output CRF.")
    parser.add_argument("--preset", default="medium", help="Output encoding preset.")
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


def expand_candidates(project_root: Path, raw_path: str | None) -> list[Path]:
    if not isinstance(raw_path, str) or not raw_path.strip():
        return []
    raw_value = raw_path.strip()
    if any(token in raw_value for token in ("*", "?", "[")):
        pattern = Path(raw_value)
        if pattern.is_absolute():
            search_root = Path(pattern.anchor)
            relative_pattern = str(pattern)[len(pattern.anchor) :]
            matches = sorted(search_root.glob(relative_pattern))
        else:
            matches = sorted(project_root.glob(raw_value))
        return [match.resolve() for match in matches if match.is_file()]

    candidate = resolve_candidate(project_root, raw_value)
    if candidate is None or not candidate.exists() or not candidate.is_file():
        return []
    return [candidate]


def expand_visual_variant_family(project_root: Path, candidate: Path) -> list[Path]:
    resolved = candidate.resolve()
    try:
        relative_path = resolved.relative_to(project_root.resolve())
    except ValueError:
        return [resolved]
    relative_parts = relative_path.parts
    if "visual-prebake" not in relative_parts or "images" not in relative_parts:
        return [resolved]
    stem_match = re.match(r"(.+)_([0-9]+)$", resolved.stem)
    if not stem_match:
        return [resolved]
    family_prefix = stem_match.group(1)
    siblings = sorted(
        item.resolve()
        for item in resolved.parent.glob(f"{family_prefix}_*{resolved.suffix}")
        if item.is_file()
    )
    return siblings or [resolved]


def relative_to_project(path: Path, project_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_root.resolve()))
    except ValueError:
        return str(path.resolve())


def suppress_duplicate_cover(
    cover_asset: dict[str, Any] | None,
    proof_assets: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if cover_asset is None:
        return None
    cover_path = cover_asset.get("path")
    if not isinstance(cover_path, Path) or not cover_path.exists():
        return cover_asset
    try:
        cover_digest = file_content_digest(str(cover_path))
    except OSError:
        return cover_asset
    for candidate in proof_assets:
        candidate_path = candidate.get("path")
        if not isinstance(candidate_path, Path) or not candidate_path.exists():
            continue
        try:
            if file_content_digest(str(candidate_path)) == cover_digest:
                return None
        except OSError:
            continue
    return cover_asset


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


def pure_text_cards_allowed(project_root: Path) -> bool:
    packet_path = detect_content_packet(project_root)
    packet = primary_packet(load_json(packet_path)) if packet_path else {}
    visual_policy = packet.get("visual_policy") if isinstance(packet.get("visual_policy"), dict) else {}
    explicit = visual_policy.get("allow_pure_text_cards")
    if isinstance(explicit, bool):
        return explicit
    return False if packet.get("deliverable_type") == "midlong-video" else True


def run_command(command: list[str]) -> None:
    subprocess.run(command, check=True, capture_output=True, text=True)


@functools.lru_cache(maxsize=None)
def file_content_digest(path_value: str) -> str:
    return hashlib.sha1(Path(path_value).read_bytes()).hexdigest()


@functools.lru_cache(maxsize=None)
def ffmpeg_filter_available(filter_name: str) -> bool:
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-filters"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False
    pattern = re.compile(rf"^\s*[\.A-Z]+\s+{re.escape(filter_name)}(?:\s|$)", flags=re.MULTILINE)
    return bool(pattern.search(result.stdout))


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


def parse_marker_timecode(value: str | None) -> float | None:
    if not isinstance(value, str) or not value.strip():
        return None
    parts = value.strip().split(":")
    try:
        if len(parts) == 2:
            minutes, seconds = parts
            return int(minutes) * 60 + float(seconds)
        if len(parts) == 3:
            hours, minutes, seconds = parts
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    except ValueError:
        return None
    return None


def normalize_text_for_match(value: str | None) -> str:
    raw = str(value or "")
    return "".join(re.findall(r"[0-9A-Za-z\u4e00-\u9fff]+", raw)).lower()


def text_match_score(left: str | None, right: str | None) -> float:
    left_normalized = normalize_text_for_match(left)
    right_normalized = normalize_text_for_match(right)
    if not left_normalized or not right_normalized:
        return 0.0
    if left_normalized in right_normalized or right_normalized in left_normalized:
        return 1.0

    def bigrams(value: str) -> set[str]:
        if len(value) < 2:
            return {value}
        return {value[index : index + 2] for index in range(len(value) - 1)}

    left_tokens = bigrams(left_normalized)
    right_tokens = bigrams(right_normalized)
    overlap = left_tokens & right_tokens
    if not overlap:
        return 0.0
    return len(overlap) / max(len(left_tokens), len(right_tokens))


def effect_text_match_score(effect_text: str | None, subtitle_text: str | None) -> float:
    candidates = [str(effect_text or "")]
    candidates.extend(part.strip() for part in re.split(r"[\\/|]", str(effect_text or "")) if part.strip())
    return max(text_match_score(candidate, subtitle_text) for candidate in candidates if candidate)


def phrase_alignment_offset(effect_text: str | None, subtitle_text: str | None, subtitle_duration: float) -> float:
    effect_normalized = normalize_text_for_match(effect_text)
    subtitle_normalized = normalize_text_for_match(subtitle_text)
    if not effect_normalized or not subtitle_normalized or effect_normalized not in subtitle_normalized:
        return 0.0
    prefix = subtitle_normalized.split(effect_normalized, 1)[0]
    if not prefix:
        return 0.0
    ratio = len(prefix) / max(len(subtitle_normalized), 1)
    return round(ratio * max(float(subtitle_duration), 0.0), 3)


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


def load_generation_video_assets(project_root: Path) -> list[dict[str, Any]]:
    generation_ledger = load_json(project_root / "assets" / "generation-ledger.json")
    entries = generation_ledger.get("entries") if isinstance(generation_ledger.get("entries"), list) else []
    assets: list[dict[str, Any]] = []
    seen_paths: set[Path] = set()
    for item in entries:
        if not isinstance(item, dict):
            continue
        if str(item.get("status") or "").strip().lower() != "success":
            continue
        candidate = resolve_candidate(project_root, item.get("asset_path"))
        if candidate is None or not candidate.exists() or candidate.suffix.lower() not in VIDEO_SUFFIXES:
            continue
        if candidate in seen_paths:
            continue
        seen_paths.add(candidate)
        duration_seconds = item.get("duration_seconds")
        assets.append(
            {
                "type": "video",
                "path": candidate,
                "chapter_id": item.get("chapter_id"),
                "clip_id": item.get("slot_id") or candidate.stem,
                "duration_seconds": float(duration_seconds) if isinstance(duration_seconds, (int, float)) else media_duration(candidate),
                "source": "generation-ledger",
                "source_track": "generated",
                "generation_type": str(item.get("generation_type") or "").strip(),
                "role": "generated-hero",
                "slot_id": item.get("slot_id"),
                "title": str(item.get("reason") or item.get("slot_id") or ""),
                "page_url": "",
                "tags": ["ai-generated", str(item.get("generation_type") or "").strip()],
                "query": str(item.get("reason") or ""),
                "preview_image_url": "",
            }
        )
    return assets


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

    if not pure_text_cards_allowed(project_root):
        return []

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
    scene_asset_plan = load_json(project_root / "assets" / "scene-asset-plan.json")
    prioritized: list[dict[str, Any]] = []
    raw_paths: list[tuple[str, str | None, int | None]] = []
    for raw_path in proof_pack.get("primary_render_assets", []):
        if isinstance(raw_path, str):
            raw_paths.append((raw_path, "ch3", None))
    for item in proof_pack.get("proof_items", []):
        if isinstance(item, dict) and isinstance(item.get("graphic_binding"), str):
            raw_paths.append((item["graphic_binding"], item.get("chapter_id"), None))
    chapters = scene_asset_plan.get("chapters") if isinstance(scene_asset_plan.get("chapters"), list) else []
    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue
        chapter_id = str(chapter.get("chapter_id") or "").strip()
        max_repeat_uses = int(chapter.get("max_repeat_uses", 2))
        proof_asset = chapter.get("proof_asset") if isinstance(chapter.get("proof_asset"), dict) else {}
        proof_asset_path = proof_asset.get("path")
        proof_asset_type = str(proof_asset.get("type") or "").strip()
        if isinstance(proof_asset_path, str) and proof_asset_path.strip():
            if not pure_text_cards_allowed(project_root) and proof_asset_type in DISALLOWED_PLAIN_CARD_TYPES:
                continue
            raw_paths.append((proof_asset_path, chapter_id, max_repeat_uses))
        fallback_graphics = chapter.get("fallback_graphics") if isinstance(chapter.get("fallback_graphics"), list) else []
        for fallback_item in fallback_graphics:
            if isinstance(fallback_item, str) and fallback_item.strip():
                raw_paths.append((fallback_item, chapter_id, max_repeat_uses))

    seen: set[Path] = set()
    for raw_path, chapter_id, max_repeat_uses in raw_paths:
        for candidate in expand_candidates(project_root, raw_path):
            for expanded_candidate in expand_visual_variant_family(project_root, candidate):
                if expanded_candidate.suffix.lower() not in IMAGE_SUFFIXES:
                    continue
                if expanded_candidate in seen:
                    continue
                seen.add(expanded_candidate)
                source = "scene-asset-plan" if chapter_id else "prompt-proof-pack"
                role = "proof"
                candidate_path = expanded_candidate.as_posix()
                if any(token in candidate_path for token in ("generated", "ai-keyframes", "visual-prebake/images")):
                    role = "keyart"
                prioritized.append(
                    {
                        "type": "image",
                        "path": expanded_candidate,
                        "chapter_id": chapter_id,
                        "order": parse_card_order(expanded_candidate),
                        "role": role,
                        "source": source,
                        "max_repeat_uses": max_repeat_uses,
                    }
                )
    return prioritized


def collect_video_assets(project_root: Path) -> list[dict[str, Any]]:
    source_manifest = load_json(project_root / "sources" / "source-manifest.json")
    source_shortlist = load_json(project_root / "sources" / "source-shortlist.json")
    exploration_shortlist = load_json(project_root / "sources" / "exploration-shortlist.json")
    scene_asset_plan = load_json(project_root / "assets" / "scene-asset-plan.json")
    exploration_ingest = load_json(project_root / "sources" / "exploration-ingest-manifest.json")
    manifest_items = source_manifest.get("source_manifest") if isinstance(source_manifest.get("source_manifest"), list) else []
    assets: list[dict[str, Any]] = []
    seen_paths: set[Path] = set()
    metadata_by_clip_id: dict[str, dict[str, Any]] = {}

    shortlist_items: list[dict[str, Any]] = []
    for payload in (source_shortlist, exploration_shortlist, source_manifest):
        shortlist_items.extend([item for item in payload.get("results", []) if isinstance(item, dict)])
        shortlist_items.extend([item for item in payload.get("source_shortlist", []) if isinstance(item, dict)])
    for item in shortlist_items:
        provider = str(item.get("provider") or "")
        provider_asset_id = str(item.get("provider_asset_id") or "")
        title = str(item.get("title") or "")
        page_url = str(item.get("page_url") or "")
        tags = item.get("tags") if isinstance(item.get("tags"), list) else []
        keys = {
            f"{provider}-{provider_asset_id}",
            provider_asset_id,
        }
        for key in keys:
            if key:
                metadata_by_clip_id[key] = {
                    "title": title,
                    "page_url": page_url,
                    "tags": [str(tag) for tag in tags],
                    "query": str(item.get("query") or ""),
                    "preview_image_url": str(item.get("preview_image_url") or ""),
                }

    def append_asset(payload: dict[str, Any]) -> None:
        candidate = resolve_candidate(project_root, payload.get("path"))
        if candidate is None or not candidate.exists() or candidate.suffix.lower() not in VIDEO_SUFFIXES:
            return
        if candidate in seen_paths:
            return
        seen_paths.add(candidate)
        clip_id = payload.get("clip_id")
        metadata = metadata_by_clip_id.get(str(clip_id or ""), {})
        if low_value_video_penalty(
            title=str(metadata.get("title") or ""),
            page_url=str(metadata.get("page_url") or ""),
            tags=metadata.get("tags") if isinstance(metadata.get("tags"), list) else [],
            query=str(metadata.get("query") or ""),
            preview_image_url=str(metadata.get("preview_image_url") or ""),
        ) <= -70:
            return
        duration_seconds = payload.get("duration_seconds")
        assets.append(
            {
                "type": "video",
                "path": candidate,
                "chapter_id": payload.get("chapter_id"),
                "clip_id": clip_id,
                "duration_seconds": float(duration_seconds) if isinstance(duration_seconds, (int, float)) else media_duration(candidate),
                "source": payload.get("source"),
                "source_track": payload.get("source_track"),
                "generation_type": payload.get("generation_type"),
                "role": payload.get("role"),
                "slot_id": payload.get("slot_id"),
                "title": str(metadata.get("title") or ""),
                "page_url": str(metadata.get("page_url") or ""),
                "tags": [str(tag) for tag in metadata.get("tags", [])],
                "query": str(metadata.get("query") or ""),
                "preview_image_url": str(metadata.get("preview_image_url") or ""),
            }
        )

    for item in manifest_items:
        if not isinstance(item, dict) or item.get("license_status") != "approved":
            continue
        append_asset(
            {
                "path": item.get("local_asset_path"),
                "chapter_id": item.get("chapter_id"),
                "clip_id": item.get("clip_id"),
                "duration_seconds": item.get("duration_seconds"),
                "source": "source-manifest",
            }
        )
    chapters = scene_asset_plan.get("chapters") if isinstance(scene_asset_plan.get("chapters"), list) else []
    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue
        chapter_id = chapter.get("chapter_id")
        supporting_b_roll = chapter.get("supporting_b_roll") if isinstance(chapter.get("supporting_b_roll"), list) else []
        for item in supporting_b_roll:
            if not isinstance(item, dict):
                continue
            append_asset(
                {
                    "path": item.get("asset_path"),
                    "chapter_id": chapter_id,
                    "clip_id": item.get("clip_id"),
                    "duration_seconds": item.get("duration_seconds"),
                    "source": "scene-asset-plan",
                    "source_track": item.get("source_track"),
                    "generation_type": item.get("generation_type"),
                    "role": "generated-hero" if str(item.get("source_track") or "") == "generated" else None,
                    "slot_id": item.get("slot_id"),
                }
            )
    ingested_assets = exploration_ingest.get("ingested_assets") if isinstance(exploration_ingest.get("ingested_assets"), list) else []
    for item in ingested_assets:
        if not isinstance(item, dict):
            continue
        append_asset(
            {
                "path": item.get("local_path"),
                "chapter_id": item.get("chapter_id"),
                "clip_id": item.get("clip_id"),
                "duration_seconds": item.get("duration_seconds"),
                "source": "exploration-ingest-manifest",
            }
        )
    for item in load_generation_video_assets(project_root):
        append_asset(item)
    return sorted(assets, key=lambda item: (item.get("chapter_id") or "zz", item.get("clip_id") or item["path"].name))


def low_value_video_penalty(
    *,
    title: str | None,
    page_url: str | None,
    tags: list[str] | None,
    query: str | None = None,
    preview_image_url: str | None = None,
) -> float:
    haystack = " ".join(
        [
            str(title or "").lower(),
            str(page_url or "").lower(),
            " ".join(str(tag).lower() for tag in (tags or [])),
            str(query or "").lower(),
            str(preview_image_url or "").lower(),
        ]
    )
    penalty = 0.0
    if any(token in haystack for token in ("white background", "white screen", "white-background", "white-screen")):
        penalty -= 90.0
    if any(token in haystack for token in ("green screen", "green-screen")):
        penalty -= 75.0
    if "icon set" in haystack or "vector" in haystack:
        penalty -= 45.0
    if any(token in haystack for token in ("sad man", "sad woman", "crying", "despair")) and any(
        token in haystack for token in ("computer", "screen", "message on screen")
    ):
        penalty -= 72.0
    if any(token in haystack for token in ("elderly", "senior", "old man", "old woman", "ageism")):
        penalty -= 58.0
    return penalty


def load_chapter_effects(project_root: Path) -> dict[str, list[dict[str, Any]]]:
    scene_manifest = load_json(project_root / "content" / "postproduction" / "scene-manifest.json")
    emphasis_fx_plan = load_json(project_root / "content" / "postproduction" / "emphasis-fx-plan.json")
    scenes = scene_manifest.get("scenes") if isinstance(scene_manifest.get("scenes"), list) else []
    scene_map = {
        str(scene.get("scene_id") or ""): scene
        for scene in scenes
        if isinstance(scene, dict) and str(scene.get("scene_id") or "")
    }
    effects_by_chapter: dict[str, list[dict[str, Any]]] = {}
    scene_fx = emphasis_fx_plan.get("scene_fx") if isinstance(emphasis_fx_plan.get("scene_fx"), list) else []
    for item in scene_fx:
        if not isinstance(item, dict):
            continue
        scene = scene_map.get(str(item.get("scene_id") or ""))
        if not scene:
            continue
        chapter_id = str(scene.get("chapter_id") or "")
        if not chapter_id:
            continue
        effects = [effect for effect in item.get("effects", []) if isinstance(effect, dict)]
        effects_by_chapter[chapter_id] = effects
    if effects_by_chapter:
        return effects_by_chapter
    for scene in scenes:
        chapter_id = str(scene.get("chapter_id") or "")
        if not chapter_id:
            continue
        effects = [effect for effect in scene.get("emphasis_fx", []) if isinstance(effect, dict)]
        if effects:
            effects_by_chapter[chapter_id] = effects
    return effects_by_chapter


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


def parse_voiceover_script_sections(project_root: Path) -> list[tuple[str, list[str]]]:
    script_path = project_root / "content" / "voiceover-script.md"
    if not script_path.exists():
        return []
    lines = script_path.read_text(encoding="utf-8").splitlines()
    sections: list[tuple[str, list[str]]] = []
    current_title: str | None = None
    current_lines: list[str] = []
    for raw_line in lines:
        line = raw_line.rstrip()
        heading_match = re.match(r"^##\s+(.*)$", line.strip())
        if heading_match:
            if current_title is not None:
                sections.append((current_title, current_lines))
            current_title = heading_match.group(1).strip()
            current_lines = []
            continue
        if current_title is not None:
            current_lines.append(line)
    if current_title is not None:
        sections.append((current_title, current_lines))
    return sections


def content_packet_chapter_outline(project_root: Path) -> list[dict[str, Any]]:
    content_packet_path = detect_content_packet(project_root)
    content_packet = primary_packet(load_json(content_packet_path))
    chapter_outline = content_packet.get("chapter_outline")
    return [item for item in chapter_outline if isinstance(item, dict)] if isinstance(chapter_outline, list) else []


def section_intro_excerpt(lines: list[str]) -> str | None:
    collected: list[str] = []
    for raw_line in lines:
        line = str(raw_line or "").strip()
        if not line or line.startswith("#"):
            continue
        collected.append(line)
        joined = "".join(collected)
        if len(joined) >= 18 and re.search(r"[。！？?!：:]$", line):
            break
        if len(joined) >= 30:
            break
    if not collected:
        return None
    return "".join(collected)


def chapter_outline_reserves_opening_slot(project_root: Path, sections: list[tuple[str, list[str]]], chapter_order: list[str]) -> bool:
    if not sections or not chapter_order:
        return False
    has_opening_section = any(title.strip().lower() == "opening" for title, _ in sections)
    if not has_opening_section:
        return False

    chapter_outline = content_packet_chapter_outline(project_root)
    first_title = str(chapter_outline[0].get("title") or "").strip().lower() if chapter_outline else ""
    opening_title_tokens = ("opening", "intro", "hook", "开场", "引子", "前言")
    if any(token in first_title for token in opening_title_tokens):
        return True

    numbered_section_count = sum(
        1 for title, _ in sections if re.match(r"chapter\s*\d+", title.strip(), flags=re.IGNORECASE)
    )
    has_outro_section = any(title.strip().lower() == "outro" for title, _ in sections)
    expected_outline_without_opening = numbered_section_count + (1 if has_outro_section else 0)
    return len(chapter_order) > expected_outline_without_opening


def infer_script_marker_chapters(
    project_root: Path,
    *,
    chapter_order: list[str],
    has_cover: bool,
    subtitle_cues: list[dict[str, Any]],
) -> list[tuple[float, str | None]] | None:
    if not subtitle_cues:
        return None
    sections = parse_voiceover_script_sections(project_root)
    if not sections:
        return None

    has_opening_section = any(title.strip().lower() == "opening" for title, _ in sections)
    opening_reserved_in_outline = chapter_outline_reserves_opening_slot(project_root, sections, chapter_order)
    planned_sections: list[tuple[str, str]] = []
    for title, body_lines in sections:
        excerpt = section_intro_excerpt(body_lines)
        if not excerpt:
            continue
        normalized_title = title.strip().lower()
        chapter_target: str | None = None
        if normalized_title == "opening":
            chapter_target = chapter_order[0] if chapter_order else ("opening" if has_cover else None)
        elif normalized_title == "outro":
            chapter_target = chapter_order[-1] if chapter_order else None
        else:
            match = re.match(r"chapter\s*(\d+)", title.strip(), flags=re.IGNORECASE)
            if match:
                chapter_index = int(match.group(1)) - 1
                if has_opening_section and opening_reserved_in_outline:
                    chapter_index += 1
                if 0 <= chapter_index < len(chapter_order):
                    chapter_target = chapter_order[chapter_index]
        if chapter_target:
            planned_sections.append((chapter_target, excerpt))

    if not planned_sections:
        return None

    marker_chapters: list[tuple[float, str | None]] = []
    previous_start = 0.0
    for target, excerpt in planned_sections:
        if target == "opening":
            marker_chapters.append((0.0, "opening"))
            previous_start = 0.0
            continue
        best_cue: dict[str, Any] | None = None
        best_score = 0.0
        for cue in subtitle_cues:
            cue_start = float(cue.get("start", 0.0))
            if cue_start + 0.01 < previous_start:
                continue
            score = text_match_score(excerpt, cue.get("text"))
            if score > best_score:
                best_score = score
                best_cue = cue
        if best_cue is None or best_score < 0.2:
            return None
        cue_start = float(best_cue.get("start", 0.0))
        marker_chapters.append((cue_start, target))
        previous_start = cue_start

    return marker_chapters or None


def chapter_targets_from_markers(
    project_root: Path,
    *,
    slots: list[dict[str, float]],
    chapter_order: list[str],
    has_cover: bool,
    subtitle_cues: list[dict[str, Any]] | None = None,
) -> list[str | None] | None:
    content_packet_path = detect_content_packet(project_root)
    content_packet = primary_packet(load_json(content_packet_path))
    chapter_markers = content_packet.get("chapter_markers")
    marker_chapters: list[tuple[float, str | None]] = []
    if isinstance(chapter_markers, list) and chapter_markers:
        parsed_markers: list[tuple[float, str]] = []
        for item in chapter_markers:
            if not isinstance(item, dict):
                continue
            start_seconds = parse_marker_timecode(item.get("timecode"))
            if start_seconds is None:
                continue
            parsed_markers.append((start_seconds, str(item.get("title") or "")))
        if parsed_markers:
            parsed_markers.sort(key=lambda item: item[0])
            if has_cover and parsed_markers and parsed_markers[0][0] <= 0.01 and len(parsed_markers) >= len(chapter_order) + 1:
                for index, chapter_id in enumerate(chapter_order, start=1):
                    if index >= len(parsed_markers):
                        break
                    marker_chapters.append((parsed_markers[index][0], chapter_id))
            else:
                for index, chapter_id in enumerate(chapter_order):
                    if index >= len(parsed_markers):
                        break
                    marker_chapters.append((parsed_markers[index][0], chapter_id))
                if has_cover and marker_chapters and marker_chapters[0][0] > 0.01:
                    marker_chapters.insert(0, (0.0, "opening"))

    if not marker_chapters:
        marker_chapters = infer_script_marker_chapters(
            project_root,
            chapter_order=chapter_order,
            has_cover=has_cover,
            subtitle_cues=subtitle_cues or [],
        ) or []

    if not marker_chapters:
        return None

    targets: list[str | None] = []
    for slot_index, slot in enumerate(slots):
        if has_cover and slot_index == 0:
            targets.append("opening")
            continue
        slot_start = float(slot["start"])
        chosen_target: str | None = marker_chapters[0][1]
        for marker_start, marker_target in marker_chapters:
            if slot_start + 0.01 >= marker_start:
                chosen_target = marker_target
            else:
                break
        targets.append(chosen_target)
    return targets


def build_chapter_targets(
    slots: list[dict[str, float]],
    chapter_order: list[str],
    assets: list[dict[str, Any]],
    has_cover: bool,
    *,
    project_root: Path | None = None,
    subtitle_cues: list[dict[str, Any]] | None = None,
) -> list[str | None]:
    if not slots:
        return []

    if project_root is not None:
        marker_targets = chapter_targets_from_markers(
            project_root,
            slots=slots,
            chapter_order=chapter_order,
            has_cover=has_cover,
            subtitle_cues=subtitle_cues,
        )
        if marker_targets is not None:
            return marker_targets

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
    for index in range(max(len(proof_assets), len(video_assets), len(graphic_assets))):
        if index < len(proof_assets):
            append_asset(proof_assets[index])
        if index < len(video_assets):
            append_asset(video_assets[index])
        if index < len(graphic_assets):
            append_asset(graphic_assets[index])
    return ordered


def motion_profile(
    slot_index: int,
    role: str | None,
    duration: float,
    *,
    asset_type: str,
    asset_path: Path,
    effects: list[dict[str, Any]],
) -> dict[str, Any]:
    directional_presets = ("push_right", "push_left", "tilt_down", "tilt_up", "diagonal_down", "diagonal_up")
    push_intensity = next(
        (str(effect.get("intensity") or "medium") for effect in effects if effect.get("type") == "camera_push"),
        "medium",
    )
    if asset_type == "image" and asset_path.name.startswith("card-"):
        return {
            "preset": "static_hold",
            "zoom_ratio": 1.0,
        }

    if asset_type == "image" and role not in {"cover", "proof", "keyart", "running-example"}:
        return {
            "preset": "static_hold",
            "zoom_ratio": 1.0,
        }

    if role == "cover":
        preset = "push_right"
        zoom_ratio = 1.135
    elif role in {"proof", "keyart"}:
        motion_seed = sum(ord(char) for char in asset_path.stem) + slot_index + (19 if role == "keyart" else 7)
        preset = directional_presets[motion_seed % len(directional_presets)]
        zoom_ratio = 1.072 if asset_type == "image" else 1.095
    else:
        preset = directional_presets[slot_index % len(directional_presets)]
        zoom_ratio = 1.105 if asset_type == "video" else 1.066

    if duration >= 7.0:
        zoom_ratio += 0.018
    if push_intensity == "high":
        zoom_ratio += 0.02
    elif push_intensity == "medium":
        zoom_ratio += 0.01

    max_zoom_ratio = 1.14 if asset_type == "image" else 1.18
    return {
        "preset": preset,
        "zoom_ratio": round(min(zoom_ratio, max_zoom_ratio), 3),
    }


def motion_progress_expressions(frame_denominator: int) -> tuple[str, str]:
    linear_progress = f"(n/{frame_denominator})"
    eased_progress = f"(0.5-0.5*cos(PI*{linear_progress}))"
    blended_progress = f"(({linear_progress}*0.34)+({eased_progress}*0.66))"
    return blended_progress, f"(1-{blended_progress})"


def assign_assets(
    slots: list[dict[str, float]],
    assets: list[dict[str, Any]],
    chapter_targets: list[str | None],
    chapter_effects_by_chapter: dict[str, list[dict[str, Any]]],
    chapter_order: list[str],
) -> list[dict[str, Any]]:
    if not assets:
        raise FileNotFoundError("No visual assets available for rebuild_timeline source generation.")

    sequence: list[dict[str, Any]] = []
    use_counts: dict[Path, int] = defaultdict(int)
    last_used_slot: dict[Path, int] = {}
    chapter_video_paths: dict[str, set[Path]] = defaultdict(set)
    typewriter_applied_chapters: set[str] = set()
    equivalent_asset_paths: dict[Path, set[Path]] = {}
    digest_groups: dict[str, set[Path]] = defaultdict(set)
    chapter_target_order: list[str] = [target for target in chapter_targets if isinstance(target, str) and target.startswith("ch")]
    opening_effect_chapter = chapter_order[0] if chapter_order else (chapter_target_order[0] if chapter_target_order else None)
    if opening_effect_chapter is None:
        opening_effect_chapter = next(
            (
                str(asset.get("chapter_id"))
                for asset in assets
                if isinstance(asset.get("chapter_id"), str) and str(asset.get("chapter_id")).startswith("ch")
            ),
            None,
        )
    for asset in assets:
        chapter_id = asset.get("chapter_id")
        if asset["type"] == "video" and isinstance(chapter_id, str) and chapter_id:
            chapter_video_paths[chapter_id].add(asset["path"])
        if asset["type"] == "image":
            try:
                digest_groups[file_content_digest(str(asset["path"]))].add(asset["path"])
            except OSError:
                continue
    for group in digest_groups.values():
        if len(group) <= 1:
            continue
        for path in group:
            equivalent_asset_paths[path] = set(group)

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

    def choose_asset(index: int, duration: float, target_chapter: str | None, *, allow_repeat_limit_breach: bool = False) -> dict[str, Any]:
        consecutive_images = consecutive_type_count("image")
        consecutive_videos = consecutive_type_count("video")
        previous_type = sequence[-1]["asset_type"] if sequence else None
        previous_target = sequence[-1].get("target_chapter") if sequence else None
        chapter_sequence = [item for item in sequence if item.get("target_chapter") == target_chapter]
        chapter_image_count = sum(1 for item in chapter_sequence if item.get("asset_type") == "image")
        chapter_video_count = len(chapter_video_paths.get(str(target_chapter or ""), set()))

        best_asset: dict[str, Any] | None = None
        best_score: tuple[float, float, float, float] | None = None

        for order_index, candidate in enumerate(assets):
            if not can_cover(candidate, duration):
                continue
            if target_chapter != "opening" and str(candidate.get("role") or "") == "cover":
                continue
            if candidate.get("role") == "generated-hero":
                candidate_chapter_value = str(candidate.get("chapter_id") or "")
                expected_opening_chapter = chapter_order[0] if chapter_order else None
                if target_chapter == "opening":
                    if candidate_chapter_value != str(expected_opening_chapter or ""):
                        continue
                elif target_chapter and candidate_chapter_value != str(target_chapter):
                    continue
            equivalent_paths = equivalent_asset_paths.get(candidate["path"], {candidate["path"]})
            equivalent_use_count = sum(use_counts[path] for path in equivalent_paths)
            previous_distance = min(
                (index - last_used_slot[path] for path in equivalent_paths if path in last_used_slot),
                default=99,
            )
            max_repeat_uses = candidate.get("max_repeat_uses")
            if (
                not allow_repeat_limit_breach
                and isinstance(max_repeat_uses, int)
                and max_repeat_uses > 0
                and equivalent_use_count >= max_repeat_uses
            ):
                continue

            score = 0.0
            candidate_chapter = candidate.get("chapter_id")
            candidate_role = candidate.get("role")
            candidate_type = candidate["type"]

            if target_chapter == "opening":
                if candidate_role == "cover":
                    score += 120
                elif candidate_role == "generated-hero":
                    score += 132
                else:
                    score -= 80
            elif target_chapter and candidate_chapter == target_chapter:
                score += 60
            elif target_chapter and candidate_chapter is None:
                score += 6
            elif target_chapter and candidate_chapter == previous_target:
                score += 4
            elif target_chapter and candidate_chapter not in {None, target_chapter}:
                score -= 10
                if candidate_type == "image":
                    score -= 35

            if target_chapter == "ch3":
                if candidate_role == "proof" and equivalent_use_count == 0:
                    score += 45
                elif candidate_role == "running-example":
                    score += 30

            if candidate_role == "keyart":
                if equivalent_use_count == 0:
                    score += 42
                elif equivalent_use_count == 1:
                    score += 6
                else:
                    score -= 18 * equivalent_use_count
            elif candidate_role == "generated-hero":
                if equivalent_use_count == 0:
                    score += 68
                elif equivalent_use_count == 1:
                    score += 14
                else:
                    score -= 24 * equivalent_use_count
            elif candidate_role == "proof":
                score += 14
                if equivalent_use_count == 0:
                    score += 10

            if target_chapter == "ch4":
                if candidate_role == "framework-overview":
                    score += 24
                elif candidate_role == "walkthrough":
                    score += 20
                elif candidate_role == "step-card":
                    score += 16

            if target_chapter == "ch1" and chapter_image_count == 0 and len(chapter_sequence) >= 3:
                if candidate_type == "image":
                    score += 70
                    if candidate_role in {"proof", "keyart"}:
                        score += 15
                elif consecutive_videos >= 3:
                    score -= 40

            if candidate_type == "video":
                score += 16
                if equivalent_use_count == 0:
                    score += 10
                if candidate.get("source") == "generation-ledger":
                    score += 28
                if duration > MAX_IMAGE_SLOT_DURATION_SECONDS:
                    score += 24
                if consecutive_images >= 4 and target_chapter and candidate_chapter == target_chapter:
                    score += 32
                    if equivalent_use_count > 0:
                        score += 18
                score += low_value_video_penalty(
                    title=str(candidate.get("title") or ""),
                    page_url=str(candidate.get("page_url") or ""),
                    tags=candidate.get("tags") if isinstance(candidate.get("tags"), list) else [],
                    query=str(candidate.get("query") or ""),
                    preview_image_url=str(candidate.get("preview_image_url") or ""),
                )
                if candidate_role == "generated-hero":
                    score += 42
                if consecutive_images >= 2:
                    score += 22
                if previous_type == "video":
                    score -= 8
                unique_video_count = len(chapter_video_paths.get(str(target_chapter or ""), set()))
                if target_chapter and candidate_chapter == target_chapter and unique_video_count > 1 and equivalent_use_count > 0:
                    score -= 28
                coverage_margin = float(candidate.get("duration_seconds", duration)) - duration
                score += min(max(coverage_margin, 0.0), 6.0)
            else:
                if duration > MAX_IMAGE_SLOT_DURATION_SECONDS:
                    score -= 120
                if consecutive_images >= 2:
                    score -= 18
                elif consecutive_images == 1:
                    score -= 6
                if consecutive_images >= 4 and chapter_video_count > 0:
                    score -= 28
                if candidate_role in {"proof", "keyart"}:
                    score += 12
                elif equivalent_use_count >= 1:
                    score -= 12
                if target_chapter and chapter_video_count > 0 and candidate_role not in {"cover", "proof", "keyart"}:
                    score -= 16

            if previous_type == candidate_type:
                score -= 10

            if target_chapter != "opening" and any(last_used_slot.get(path) == 0 for path in equivalent_paths):
                score -= 140
            if previous_distance < 4:
                score -= (4 - previous_distance) * 10
            else:
                score += min(previous_distance, 8)

            if candidate_role == "keyart" and equivalent_use_count >= 2:
                score -= equivalent_use_count * 10
            else:
                score -= equivalent_use_count * (12 if candidate_type == "image" and candidate_role not in {"cover", "proof", "keyart"} else 4)

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
        if not allow_repeat_limit_breach:
            return choose_asset(index, duration, target_chapter, allow_repeat_limit_breach=True)

        for candidate in assets:
            if target_chapter != "opening" and str(candidate.get("role") or "") == "cover":
                continue
            if candidate["type"] == "image":
                return candidate
        return assets[0]

    for index, slot in enumerate(slots):
        target_chapter = chapter_targets[index] if index < len(chapter_targets) else None
        asset = choose_asset(index, slot["duration"], target_chapter)
        use_count = use_counts[asset["path"]]
        use_counts[asset["path"]] += 1
        last_used_slot[asset["path"]] = index
        chapter_fx_key = str(target_chapter or asset.get("chapter_id") or "")
        if chapter_fx_key == "opening" and opening_effect_chapter:
            chapter_fx_key = opening_effect_chapter
        chapter_effects = chapter_effects_by_chapter.get(chapter_fx_key, [])

        clip_start = 0.0
        if asset["type"] == "video":
            duration_seconds = float(asset.get("duration_seconds", slot["duration"]))
            max_offset = max(duration_seconds - slot["duration"], 0.0)
            if max_offset > 0:
                clip_start = round(min((use_count * 1.618) % max_offset, max_offset), 3)

        motion = motion_profile(
            index,
            asset.get("role"),
            slot["duration"],
            asset_type=asset["type"],
            asset_path=asset["path"],
            effects=chapter_effects,
        )
        typewriter_effect = None
        if chapter_fx_key and chapter_fx_key not in typewriter_applied_chapters:
            typewriter_effect = next(
                (
                    effect
                    for effect in chapter_effects
                    if effect.get("type") == "typewriter_quote"
                    and str(effect.get("text") or "").strip()
                    and (
                        not str(effect.get("target_role") or "").strip()
                        or str(effect.get("target_role") or "").strip() == str(asset.get("role") or "")
                    )
                ),
                None,
            )
            if typewriter_effect is not None:
                typewriter_applied_chapters.add(chapter_fx_key)

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
                "motion_preset": motion["preset"],
                "motion_zoom_ratio": motion["zoom_ratio"],
                "typewriter_text": typewriter_effect.get("text") if typewriter_effect else None,
                "typewriter_anchor": typewriter_effect.get("anchor") if typewriter_effect else None,
                "typewriter_chars_per_second": typewriter_effect.get("chars_per_second") if typewriter_effect else None,
                "typewriter_start_offset_seconds": typewriter_effect.get("start_offset_seconds") if typewriter_effect else None,
                "typewriter_duration_seconds": typewriter_effect.get("duration_seconds") if typewriter_effect else None,
            }
        )

    return sequence


def align_typewriter_effects_to_subtitles(
    sequence: list[dict[str, Any]],
    *,
    chapter_effects_by_chapter: dict[str, list[dict[str, Any]]],
    subtitle_cues: list[dict[str, Any]],
    chapter_order: list[str],
) -> list[dict[str, Any]]:
    if not sequence:
        return sequence

    def update_slot_window(item: dict[str, Any], *, start: float | None = None, end: float | None = None) -> None:
        slot_start = float(item.get("slot_start", 0.0)) if start is None else float(start)
        slot_end = float(item.get("slot_end", slot_start)) if end is None else float(end)
        slot_end = max(slot_end, slot_start)
        item["slot_start"] = round(slot_start, 3)
        item["slot_end"] = round(slot_end, 3)
        item["slot_duration"] = round(max(slot_end - slot_start, 0.0), 3)

    def retime_slot_boundary(
        *,
        chosen_index: int,
        cue_start: float,
        boundary_start: float,
    ) -> tuple[int, float]:
        chosen_slot = updated[chosen_index]
        chosen_start = float(chosen_slot["slot_start"])
        chosen_end = float(chosen_slot["slot_end"])
        if chosen_start <= cue_start < chosen_end:
            return chosen_index, max(cue_start - chosen_start, 0.0)

        if cue_start < chosen_start and chosen_index > 0:
            previous_slot = updated[chosen_index - 1]
            previous_start = float(previous_slot["slot_start"])
            previous_end = float(previous_slot["slot_end"])
            adjusted_boundary = min(max(boundary_start, previous_start + 0.35), chosen_start - 0.35)
            if previous_start + 0.35 <= adjusted_boundary <= previous_end - 0.35:
                update_slot_window(previous_slot, end=adjusted_boundary)
                update_slot_window(chosen_slot, start=adjusted_boundary)
                return chosen_index, max(cue_start - adjusted_boundary, 0.0)

        if cue_start >= chosen_end and chosen_index + 1 < len(updated):
            next_slot = updated[chosen_index + 1]
            next_start = float(next_slot["slot_start"])
            next_end = float(next_slot["slot_end"])
            adjusted_boundary = max(min(boundary_start, next_end - 0.35), chosen_end + 0.35)
            if next_start + 0.35 <= adjusted_boundary <= next_end - 0.35:
                update_slot_window(chosen_slot, end=adjusted_boundary)
                update_slot_window(next_slot, start=adjusted_boundary)
                return chosen_index + 1, max(cue_start - adjusted_boundary, 0.0)

        return chosen_index, max(cue_start - chosen_start, 0.0)

    chapter_target_slots: dict[str, list[int]] = defaultdict(list)
    chapter_asset_slots: dict[str, list[int]] = defaultdict(list)
    for index, item in enumerate(sequence):
        target_chapter = str(item.get("target_chapter") or "")
        chapter_id = str(item.get("chapter_id") or "")
        if target_chapter:
            chapter_target_slots[target_chapter].append(index)
        if chapter_id:
            chapter_asset_slots[chapter_id].append(index)
        if target_chapter == "opening" and chapter_order:
            chapter_target_slots[chapter_order[0]].append(index)

    updated = [{**item} for item in sequence]
    for item in updated:
        item["typewriter_text"] = None
        item["typewriter_anchor"] = None
        item["typewriter_chars_per_second"] = None
        item["typewriter_start_offset_seconds"] = None
        item["typewriter_duration_seconds"] = None

    for chapter_id, effects in chapter_effects_by_chapter.items():
        typewriter_effects = [
            effect
            for effect in effects
            if isinstance(effect, dict) and effect.get("type") == "typewriter_quote" and str(effect.get("text") or "").strip()
        ]
        if not typewriter_effects:
            continue
        slot_indexes = sorted(set(chapter_target_slots.get(chapter_id, [])))
        if not slot_indexes:
            slot_indexes = sorted(set(chapter_asset_slots.get(chapter_id, [])))
        if not slot_indexes:
            continue
        slot_window_start = min(float(updated[index]["slot_start"]) for index in slot_indexes)
        slot_window_end = max(float(updated[index]["slot_end"]) for index in slot_indexes)
        candidate_subtitles = [
            cue
            for cue in subtitle_cues
            if float(cue.get("end", 0.0)) >= slot_window_start - 0.35
            and float(cue.get("start", 0.0)) <= slot_window_end + 0.35
        ] or list(subtitle_cues)

        for effect in typewriter_effects:
            target_role = str(effect.get("target_role") or "").strip()
            preferred_slot_candidates = [
                slot_index
                for slot_index in slot_indexes
                if (
                    not target_role
                    or str(updated[slot_index].get("role") or "") == target_role
                )
            ]
            if not preferred_slot_candidates:
                preferred_slot_candidates = list(slot_indexes)
            if not preferred_slot_candidates:
                preferred_slot_candidates = [
                    index
                    for index, item in enumerate(updated)
                    if not target_role or str(item.get("role") or "") == target_role
                ]
            if not preferred_slot_candidates:
                preferred_slot_candidates = list(range(len(updated)))

            matched_cue = None
            matched_score = 0.0
            for cue in candidate_subtitles:
                score = effect_text_match_score(effect.get("text"), cue.get("text"))
                if score > matched_score:
                    matched_score = score
                    matched_cue = cue

            chosen_index = preferred_slot_candidates[0]
            start_offset_seconds = float(effect.get("start_offset_seconds") or 0.0)
            if matched_cue is not None and matched_score >= 0.3:
                cue_window_start = float(matched_cue.get("start", 0.0))
                cue_start = float(matched_cue.get("start", 0.0))
                cue_start += phrase_alignment_offset(
                    effect.get("text"),
                    matched_cue.get("text"),
                    float(matched_cue.get("duration", 0.0)),
                )
                for index in preferred_slot_candidates:
                    slot_start = float(updated[index]["slot_start"])
                    if abs(slot_start - cue_start) <= 0.05:
                        chosen_index = index
                        start_offset_seconds = 0.0
                        break
                else:
                    for index in preferred_slot_candidates:
                        slot_start = float(updated[index]["slot_start"])
                        slot_end = float(updated[index]["slot_end"])
                        if slot_start <= cue_start < slot_end:
                            chosen_index = index
                            start_offset_seconds = max(cue_start - slot_start, 0.0)
                            break
                    else:
                        chosen_index = min(
                            preferred_slot_candidates,
                            key=lambda index: abs(float(updated[index]["slot_start"]) - cue_start),
                        )
                        chosen_index, start_offset_seconds = retime_slot_boundary(
                            chosen_index=chosen_index,
                            cue_start=cue_start,
                            boundary_start=cue_window_start,
                        )
                        if start_offset_seconds > 0.0:
                            for index in range(len(updated)):
                                slot_start = float(updated[index]["slot_start"])
                                if abs(slot_start - cue_start) <= 0.05:
                                    chosen_index = index
                                    start_offset_seconds = 0.0
                                    break
                            else:
                                for index in range(len(updated)):
                                    slot_start = float(updated[index]["slot_start"])
                                    slot_end = float(updated[index]["slot_end"])
                                    if slot_start <= cue_start < slot_end:
                                        chosen_index = index
                                        start_offset_seconds = max(cue_start - slot_start, 0.0)
                                        break
                                else:
                                    chosen_index = min(
                                        preferred_slot_candidates,
                                        key=lambda index: abs(float(updated[index]["slot_start"]) - cue_start),
                                    )
                                    chosen_index, start_offset_seconds = retime_slot_boundary(
                                        chosen_index=chosen_index,
                                        cue_start=cue_start,
                                        boundary_start=cue_window_start,
                                    )

            updated[chosen_index]["typewriter_text"] = effect.get("text")
            updated[chosen_index]["typewriter_anchor"] = effect.get("anchor")
            updated[chosen_index]["typewriter_chars_per_second"] = effect.get("chars_per_second")
            updated[chosen_index]["typewriter_start_offset_seconds"] = round(start_offset_seconds, 3)
            updated[chosen_index]["typewriter_duration_seconds"] = effect.get("duration_seconds")

    return updated


def ensure_opening_variety(
    sequence: list[dict[str, Any]],
    *,
    assets: list[dict[str, Any]],
    opening_seconds: float = 42.0,
) -> list[dict[str, Any]]:
    if not sequence:
        return sequence

    early_indexes = [index for index, item in enumerate(sequence) if float(item.get("slot_start", 0.0)) < opening_seconds]
    if len(early_indexes) <= 2:
        return sequence

    non_cover_image_indexes = [
        index
        for index in early_indexes
        if sequence[index].get("asset_type") == "image"
        and sequence[index].get("role") != "cover"
        and str(sequence[index].get("target_chapter") or "") == "ch1"
        and str(sequence[index].get("chapter_id") or "") in {"ch1", ""}
    ]
    if non_cover_image_indexes:
        return sequence

    replacement_asset = next(
        (
            asset
            for asset in assets
            if asset.get("type") == "image"
            and asset.get("role") != "cover"
            and str(asset.get("chapter_id") or "") == "ch1"
        ),
        None,
    )
    if replacement_asset is None:
        return sequence

    target_indexes = [
        index
        for index in early_indexes
        if sequence[index].get("asset_type") == "video" and str(sequence[index].get("target_chapter") or "") == "ch1"
    ]
    if not target_indexes:
        return sequence

    chosen_index = target_indexes[min(2, len(target_indexes) - 1)]
    updated = [{**item} for item in sequence]
    item = updated[chosen_index]
    item["asset_type"] = "image"
    item["asset_path"] = replacement_asset["path"]
    item["chapter_id"] = replacement_asset.get("chapter_id")
    item["asset_source"] = replacement_asset.get("source")
    item["role"] = replacement_asset.get("role")
    item["clip_id"] = replacement_asset.get("clip_id")
    item["clip_start"] = 0.0
    item["motion_preset"] = "static_hold"
    item["motion_zoom_ratio"] = 1.0
    return updated


def escape_drawtext_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
        .replace(",", "\\,")
    )


def typewriter_drawtext_filters(
    *,
    text: str | None,
    duration: float,
    anchor: str | None,
    chars_per_second: float | None,
    start_offset_seconds: float | None,
    duration_seconds: float | None,
) -> list[str]:
    raw_text = str(text or "").strip()
    if not raw_text:
        return []
    if not ffmpeg_filter_available("drawtext"):
        return []
    cps = max(float(chars_per_second or 12), 4.0)
    start_offset = max(float(start_offset_seconds or 0.0), 0.0)
    visible_until = min(duration, start_offset + max(float(duration_seconds or duration), len(raw_text) / cps + 0.6))
    anchor_name = str(anchor or "lower_left")
    if anchor_name == "upper_right":
        x_expr = "w-tw-96"
        y_expr = "118"
        font_size = 76
    elif anchor_name == "upper_left":
        x_expr = "96"
        y_expr = "118"
        font_size = 76
    elif anchor_name == "upper_center":
        x_expr = "(w-tw)/2"
        y_expr = "110"
        font_size = 84
    elif anchor_name == "center":
        x_expr = "(w-tw)/2"
        y_expr = "h*0.18"
        font_size = 88
    else:
        x_expr = "96"
        y_expr = "h-210"
        font_size = 74

    filters: list[str] = []
    characters = list(raw_text)
    for index in range(1, len(characters) + 1):
        prefix = "".join(characters[:index])
        start = start_offset + ((index - 1) / cps)
        end = visible_until if index == len(characters) else min(start_offset + (index / cps), visible_until)
        if end <= start:
            continue
        filters.append(
            "drawtext="
            f"font='Arial Unicode MS':"
            f"text='{escape_drawtext_text(prefix)}':"
            f"fontcolor=white@1.0:fontsize={font_size}:"
            "borderw=3:bordercolor=0x000000@0.9:"
            "box=1:boxcolor=0x0E1117@0.82:boxborderw=28:"
            f"x={x_expr}:y={y_expr}:"
            f"enable='between(t\\,{start:.3f}\\,{end:.3f})'"
        )
    return filters


def quote_concat_path(path: Path) -> str:
    return str(path).replace("'", "'\\''")


def even_int(value: float) -> int:
    rounded = int(round(value))
    return rounded if rounded % 2 == 0 else rounded + 1


def image_motion_fps(fps: int) -> int:
    return max(int(fps) * IMAGE_MOTION_OVERSAMPLE_FACTOR, int(fps))


def image_filter(
    *,
    asset_path: str | None,
    width: int,
    height: int,
    fps: int,
    duration: float,
    motion_preset: str | None,
    motion_zoom_ratio: float | None,
    typewriter_text: str | None,
    typewriter_anchor: str | None,
    typewriter_chars_per_second: float | None,
    typewriter_start_offset_seconds: float | None,
    typewriter_duration_seconds: float | None,
) -> str:
    fade_out_start = max(duration - 0.2, 0.0)
    is_card_asset = Path(str(asset_path or "")).name.startswith("card-")
    scale_width = int(round(width * 0.86)) if is_card_asset else width
    scale_height = int(round(height * 0.86)) if is_card_asset else height
    if motion_preset == "static_hold" or (motion_zoom_ratio or 1.0) <= 1.001:
        filters = [
            f"scale={scale_width}:{scale_height}:force_original_aspect_ratio=decrease:flags=lanczos",
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
            "setsar=1",
            f"fps={fps}",
            "format=yuv420p",
        ]
        filters.extend(
            typewriter_drawtext_filters(
                text=typewriter_text,
                duration=duration,
                anchor=typewriter_anchor,
                chars_per_second=typewriter_chars_per_second,
                start_offset_seconds=typewriter_start_offset_seconds,
                duration_seconds=typewriter_duration_seconds,
            )
        )
        return ",".join(filters)

    zoom_ratio = motion_zoom_ratio or 1.08
    motion_fps = image_motion_fps(fps)
    overscan_width = even_int(width * zoom_ratio)
    overscan_height = even_int(height * zoom_ratio)
    spare_x = max(overscan_width - width, 2)
    spare_y = max(overscan_height - height, 2)
    frame_denominator = max(int(round(duration * motion_fps)) - 1, 1)

    progress_expr, inverse_progress_expr = motion_progress_expressions(frame_denominator)

    if motion_preset == "push_left":
        x_expr = f"({spare_x}*{inverse_progress_expr})"
        y_expr = f"{spare_y}/2"
    elif motion_preset == "tilt_down":
        x_expr = f"{spare_x}/2"
        y_expr = f"({spare_y}*{progress_expr})"
    elif motion_preset == "tilt_up":
        x_expr = f"{spare_x}/2"
        y_expr = f"({spare_y}*{inverse_progress_expr})"
    elif motion_preset == "diagonal_down":
        x_expr = f"({spare_x}*{progress_expr})"
        y_expr = f"({spare_y}*{progress_expr})"
    elif motion_preset == "diagonal_up":
        x_expr = f"({spare_x}*{inverse_progress_expr})"
        y_expr = f"({spare_y}*{inverse_progress_expr})"
    else:
        x_expr = f"({spare_x}*{progress_expr})"
        y_expr = f"{spare_y}/2"

    filters = [
        f"scale={scale_width}:{scale_height}:force_original_aspect_ratio=decrease:flags=lanczos",
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
        "setsar=1",
        f"fps={motion_fps}",
        f"scale={overscan_width}:{overscan_height}:flags=lanczos",
        f"crop={width}:{height}:x={x_expr}:y={y_expr}",
        "tmix=frames=2:weights='1 1'",
        f"fps={fps}",
        "format=yuv420p",
    ]
    filters.extend(
        typewriter_drawtext_filters(
            text=typewriter_text,
            duration=duration,
            anchor=typewriter_anchor,
            chars_per_second=typewriter_chars_per_second,
            start_offset_seconds=typewriter_start_offset_seconds,
            duration_seconds=typewriter_duration_seconds,
        )
    )
    return ",".join(filters)


def video_filter(
    *,
    width: int,
    height: int,
    fps: int,
    duration: float,
    motion_preset: str | None,
    motion_zoom_ratio: float | None,
    typewriter_text: str | None,
    typewriter_anchor: str | None,
    typewriter_chars_per_second: float | None,
    typewriter_start_offset_seconds: float | None,
    typewriter_duration_seconds: float | None,
) -> str:
    fade_out_start = max(duration - 0.2, 0.0)
    zoom_ratio = motion_zoom_ratio or 1.08
    overscan_width = even_int(width * zoom_ratio)
    overscan_height = even_int(height * zoom_ratio)
    spare_x = max(overscan_width - width, 2)
    spare_y = max(overscan_height - height, 2)
    frame_denominator = max(int(round(duration * fps)) - 1, 1)

    progress_expr, inverse_progress_expr = motion_progress_expressions(frame_denominator)

    if motion_preset == "push_left":
        x_expr = f"({spare_x}*{inverse_progress_expr})"
        y_expr = f"{spare_y}/2"
    elif motion_preset == "tilt_down":
        x_expr = f"{spare_x}/2"
        y_expr = f"({spare_y}*{progress_expr})"
    elif motion_preset == "tilt_up":
        x_expr = f"{spare_x}/2"
        y_expr = f"({spare_y}*{inverse_progress_expr})"
    elif motion_preset == "diagonal_down":
        x_expr = f"({spare_x}*{progress_expr})"
        y_expr = f"({spare_y}*{progress_expr})"
    elif motion_preset == "diagonal_up":
        x_expr = f"({spare_x}*{inverse_progress_expr})"
        y_expr = f"({spare_y}*{inverse_progress_expr})"
    else:
        x_expr = f"({spare_x}*{progress_expr})"
        y_expr = f"{spare_y}/2"

    filters = [
        f"scale={overscan_width}:{overscan_height}:force_original_aspect_ratio=increase:flags=lanczos",
        f"crop={width}:{height}:x={x_expr}:y={y_expr}",
        "setsar=1",
        f"fps={fps}",
        "format=yuv420p",
    ]
    filters.extend(
        typewriter_drawtext_filters(
            text=typewriter_text,
            duration=duration,
            anchor=typewriter_anchor,
            chars_per_second=typewriter_chars_per_second,
            start_offset_seconds=typewriter_start_offset_seconds,
            duration_seconds=typewriter_duration_seconds,
        )
    )
    return ",".join(filters)


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
                    "-framerate",
                    str(fps),
                    "-loop",
                    "1",
                    "-i",
                    str(asset_path),
                    "-t",
                    f"{duration:.3f}",
                    "-vf",
                    image_filter(
                        asset_path=str(asset_path),
                        width=width,
                        height=height,
                        fps=fps,
                        duration=duration,
                        motion_preset=item.get("motion_preset"),
                        motion_zoom_ratio=item.get("motion_zoom_ratio"),
                        typewriter_text=item.get("typewriter_text"),
                        typewriter_anchor=item.get("typewriter_anchor"),
                        typewriter_chars_per_second=item.get("typewriter_chars_per_second"),
                        typewriter_start_offset_seconds=item.get("typewriter_start_offset_seconds"),
                        typewriter_duration_seconds=item.get("typewriter_duration_seconds"),
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
                    video_filter(
                        width=width,
                        height=height,
                        fps=fps,
                        duration=duration,
                        motion_preset=item.get("motion_preset"),
                        motion_zoom_ratio=item.get("motion_zoom_ratio"),
                        typewriter_text=item.get("typewriter_text"),
                        typewriter_anchor=item.get("typewriter_anchor"),
                        typewriter_chars_per_second=item.get("typewriter_chars_per_second"),
                        typewriter_start_offset_seconds=item.get("typewriter_start_offset_seconds"),
                        typewriter_duration_seconds=item.get("typewriter_duration_seconds"),
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
    proof_slots = [item for item in sequence if item.get("role") in {"proof", "keyart"}]
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
    cover_asset = suppress_duplicate_cover(cover_asset, proof_assets)
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
    chapter_targets = build_chapter_targets(
        slots,
        chapter_order,
        assets,
        has_cover=cover_asset is not None,
        project_root=project_root,
        subtitle_cues=cues,
    )
    chapter_effects_by_chapter = load_chapter_effects(project_root)
    sequence = assign_assets(slots, assets, chapter_targets, chapter_effects_by_chapter, chapter_order)
    sequence = align_typewriter_effects_to_subtitles(
        sequence,
        chapter_effects_by_chapter=chapter_effects_by_chapter,
        subtitle_cues=cues,
        chapter_order=chapter_order,
    )
    sequence = ensure_opening_variety(sequence, assets=assets)
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
