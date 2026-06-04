#!/usr/bin/env python3
"""Build a MiniMax shot plan and generation ledger from approved slots.

除了把 approved slot 整理成 shot plan，本脚本还为每个 slot **注入电影语言 prompt**：
从 cinematic_prompt_lib 按 slot 序号与本期 visual_grammar 组合出带构图/光影/景深/
色彩的完整 prompt，保证同期镜头有变化梯度，从根上解决"全 AI 图却一个调调"。
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cinematic_prompt_lib import build_cinematic_prompt, diversity_metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", help="Media package root directory.")
    parser.add_argument("--content-id", help="Content package id under the media-ops root.")
    parser.add_argument(
        "--media-ops-root",
        help="Root directory containing media packages. Defaults to repo-local data/media-ops.",
    )
    parser.add_argument(
        "--shot-plan-output",
        default="assets/minimax-shot-plan.json",
        help="MiniMax shot plan output path relative to the project root.",
    )
    parser.add_argument(
        "--ledger-output",
        default="assets/generation-ledger.json",
        help="Generation ledger output path relative to the project root.",
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


def visual_grammar_keywords(project_root: Path) -> list[str]:
    """从本期 divergence contract 取选定视觉语法的电影关键词，注入生图 prompt。"""
    contract = load_json(project_root / "planning" / "creative-divergence-brief.json")
    plan = contract.get("rotation_plan") if isinstance(contract.get("rotation_plan"), dict) else {}
    grammars = plan.get("visual_grammars") if isinstance(plan.get("visual_grammars"), dict) else {}
    recommended = grammars.get("recommended") if isinstance(grammars.get("recommended"), dict) else {}
    rec_id = recommended.get("id")
    if not rec_id:
        return []
    # 关键词在 rotation-pools 的 cinematic_keywords 字段里。
    media_ops_root = project_root.parent
    pools = load_json(media_ops_root / "_strategy" / "rotation-pools.json")
    for item in pools.get("visual_grammars", []):
        if isinstance(item, dict) and item.get("id") == rec_id:
            return [str(k) for k in item.get("cinematic_keywords", []) if str(k).strip()]
    return []


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)
    generation_budget = load_json(project_root / "assets" / "generation-budget.json")
    grammar_keywords = visual_grammar_keywords(project_root)

    approved_slots = [item for item in generation_budget.get("approved_generation_slots", []) if isinstance(item, dict)]
    blocked_slots = [item for item in generation_budget.get("blocked_generation_slots", []) if isinstance(item, dict)]
    quota = generation_budget.get("quota") if isinstance(generation_budget.get("quota"), dict) else {}

    # 为每个 approved slot 注入电影语言 prompt（保留原 subject/意图，叠加镜头语言）。
    chapter_seen: dict[str, int] = {}
    enriched_slots: list[dict[str, Any]] = []
    for slot_index, slot in enumerate(approved_slots):
        chapter_id = str(slot.get("chapter_id") or "")
        chapter_index = list(dict.fromkeys([str(s.get("chapter_id") or "") for s in approved_slots])).index(chapter_id) if chapter_id else 0
        chapter_seen[chapter_id] = chapter_seen.get(chapter_id, 0) + 1
        subject = str(slot.get("subject") or slot.get("prompt") or slot.get("description") or slot.get("reason") or "")
        cine = build_cinematic_prompt(
            subject=subject,
            slot_index=slot_index,
            chapter_index=chapter_index,
            visual_grammar_keywords=grammar_keywords,
            scene_goal=str(slot.get("scene_goal") or ""),
        )
        merged = dict(slot)
        merged["base_subject"] = subject
        merged["cinematic_prompt"] = cine["prompt"]
        merged["cinematic"] = cine["cinematic"]
        enriched_slots.append(merged)

    shot_plan_payload = {
        "content_id": generation_budget.get("content_id") or project_root.name,
        "quota": quota,
        "visual_grammar_keywords": grammar_keywords,
        "approved_slots": enriched_slots,
        "blocked_slots": blocked_slots,
        "diversity": diversity_metrics(enriched_slots),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    ledger_payload = {
        "content_id": shot_plan_payload["content_id"],
        "entries": [
            {
                "slot_id": str(item.get("slot_id") or ""),
                "chapter_id": str(item.get("chapter_id") or ""),
                "generation_type": str(item.get("generation_type") or ""),
                "cinematic_prompt": str(item.get("cinematic_prompt") or ""),
                "status": "not_run",
                "reason": str(item.get("reason") or ""),
            }
            for item in enriched_slots
        ],
        "generated_at": shot_plan_payload["generated_at"],
    }

    shot_plan_output = (project_root / args.shot_plan_output).resolve()
    ledger_output = (project_root / args.ledger_output).resolve()
    write_json(shot_plan_output, shot_plan_payload)
    write_json(ledger_output, ledger_payload)
    print(
        json.dumps(
            {
                "shot_plan_output": str(shot_plan_output),
                "ledger_output": str(ledger_output),
                "approved_slot_count": len(approved_slots),
                "diversity": shot_plan_payload["diversity"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
