#!/usr/bin/env python3
"""Build transition and emphasis-fx plans from a scene manifest.

转场不再是"同类场景永远同一种"：按 scene_goal 分类后在类别内轮换转场库，
并依据本期 visual_grammar 偏好微调，避免整片只有 2-3 种切法。
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# 转场库：按场景意图分类，每类多个变体供轮换。
TRANSITION_POOLS: dict[str, list[str]] = {
    # 框架/步骤/模板类：强调结构揭示
    "framework": ["framework_reveal", "grid_build_in", "wipe_reveal", "stack_slide"],
    # 案例/证明类：强调画面对接与因果
    "proof": ["proof_match_cut", "whip_pan_match", "morph_dissolve", "j_cut"],
    # 转折/反转类：制造节奏断点
    "turn": ["flash_cut", "glitch_jump", "speed_ramp_cut", "hard_cut_punch"],
    # 默认章节推进
    "pulse": ["chapter_pulse", "cross_dissolve", "soft_fade", "light_leak_swipe"],
}

# 视觉语法 -> 偏好的转场类别权重微调（让转场和画面风格协同）。
GRAMMAR_TRANSITION_BIAS: dict[str, str] = {
    "neon_mood": "glitch_jump",
    "film_grain_retro": "light_leak_swipe",
    "documentary_candid": "j_cut",
    "info_viz": "grid_build_in",
    "split_compare": "whip_pan_match",
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


def transition_category(scene_goal: str) -> str:
    if any(keyword in scene_goal for keyword in ("框架", "步骤", "模板", "方法", "清单")):
        return "framework"
    if any(keyword in scene_goal for keyword in ("案例", "证明", "例子", "数据", "证据")):
        return "proof"
    if any(keyword in scene_goal for keyword in ("反转", "转折", "其实", "真相", "误区")):
        return "turn"
    return "pulse"


def recommended_visual_grammar(project_root: Path) -> str:
    """取本期 divergence contract 推荐的视觉语法 id，用于转场偏好。"""
    contract = load_json(project_root / "planning" / "creative-divergence-brief.json")
    plan = contract.get("rotation_plan") if isinstance(contract.get("rotation_plan"), dict) else {}
    grammars = plan.get("visual_grammars") if isinstance(plan.get("visual_grammars"), dict) else {}
    rec = grammars.get("recommended") if isinstance(grammars.get("recommended"), dict) else {}
    return str(rec.get("id") or "")


def pick_transition(category: str, rotation_index: int, grammar_bias: str | None) -> str:
    pool = TRANSITION_POOLS.get(category, TRANSITION_POOLS["pulse"])
    # 第一次出现某类别时优先用 grammar 偏好的转场（若该转场属于本类别池）。
    if grammar_bias and grammar_bias in pool and rotation_index == 0:
        return grammar_bias
    return pool[rotation_index % len(pool)]


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)
    scene_manifest = load_json(project_root / "content" / "postproduction" / "scene-manifest.json")
    scenes = [item for item in scene_manifest.get("scenes", []) if isinstance(item, dict)]
    grammar_bias = GRAMMAR_TRANSITION_BIAS.get(recommended_visual_grammar(project_root))

    transitions: list[dict[str, Any]] = []
    category_counts: dict[str, int] = {}
    for current, nxt in zip(scenes, scenes[1:]):
        category = transition_category(str(nxt.get("scene_goal") or ""))
        rotation_index = category_counts.get(category, 0)
        category_counts[category] = rotation_index + 1
        style = pick_transition(category, rotation_index, grammar_bias)
        transitions.append(
            {
                "from_scene_id": current.get("scene_id"),
                "to_scene_id": nxt.get("scene_id"),
                "category": category,
                "style": style,
                "duration_frames": 8 if category == "pulse" else 6,
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
