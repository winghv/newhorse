#!/usr/bin/env python3
"""Build Bilibili opening and follow-conversion artifacts from an angle brief."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OPENING_WINDOWS = ("0-3s", "3-10s", "10-30s")
PROOF_WINDOWS = ("10-30s", "30-60s", "60-120s", "120s+")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", help="Media package root directory.")
    parser.add_argument("--content-id", help="Content package id under the media-ops root.")
    parser.add_argument(
        "--media-ops-root",
        help="Root directory containing media packages. Defaults to repo-local data/media-ops.",
    )
    parser.add_argument(
        "--structure-output",
        default="angles/attention-structure-template.json",
        help="Attention structure output path relative to the project root.",
    )
    parser.add_argument(
        "--follow-output",
        default="angles/follow-conversion-hooks.json",
        help="Follow conversion hooks output path relative to the project root.",
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


def infer_platform(angle_brief: dict[str, Any]) -> str:
    platforms = angle_brief.get("platforms")
    if isinstance(platforms, list) and platforms:
        return str(platforms[0])
    return "bilibili"


def infer_selected_topic(topic_selection: dict[str, Any]) -> str:
    selected_topic = topic_selection.get("selected_topic")
    if isinstance(selected_topic, dict):
        topic = selected_topic.get("topic")
        if isinstance(topic, str) and topic:
            return topic
    return ""


def infer_episode_completion_mode(angle_brief: dict[str, Any]) -> str:
    for key in ("episode_completion_mode", "completion_mode"):
        value = angle_brief.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    for key in ("is_multi_part", "multipart", "explicit_series_bridge"):
        value = angle_brief.get(key)
        if isinstance(value, bool):
            return "multipart" if value else "standalone"
    return "standalone"


def clean_backup_angle(value: str) -> str:
    cleaned = value.strip().strip("。")
    cleaned = cleaned.removeprefix("从")
    cleaned = cleaned.strip()
    if "切入" in cleaned:
        cleaned = cleaned.split("切入", 1)[0].strip("，, ")
    cleaned = cleaned.strip("“”\"' ")
    return cleaned or value.strip().strip("。")


def clean_proof_phrase(value: str) -> str:
    cleaned = value.strip().strip("。")
    for prefix in ("先", "再", "最后", "然后"):
        if cleaned.startswith(prefix):
            cleaned = cleaned.removeprefix(prefix).strip()
            break
    for marker in ("交付一套可截图的转换框架：", "交付一套可截图的框架：", "把判断框架完整跑一遍："):
        if cleaned.startswith(marker):
            cleaned = cleaned.removeprefix(marker).strip()
            break
    return cleaned.strip("。")


def infer_save_trigger(proof_plan: list[str]) -> str:
    for item in proof_plan:
        if any(keyword in item for keyword in ("框架", "步骤", "模板", "清单")):
            cleaned = clean_proof_phrase(item)
            return f"值得收藏，因为这条会把「{cleaned}」压成一套可截图的动作框架。"
    if proof_plan:
        return f"值得收藏，因为它会把「{clean_proof_phrase(proof_plan[-1])}」讲成可执行动作。"
    return "值得收藏，因为它不只给观点，还会给下一步动作。"


def infer_series_bridges(selected_topic: str, backup_angles: list[str]) -> list[str]:
    bridges = []
    for angle in backup_angles[:2]:
        bridges.append(f"下一条我会从「{clean_backup_angle(angle)}」继续拆。")
    if not bridges and selected_topic:
        bridges.append(f"下一条继续拆「{selected_topic}」里最容易卡住的一步。")
    return bridges


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)

    angle_path = project_root / "angles" / "angle-brief.json"
    topic_selection_path = project_root / "planning" / "topic-selection.json"
    pattern_pack_path = project_root / "benchmarks" / "bilibili-hook-patterns.json"

    angle_brief = load_json(angle_path)
    topic_selection = load_json(topic_selection_path)
    pattern_pack = load_json(pattern_pack_path)

    hook_hypotheses = [str(item) for item in angle_brief.get("hook_hypotheses", []) if item]
    proof_plan = [str(item) for item in angle_brief.get("proof_plan", []) if item]
    backup_angles = [str(item) for item in angle_brief.get("backup_angles", []) if item]
    lead_hook = hook_hypotheses[0] if hook_hypotheses else str(angle_brief.get("core_angle") or "")
    supporting_hooks = hook_hypotheses[1:]
    selected_topic = infer_selected_topic(topic_selection)
    comment_prompt = str(angle_brief.get("comment_prompt") or "")
    cta = str(angle_brief.get("cta") or "")
    episode_completion_mode = infer_episode_completion_mode(angle_brief)
    allow_series_bridge = episode_completion_mode == "multipart"

    opening_sequence = [
        {
            "time_window": OPENING_WINDOWS[0],
            "goal": "先给结果、冲突或异常点，阻断划走。",
            "script_line": lead_hook,
            "visual_intent": "直接上结论或异常，不做背景铺垫。",
            "retention_goal": "stop_the_scroll",
        },
        {
            "time_window": OPENING_WINDOWS[1],
            "goal": "补代价或误区，明确为什么现在就该继续看。",
            "script_line": supporting_hooks[0] if supporting_hooks else cta,
            "visual_intent": "把误判代价或常见错法说透。",
            "retention_goal": "explain_the_cost",
        },
        {
            "time_window": OPENING_WINDOWS[2],
            "goal": "在前 30 秒内给出第一层证明或框架承诺。",
            "script_line": proof_plan[0] if proof_plan else cta,
            "visual_intent": "第一层证据或第一块框架直接上屏。",
            "retention_goal": "prove_it_fast",
        },
    ]

    proof_reveal_plan = [
        {
            "time_window": PROOF_WINDOWS[index] if index < len(PROOF_WINDOWS) else PROOF_WINDOWS[-1],
            "proof_beat": proof,
            "why_this_beat_matters": "让观众在继续看下去前先拿到一层可验证内容。",
        }
        for index, proof in enumerate(proof_plan)
    ]

    save_trigger = infer_save_trigger(proof_plan)
    series_bridge_variants = infer_series_bridges(selected_topic, backup_angles) if allow_series_bridge else []
    follow_cta_variants = (
        [
            f"如果这条你有共鸣，下一条我把「{clean_backup_angle(backup_angles[0])}」拆开讲。"
            if backup_angles
            else f"如果这条你有共鸣，下一条我把「{selected_topic or lead_hook}」拆开讲。",
            f"如果你也卡在「{selected_topic or lead_hook}」，关注后继续看下一条。",
            cta or "先把问题压回现实，再决定要不要继续问 AI。",
        ]
        if allow_series_bridge
        else [
            cta or "先把问题压回现实，再做一次验证。",
            f"如果你也卡在「{selected_topic or lead_hook}」，先把最近一次输入逼成一次现实验证。",
            "别再先加一条收藏，先把最近学过的一样东西推进现实。",
        ]
    )

    structure_payload = {
        "content_id": project_root.name,
        "platform": infer_platform(angle_brief),
        "deliverable_type": angle_brief.get("deliverable_type") or "midlong-video",
        "episode_completion_mode": episode_completion_mode,
        "core_angle": angle_brief.get("core_angle"),
        "selected_topic": selected_topic,
        "lead_hook": lead_hook,
        "supporting_hooks": supporting_hooks,
        "opening_sequence": opening_sequence,
        "proof_reveal_plan": proof_reveal_plan,
        "retention_bridges": [
            {
                "stage": f"bridge-{index + 1}",
                "bridge_line": proof,
            }
            for index, proof in enumerate(proof_plan[1:], start=1)
        ],
        "save_trigger": save_trigger,
        "comment_trigger": comment_prompt,
        "follow_trigger": follow_cta_variants[0],
        "chapter_structure_template": [
            "cold_open",
            "cost_of_delay",
            "proof_or_case",
            "framework_delivery",
            "comment_and_follow_cta",
        ],
        "reference_patterns": pattern_pack.get("opening_patterns", [])[:2],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    follow_payload = {
        "content_id": project_root.name,
        "platform": structure_payload["platform"],
        "episode_completion_mode": episode_completion_mode,
        "comment_prompt": comment_prompt,
        "save_trigger": save_trigger,
        "follow_cta_variants": follow_cta_variants,
        "series_bridge_variants": series_bridge_variants,
        "pattern_pack_refs": [item.get("label") for item in pattern_pack.get("follow_conversion_patterns", [])],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    structure_output = (project_root / args.structure_output).resolve()
    follow_output = (project_root / args.follow_output).resolve()
    write_json(structure_output, structure_payload)
    write_json(follow_output, follow_payload)
    print(
        json.dumps(
            {
                "structure_output": str(structure_output),
                "follow_output": str(follow_output),
                "lead_hook": lead_hook,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
