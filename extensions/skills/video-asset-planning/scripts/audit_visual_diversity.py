#!/usr/bin/env python3
"""Audit repeated visual asset usage and produce a diversity report."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
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
        default="assets/visual-diversity-report.json",
        help="Visual diversity report output path relative to the project root.",
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
    scene_plan = load_json(project_root / "assets" / "scene-asset-plan.json")
    chapters = [item for item in scene_plan.get("chapters", []) if isinstance(item, dict)]

    usage: dict[str, dict[str, Any]] = defaultdict(lambda: {"chapter_ids": [], "usage_count": 0, "max_repeat_uses": []})
    proof_asset_count = 0
    b_roll_asset_count = 0
    for chapter in chapters:
        chapter_id = str(chapter.get("chapter_id") or "")
        max_repeat_uses = int(chapter.get("max_repeat_uses", 2))
        chapter_seen_paths: set[str] = set()
        proof_asset = chapter.get("proof_asset") if isinstance(chapter.get("proof_asset"), dict) else {}
        proof_path = proof_asset.get("path")
        if isinstance(proof_path, str) and proof_path:
            proof_asset_count += 1
            if proof_path not in chapter_seen_paths:
                usage[proof_path]["chapter_ids"].append(chapter_id)
                usage[proof_path]["usage_count"] += 1
                usage[proof_path]["max_repeat_uses"].append(max_repeat_uses)
                chapter_seen_paths.add(proof_path)

        for item in chapter.get("supporting_b_roll", []):
            if not isinstance(item, dict):
                continue
            asset_path = str(item.get("asset_path") or "").strip()
            if not asset_path:
                continue
            b_roll_asset_count += 1
            if asset_path not in chapter_seen_paths:
                usage[asset_path]["chapter_ids"].append(chapter_id)
                usage[asset_path]["usage_count"] += 1
                usage[asset_path]["max_repeat_uses"].append(max_repeat_uses)
                chapter_seen_paths.add(asset_path)

        for raw_path in chapter.get("fallback_graphics", []):
            asset_path = str(raw_path or "").strip()
            if not asset_path:
                continue
            if asset_path not in chapter_seen_paths:
                usage[asset_path]["chapter_ids"].append(chapter_id)
                usage[asset_path]["usage_count"] += 1
                usage[asset_path]["max_repeat_uses"].append(max_repeat_uses)
                chapter_seen_paths.add(asset_path)

    repeated_assets: list[dict[str, Any]] = []
    for asset_path, info in usage.items():
        usage_count = int(info["usage_count"])
        allowed = min(info["max_repeat_uses"]) if info["max_repeat_uses"] else 2
        if usage_count > allowed:
            repeated_assets.append(
                {
                    "asset_path": asset_path,
                    "usage_count": usage_count,
                    "max_repeat_uses": allowed,
                    "chapter_ids": info["chapter_ids"],
                }
            )

    status = "pass"
    if repeated_assets:
        status = "revise"
    if not chapters:
        status = "block"

    payload = {
        "content_id": scene_plan.get("content_id") or project_root.name,
        "status": status,
        "chapter_count": len(chapters),
        "proof_asset_count": proof_asset_count,
        "supporting_b_roll_asset_count": b_roll_asset_count,
        "unique_asset_count": len(usage),
        "repeated_asset_count": len(repeated_assets),
        "repeated_assets": repeated_assets,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    output_path = (project_root / args.output).resolve()
    write_json(output_path, payload)
    print(json.dumps({"output_path": str(output_path), "status": status}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
