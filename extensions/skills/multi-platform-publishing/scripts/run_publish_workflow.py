#!/usr/bin/env python3
"""Execute publishing from an auto-generated publish manifest."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import re
import shutil
from pathlib import Path
from typing import Any

from build_publish_manifest import (
    RELEASE_RECORD_RELATIVE_PATH,
    build_cover_state,
    build_manifest,
    load_json as load_optional_json,
    merge_result_history,
    now_iso,
    release_record_path,
    resolve_project_root,
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_sau_binary() -> str:
    source_root = Path.home() / ".local" / "src"
    if source_root.exists():
        source_candidates = sorted(
            (path for path in source_root.glob("social-auto-upload*") if path.is_dir()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for candidate_root in source_candidates:
            candidate = candidate_root / ".venv" / "bin" / "sau"
            if candidate.exists() and os.access(candidate, os.X_OK):
                return str(candidate.resolve())

    resolved = shutil.which("sau")
    if resolved and os.access(resolved, os.X_OK):
        return resolved

    fallback = (Path.home() / ".local" / "bin" / "sau").resolve()
    if fallback.exists() and os.access(fallback, os.X_OK):
        return str(fallback)

    return "sau"


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
    video_path = resolve_asset_path(project_root, manifest["asset_paths"][0])
    wrapper_script = Path(__file__).resolve().parents[2] / "bilibili-upload" / "scripts" / "upload_bilibili_video.py"
    command = [
        "python3",
        str(wrapper_script.resolve()),
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
    thumbnail_path = metadata.get("thumbnail_path")
    if thumbnail_path:
        command.extend(["--thumbnail", str(resolve_asset_path(project_root, thumbnail_path))])
    schedule = manifest.get("schedule")
    if schedule:
        command.extend(["--schedule", schedule])
    return command


def resolve_asset_path(project_root: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = project_root / candidate
    return candidate.resolve()


def build_xiaohongshu_note_command(project_root: Path, manifest: dict[str, Any]) -> list[str]:
    metadata = manifest["metadata"]
    raw_assets = manifest.get("asset_paths") or []
    image_paths = [str(resolve_asset_path(project_root, raw_path)) for raw_path in raw_assets]
    if not image_paths:
        raise ValueError("Xiaohongshu note publishing requires at least one image asset.")

    command = [
        "sau",
        "xiaohongshu",
        "upload-note",
        "--account",
        manifest["account_name"],
        "--images",
        *image_paths,
        "--title",
        metadata["title"],
    ]
    note = metadata.get("note")
    if note:
        command.extend(["--note", note])
    tags = metadata.get("tags") or []
    if tags:
        command.extend(["--tags", ",".join(tags)])
    schedule = manifest.get("schedule")
    if schedule:
        command.extend(["--schedule", schedule])
    return command


def build_xiaohongshu_video_command(project_root: Path, manifest: dict[str, Any]) -> list[str]:
    metadata = manifest["metadata"]
    raw_assets = manifest.get("asset_paths") or []
    if not raw_assets:
        raise ValueError("Xiaohongshu video publishing requires a video asset.")

    video_path = resolve_asset_path(project_root, raw_assets[0])
    command = [
        "sau",
        "xiaohongshu",
        "upload-video",
        "--account",
        manifest["account_name"],
        "--file",
        str(video_path),
        "--title",
        metadata["title"],
    ]
    description = metadata.get("description")
    if description:
        command.extend(["--desc", description])
    tags = metadata.get("tags") or []
    if tags:
        command.extend(["--tags", ",".join(tags)])
    thumbnail_path = metadata.get("thumbnail_path")
    if thumbnail_path:
        command.extend(["--thumbnail", str(resolve_asset_path(project_root, thumbnail_path))])
    schedule = manifest.get("schedule")
    if schedule:
        command.extend(["--schedule", schedule])
    return command


def build_command(project_root: Path, manifest: dict[str, Any]) -> tuple[list[str], list[str]]:
    platform = manifest.get("platform")
    content_type = manifest.get("content_type", "video")

    if platform == "bilibili":
        return build_bilibili_command(project_root, manifest), ["sau", "bilibili", "check", "--account", manifest["account_name"]]
    if platform == "xiaohongshu" and content_type == "note":
        return build_xiaohongshu_note_command(project_root, manifest), ["sau", "xiaohongshu", "check", "--account", manifest["account_name"]]
    if platform == "xiaohongshu" and content_type == "video":
        return build_xiaohongshu_video_command(project_root, manifest), ["sau", "xiaohongshu", "check", "--account", manifest["account_name"]]
    raise NotImplementedError(f"Unsupported publish route: platform={platform}, content_type={content_type}")


def executable_command(command: list[str]) -> list[str]:
    if command and command[0] == "sau":
        return [resolve_sau_binary(), *command[1:]]
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


def extract_publish_identifiers(platform: str, raw_text: str | None) -> dict[str, str]:
    if not raw_text:
        return {}

    identifiers: dict[str, str] = {}
    if platform == "bilibili":
        bvid_match = re.search(r"\bBV[0-9A-Za-z]{10,}\b", raw_text)
        aid_match = re.search(r"(?i)\baid\b\s*[:=]\s*(\d+)\b", raw_text)
        if bvid_match:
            identifiers["bvid"] = bvid_match.group(0)
        if aid_match:
            identifiers["aid"] = aid_match.group(1)

    generic_patterns = {
        "note_id": r"(?i)\bnote[_\s-]?id\b\s*[:=]\s*([A-Za-z0-9_-]+)\b",
        "video_id": r"(?i)\bvideo[_\s-]?id\b\s*[:=]\s*([A-Za-z0-9_-]+)\b",
        "post_id": r"(?i)\bpost[_\s-]?id\b\s*[:=]\s*([A-Za-z0-9_-]+)\b",
    }
    for key, pattern in generic_patterns.items():
        match = re.search(pattern, raw_text)
        if match:
            identifiers[key] = match.group(1)
    return identifiers


def extract_review_status(raw_text: str | None) -> str | None:
    if not raw_text:
        return None
    lowered = raw_text.lower()
    if "审核中" in raw_text or "reviewing" in lowered or "pending review" in lowered:
        return "reviewing"
    if "submitted" in lowered:
        return "submitted"
    if "published" in lowered or "已发布" in raw_text:
        return "published"
    return None


def update_release_record_from_result(
    *,
    project_root: Path,
    manifest: dict[str, Any],
    result_path: Path,
    mode: str,
    status: str,
    account_status: str | None,
    upload_stdout: str | None,
    upload_stderr: str | None,
) -> None:
    record_path = release_record_path(project_root)
    existing = load_optional_json(record_path)
    raw_output = "\n".join(part for part in (upload_stdout, upload_stderr) if part)
    identifiers = {
        **existing.get("publish", {}).get("publish_identifiers", {}),
        **extract_publish_identifiers(manifest["platform"], raw_output),
    }
    review_status = extract_review_status(raw_output) or existing.get("publish", {}).get("review_status")
    current_assets = existing.get("current_assets", {})
    asset_paths = manifest.get("asset_paths") or []
    thumbnail_path = manifest.get("metadata", {}).get("thumbnail_path") or current_assets.get("thumbnail_path")
    cover_state = build_cover_state(
        manifest.get("platform", ""),
        manifest.get("content_type", "video"),
        thumbnail_path,
        live_submitted=mode == "live" and status in {"submitted", "published"},
    )
    latest_result_rel = str(result_path.resolve().relative_to(project_root.resolve()))
    latest_manifest_rel = existing.get("publish", {}).get("latest_manifest_path") or current_assets.get("publish_ready_manifest_path")
    history = {
        "manifest_paths": existing.get("history", {}).get("manifest_paths") or ([latest_manifest_rel] if latest_manifest_rel else []),
        "result_paths": merge_result_history(existing, latest_result_rel),
    }

    record = {
        **existing,
        "content_id": manifest.get("content_id"),
        "platform": manifest.get("platform"),
        "content_type": manifest.get("content_type"),
        "deliverable_type": existing.get("deliverable_type"),
        "account_name": manifest.get("account_name"),
        "approval_status": manifest.get("approval_status"),
        "safe_to_publish": existing.get("safe_to_publish"),
        "status": {
            ("dry_run", "not_executed"): "dry_run_ready",
            ("live", "submitted"): "live_submitted",
            ("live", "failed"): "live_failed",
            ("live", "blocked"): "blocked",
        }.get((mode, status), existing.get("status", "manifest_prepared")),
        "current_assets": {
            "master_path": current_assets.get("master_path") or manifest.get("render_context", {}).get("final_cut"),
            "upload_path": asset_paths[0] if asset_paths else current_assets.get("upload_path"),
            "thumbnail_path": thumbnail_path,
            "publish_ready_manifest_path": existing.get("current_assets", {}).get("publish_ready_manifest_path")
            or "publish/publish-manifest-auto.json",
        },
        "voiceover": {
            "voiceover_audio": manifest.get("render_context", {}).get("voiceover"),
            "subtitles": manifest.get("render_context", {}).get("subtitles"),
        },
        "runtime": {
            "duration_seconds": manifest.get("render_context", {}).get("duration_seconds"),
        },
        "metadata_snapshot": manifest.get("metadata", {}),
        "publish": {
            "decision": manifest.get("decision"),
            "mode": manifest.get("publish_mode"),
            "schedule": manifest.get("schedule"),
            "latest_manifest_path": latest_manifest_rel or "publish/publish-manifest-auto.json",
            "latest_result_path": latest_result_rel,
            "publish_identifiers": identifiers,
            "review_status": review_status,
            "first_comment": manifest.get("metadata", {}).get("pinned_comment"),
            "cover_set": cover_state["delivery_status"] == "uploaded_via_cli",
            "cover_asset_ready": cover_state["asset_ready"],
            "cover_delivery_status": cover_state["delivery_status"],
            "thumbnail_upload_supported": cover_state["thumbnail_upload_supported"],
            "account_status": account_status,
        },
        "history": history,
        "updated_at": now_iso(),
    }
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def result_payload(
    manifest: dict[str, Any],
    mode: str,
    status: str,
    command_preview: list[str],
    account_status: str | None = None,
    upload_stdout: str | None = None,
    upload_stderr: str | None = None,
) -> dict[str, Any]:
    content_type = manifest.get("content_type", "video")
    asset_paths = manifest.get("asset_paths") or []
    cover_state = build_cover_state(
        manifest.get("platform", ""),
        content_type,
        manifest.get("metadata", {}).get("thumbnail_path"),
        live_submitted=mode == "live" and status in {"submitted", "published"},
    )
    assets: dict[str, Any] = {
        "voiceover": manifest.get("render_context", {}).get("voiceover"),
        "subtitles": manifest.get("render_context", {}).get("subtitles"),
    }
    if content_type == "note":
        assets["images"] = asset_paths
    else:
        assets["video"] = asset_paths[0] if asset_paths else None
        assets["cover"] = asset_paths[1] if len(asset_paths) > 1 else None

    raw_output = "\n".join(part for part in (upload_stdout, upload_stderr) if part)

    return {
        "platform": manifest["platform"],
        "content_type": content_type,
        "content_id": manifest["content_id"],
        "version": manifest["version"],
        "mode": mode,
        "status": status,
        "decision": manifest["decision"],
        "account": {
            "account_name": manifest.get("account_name"),
            "status": account_status or manifest.get("account_status", "pending_check"),
        },
        "assets": assets,
        "metadata": manifest.get("metadata", {}),
        "cover_state": cover_state,
        "command_preview": command_preview,
        "blocking_reasons": manifest.get("blocking_reasons", []),
        "notes": manifest.get("notes", []),
        "release_record_path": manifest.get("release_record_path", RELEASE_RECORD_RELATIVE_PATH),
        "publish_identifiers": extract_publish_identifiers(manifest["platform"], raw_output),
        "review_status": extract_review_status(raw_output),
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

    command_preview, check_command = build_command(project_root, manifest)
    mode = "live" if args.live else "dry_run"

    if not args.live:
        payload = result_payload(
            manifest=manifest,
            mode=mode,
            status="not_executed",
            command_preview=command_preview,
        )
        result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        update_release_record_from_result(
            project_root=project_root,
            manifest=manifest,
            result_path=result_path,
            mode=mode,
            status="not_executed",
            account_status=None,
            upload_stdout=None,
            upload_stderr=None,
        )
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
        update_release_record_from_result(
            project_root=project_root,
            manifest=manifest,
            result_path=result_path,
            mode=mode,
            status="blocked",
            account_status=None,
            upload_stdout=None,
            upload_stderr=None,
        )
        raise SystemExit("Publish manifest is not ready for live publish.")

    check_result = run_command(executable_command(check_command))
    account_status = check_result.stdout.strip() or "unknown"
    try:
        upload_result = run_command(executable_command(command_preview))
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
        update_release_record_from_result(
            project_root=project_root,
            manifest=manifest,
            result_path=result_path,
            mode=mode,
            status="failed",
            account_status=account_status,
            upload_stdout=sanitize_cli_output(exc.stdout),
            upload_stderr=sanitize_cli_output(exc.stderr),
        )
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
    update_release_record_from_result(
        project_root=project_root,
        manifest=manifest,
        result_path=result_path,
        mode=mode,
        status="submitted",
        account_status=account_status,
        upload_stdout=sanitize_cli_output(upload_result.stdout),
        upload_stderr=sanitize_cli_output(upload_result.stderr),
    )
    print(json.dumps({"publish_result": str(result_path), "mode": mode}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
