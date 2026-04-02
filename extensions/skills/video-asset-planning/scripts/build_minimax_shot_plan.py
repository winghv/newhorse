#!/usr/bin/env python3
"""Build a MiniMax shot plan and generation ledger from approved slots."""

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


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)
    generation_budget = load_json(project_root / "assets" / "generation-budget.json")

    approved_slots = [item for item in generation_budget.get("approved_generation_slots", []) if isinstance(item, dict)]
    blocked_slots = [item for item in generation_budget.get("blocked_generation_slots", []) if isinstance(item, dict)]
    quota = generation_budget.get("quota") if isinstance(generation_budget.get("quota"), dict) else {}

    shot_plan_payload = {
        "content_id": generation_budget.get("content_id") or project_root.name,
        "quota": quota,
        "approved_slots": approved_slots,
        "blocked_slots": blocked_slots,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    ledger_payload = {
        "content_id": shot_plan_payload["content_id"],
        "entries": [
            {
                "slot_id": str(item.get("slot_id") or ""),
                "chapter_id": str(item.get("chapter_id") or ""),
                "generation_type": str(item.get("generation_type") or ""),
                "status": "not_run",
                "reason": str(item.get("reason") or ""),
            }
            for item in approved_slots
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
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
