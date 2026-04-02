#!/usr/bin/env python3
"""Build transition and emphasis-fx plans from a scene manifest."""

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
        "--transition-output",
        default="content/postproduction/transition-plan.json",
        help="Transition plan output path relative to the project root.",
    )
    parser.add_argument(
        "--emphasis-output",
        default="content/postproduction/emphasis-fx-plan.json",
        help="Emphasis FX plan output path relative to the project root.",
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


def transition_style(scene_goal: str) -> str:
    if any(keyword in scene_goal for keyword in ("框架", "步骤", "模板")):
        return "framework_reveal"
    if any(keyword in scene_goal for keyword in ("案例", "证明", "例子")):
        return "proof_match_cut"
    return "chapter_pulse"


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)
    scene_manifest = load_json(project_root / "content" / "postproduction" / "scene-manifest.json")
    scenes = [item for item in scene_manifest.get("scenes", []) if isinstance(item, dict)]

    transitions: list[dict[str, Any]] = []
    for current, nxt in zip(scenes, scenes[1:], strict=False):
        style = transition_style(str(nxt.get("scene_goal") or ""))
        transitions.append(
            {
                "from_scene_id": current.get("scene_id"),
                "to_scene_id": nxt.get("scene_id"),
                "style": style,
                "duration_frames": 8 if style == "chapter_pulse" else 6,
                "rationale": str(nxt.get("scene_goal") or ""),
            }
        )

    emphasis_payload = {
        "content_id": scene_manifest.get("content_id") or project_root.name,
        "scene_fx": [
            {
                "scene_id": scene.get("scene_id"),
                "effects": scene.get("emphasis_fx", []),
            }
            for scene in scenes
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    transition_payload = {
        "content_id": scene_manifest.get("content_id") or project_root.name,
        "scene_count": len(scenes),
        "transitions": transitions,
        "generated_at": emphasis_payload["generated_at"],
    }

    transition_output = (project_root / args.transition_output).resolve()
    emphasis_output = (project_root / args.emphasis_output).resolve()
    write_json(transition_output, transition_payload)
    write_json(emphasis_output, emphasis_payload)
    print(
        json.dumps(
            {
                "transition_output": str(transition_output),
                "emphasis_output": str(emphasis_output),
                "transition_count": len(transitions),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
