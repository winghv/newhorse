#!/usr/bin/env python3
"""Build a content-driven scene manifest for midform video assembly."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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
        default="content/postproduction/scene-manifest.json",
        help="Scene manifest output path relative to the project root.",
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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def primary_packet(payload: dict[str, Any]) -> dict[str, Any]:
    nested = payload.get("content_packet")
    return nested if isinstance(nested, dict) else payload


def build_emphasis_fx(
    chapter_title: str,
    chapter_goal: str,
    *,
    index: int,
    lead_hook: str,
) -> list[dict[str, Any]]:
    combined = f"{chapter_title} {chapter_goal}"
    if index == 0 or any(keyword in combined for keyword in ("问题", "危险", "冲突", "异常", "开场")):
        return [
            {"type": "headline_punch", "intensity": "high"},
            {
                "type": "typewriter_quote",
                "text": "平台不是更懂你",
                "anchor": "upper_center",
                "chars_per_second": 8,
                "start_offset_seconds": 0.0,
                "duration_seconds": 3.8,
            },
            {"type": "camera_push", "intensity": "high"},
        ]
    if any(keyword in combined for keyword in ("案例", "offer", "证明", "例子")):
        return [
            {"type": "proof_focus", "intensity": "medium"},
            {
                "type": "typewriter_quote",
                "text": "平台没有在帮你逼近真相",
                "anchor": "upper_center",
                "chars_per_second": 9,
                "start_offset_seconds": 0.0,
                "duration_seconds": 3.1,
                "target_role": "keyart",
            },
            {"type": "camera_push", "intensity": "medium"},
        ]
    if any(keyword in combined for keyword in ("框架", "步骤", "模板", "四步")):
        return [
            {"type": "framework_stack", "intensity": "medium"},
            {
                "type": "typewriter_quote",
                "text": "看目标 / 查来源 / 补反例 / 离开 feed 验证",
                "anchor": "upper_center",
                "chars_per_second": 9,
                "start_offset_seconds": 0.0,
                "duration_seconds": 4.0,
            },
            {"type": "camera_push", "intensity": "medium"},
        ]
    if any(keyword in combined for keyword in ("动作", "信号", "退出")):
        return [
            {"type": "key_phrase_glow", "intensity": "medium"},
            {
                "type": "typewriter_quote",
                "text": "先退出 feed",
                "anchor": "center",
                "chars_per_second": 7,
                "start_offset_seconds": 0.0,
                "duration_seconds": 2.6,
            },
            {"type": "camera_push", "intensity": "medium"},
        ]
    return [
        {"type": "key_phrase_glow", "intensity": "medium"},
        {"type": "camera_push", "intensity": "medium"},
    ]


def motion_recipe(asset_type: str) -> str:
    return "ken_burns_push" if asset_type == "graphics-card" else "steady_crop"


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)

    packet_path = detect_content_packet(project_root)
    packet = primary_packet(load_json(packet_path))
    hook_hypotheses = [str(item) for item in packet.get("hook_hypotheses", []) if isinstance(item, str) and item.strip()]
    lead_hook = hook_hypotheses[0] if hook_hypotheses else ""
    scene_asset_plan = load_json(project_root / "assets" / "scene-asset-plan.json")
    asset_chapters = {
        str(item.get("chapter_id") or ""): item
        for item in scene_asset_plan.get("chapters", [])
        if isinstance(item, dict)
    }

    scenes: list[dict[str, Any]] = []
    chapter_outline = [item for item in packet.get("chapter_outline", []) if isinstance(item, dict)]
    for index, chapter in enumerate(chapter_outline):
        chapter_id = str(chapter.get("chapter_id") or f"ch{index + 1}")
        scene_asset = asset_chapters.get(chapter_id, {})
        proof_asset = scene_asset.get("proof_asset") if isinstance(scene_asset.get("proof_asset"), dict) else {}
        asset_type = str(proof_asset.get("type") or "graphics-card")
        chapter_title = str(chapter.get("title") or "")
        chapter_goal = str(chapter.get("chapter_goal") or chapter.get("summary") or scene_asset.get("scene_goal") or "")

        scenes.append(
            {
                "scene_id": f"scene-{index + 1:02d}-{chapter_id}",
                "chapter_id": chapter_id,
                "scene_title": chapter_title,
                "scene_goal": chapter_goal,
                "primary_asset": {
                    "path": proof_asset.get("path"),
                    "type": asset_type,
                },
                "supporting_assets": scene_asset.get("supporting_b_roll", []),
                "motion_recipe": motion_recipe(asset_type),
                "transition_in": "cold_open_cut" if index == 0 else "chapter_pulse",
                "transition_out": "resolve_hold" if index == len(chapter_outline) - 1 else "content_lift",
                "subtitle_mode": "narrated_hardsub",
                "emphasis_fx": build_emphasis_fx(chapter_title, chapter_goal, index=index, lead_hook=lead_hook),
            }
        )

    payload = {
        "content_id": packet.get("content_id") or project_root.name,
        "platforms": packet.get("platforms", []),
        "deliverable_type": packet.get("deliverable_type"),
        "scene_count": len(scenes),
        "scenes": scenes,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    output_path = (project_root / args.output).resolve()
    write_json(output_path, payload)
    print(json.dumps({"output_path": str(output_path), "scene_count": len(scenes)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
