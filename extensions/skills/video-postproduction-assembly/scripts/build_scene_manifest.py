#!/usr/bin/env python3
"""Build a content-driven scene manifest for midform video assembly."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm"}
DISALLOWED_PRIMARY_ASSET_TYPES = {"graphics-card", "text-card", "text-only-card"}


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


def fallback_quote_text(*candidates: str, max_length: int = 28) -> str:
    for candidate in candidates:
        text = str(candidate or "").strip().replace("\n", "")
        if not text:
            continue
        text = text.split("。", 1)[0].split("？", 1)[0].split("！", 1)[0].strip("，,:： ")
        if text:
            return text[:max_length]
    return "先进入现实"


def normalize_typewriter_quote(raw_quote: Any) -> dict[str, Any] | None:
    if isinstance(raw_quote, str):
        text = raw_quote.strip()
        if not text:
            return None
        return {
            "type": "typewriter_quote",
            "text": text,
            "anchor": "upper_center",
            "chars_per_second": 8,
            "start_offset_seconds": 0.0,
            "duration_seconds": min(max(len(text) / 5.5, 2.4), 4.4),
        }
    if not isinstance(raw_quote, dict):
        return None
    text = str(raw_quote.get("text") or "").strip()
    if not text:
        return None
    payload = {
        "type": "typewriter_quote",
        "text": text,
        "anchor": str(raw_quote.get("anchor") or "upper_center"),
        "chars_per_second": float(raw_quote.get("chars_per_second") or 8),
        "start_offset_seconds": float(raw_quote.get("start_offset_seconds") or 0.0),
        "duration_seconds": float(raw_quote.get("duration_seconds") or min(max(len(text) / 5.5, 2.4), 4.4)),
    }
    if raw_quote.get("target_role"):
        payload["target_role"] = str(raw_quote.get("target_role"))
    return payload


def expand_candidates(project_root: Path, raw_path: str | None) -> list[Path]:
    if not isinstance(raw_path, str) or not raw_path.strip():
        return []
    raw_value = raw_path.strip()
    if any(token in raw_value for token in ("*", "?", "[")):
        return [path.resolve() for path in sorted(project_root.glob(raw_value)) if path.is_file()]

    candidate = Path(raw_value)
    if not candidate.is_absolute():
        candidate = project_root / candidate
    candidate = candidate.resolve()
    if not candidate.exists() or not candidate.is_file():
        return []
    return [candidate]


def build_emphasis_fx(
    chapter_title: str,
    chapter_goal: str,
    *,
    index: int,
    lead_hook: str,
    chapter_payload: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    combined = f"{chapter_title} {chapter_goal}"
    explicit_quotes = []
    if isinstance(chapter_payload, dict):
        explicit_quotes = [
            normalized
            for normalized in (
                normalize_typewriter_quote(item)
                for item in chapter_payload.get("emphasis_quotes", [])
            )
            if normalized is not None
        ]

    def merge_effects(*base_effects: dict[str, Any]) -> list[dict[str, Any]]:
        if explicit_quotes:
            filtered_base_effects = [effect for effect in base_effects if effect.get("type") != "typewriter_quote"]
            has_camera_push = any(effect.get("type") == "camera_push" for effect in filtered_base_effects)
            return [
                *filtered_base_effects,
                *explicit_quotes,
                *([] if has_camera_push else [{"type": "camera_push", "intensity": "high" if index == 0 else "medium"}]),
            ]
        return list(base_effects)

    if index == 0 or any(keyword in combined for keyword in ("问题", "危险", "冲突", "异常", "开场")):
        opening_quote = fallback_quote_text(lead_hook, chapter_title, chapter_goal, max_length=30)
        return merge_effects(
            {"type": "headline_punch", "intensity": "high"},
            {
                "type": "typewriter_quote",
                "text": opening_quote,
                "anchor": "upper_center",
                "chars_per_second": 8,
                "start_offset_seconds": 0.0,
                "duration_seconds": min(max(len(opening_quote) / 5.2, 2.8), 4.6),
            },
            {"type": "camera_push", "intensity": "high"},
        )
    if any(keyword in combined for keyword in ("案例", "offer", "证明", "例子")):
        proof_quote = fallback_quote_text(chapter_title, chapter_goal, max_length=24)
        return merge_effects(
            {"type": "proof_focus", "intensity": "medium"},
            {
                "type": "typewriter_quote",
                "text": proof_quote,
                "anchor": "upper_center",
                "chars_per_second": 9,
                "start_offset_seconds": 0.0,
                "duration_seconds": min(max(len(proof_quote) / 5.2, 2.6), 4.0),
                "target_role": "keyart",
            },
            {"type": "camera_push", "intensity": "medium"},
        )
    if any(keyword in combined for keyword in ("框架", "步骤", "模板", "四步")):
        framework_quote = fallback_quote_text(chapter_title, chapter_goal, max_length=24)
        return merge_effects(
            {"type": "framework_stack", "intensity": "medium"},
            {
                "type": "typewriter_quote",
                "text": framework_quote,
                "anchor": "upper_center",
                "chars_per_second": 9,
                "start_offset_seconds": 0.0,
                "duration_seconds": min(max(len(framework_quote) / 5.2, 2.8), 4.2),
            },
            {"type": "camera_push", "intensity": "medium"},
        )
    if any(keyword in combined for keyword in ("动作", "信号", "退出")):
        action_quote = fallback_quote_text(chapter_title, chapter_goal, max_length=20)
        return merge_effects(
            {"type": "key_phrase_glow", "intensity": "medium"},
            {
                "type": "typewriter_quote",
                "text": action_quote,
                "anchor": "center",
                "chars_per_second": 7,
                "start_offset_seconds": 0.0,
                "duration_seconds": min(max(len(action_quote) / 5.0, 2.4), 3.4),
            },
            {"type": "camera_push", "intensity": "medium"},
        )
    if explicit_quotes:
        return [
            {"type": "key_phrase_glow", "intensity": "medium"},
            *explicit_quotes,
            {"type": "camera_push", "intensity": "medium"},
        ]
    return [
        {"type": "key_phrase_glow", "intensity": "medium"},
        {"type": "camera_push", "intensity": "medium"},
    ]


def motion_recipe(asset_type: str) -> str:
    if asset_type in DISALLOWED_PRIMARY_ASSET_TYPES:
        return "ken_burns_push"
    return "steady_crop"


def infer_media_type(raw_path: str | None) -> str:
    suffix = Path(str(raw_path or "")).suffix.lower()
    if suffix in VIDEO_SUFFIXES:
        return "video"
    if suffix in IMAGE_SUFFIXES:
        return "image"
    return "image"


def choose_primary_asset(scene_asset: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    project_root = Path(scene_asset.get("__project_root__") or "")
    proof_asset = scene_asset.get("proof_asset") if isinstance(scene_asset.get("proof_asset"), dict) else {}
    supporting_b_roll = scene_asset.get("supporting_b_roll") if isinstance(scene_asset.get("supporting_b_roll"), list) else []
    fallback_graphics = scene_asset.get("fallback_graphics") if isinstance(scene_asset.get("fallback_graphics"), list) else []

    proof_path = str(proof_asset.get("path") or "").strip()
    proof_type = str(proof_asset.get("type") or "").strip()
    if proof_path and proof_type not in DISALLOWED_PRIMARY_ASSET_TYPES:
        return (
            {
                "path": proof_path,
                "type": proof_type,
                "role": "proof" if proof_type == "generated-keyart" else "primary",
                "source": "proof_asset",
            },
            [],
        )

    for item in supporting_b_roll:
        if not isinstance(item, dict):
            continue
        asset_path = str(item.get("asset_path") or "").strip()
        if not asset_path:
            continue
        return (
            {
                "path": asset_path,
                "type": infer_media_type(asset_path),
                "role": "background_visual",
                "source": "supporting_b_roll",
            },
            ["primary_visual_promoted_from_supporting_b_roll"] if proof_path else [],
        )

    for raw_path in fallback_graphics:
        fallback_path = str(raw_path or "").strip()
        if not fallback_path:
            continue
        expanded_candidates = expand_candidates(project_root, fallback_path) if str(project_root) else []
        if expanded_candidates:
            candidate = expanded_candidates[0]
            if candidate.name.startswith("card-"):
                continue
            return (
                {
                    "path": str(candidate.relative_to(project_root)),
                    "type": infer_media_type(str(candidate.relative_to(project_root))),
                    "role": "fallback_visual",
                    "source": "fallback_graphics",
                },
                ["primary_visual_promoted_from_fallback_graphics"],
            )
        if Path(fallback_path).name.startswith("card-"):
            continue
        return (
            {
                "path": fallback_path,
                "type": infer_media_type(fallback_path),
                "role": "fallback_visual",
                "source": "fallback_graphics",
            },
            ["primary_visual_promoted_from_fallback_graphics"],
        )

    warnings: list[str] = []
    if proof_path:
        warnings.append("pure_text_card_fallback_only")
    return (
        {
            "path": proof_path or None,
            "type": proof_type or "graphics-card",
            "role": "fallback_text_card",
            "source": "proof_asset",
        },
        warnings,
    )


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
        scene_asset = {**asset_chapters.get(chapter_id, {}), "__project_root__": str(project_root)}
        primary_asset, visual_warnings = choose_primary_asset(scene_asset)
        asset_type = str(primary_asset.get("type") or "image")
        chapter_title = str(chapter.get("title") or "")
        chapter_goal = str(chapter.get("chapter_goal") or chapter.get("summary") or scene_asset.get("scene_goal") or "")

        scenes.append(
            {
                "scene_id": f"scene-{index + 1:02d}-{chapter_id}",
                "chapter_id": chapter_id,
                "scene_title": chapter_title,
                "scene_goal": chapter_goal,
                "primary_asset": primary_asset,
                "supporting_assets": scene_asset.get("supporting_b_roll", []),
                "motion_recipe": motion_recipe(asset_type),
                "transition_in": "cold_open_cut" if index == 0 else "chapter_pulse",
                "transition_out": "resolve_hold" if index == len(chapter_outline) - 1 else "content_lift",
                "subtitle_mode": "bilingual_hardsub",
                "subtitle_layout": "zh_en_dual_line",
                "visual_treatment": {
                    "base_visual_required": True,
                    "pure_text_card_allowed": False,
                    "overlay_text_allowed": True,
                    "preferred_overlay_anchor": "upper_center",
                    "warnings": visual_warnings,
                },
                "emphasis_fx": build_emphasis_fx(
                    chapter_title,
                    chapter_goal,
                    index=index,
                    lead_hook=lead_hook,
                    chapter_payload=chapter,
                ),
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
