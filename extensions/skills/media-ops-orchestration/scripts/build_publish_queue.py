#!/usr/bin/env python3
"""Build a supervisor-facing publish queue from media-ops packages."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from audit_artifacts import build_package_record, list_package_dirs, load_json, relative_to

QUEUE_PRIORITY = {
    "ready_for_live": 0,
    "blocked": 1,
    "in_prep": 2,
    "published": 3,
}


def dedupe_strings(items: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def first_non_empty_string(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return None


def resolve_platform(package: dict[str, Any], prelive_manifest: dict[str, Any], live_plan: dict[str, Any]) -> str | None:
    package_platforms = package.get("platforms") or []
    first_platform = package_platforms[0] if package_platforms else None
    return first_non_empty_string(
        live_plan.get("platform"),
        prelive_manifest.get("platform"),
        first_platform,
    )


def resolve_account_name(package: dict[str, Any], prelive_manifest: dict[str, Any], live_plan: dict[str, Any]) -> str | None:
    return first_non_empty_string(
        live_plan.get("account_name"),
        prelive_manifest.get("account_name"),
        package.get("publish", {}).get("account_name"),
    )


def collect_blocking_reasons(
    package: dict[str, Any],
    prelive_manifest: dict[str, Any],
    live_plan: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    for source in (live_plan, prelive_manifest):
        raw_reasons = source.get("blocking_reasons")
        if isinstance(raw_reasons, list):
            reasons.extend(str(item) for item in raw_reasons if item)

    review = package.get("review", {})
    approval_status = review.get("approval_status")
    safe_to_publish = review.get("safe_to_publish")
    if approval_status in {"revise", "block"}:
        reasons.append("approval_not_granted")
    if safe_to_publish is False:
        reasons.append("review_gate_not_safe")
    return dedupe_strings(reasons)


def infer_queue_status(
    package: dict[str, Any],
    prelive_manifest: dict[str, Any],
    live_plan: dict[str, Any],
    blocking_reasons: list[str],
) -> str:
    publish = package.get("publish", {})
    publish_status = publish.get("result_status")
    publish_mode = publish.get("result_mode")
    if publish_status in {"success", "submitted"} and publish_mode not in {None, "dry_run"}:
        return "published"

    if package.get("missing_required"):
        return "in_prep"

    if live_plan.get("live_ready") is True:
        return "ready_for_live"
    if prelive_manifest.get("decision") == "ready_for_live_publish":
        return "ready_for_live"
    if package.get("lifecycle_status") == "ready_for_publish":
        return "ready_for_live"

    if blocking_reasons or live_plan or prelive_manifest or package.get("lifecycle_status") == "reviewed_not_ready":
        return "blocked"
    return "in_prep"


def recommend_next_action(queue_status: str, blocking_reasons: list[str], missing_required: list[str]) -> str:
    if queue_status == "ready_for_live":
        return "await_manual_live_trigger"
    if queue_status == "published":
        return "collect_post_publish_metrics"
    if missing_required:
        return "fill_required_artifacts"
    if "review_gate_not_safe" in blocking_reasons:
        return "revise_content_and_review_gate"
    if "workflow_quality_gate_not_passed" in blocking_reasons:
        return "fix_workflow_quality_gate"
    if "approval_not_granted" in blocking_reasons:
        return "obtain_supervisor_approval"
    if "auto_base_quality_not_passed" in blocking_reasons or "auto_base_quality_report_missing" in blocking_reasons:
        return "improve_auto_timeline_quality"
    if "metadata_incomplete" in blocking_reasons:
        return "complete_publish_metadata"
    if "account_missing" in blocking_reasons:
        return "bind_publish_account"
    return "continue_package_production"


def build_entry(project_root: Path, media_ops_root: Path) -> dict[str, Any]:
    package = build_package_record(project_root, media_ops_root)
    publish_dir = project_root / "publish"
    live_plan_path = publish_dir / "live-execution-plan.json"
    prelive_manifest_path = publish_dir / "publish-manifest-prelive.json"
    release_record_path = publish_dir / "release-record.json"
    live_plan = load_json(live_plan_path)
    prelive_manifest = load_json(prelive_manifest_path)

    platform = resolve_platform(package, prelive_manifest, live_plan)
    account_name = resolve_account_name(package, prelive_manifest, live_plan)
    blocking_reasons = collect_blocking_reasons(package, prelive_manifest, live_plan)
    queue_status = infer_queue_status(package, prelive_manifest, live_plan, blocking_reasons)
    missing_required = package.get("missing_required") or []

    return {
        "content_id": package["content_id"],
        "package_path": package["package_path"],
        "platform": platform,
        "content_type": package["content_type"],
        "deliverable_type": package["deliverable_type"],
        "queue_status": queue_status,
        "lifecycle_status": package["lifecycle_status"],
        "account_name": account_name,
        "assembly_strategy": first_non_empty_string(
            prelive_manifest.get("render_context", {}).get("assembly_strategy"),
            live_plan.get("render_context", {}).get("assembly_strategy"),
        ),
        "auto_base_quality_status": first_non_empty_string(
            prelive_manifest.get("render_context", {}).get("auto_base_quality_status"),
            live_plan.get("render_context", {}).get("auto_base_quality_status"),
        ),
        "workflow_quality_status": first_non_empty_string(
            prelive_manifest.get("workflow_quality_gate", {}).get("overall_status"),
            live_plan.get("workflow_quality_gate", {}).get("overall_status"),
        ),
        "approval_status": package.get("review", {}).get("approval_status"),
        "safe_to_publish": package.get("review", {}).get("safe_to_publish"),
        "missing_required": missing_required,
        "missing_recommended": package.get("missing_recommended") or [],
        "blocking_reasons": blocking_reasons,
        "next_action": recommend_next_action(queue_status, blocking_reasons, missing_required),
        "live_ready": bool(live_plan.get("live_ready")),
        "manifest_path": relative_to(prelive_manifest_path, project_root) if prelive_manifest_path.exists() else None,
        "live_execution_plan_path": relative_to(live_plan_path, project_root) if live_plan_path.exists() else None,
        "release_record_path": relative_to(release_record_path, project_root) if release_record_path.exists() else None,
        "workflow_live_command": live_plan.get("workflow_live_command"),
        "account_check_command": live_plan.get("account_check_command"),
        "publish_command_preview": live_plan.get("publish_command_preview"),
        "last_updated_at": package.get("last_updated_at"),
    }


def sort_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        entries,
        key=lambda entry: (
            QUEUE_PRIORITY.get(entry["queue_status"], 99),
            entry.get("account_name") or "",
            entry.get("last_updated_at") or "",
        ),
        reverse=False,
    )


def build_summary(entries: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts = Counter(entry["queue_status"] for entry in entries)
    platform_counts = Counter(entry["platform"] for entry in entries if entry.get("platform"))
    account_counts = Counter(entry["account_name"] for entry in entries if entry.get("account_name"))
    return {
        "entry_count": len(entries),
        "ready_for_live": status_counts.get("ready_for_live", 0),
        "blocked": status_counts.get("blocked", 0),
        "in_prep": status_counts.get("in_prep", 0),
        "published": status_counts.get("published", 0),
        "platform_counts": dict(platform_counts),
        "account_counts": dict(account_counts),
    }


def build_markdown_report(queue: dict[str, Any]) -> str:
    lines: list[str] = []
    summary = queue["summary"]
    lines.append("# Media Ops Publish Queue")
    lines.append("")
    lines.append(f"- `generated_at`: `{queue['generated_at']}`")
    lines.append(f"- `media_ops_root`: `{queue['media_ops_root']}`")
    lines.append(f"- `entry_count`: `{summary['entry_count']}`")
    lines.append("")
    lines.append("## Status Summary")
    lines.append("")
    lines.append(f"- `ready_for_live`: `{summary['ready_for_live']}`")
    lines.append(f"- `blocked`: `{summary['blocked']}`")
    lines.append(f"- `in_prep`: `{summary['in_prep']}`")
    lines.append(f"- `published`: `{summary['published']}`")
    lines.append("")
    lines.append("## Queue")
    lines.append("")
    lines.append("| content_id | platform | account | status | auto_base_quality | blocking_reasons | next_action |")
    lines.append("|---|---|---|---|---|---|---|")
    for entry in queue["entries"]:
        blocking = ",".join(entry["blocking_reasons"]) or "-"
        auto_base_quality = entry.get("auto_base_quality_status") or "-"
        lines.append(
            f"| {entry['content_id']} | {entry.get('platform') or '-'} | {entry.get('account_name') or '-'} | "
            f"{entry['queue_status']} | {auto_base_quality} | {blocking} | {entry['next_action']} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--media-ops-root",
        default=str(Path(__file__).resolve().parents[4] / "data" / "media-ops"),
        help="Root directory containing media content packages.",
    )
    parser.add_argument("--platform", default=None, help="Optional platform filter.")
    parser.add_argument("--account-name", default=None, help="Optional publishing account filter.")
    parser.add_argument("--include-hidden", action="store_true", help="Include directories that start with '_' .")
    parser.add_argument(
        "--output",
        default=None,
        help="JSON output path. Defaults to <media-ops-root>/_registry/publish-queue.json",
    )
    parser.add_argument(
        "--summary-output",
        default=None,
        help="Markdown output path. Defaults to <media-ops-root>/_registry/publish-queue.md",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    media_ops_root = Path(args.media_ops_root).resolve()
    package_dirs = list_package_dirs(media_ops_root, include_hidden=args.include_hidden)

    entries = [build_entry(project_root, media_ops_root) for project_root in package_dirs]
    if args.platform:
        entries = [entry for entry in entries if entry.get("platform") == args.platform]
    if args.account_name:
        entries = [entry for entry in entries if entry.get("account_name") == args.account_name]

    queue = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "media_ops_root": str(media_ops_root),
        "summary": build_summary(entries),
        "entries": sort_entries(entries),
    }

    output_path = Path(args.output).resolve() if args.output else media_ops_root / "_registry" / "publish-queue.json"
    summary_output_path = Path(args.summary_output).resolve() if args.summary_output else media_ops_root / "_registry" / "publish-queue.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary_output_path.write_text(build_markdown_report(queue), encoding="utf-8")

    print(
        json.dumps(
            {
                "publish_queue": str(output_path),
                "summary_output": str(summary_output_path),
                "entry_count": queue["summary"]["entry_count"],
                "ready_for_live": queue["summary"]["ready_for_live"],
                "blocked": queue["summary"]["blocked"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
