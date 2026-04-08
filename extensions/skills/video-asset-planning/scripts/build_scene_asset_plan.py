#!/usr/bin/env python3
"""Build a scene asset plan, visual evidence map, and generation budget."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm"}
ALLOWED_GENERATION_TYPES = {
    "text-to-image",
    "image-to-image",
    "text-to-video",
    "image-to-video",
    "first-last-frame-video",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", help="Media package root directory.")
    parser.add_argument("--content-id", help="Content package id under the media-ops root.")
    parser.add_argument(
        "--media-ops-root",
        help="Root directory containing media packages. Defaults to repo-local data/media-ops.",
    )
    parser.add_argument(
        "--scene-output",
        default="assets/scene-asset-plan.json",
        help="Scene asset plan output path relative to the project root.",
    )
    parser.add_argument(
        "--visual-map-output",
        default="assets/visual-evidence-map.json",
        help="Visual evidence map output path relative to the project root.",
    )
    parser.add_argument(
        "--generation-budget-output",
        default="assets/generation-budget.json",
        help="Generation budget output path relative to the project root.",
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


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def detect_content_packet(project_root: Path) -> Path:
    content_dir = project_root / "content"
    prioritized = ["*video.json", "content-packet.json", "*.json"]
    for pattern in prioritized:
        matches = sorted(path for path in content_dir.glob(pattern) if path.is_file())
        if matches:
            return matches[0]
    raise FileNotFoundError(f"no content packet found under {content_dir}")


def relative_to_project(path: Path, project_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_root.resolve()))
    except ValueError:
        return str(path.resolve())


def resolve_candidate(project_root: Path, raw_path: str | None) -> Path | None:
    if not raw_path:
        return None
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = project_root / candidate
    return candidate.resolve()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def approved_source_entries(source_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    items = source_manifest.get("source_manifest")
    if not isinstance(items, list):
        return []
    approved: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if str(item.get("license_status") or "").lower() != "approved":
            continue
        approved.append(item)
    return approved


def grouped_by_chapter(entries: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        chapter_id = str(entry.get("chapter_id") or "")
        if not chapter_id:
            continue
        grouped.setdefault(chapter_id, []).append(entry)
    return grouped


def ingested_assets_by_chapter(ingest_manifest: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    items = ingest_manifest.get("ingested_assets")
    if not isinstance(items, list):
        return {}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        chapter_id = str(item.get("chapter_id") or "").strip()
        local_path = str(item.get("local_path") or "").strip()
        if not chapter_id or not local_path:
            continue
        grouped.setdefault(chapter_id, []).append(item)
    return grouped


def ordered_graphics(project_root: Path) -> list[Path]:
    return sorted((project_root / "assets" / "graphics").glob("card-*.png"))


def infer_chapter_id_from_path(path: Path) -> str | None:
    match = re.search(r"(ch\d+)", path.as_posix(), flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).lower()


def generated_keyframes_by_chapter(project_root: Path) -> dict[str, list[Path]]:
    search_roots = [
        project_root / "assets" / "generated",
        project_root / "assets" / "ai-keyframes",
        project_root / "assets" / "generated-keyframes",
    ]
    grouped: dict[str, list[Path]] = {}
    for root in search_roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            chapter_id = infer_chapter_id_from_path(path)
            if not chapter_id:
                continue
            grouped.setdefault(chapter_id, []).append(path.resolve())
    return grouped


def visual_prebake_assets_by_chapter(project_root: Path) -> dict[str, dict[str, Any]]:
    payload = load_json(project_root / "assets" / "visual-prebake-plan.json")
    chapters = payload.get("chapters") if isinstance(payload.get("chapters"), list) else []
    grouped: dict[str, dict[str, Any]] = {}
    for item in chapters:
        if not isinstance(item, dict):
            continue
        chapter_id = str(item.get("chapter_id") or "").strip()
        if not chapter_id:
            continue

        proof_spec = item.get("proof_asset")
        proof_asset_path: Path | None = None
        proof_asset_type = "generated-keyart"
        if isinstance(proof_spec, dict):
            proof_asset_path = resolve_candidate(project_root, str(proof_spec.get("path") or "").strip())
            proof_asset_type = str(proof_spec.get("type") or "generated-keyart").strip() or "generated-keyart"
        elif isinstance(proof_spec, str):
            proof_asset_path = resolve_candidate(project_root, proof_spec.strip())

        candidate_images: list[Path] = []
        for raw_path in item.get("supporting_images", []):
            if not isinstance(raw_path, str):
                continue
            candidate = resolve_candidate(project_root, raw_path.strip())
            if candidate is None or not candidate.exists() or candidate.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            candidate_images.append(candidate)

        fallback_graphics: list[Path] = []
        for raw_path in item.get("fallback_graphics", []):
            if not isinstance(raw_path, str):
                continue
            candidate = resolve_candidate(project_root, raw_path.strip())
            if candidate is None or not candidate.exists() or candidate.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            fallback_graphics.append(candidate)

        if proof_asset_path is not None and (
            not proof_asset_path.exists() or proof_asset_path.suffix.lower() not in IMAGE_SUFFIXES
        ):
            proof_asset_path = None

        if proof_asset_path is None and candidate_images:
            proof_asset_path = candidate_images[0]

        supporting_images: list[Path] = []
        seen_paths: set[Path] = set()
        for candidate in [*candidate_images, *fallback_graphics]:
            if proof_asset_path is not None and candidate == proof_asset_path:
                continue
            if candidate in seen_paths:
                continue
            seen_paths.add(candidate)
            supporting_images.append(candidate)

        grouped[chapter_id] = {
            "proof_asset_path": proof_asset_path,
            "proof_asset_type": proof_asset_type,
            "supporting_images": supporting_images,
            "max_repeat_uses": int(item.get("max_repeat_uses", 2)),
        }
    return grouped


def extract_quota(payload: dict[str, Any]) -> dict[str, Any]:
    snapshot = payload.get("quota_snapshot") if isinstance(payload.get("quota_snapshot"), dict) else {}
    daily_limit = payload.get("daily_quota_limit") or snapshot.get("daily_limit") or 0
    daily_remaining = snapshot.get("daily_remaining", daily_limit)
    return {
        "daily_limit": int(daily_limit),
        "daily_remaining": int(daily_remaining),
    }


def normalize_generation_slot(slot: dict[str, Any]) -> dict[str, Any]:
    generation_type = str(slot.get("generation_type") or "").strip()
    if generation_type not in ALLOWED_GENERATION_TYPES:
        generation_type = "image-to-video"
    return {
        "slot_id": str(slot.get("slot_id") or ""),
        "chapter_id": str(slot.get("chapter_id") or ""),
        "generation_type": generation_type,
        "reason": str(slot.get("reason") or ""),
    }


def generated_video_assets_by_chapter(project_root: Path) -> dict[str, list[dict[str, Any]]]:
    generation_ledger = load_json(project_root / "assets" / "generation-ledger.json")
    entries = generation_ledger.get("entries")
    if not isinstance(entries, list):
        return {}

    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in entries:
        if not isinstance(item, dict):
            continue
        if str(item.get("status") or "").strip().lower() != "success":
            continue
        chapter_id = str(item.get("chapter_id") or "").strip()
        asset_path = str(item.get("asset_path") or "").strip()
        if not chapter_id or not asset_path:
            continue
        candidate = resolve_candidate(project_root, asset_path)
        if candidate is None or not candidate.exists() or candidate.suffix.lower() not in VIDEO_SUFFIXES:
            continue
        grouped.setdefault(chapter_id, []).append(
            {
                "clip_id": str(item.get("slot_id") or candidate.stem),
                "local_path": relative_to_project(candidate, project_root),
                "source_type": "generated-media",
                "source_track": "generated",
                "generation_type": str(item.get("generation_type") or ""),
            }
        )
    return grouped


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)

    packet_path = detect_content_packet(project_root)
    packet = load_json(packet_path)
    primary = packet.get("content_packet") if isinstance(packet.get("content_packet"), dict) else packet

    source_manifest_path = project_root / "sources" / "source-manifest.json"
    source_manifest = load_json(source_manifest_path)
    asset_ingest_manifest = load_json(project_root / "sources" / "asset-ingest-manifest.json")
    exploration_ingest_manifest = load_json(project_root / "sources" / "exploration-ingest-manifest.json")
    approved_sources = approved_source_entries(source_manifest)
    approved_by_chapter = grouped_by_chapter(approved_sources)
    production_ingests = ingested_assets_by_chapter(asset_ingest_manifest)
    exploration_ingests = ingested_assets_by_chapter(exploration_ingest_manifest)
    generated_video_ingests = generated_video_assets_by_chapter(project_root)
    graphics = ordered_graphics(project_root)
    generated_keyframes = generated_keyframes_by_chapter(project_root)
    visual_prebake = visual_prebake_assets_by_chapter(project_root)

    generation_budget_decision = (
        primary.get("generation_budget_decision")
        if isinstance(primary.get("generation_budget_decision"), dict)
        else {}
    )
    approved_generated_assets = [
        normalize_generation_slot(item)
        for item in generation_budget_decision.get("approved_generated_assets", [])
        if isinstance(item, dict)
    ]
    blocked_generated_assets = [
        normalize_generation_slot(item)
        for item in generation_budget_decision.get("blocked_generated_assets", [])
        if isinstance(item, dict)
    ]
    chapter_outline = [item for item in primary.get("chapter_outline", []) if isinstance(item, dict)]
    clip_sourcing_brief = grouped_by_chapter(
        [item for item in primary.get("clip_sourcing_brief", []) if isinstance(item, dict)]
    )

    chapters: list[dict[str, Any]] = []
    visual_map_chapters: list[dict[str, Any]] = []
    for index, chapter in enumerate(chapter_outline):
        chapter_id = str(chapter.get("chapter_id") or f"ch{index + 1}")
        fallback_graphic_path = graphics[index] if index < len(graphics) else None
        prebaked_visuals = visual_prebake.get(chapter_id, {})
        generated_chapter_assets = generated_keyframes.get(chapter_id, [])
        supporting_images = [
            path
            for path in prebaked_visuals.get("supporting_images", [])
            if isinstance(path, Path) and path.exists()
        ]
        proof_asset_path = prebaked_visuals.get("proof_asset_path") or (generated_chapter_assets[0] if generated_chapter_assets else fallback_graphic_path)
        if proof_asset_path is not None and prebaked_visuals.get("proof_asset_path") is not None:
            proof_asset_type = str(prebaked_visuals.get("proof_asset_type") or "generated-keyart")
        elif generated_chapter_assets:
            proof_asset_type = "generated-keyart"
        else:
            proof_asset_type = "graphics-card" if fallback_graphic_path else "missing"
        supporting_b_roll: list[dict[str, Any]] = []
        seen_asset_paths: set[str] = set()
        for item in approved_by_chapter.get(chapter_id, []):
            asset_path = str(item.get("local_asset_path") or "").strip()
            if not asset_path:
                continue
            if asset_path in seen_asset_paths:
                continue
            seen_asset_paths.add(asset_path)
            supporting_b_roll.append(
                {
                    "clip_id": str(item.get("clip_id") or ""),
                    "asset_path": asset_path,
                    "source_type": str(item.get("source_type") or ""),
                    "source_track": "production",
                }
            )
        for item in production_ingests.get(chapter_id, []):
            asset_path = str(item.get("local_path") or "").strip()
            if not asset_path or asset_path in seen_asset_paths:
                continue
            seen_asset_paths.add(asset_path)
            supporting_b_roll.append(
                {
                    "clip_id": str(item.get("clip_id") or ""),
                    "asset_path": asset_path,
                    "source_type": str(item.get("source_type") or "stock-library"),
                    "source_track": str(item.get("source_track") or "production"),
                }
            )
        for item in generated_video_ingests.get(chapter_id, []):
            asset_path = str(item.get("local_path") or "").strip()
            if not asset_path or asset_path in seen_asset_paths:
                continue
            seen_asset_paths.add(asset_path)
            supporting_b_roll.append(
                {
                    "clip_id": str(item.get("clip_id") or ""),
                    "asset_path": asset_path,
                    "source_type": str(item.get("source_type") or "generated-media"),
                    "source_track": str(item.get("source_track") or "generated"),
                    "generation_type": str(item.get("generation_type") or ""),
                }
            )
        for item in exploration_ingests.get(chapter_id, []):
            asset_path = str(item.get("local_path") or "").strip()
            if not asset_path or asset_path in seen_asset_paths:
                continue
            seen_asset_paths.add(asset_path)
            supporting_b_roll.append(
                {
                    "clip_id": str(item.get("clip_id") or ""),
                    "asset_path": asset_path,
                    "source_type": str(item.get("source_type") or "exploration"),
                    "source_track": str(item.get("source_track") or "exploration"),
                }
            )
        fallback_graphics: list[str] = []
        if proof_asset_path is not None:
            fallback_graphics.append(relative_to_project(proof_asset_path, project_root))
        for prebaked_path in supporting_images:
            relative_path = relative_to_project(prebaked_path, project_root)
            if relative_path not in fallback_graphics:
                fallback_graphics.append(relative_path)
        for generated_path in generated_chapter_assets[1:]:
            relative_path = relative_to_project(generated_path, project_root)
            if relative_path not in fallback_graphics:
                fallback_graphics.append(relative_path)
        if fallback_graphic_path is not None and fallback_graphic_path != proof_asset_path:
            relative_path = relative_to_project(fallback_graphic_path, project_root)
            if relative_path not in fallback_graphics:
                fallback_graphics.append(relative_path)
        approved_generation_slots = [item for item in approved_generated_assets if item["chapter_id"] == chapter_id]

        chapters.append(
            {
                "chapter_id": chapter_id,
                "title": chapter.get("title"),
                "scene_goal": chapter.get("summary") or chapter.get("chapter_goal"),
                "proof_asset": {
                    "path": relative_to_project(proof_asset_path, project_root) if proof_asset_path else None,
                    "type": proof_asset_type,
                },
                "supporting_b_roll": supporting_b_roll,
                "fallback_graphics": fallback_graphics,
                "must_capture_list": [],
                "max_repeat_uses": int(prebaked_visuals.get("max_repeat_uses", 2)),
                "approved_generation_slots": approved_generation_slots,
            }
        )
        visual_map_chapters.append(
            {
                "chapter_id": chapter_id,
                "shot_intent": (clip_sourcing_brief.get(chapter_id) or [{}])[0].get("shot_intent"),
                "proof_asset": relative_to_project(proof_asset_path, project_root) if proof_asset_path else None,
                "supporting_b_roll": [item["asset_path"] for item in supporting_b_roll],
                "fallback_graphics": fallback_graphics,
            }
        )

    scene_payload = {
        "content_id": primary.get("content_id") or project_root.name,
        "platforms": primary.get("platforms", []),
        "deliverable_type": primary.get("deliverable_type"),
        "chapters": chapters,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    visual_map_payload = {
        "content_id": scene_payload["content_id"],
        "chapters": visual_map_chapters,
        "generated_at": scene_payload["generated_at"],
    }
    generation_budget_payload = {
        "content_id": scene_payload["content_id"],
        "quota": extract_quota(generation_budget_decision),
        "approved_generation_slots": approved_generated_assets,
        "blocked_generation_slots": blocked_generated_assets,
        "generated_at": scene_payload["generated_at"],
    }

    scene_output = (project_root / args.scene_output).resolve()
    visual_map_output = (project_root / args.visual_map_output).resolve()
    generation_budget_output = (project_root / args.generation_budget_output).resolve()
    write_json(scene_output, scene_payload)
    write_json(visual_map_output, visual_map_payload)
    write_json(generation_budget_output, generation_budget_payload)
    print(
        json.dumps(
            {
                "scene_output": str(scene_output),
                "visual_map_output": str(visual_map_output),
                "generation_budget_output": str(generation_budget_output),
                "chapter_count": len(chapters),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
