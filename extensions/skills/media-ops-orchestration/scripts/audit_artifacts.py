#!/usr/bin/env python3
"""Audit media-ops content packages and build an artifact registry."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def list_package_dirs(media_ops_root: Path, include_hidden: bool) -> list[Path]:
    if not media_ops_root.exists():
        return []
    dirs = [entry for entry in media_ops_root.iterdir() if entry.is_dir()]
    if not include_hidden:
        dirs = [entry for entry in dirs if not entry.name.startswith("_")]
    return sorted(dirs)


def find_latest(directory: Path, pattern: str) -> Path | None:
    if not directory.exists():
        return None
    candidates = [path for path in directory.glob(pattern) if path.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def path_present(project_root: Path, path_or_glob: str) -> bool:
    if "*" in path_or_glob:
        return any((project_root).glob(path_or_glob))
    return (project_root / path_or_glob).exists()


def detect_content_packet(project_root: Path) -> Path | None:
    content_dir = project_root / "content"
    if not content_dir.exists():
        return None

    prioritized = [
        "*video.json",
        "*note.json",
        "content-packet.json",
    ]
    for pattern in prioritized:
        matches = sorted(path for path in content_dir.glob(pattern) if path.is_file())
        if matches:
            return matches[0]

    all_json = sorted(path for path in content_dir.glob("*.json") if path.is_file())
    return all_json[0] if all_json else None


def primary_packet(content_packet: dict[str, Any]) -> dict[str, Any]:
    nested = content_packet.get("content_packet")
    if isinstance(nested, dict):
        return nested
    return content_packet


def detect_content_type(content_packet: dict[str, Any], content_packet_path: Path | None) -> str:
    packet = primary_packet(content_packet)
    packet_format = str(packet.get("format") or content_packet.get("format") or "").lower()
    deliverable_type = str(packet.get("deliverable_type") or content_packet.get("deliverable_type") or "").lower()
    filename = content_packet_path.stem.lower() if content_packet_path else ""

    if packet_format == "note" or deliverable_type in {"note", "image-note", "graphic-note"}:
        return "note"
    if "note" in filename:
        return "note"
    return "video"


def detect_deliverable_type(content_packet: dict[str, Any]) -> str:
    packet = primary_packet(content_packet)
    return str(packet.get("deliverable_type") or content_packet.get("deliverable_type") or "").lower()


def detect_platforms(content_packet: dict[str, Any], latest_manifest: dict[str, Any]) -> list[str]:
    packet = primary_packet(content_packet)
    platforms: list[str] = []
    packet_platforms = packet.get("platforms") or content_packet.get("platforms")
    if isinstance(packet_platforms, list):
        platforms.extend(str(item) for item in packet_platforms if item)

    packet_platform = packet.get("platform") or content_packet.get("platform")
    if isinstance(packet_platform, str) and packet_platform:
        platforms.append(packet_platform)

    manifest_platform = latest_manifest.get("platform")
    if isinstance(manifest_platform, str) and manifest_platform:
        platforms.append(manifest_platform)

    deduped: list[str] = []
    seen: set[str] = set()
    for platform in platforms:
        if platform not in seen:
            seen.add(platform)
            deduped.append(platform)
    return deduped


def relative_to(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


@dataclass(frozen=True)
class Requirement:
    key: str
    pattern: str
    required: bool


def build_requirements(
    content_type: str,
    *,
    deliverable_type: str,
    platforms: list[str],
    publish_decision: str | None,
    publish_status: str | None,
) -> list[Requirement]:
    is_published = publish_status in {"success", "submitted"}
    publish_result_required = bool(publish_status) or publish_decision in {"ready_for_live_publish", "approve_publish"}
    publish_stage_started = bool(publish_decision or publish_status)
    requirements = [
        Requirement("research_brief", "research/research-brief.md", True),
        Requirement("topic_selection", "planning/topic-selection.json", True),
        Requirement("angle_brief", "angles/angle-brief.json", True),
        Requirement("content_packet", "content/*.json", True),
        Requirement("competitive_scorecard", "review/competitive-scorecard.json", True),
        Requirement("review_gate", "review/review-gate.json", True),
        Requirement("publish_manifest", "publish/publish-manifest*.json", True),
        Requirement("release_record", "publish/release-record.json", publish_stage_started),
        Requirement("publish_result", "publish/publish-result*.json", publish_result_required),
        Requirement("retro_plan", "retros/retro-plan.md", is_published),
        Requirement("performance_summary", "retros/performance-summary.md", False),
        Requirement("next_experiment_brief", "retros/next-experiment-brief.json", False),
        Requirement("workflow_quality_gate", "review/workflow-quality-gate.json", False),
        Requirement("upgrade_status_board", "review/upgrade-status-board.json", False),
        Requirement("prelive_quality_summary", "publish/prelive-quality-summary.json", False),
    ]
    if content_type == "video":
        requirements.append(Requirement("render_manifest", "content/postproduction/render-manifest.json", True))
        requirements.append(Requirement("assembly_qa_report", "review/assembly-qa-report.json", publish_stage_started))
        requirements.append(Requirement("render_verification", "review/render-verification*.md", False))
        requirements.append(Requirement("voice_performance_plan", "content/postproduction/voice-performance-plan.json", False))
        requirements.append(Requirement("subtitle_style_pack", "content/postproduction/subtitle-style-pack.json", False))
        requirements.append(Requirement("audio_cue_sheet", "content/postproduction/audio-cue-sheet.json", False))
        requirements.append(Requirement("subtitle_quality_report", "review/subtitle-quality-report.json", False))
        requirements.append(Requirement("scene_asset_plan", "assets/scene-asset-plan.json", False))
        requirements.append(Requirement("visual_evidence_map", "assets/visual-evidence-map.json", False))
        requirements.append(Requirement("generation_budget", "assets/generation-budget.json", False))
        requirements.append(Requirement("visual_diversity_report", "assets/visual-diversity-report.json", False))
        requirements.append(Requirement("minimax_shot_plan", "assets/minimax-shot-plan.json", False))
        requirements.append(Requirement("generation_ledger", "assets/generation-ledger.json", False))
        requirements.append(Requirement("scene_manifest", "content/postproduction/scene-manifest.json", False))
        requirements.append(Requirement("transition_plan", "content/postproduction/transition-plan.json", False))
        requirements.append(Requirement("emphasis_fx_plan", "content/postproduction/emphasis-fx-plan.json", False))
        requirements.append(Requirement("scene_assembly_report", "review/scene-assembly-report.json", False))
    if deliverable_type == "midlong-video":
        requirements.append(Requirement("cognitive_punch_gate", "planning/cognitive-punch-gate.json", publish_stage_started))
        requirements.append(Requirement("source_manifest", "sources/source-manifest.json", True))
        requirements.append(Requirement("source_shortlist", "sources/source-shortlist.json", True))
        requirements.append(Requirement("asset_ingest_manifest", "sources/asset-ingest-manifest.json", True))
        requirements.append(Requirement("chapter_coverage_report", "sources/chapter-coverage-report.json", publish_stage_started))
        requirements.append(Requirement("clip_query_sheet", "sources/clip-query-sheet.md", False))
    if "bilibili" in platforms:
        requirements.append(Requirement("bilibili_hook_patterns", "benchmarks/bilibili-hook-patterns.json", False))
        requirements.append(Requirement("attention_structure_template", "angles/attention-structure-template.json", False))
        requirements.append(Requirement("follow_conversion_hooks", "angles/follow-conversion-hooks.json", False))
        requirements.append(Requirement("opening_scorecard", "review/opening-scorecard.json", False))
    if content_type == "note":
        requirements.append(Requirement("auto_publish_manifest", "publish/publish-manifest-auto.json", False))
        requirements.append(Requirement("auto_publish_result", "publish/publish-result-auto.json", False))
    if "xiaohongshu" in platforms and is_published:
        requirements.append(Requirement("comment_insights", "retros/comment-insights.json", False))
        requirements.append(Requirement("profile_visit_signal", "retros/profile-visit-signal.json", False))
        requirements.append(Requirement("follow_conversion_readout", "retros/follow-conversion-readout.json", False))
        requirements.append(Requirement("live_monitoring_checklist", "retros/live-monitoring-checklist.md", False))
    return requirements


def find_latest_mtime(directory: Path) -> str | None:
    files = [path for path in directory.rglob("*") if path.is_file()]
    if not files:
        return None
    latest = max(files, key=lambda path: path.stat().st_mtime)
    return datetime.fromtimestamp(latest.stat().st_mtime, tz=timezone.utc).isoformat()


def infer_lifecycle(
    *,
    has_content_packet: bool,
    has_review_gate: bool,
    publish_decision: str | None,
    publish_status: str | None,
    has_retro_plan: bool,
    has_performance_summary: bool,
    has_next_experiment_brief: bool,
) -> str:
    if publish_status in {"success", "submitted"}:
        if has_performance_summary and has_next_experiment_brief:
            return "retros_complete"
        if has_retro_plan:
            return "published_pending_metrics"
        return "published_no_retro_plan"
    if publish_decision == "ready_for_live_publish":
        return "ready_for_publish"
    if has_review_gate:
        return "reviewed_not_ready"
    if has_content_packet:
        return "in_production"
    return "draft"


def build_package_record(project_root: Path, media_ops_root: Path) -> dict[str, Any]:
    content_packet_path = detect_content_packet(project_root)
    content_packet = load_json(content_packet_path)

    latest_manifest_path = find_latest(project_root / "publish", "publish-manifest*.json")
    latest_result_path = find_latest(project_root / "publish", "publish-result*.json")
    latest_manifest = load_json(latest_manifest_path)
    latest_result = load_json(latest_result_path)
    publish_decision = latest_manifest.get("decision")
    publish_status = latest_result.get("status")

    content_type = detect_content_type(content_packet, content_packet_path)
    deliverable_type = detect_deliverable_type(content_packet)
    platforms = detect_platforms(content_packet, latest_manifest)
    requirements = build_requirements(
        content_type,
        deliverable_type=deliverable_type,
        platforms=platforms,
        publish_decision=publish_decision,
        publish_status=publish_status,
    )

    checks = {
        req.key: {
            "pattern": req.pattern,
            "required": req.required,
            "present": path_present(project_root, req.pattern),
        }
        for req in requirements
    }

    missing_required = sorted(key for key, item in checks.items() if item["required"] and not item["present"])
    missing_recommended = sorted(key for key, item in checks.items() if (not item["required"]) and (not item["present"]))

    has_content_packet = checks["content_packet"]["present"]
    has_review_gate = checks["review_gate"]["present"]
    has_retro_plan = checks.get("retro_plan", {}).get("present", False)
    has_performance_summary = checks["performance_summary"]["present"]
    has_next_experiment_brief = checks["next_experiment_brief"]["present"]

    lifecycle_status = infer_lifecycle(
        has_content_packet=has_content_packet,
        has_review_gate=has_review_gate,
        publish_decision=publish_decision,
        publish_status=publish_status,
        has_retro_plan=has_retro_plan,
        has_performance_summary=has_performance_summary,
        has_next_experiment_brief=has_next_experiment_brief,
    )

    warnings: list[str] = []
    publish_manifest_count = len(list((project_root / "publish").glob("publish-manifest*.json")))
    publish_result_count = len(list((project_root / "publish").glob("publish-result*.json")))
    if publish_manifest_count > 3:
        warnings.append("publish_manifest_sprawl")
    if publish_result_count > 3:
        warnings.append("publish_result_sprawl")
    if publish_status in {"success", "submitted"} and not has_retro_plan:
        warnings.append("published_without_retro_plan")
    if publish_status in {"success", "submitted"} and not has_performance_summary:
        warnings.append("missing_performance_summary_after_publish")

    packet = primary_packet(content_packet)
    stage_presence = {
        "research": any((project_root / "research").glob("*")),
        "benchmarks": any((project_root / "benchmarks").glob("*")),
        "planning": any((project_root / "planning").glob("*")),
        "angles": any((project_root / "angles").glob("*")),
        "content": any((project_root / "content").glob("*")),
        "sources": any((project_root / "sources").glob("*")),
        "review": any((project_root / "review").glob("*")),
        "publish": any((project_root / "publish").glob("*")),
        "retros": any((project_root / "retros").glob("*")),
    }

    score_total = len([item for item in checks.values() if item["required"]])
    score_passed = len([item for item in checks.values() if item["required"] and item["present"]])
    health_score = round(score_passed / score_total, 4) if score_total else 0.0

    return {
        "content_id": project_root.name,
        "package_path": relative_to(project_root, media_ops_root),
        "content_type": content_type,
        "deliverable_type": deliverable_type,
        "platforms": platforms,
        "objective": content_packet.get("objective") or packet.get("objective"),
        "core_angle": content_packet.get("core_angle") or packet.get("core_angle"),
        "lifecycle_status": lifecycle_status,
        "health_score": health_score,
        "stage_presence": stage_presence,
        "checks": checks,
        "missing_required": missing_required,
        "missing_recommended": missing_recommended,
        "review": {
            "competitive_total_score": load_json(project_root / "review" / "competitive-scorecard.json").get("total_score"),
            "review_decision": load_json(project_root / "review" / "competitive-scorecard.json").get("review_decision"),
            "approval_status": load_json(project_root / "review" / "review-gate.json").get("approval_status"),
            "safe_to_publish": load_json(project_root / "review" / "review-gate.json").get("safe_to_publish"),
        },
        "publish": {
            "latest_manifest_path": relative_to(latest_manifest_path, project_root) if latest_manifest_path else None,
            "latest_result_path": relative_to(latest_result_path, project_root) if latest_result_path else None,
            "decision": publish_decision,
            "result_status": publish_status,
            "result_mode": latest_result.get("mode") or latest_result.get("publish_mode"),
            "account_name": latest_manifest.get("account_name") or latest_result.get("account_name"),
        },
        "artifact_counts": {
            "publish_manifest_count": publish_manifest_count,
            "publish_result_count": publish_result_count,
            "final_cut_count": len(list((project_root / "content" / "final-cut").glob("*.mp4"))),
            "review_preview_count": len([path for path in (project_root / "review" / "previews").glob("*") if path.is_file()]),
        },
        "warnings": warnings,
        "last_updated_at": find_latest_mtime(project_root),
    }


def build_summary(packages: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts = Counter(pkg["lifecycle_status"] for pkg in packages)
    platform_counts = Counter(platform for pkg in packages for platform in pkg.get("platforms", []))
    missing_required_counts = Counter(item for pkg in packages for item in pkg["missing_required"])
    missing_recommended_counts = Counter(item for pkg in packages for item in pkg["missing_recommended"])

    return {
        "status_counts": dict(status_counts),
        "platform_counts": dict(platform_counts),
        "packages_with_missing_required": sum(1 for pkg in packages if pkg["missing_required"]),
        "packages_with_warnings": sum(1 for pkg in packages if pkg["warnings"]),
        "top_missing_required": [
            {"artifact": artifact, "count": count}
            for artifact, count in missing_required_counts.most_common(10)
        ],
        "top_missing_recommended": [
            {"artifact": artifact, "count": count}
            for artifact, count in missing_recommended_counts.most_common(10)
        ],
    }


def build_markdown_report(registry: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Media Ops Artifact Registry")
    lines.append("")
    lines.append(f"- `generated_at`: `{registry['generated_at']}`")
    lines.append(f"- `media_ops_root`: `{registry['media_ops_root']}`")
    lines.append(f"- `package_count`: `{registry['package_count']}`")
    lines.append("")
    lines.append("## Status Summary")
    lines.append("")
    summary = registry["summary"]
    for status, count in sorted(summary["status_counts"].items()):
        lines.append(f"- `{status}`: `{count}`")
    lines.append("")
    lines.append("## Package Table")
    lines.append("")
    lines.append("| content_id | type | platforms | status | health | missing_required | warnings |")
    lines.append("|---|---|---|---|---:|---:|---:|")
    packages = sorted(
        registry["packages"],
        key=lambda pkg: pkg.get("last_updated_at") or "",
        reverse=True,
    )
    for pkg in packages:
        platforms = ",".join(pkg.get("platforms", []))
        lines.append(
            f"| {pkg['content_id']} | {pkg['content_type']} | {platforms} | {pkg['lifecycle_status']} | "
            f"{pkg['health_score']:.2f} | {len(pkg['missing_required'])} | {len(pkg['warnings'])} |"
        )
    lines.append("")
    lines.append("## Top Gaps")
    lines.append("")
    for item in summary["top_missing_required"]:
        lines.append(f"- required: `{item['artifact']}` x `{item['count']}`")
    for item in summary["top_missing_recommended"]:
        lines.append(f"- recommended: `{item['artifact']}` x `{item['count']}`")
    lines.append("")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--media-ops-root",
        default=str(Path(__file__).resolve().parents[4] / "data" / "media-ops"),
        help="Root directory containing media content packages.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="JSON output path. Defaults to <media-ops-root>/_registry/artifact-registry.json",
    )
    parser.add_argument(
        "--summary-output",
        default=None,
        help="Markdown summary output path. Defaults to <media-ops-root>/_registry/artifact-registry.md",
    )
    parser.add_argument("--include-hidden", action="store_true", help="Include directories that start with '_' .")
    parser.add_argument(
        "--fail-on-missing-required",
        action="store_true",
        help="Return exit code 2 when any package has missing required artifacts.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    media_ops_root = Path(args.media_ops_root).resolve()
    package_dirs = list_package_dirs(media_ops_root, include_hidden=args.include_hidden)

    packages = [build_package_record(project_dir, media_ops_root) for project_dir in package_dirs]
    registry = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "media_ops_root": str(media_ops_root),
        "package_count": len(packages),
        "summary": build_summary(packages),
        "packages": packages,
    }

    output_path = Path(args.output).resolve() if args.output else media_ops_root / "_registry" / "artifact-registry.json"
    summary_output_path = (
        Path(args.summary_output).resolve() if args.summary_output else media_ops_root / "_registry" / "artifact-registry.md"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary_output_path.write_text(build_markdown_report(registry), encoding="utf-8")

    print(
        json.dumps(
            {
                "registry_output": str(output_path),
                "summary_output": str(summary_output_path),
                "package_count": registry["package_count"],
                "packages_with_missing_required": registry["summary"]["packages_with_missing_required"],
            },
            ensure_ascii=False,
        )
    )

    if args.fail_on_missing_required and registry["summary"]["packages_with_missing_required"] > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
