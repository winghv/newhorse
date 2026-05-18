#!/usr/bin/env python3
"""Gate visual production readiness before voiceover and render."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TEXT_CARD_TYPES = {"graphics-card", "text-card", "text-only-card"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", help="Media package root directory.")
    parser.add_argument("--content-id", help="Content package id under the media-ops root.")
    parser.add_argument(
        "--media-ops-root",
        help="Root directory containing media packages. Defaults to repo-local data/media-ops.",
    )
    parser.add_argument(
        "--output",
        default="assets/visual-production-gate.json",
        help="Gate output path relative to project root.",
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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def detect_content_packet(project_root: Path) -> Path | None:
    content_dir = project_root / "content"
    for pattern in ("*video.json", "content-packet.json", "*.json"):
        matches = sorted(path for path in content_dir.glob(pattern) if path.is_file())
        if matches:
            return matches[0]
    return None


def primary_packet(payload: dict[str, Any]) -> dict[str, Any]:
    nested = payload.get("content_packet")
    return nested if isinstance(nested, dict) else payload


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


def is_text_card_asset(proof_asset: dict[str, Any]) -> bool:
    asset_type = str(proof_asset.get("type") or "").strip().lower()
    raw_path = str(proof_asset.get("path") or "")
    return asset_type in TEXT_CARD_TYPES or Path(raw_path).name.startswith("card-")


def is_generated_visual_path(raw_path: str | None) -> bool:
    value = str(raw_path or "").lower()
    return any(token in value for token in ("generated", "ai-keyframes", "visual-prebake"))


def existing_media_count(project_root: Path, raw_paths: list[str], suffixes: set[str]) -> int:
    count = 0
    seen: set[Path] = set()
    for raw_path in raw_paths:
        candidate = resolve_candidate(project_root, raw_path)
        if candidate is None or candidate in seen or candidate.suffix.lower() not in suffixes:
            continue
        if candidate.exists():
            count += 1
            seen.add(candidate)
    return count


def build_gate(project_root: Path) -> dict[str, Any]:
    packet_path = detect_content_packet(project_root)
    packet = primary_packet(load_json(packet_path)) if packet_path else {}
    platforms = packet.get("platforms") if isinstance(packet.get("platforms"), list) else []
    is_bilibili_midform = "bilibili" in platforms and packet.get("deliverable_type") == "midlong-video"

    scene_plan_path = project_root / "assets" / "scene-asset-plan.json"
    generation_budget_path = project_root / "assets" / "generation-budget.json"
    generation_ledger_path = project_root / "assets" / "generation-ledger.json"
    scene_plan = load_json(scene_plan_path)
    generation_budget = load_json(generation_budget_path)
    generation_ledger = load_json(generation_ledger_path)
    chapters = scene_plan.get("chapters") if isinstance(scene_plan.get("chapters"), list) else []

    primary_assets = [
        chapter.get("proof_asset")
        for chapter in chapters
        if isinstance(chapter, dict) and isinstance(chapter.get("proof_asset"), dict)
    ]
    text_card_primary_count = sum(1 for asset in primary_assets if is_text_card_asset(asset))
    primary_count = len(primary_assets)
    primary_text_card_ratio = round(text_card_primary_count / primary_count, 3) if primary_count else 0.0

    production_footage_paths: list[str] = []
    generated_visual_paths: list[str] = []
    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue
        proof_asset = chapter.get("proof_asset") if isinstance(chapter.get("proof_asset"), dict) else {}
        proof_path = str(proof_asset.get("path") or "")
        proof_type = str(proof_asset.get("type") or "")
        if proof_type == "generated-keyart" or is_generated_visual_path(proof_path):
            generated_visual_paths.append(proof_path)
        for raw_path in chapter.get("fallback_graphics", []):
            if isinstance(raw_path, str) and is_generated_visual_path(raw_path):
                generated_visual_paths.append(raw_path)
        for item in chapter.get("supporting_b_roll", []):
            if not isinstance(item, dict):
                continue
            asset_path = str(item.get("asset_path") or "")
            source_track = str(item.get("source_track") or "").lower()
            if source_track == "production":
                production_footage_paths.append(asset_path)
            if source_track == "generated" or is_generated_visual_path(asset_path):
                generated_visual_paths.append(asset_path)

    ledger_entries = generation_ledger.get("entries") if isinstance(generation_ledger.get("entries"), list) else []
    delivered_generation_count = 0
    for entry in ledger_entries:
        if not isinstance(entry, dict) or str(entry.get("status") or "").lower() != "success":
            continue
        asset_path = str(entry.get("asset_path") or "")
        candidate = resolve_candidate(project_root, asset_path)
        if candidate is not None and candidate.exists() and candidate.suffix.lower() in IMAGE_SUFFIXES | VIDEO_SUFFIXES:
            delivered_generation_count += 1
            generated_visual_paths.append(asset_path)

    production_footage_count = existing_media_count(project_root, production_footage_paths, VIDEO_SUFFIXES)
    generated_visual_count = existing_media_count(project_root, generated_visual_paths, IMAGE_SUFFIXES | VIDEO_SUFFIXES)
    approved_slots = generation_budget.get("approved_generation_slots")
    approved_generation_count = len(approved_slots) if isinstance(approved_slots, list) else 0

    checks: dict[str, dict[str, Any]] = {
        "scene_asset_plan_present": {
            "status": "pass" if scene_plan_path.exists() and chapters else "revise",
            "path": relative_to_project(scene_plan_path, project_root),
        },
        "primary_visuals_not_all_cards": {
            "status": "pass" if primary_count and primary_text_card_ratio < 1.0 else "revise",
            "primary_count": primary_count,
            "primary_text_card_ratio": primary_text_card_ratio,
        },
        "production_footage_present": {
            "status": "pass" if production_footage_count > 0 else "revise",
            "production_footage_count": production_footage_count,
        },
        "approved_generation_delivered": {
            "status": "pass" if approved_generation_count == 0 or delivered_generation_count > 0 else "revise",
            "approved_generation_count": approved_generation_count,
            "delivered_generation_count": delivered_generation_count,
        },
    }

    reasons: list[str] = []
    if checks["scene_asset_plan_present"]["status"] != "pass":
        reasons.append("scene_asset_plan_missing")
    if checks["primary_visuals_not_all_cards"]["status"] != "pass":
        reasons.append("primary_visuals_are_all_text_cards")
    if checks["production_footage_present"]["status"] != "pass":
        reasons.append("production_footage_missing")
    if checks["approved_generation_delivered"]["status"] != "pass":
        reasons.append("approved_generation_not_delivered")

    status = "pass"
    if is_bilibili_midform and reasons:
        status = "revise"
    elif not is_bilibili_midform:
        status = "not_applicable"

    return {
        "content_id": packet.get("content_id") or project_root.name,
        "platforms": platforms,
        "deliverable_type": packet.get("deliverable_type"),
        "status": status,
        "reasons": reasons if status == "revise" else [],
        "checks": checks,
        "summary": {
            "primary_visual_count": primary_count,
            "primary_text_card_count": text_card_primary_count,
            "primary_text_card_ratio": primary_text_card_ratio,
            "production_footage_count": production_footage_count,
            "generated_visual_count": generated_visual_count,
            "approved_generation_count": approved_generation_count,
            "delivered_generation_count": delivered_generation_count,
        },
        "source_paths": {
            "scene_asset_plan": relative_to_project(scene_plan_path, project_root) if scene_plan_path.exists() else None,
            "generation_budget": relative_to_project(generation_budget_path, project_root)
            if generation_budget_path.exists()
            else None,
            "generation_ledger": relative_to_project(generation_ledger_path, project_root)
            if generation_ledger_path.exists()
            else None,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)
    output_path = (project_root / args.output).resolve()
    payload = build_gate(project_root)
    write_json(output_path, payload)
    print(json.dumps({"output_path": relative_to_project(output_path, project_root), "status": payload["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
