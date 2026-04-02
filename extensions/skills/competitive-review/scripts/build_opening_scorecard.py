#!/usr/bin/env python3
"""Build an opening scorecard for Bilibili growth review."""

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
        default="review/opening-scorecard.json",
        help="Opening scorecard output path relative to the project root.",
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


def decide_status(opening_hold_power: int | None, proof_reveal_present: bool, follow_conversion_power: int | None) -> str:
    if opening_hold_power is None or follow_conversion_power is None:
        return "revise"
    if opening_hold_power >= 4 and proof_reveal_present and follow_conversion_power >= 3:
        return "pass"
    if opening_hold_power <= 1 or follow_conversion_power <= 1:
        return "block"
    return "revise"


def infer_opening_hold_power(
    score_by_dimension: dict[str, Any],
    *,
    proof_reveal_present: bool,
    opening_sequence: list[dict[str, Any]],
) -> tuple[int | None, str]:
    explicit = score_by_dimension.get("opening_hold_power")
    if isinstance(explicit, int):
        return explicit, "explicit"

    hook_strength = score_by_dimension.get("hook_strength")
    proof_strength = score_by_dimension.get("proof_strength")
    if not isinstance(hook_strength, int):
        return None, "missing"

    inferred = 0
    if hook_strength >= 5:
        inferred += 3
    elif hook_strength >= 4:
        inferred += 2
    elif hook_strength >= 3:
        inferred += 1

    if proof_reveal_present and isinstance(proof_strength, int) and proof_strength >= 4:
        inferred += 1
    if len(opening_sequence) >= 3 and all(str(item.get("script_line") or "").strip() for item in opening_sequence[:3]):
        inferred += 1

    return min(inferred, 5), "inferred"


def infer_follow_conversion_power(
    score_by_dimension: dict[str, Any],
    *,
    comment_trigger_present: bool,
    follow_trigger_present: bool,
) -> tuple[int | None, str]:
    explicit = score_by_dimension.get("follow_conversion_power")
    if isinstance(explicit, int):
        return explicit, "explicit"

    save_share_potential = score_by_dimension.get("save_share_potential")
    series_potential = score_by_dimension.get("series_potential")

    inferred = 0
    if comment_trigger_present:
        inferred += 1
    if follow_trigger_present:
        inferred += 1
    if comment_trigger_present and follow_trigger_present:
        inferred += 1
    if isinstance(save_share_potential, int) and save_share_potential >= 4:
        inferred += 1
    if isinstance(series_potential, int) and series_potential >= 4:
        inferred += 1

    return min(max(inferred, 1 if (comment_trigger_present or follow_trigger_present) else 0), 5), "inferred"


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)

    attention_path = project_root / "angles" / "attention-structure-template.json"
    scorecard_path = project_root / "review" / "competitive-scorecard.json"

    attention = load_json(attention_path)
    scorecard = load_json(scorecard_path)
    score_by_dimension = scorecard.get("score_by_dimension") if isinstance(scorecard.get("score_by_dimension"), dict) else {}

    opening_sequence = attention.get("opening_sequence") if isinstance(attention.get("opening_sequence"), list) else []
    proof_reveal_plan = attention.get("proof_reveal_plan") if isinstance(attention.get("proof_reveal_plan"), list) else []
    proof_reveal_present = bool(proof_reveal_plan)
    comment_trigger_present = bool(attention.get("comment_trigger"))
    follow_trigger_present = bool(attention.get("follow_trigger"))
    opening_hold_power, opening_hold_source = infer_opening_hold_power(
        score_by_dimension,
        proof_reveal_present=proof_reveal_present,
        opening_sequence=opening_sequence,
    )
    follow_conversion_power, follow_conversion_source = infer_follow_conversion_power(
        score_by_dimension,
        comment_trigger_present=comment_trigger_present,
        follow_trigger_present=follow_trigger_present,
    )

    payload = {
        "content_id": project_root.name,
        "opening_promise": attention.get("lead_hook"),
        "first_thirty_seconds": {
            "opening_sequence": opening_sequence,
            "proof_reveal_present": proof_reveal_present,
            "comment_trigger_present": comment_trigger_present,
            "follow_trigger_present": follow_trigger_present,
        },
        "score_by_dimension": {
            "opening_hold_power": opening_hold_power,
            "hook_strength": score_by_dimension.get("hook_strength"),
            "proof_strength": score_by_dimension.get("proof_strength"),
            "follow_conversion_power": follow_conversion_power,
        },
        "score_sources": {
            "opening_hold_power": opening_hold_source,
            "follow_conversion_power": follow_conversion_source,
        },
        "decision": decide_status(
            opening_hold_power if isinstance(opening_hold_power, int) else None,
            proof_reveal_present,
            follow_conversion_power if isinstance(follow_conversion_power, int) else None,
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    output_path = (project_root / args.output).resolve()
    write_json(output_path, payload)
    print(json.dumps({"output_path": str(output_path), "decision": payload["decision"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
