#!/usr/bin/env python3
"""Build workflow quality gate and upgrade status board for media packages."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


QUALITY_DIMENSIONS = (
    "growth_structure_status",
    "voice_performance_status",
    "subtitle_quality_status",
    "visual_diversity_status",
    "scene_assembly_status",
    "generation_budget_status",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", help="Media package root directory.")
    parser.add_argument("--content-id", help="Content package id under media-ops root.")
    parser.add_argument("--media-ops-root", help="Root directory containing media packages.")
    parser.add_argument(
        "--gate-output",
        default="review/workflow-quality-gate.json",
        help="Workflow quality gate output path, relative to project root.",
    )
    parser.add_argument(
        "--board-output",
        default="review/upgrade-status-board.json",
        help="Upgrade status board output path, relative to project root.",
    )
    args = parser.parse_args()
    if not args.project_root and not args.content_id:
        parser.error("one of --project-root or --content-id is required")
    return args


def default_media_ops_root() -> Path:
    return Path(__file__).resolve().parents[4] / "data" / "media-ops"


def resolve_project_root(args: argparse.Namespace) -> Path:
    if args.project_root:
        return Path(args.project_root).resolve()
    media_ops_root = Path(args.media_ops_root).resolve() if args.media_ops_root else default_media_ops_root().resolve()
    return (media_ops_root / args.content_id).resolve()


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def detect_content_packet(project_root: Path) -> Path | None:
    content_dir = project_root / "content"
    if not content_dir.exists():
        return None
    prioritized = ["*video.json", "*note.json", "content-packet.json", "*.json"]
    for pattern in prioritized:
        matches = sorted(path for path in content_dir.glob(pattern) if path.is_file())
        if matches:
            return matches[0]
    return None


def primary_packet(content_packet: dict[str, Any]) -> dict[str, Any]:
    nested = content_packet.get("content_packet")
    return nested if isinstance(nested, dict) else content_packet


def relative_to(path: Path | None, root: Path) -> str | None:
    if path is None:
        return None
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_dimension(
    *,
    key: str,
    applicable: bool,
    status: str,
    artifact_paths: list[Path],
    project_root: Path,
    reasons: list[str] | None = None,
) -> dict[str, Any]:
    if not applicable:
        return {
            "status": "not_applicable",
            "artifact_paths": [],
            "missing_artifacts": [],
            "reasons": [],
        }

    missing = [relative_to(path, project_root) for path in artifact_paths if not path.exists()]
    return {
        "status": status,
        "artifact_paths": [relative_to(path, project_root) for path in artifact_paths],
        "missing_artifacts": [item for item in missing if item],
        "reasons": reasons or [],
    }


def build_dimension_statuses(project_root: Path, packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    platforms = packet.get("platforms") if isinstance(packet.get("platforms"), list) else []
    deliverable_type = str(packet.get("deliverable_type") or "").lower()
    is_bilibili_midform = "bilibili" in platforms and deliverable_type == "midlong-video"

    growth_paths = [
        project_root / "benchmarks" / "bilibili-hook-patterns.json",
        project_root / "angles" / "attention-structure-template.json",
        project_root / "angles" / "follow-conversion-hooks.json",
        project_root / "review" / "opening-scorecard.json",
    ]
    opening_scorecard = load_json(growth_paths[-1])
    growth_status = "pass"
    if is_bilibili_midform:
        if any(not path.exists() for path in growth_paths):
            growth_status = "revise"
        elif str(opening_scorecard.get("decision") or opening_scorecard.get("status") or "") not in {"pass", "approved"}:
            growth_status = "revise"

    voice_paths = [
        project_root / "content" / "postproduction" / "voice-performance-plan.json",
        project_root / "content" / "postproduction" / "voiceover-profile.json",
        project_root / "content" / "postproduction" / "voiceover-segments.json",
    ]
    voice_segments = load_json(voice_paths[-1]) if voice_paths[-1].exists() else {}
    voice_status = "pass"
    if is_bilibili_midform:
        if any(not path.exists() for path in voice_paths):
            voice_status = "revise"
        else:
            raw_segments = voice_segments if isinstance(voice_segments, list) else []
            if raw_segments and any(not str(item.get("emotion") or "").strip() for item in raw_segments if isinstance(item, dict)):
                voice_status = "revise"

    subtitle_quality_path = project_root / "review" / "subtitle-quality-report.json"
    subtitle_quality = load_json(subtitle_quality_path)
    subtitle_status = str(subtitle_quality.get("status") or ("revise" if is_bilibili_midform else "not_applicable"))

    visual_diversity_path = project_root / "assets" / "visual-diversity-report.json"
    visual_diversity = load_json(visual_diversity_path)
    visual_status = str(visual_diversity.get("status") or ("revise" if is_bilibili_midform else "not_applicable"))

    scene_paths = [
        project_root / "content" / "postproduction" / "scene-manifest.json",
        project_root / "content" / "postproduction" / "transition-plan.json",
        project_root / "content" / "postproduction" / "emphasis-fx-plan.json",
        project_root / "review" / "scene-assembly-report.json",
    ]
    scene_report = load_json(scene_paths[-1])
    scene_status = "pass"
    if is_bilibili_midform:
        if any(not path.exists() for path in scene_paths):
            scene_status = "revise"
        else:
            scene_status = str(scene_report.get("status") or "revise")

    generation_paths = [
        project_root / "assets" / "generation-budget.json",
        project_root / "assets" / "minimax-shot-plan.json",
        project_root / "assets" / "generation-ledger.json",
    ]
    generation_budget = load_json(generation_paths[0])
    approved_slots = generation_budget.get("approved_generation_slots") or []
    generation_status = "pass"
    if is_bilibili_midform:
        if not generation_paths[0].exists():
            generation_status = "revise"
        elif approved_slots and (not generation_paths[1].exists() or not generation_paths[2].exists()):
            generation_status = "revise"

    return {
        "growth_structure_status": make_dimension(
            key="growth_structure_status",
            applicable=is_bilibili_midform,
            status=growth_status,
            artifact_paths=growth_paths,
            project_root=project_root,
        ),
        "voice_performance_status": make_dimension(
            key="voice_performance_status",
            applicable=is_bilibili_midform,
            status=voice_status,
            artifact_paths=voice_paths,
            project_root=project_root,
        ),
        "subtitle_quality_status": make_dimension(
            key="subtitle_quality_status",
            applicable=is_bilibili_midform,
            status=subtitle_status if is_bilibili_midform else "not_applicable",
            artifact_paths=[subtitle_quality_path],
            project_root=project_root,
        ),
        "visual_diversity_status": make_dimension(
            key="visual_diversity_status",
            applicable=is_bilibili_midform,
            status=visual_status if is_bilibili_midform else "not_applicable",
            artifact_paths=[visual_diversity_path],
            project_root=project_root,
        ),
        "scene_assembly_status": make_dimension(
            key="scene_assembly_status",
            applicable=is_bilibili_midform,
            status=scene_status,
            artifact_paths=scene_paths,
            project_root=project_root,
        ),
        "generation_budget_status": make_dimension(
            key="generation_budget_status",
            applicable=is_bilibili_midform,
            status=generation_status,
            artifact_paths=generation_paths,
            project_root=project_root,
        ),
    }


def overall_status(dimensions: dict[str, dict[str, Any]]) -> str:
    statuses = [str(payload["status"]) for payload in dimensions.values() if payload["status"] != "not_applicable"]
    if not statuses:
        return "pass"
    if any(status == "block" for status in statuses):
        return "block"
    if any(status != "pass" for status in statuses):
        return "revise"
    return "pass"


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)
    packet_path = detect_content_packet(project_root)
    packet = primary_packet(load_json(packet_path))
    dimensions = build_dimension_statuses(project_root, packet)
    gate_status = overall_status(dimensions)

    blocking_dimensions = [key for key, payload in dimensions.items() if payload["status"] == "block"]
    revise_dimensions = [key for key, payload in dimensions.items() if payload["status"] == "revise"]

    gate_payload = {
        "content_id": packet.get("content_id") or project_root.name,
        "deliverable_type": packet.get("deliverable_type"),
        "platforms": packet.get("platforms", []),
        "overall_status": gate_status,
        "blocking_dimensions": blocking_dimensions,
        "revise_dimensions": revise_dimensions,
        "dimensions": dimensions,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    board_payload = {
        "content_id": gate_payload["content_id"],
        "overall_status": gate_status,
        "rows": [
            {
                "dimension": key,
                "status": payload["status"],
                "missing_artifact_count": len(payload["missing_artifacts"]),
                "artifact_paths": payload["artifact_paths"],
            }
            for key, payload in dimensions.items()
        ],
        "generated_at": gate_payload["generated_at"],
    }

    gate_output = (project_root / args.gate_output).resolve()
    board_output = (project_root / args.board_output).resolve()
    write_json(gate_output, gate_payload)
    write_json(board_output, board_payload)
    print(
        json.dumps(
            {
                "gate_output": str(gate_output),
                "board_output": str(board_output),
                "overall_status": gate_status,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
