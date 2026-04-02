#!/usr/bin/env python3
"""Build a supervisor-facing live execution plan from a prelive publish manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from build_publish_manifest import build_manifest, resolve_project_root
from run_publish_workflow import build_command


def relative_to_root(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def resolve_output_path(project_root: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = project_root / candidate
    return candidate.resolve()


def build_manifest_args(args: argparse.Namespace, project_root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        project_root=str(project_root),
        content_id=args.content_id,
        media_ops_root=args.media_ops_root,
        account_name=args.account_name,
        publish_mode=args.publish_mode,
        schedule=args.schedule,
        platform=args.platform,
        approval_status=args.approval_status,
        output=args.manifest_output,
    )


def build_workflow_live_command(project_root: Path, account_name: str, manifest_path: str) -> list[str]:
    return [
        "python3",
        "extensions/skills/multi-platform-publishing/scripts/run_publish_workflow.py",
        "--project-root",
        str(project_root),
        "--account-name",
        account_name,
        "--manifest",
        manifest_path,
        "--live",
    ]


def build_assets_preview(manifest: dict[str, Any]) -> dict[str, Any]:
    asset_paths = manifest.get("asset_paths") or []
    content_type = manifest.get("content_type", "video")
    if content_type == "note":
        return {"images": asset_paths}
    return {
        "video": asset_paths[0] if asset_paths else None,
        "cover": asset_paths[1] if len(asset_paths) > 1 else None,
    }


def render_summary(plan: dict[str, Any]) -> str:
    lines = [
        "# Live Execution Summary",
        "",
        f"- `content_id`: `{plan['content_id']}`",
        f"- `platform`: `{plan['platform']}`",
        f"- `content_type`: `{plan['content_type']}`",
        f"- `account_name`: `{plan['account_name']}`",
        f"- `decision`: `{plan['decision']}`",
        f"- `live_ready`: `{str(plan['live_ready']).lower()}`",
        "",
        "## Manifest",
        "",
        f"- `{plan['manifest_path']}`",
        "",
        "## Account Check Command",
        "",
        "```bash",
        " ".join(plan["account_check_command"]),
        "```",
        "",
        "## Platform Command Preview",
        "",
        "```bash",
        " ".join(plan["publish_command_preview"]),
        "```",
        "",
        "## Workflow Live Command",
        "",
        "```bash",
        " ".join(plan["workflow_live_command"]),
        "```",
    ]

    cover_state = plan.get("cover_state") or {}
    if cover_state:
        lines.extend(
            [
                "",
                "## Cover State",
                "",
                f"- `asset_ready`: `{str(cover_state.get('asset_ready', False)).lower()}`",
                f"- `thumbnail_upload_supported`: `{str(cover_state.get('thumbnail_upload_supported', False)).lower()}`",
                f"- `delivery_status`: `{cover_state.get('delivery_status')}`",
            ]
        )

    blocking_reasons = plan.get("blocking_reasons") or []
    if blocking_reasons:
        lines.extend(
            [
                "",
                "## Blocking Reasons",
                "",
                *[f"- `{reason}`" for reason in blocking_reasons],
            ]
        )

    notes = plan.get("notes") or []
    if notes:
        lines.extend(
            [
                "",
                "## Notes",
                "",
                *[f"- {note}" for note in notes],
            ]
        )

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", help="Media package root directory.")
    parser.add_argument("--content-id", help="Content package id under media-ops root.")
    parser.add_argument("--media-ops-root", help="Root directory containing media packages.")
    parser.add_argument("--account-name", default=None, help="Publishing account identifier.")
    parser.add_argument("--publish-mode", default="immediate_live_publish", help="Publish mode used for prelive manifest generation.")
    parser.add_argument("--schedule", default=None, help="Schedule override.")
    parser.add_argument("--platform", default=None, help="Platform override.")
    parser.add_argument("--approval-status", default=None, help="Approval status override.")
    parser.add_argument(
        "--manifest-output",
        default="publish/publish-manifest-prelive.json",
        help="Where to write the prelive manifest, relative to project root.",
    )
    parser.add_argument(
        "--output",
        default="publish/live-execution-plan.json",
        help="Where to write the live execution plan JSON, relative to project root.",
    )
    parser.add_argument(
        "--summary-output",
        default="publish/live-execution-summary.md",
        help="Where to write the live execution summary markdown, relative to project root.",
    )
    args = parser.parse_args()
    if not args.project_root and not args.content_id:
        parser.error("one of --project-root or --content-id is required")
    return args


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)
    if not project_root.exists():
        raise FileNotFoundError(f"Project root does not exist: {project_root}")

    manifest, manifest_path = build_manifest(build_manifest_args(args, project_root))
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    publish_command_preview, account_check_command = build_command(project_root, manifest)
    manifest_rel = relative_to_root(manifest_path, project_root)
    plan = {
        "content_id": manifest["content_id"],
        "platform": manifest["platform"],
        "content_type": manifest.get("content_type", "video"),
        "account_name": manifest["account_name"],
        "manifest_path": manifest_rel,
        "release_record_path": manifest.get("release_record_path"),
        "decision": manifest["decision"],
        "live_ready": manifest["decision"] == "ready_for_live_publish",
        "blocking_reasons": manifest.get("blocking_reasons", []),
        "assets_preview": build_assets_preview(manifest),
        "cover_state": manifest.get("cover_state", {}),
        "prelive_quality_summary_path": manifest.get("prelive_quality_summary_path"),
        "workflow_quality_gate": manifest.get("workflow_quality_gate", {}),
        "account_check_command": account_check_command,
        "publish_command_preview": publish_command_preview,
        "workflow_live_command": build_workflow_live_command(project_root, manifest["account_name"], manifest_rel),
        "notes": manifest.get("notes", []),
        "render_context": manifest.get("render_context", {}),
    }

    output_path = resolve_output_path(project_root, args.output)
    summary_output_path = resolve_output_path(project_root, args.summary_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary_output_path.write_text(render_summary(plan), encoding="utf-8")

    print(
        json.dumps(
            {
                "live_execution_plan": str(output_path),
                "summary_output": str(summary_output_path),
                "manifest_path": str(manifest_path),
                "live_ready": plan["live_ready"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
