#!/usr/bin/env python3
"""Execute publishing from an auto-generated publish manifest."""

from __future__ import annotations

import argparse
import json
import subprocess
import re
from pathlib import Path
from typing import Any

from build_publish_manifest import build_manifest, resolve_project_root


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_manifest_path(project_root: Path, raw_path: str | None) -> Path:
    if raw_path:
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = project_root / candidate
        return candidate.resolve()
    return (project_root / "publish" / "publish-manifest-auto.json").resolve()


def resolve_result_path(project_root: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = project_root / candidate
    return candidate.resolve()


def build_manifest_args(args: argparse.Namespace, project_root: Path) -> argparse.Namespace:
    return argparse.Namespace(
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


def build_bilibili_command(project_root: Path, manifest: dict[str, Any]) -> list[str]:
    metadata = manifest["metadata"]
    video_path = project_root / manifest["asset_paths"][0]
    command = [
        "sau",
        "bilibili",
        "upload-video",
        "--account",
        manifest["account_name"],
        "--file",
        str(video_path),
        "--title",
        metadata["title"],
        "--desc",
        metadata["description"],
        "--tid",
        str(metadata["partition"]),
    ]
    tags = metadata.get("tags") or []
    if tags:
        command.extend(["--tags", ",".join(tags)])
    schedule = manifest.get("schedule")
    if schedule:
        command.extend(["--schedule", schedule])
    return command


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, capture_output=True, text=True)


def sanitize_cli_output(raw_text: str | None) -> str | None:
    if not raw_text:
        return None

    sanitized = raw_text
    sanitized = re.sub(
        r"(?i)\b(cookie|token|access_token|refresh_token|authorization|sessdata|bili_jct)\b\s*[:=]\s*([^\s,;]+)",
        r"\1=<redacted>",
        sanitized,
    )
    sanitized = re.sub(r"\bsk-[A-Za-z0-9._-]+\b", "sk-<redacted>", sanitized)
    return sanitized.strip() or None


def result_payload(
    manifest: dict[str, Any],
    mode: str,
    status: str,
    command_preview: list[str],
    account_status: str | None = None,
    upload_stdout: str | None = None,
    upload_stderr: str | None = None,
) -> dict[str, Any]:
    return {
        "platform": manifest["platform"],
        "content_id": manifest["content_id"],
        "version": manifest["version"],
        "mode": mode,
        "status": status,
        "decision": manifest["decision"],
        "account": {
            "account_name": manifest.get("account_name"),
            "status": account_status or manifest.get("account_status", "pending_check"),
        },
        "assets": {
            "video": manifest["asset_paths"][0] if manifest.get("asset_paths") else None,
            "cover": manifest["asset_paths"][1] if len(manifest.get("asset_paths", [])) > 1 else None,
            "voiceover": manifest.get("render_context", {}).get("voiceover"),
            "subtitles": manifest.get("render_context", {}).get("subtitles"),
        },
        "metadata": manifest.get("metadata", {}),
        "command_preview": command_preview,
        "blocking_reasons": manifest.get("blocking_reasons", []),
        "notes": manifest.get("notes", []),
        "upload_stdout": upload_stdout,
        "upload_stderr": upload_stderr,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", help="Media package root directory.")
    parser.add_argument("--content-id", help="Content package id under media-ops root.")
    parser.add_argument("--media-ops-root", help="Root directory containing media packages.")
    parser.add_argument("--account-name", help="Publishing account identifier.")
    parser.add_argument("--manifest", help="Existing publish manifest path.")
    parser.add_argument("--publish-mode", default=None, help="Publish mode override for auto-generated manifests.")
    parser.add_argument("--schedule", default=None, help="Schedule override for auto-generated manifests.")
    parser.add_argument("--platform", default=None, help="Platform override for auto-generated manifests.")
    parser.add_argument("--approval-status", default=None, help="Approval status override for auto-generated manifests.")
    parser.add_argument(
        "--manifest-output",
        default="publish/publish-manifest-auto.json",
        help="Where to write an auto-generated publish manifest when one is needed.",
    )
    parser.add_argument(
        "--result-output",
        default="publish/publish-result-auto.json",
        help="Where to write the publish result summary.",
    )
    parser.add_argument("--live", action="store_true", help="Execute live publishing instead of dry-run.")
    args = parser.parse_args()
    if not args.project_root and not args.content_id:
        parser.error("one of --project-root or --content-id is required")
    return args


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)
    if not project_root.exists():
        raise FileNotFoundError(f"Project root does not exist: {project_root}")

    manifest_path = resolve_manifest_path(project_root, args.manifest)
    if manifest_path.exists():
        manifest = load_json(manifest_path)
    else:
        manifest, manifest_path = build_manifest(build_manifest_args(args, project_root))
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result_path = resolve_result_path(project_root, args.result_output)
    result_path.parent.mkdir(parents=True, exist_ok=True)

    if manifest["platform"] != "bilibili":
        raise NotImplementedError(f"Unsupported platform for publish runner: {manifest['platform']}")

    command_preview = build_bilibili_command(project_root, manifest)
    mode = "live" if args.live else "dry_run"

    if not args.live:
        payload = result_payload(
            manifest=manifest,
            mode=mode,
            status="not_executed",
            command_preview=command_preview,
        )
        result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"publish_result": str(result_path), "mode": mode}, ensure_ascii=False))
        return 0

    if manifest["decision"] != "ready_for_live_publish":
        payload = result_payload(
            manifest=manifest,
            mode=mode,
            status="blocked",
            command_preview=command_preview,
        )
        result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raise SystemExit("Publish manifest is not ready for live publish.")

    check_result = run_command(["sau", "bilibili", "check", "--account", manifest["account_name"]])
    account_status = check_result.stdout.strip() or "unknown"
    try:
        upload_result = run_command(command_preview)
    except subprocess.CalledProcessError as exc:
        payload = result_payload(
            manifest=manifest,
            mode=mode,
            status="failed",
            command_preview=command_preview,
            account_status=account_status,
            upload_stdout=sanitize_cli_output(exc.stdout),
            upload_stderr=sanitize_cli_output(exc.stderr),
        )
        result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raise

    payload = result_payload(
        manifest=manifest,
        mode=mode,
        status="submitted",
        command_preview=command_preview,
        account_status=account_status,
        upload_stdout=sanitize_cli_output(upload_result.stdout),
        upload_stderr=sanitize_cli_output(upload_result.stderr),
    )
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"publish_result": str(result_path), "mode": mode}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
