#!/usr/bin/env python3
"""Build a publish manifest from a media package."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RELEASE_RECORD_RELATIVE_PATH = "publish/release-record.json"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_candidate(root: Path, raw_path: str | None) -> Path | None:
    if not raw_path:
        return None
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate.resolve()


def relative_to_root(path: Path, root: Path) -> str:
    resolved_path = path.resolve()
    resolved_root = root.resolve()
    try:
        return str(resolved_path.relative_to(resolved_root))
    except ValueError:
        # Some assets (for example shared screenshots) may live outside the package root.
        return str(resolved_path)


def dedupe_strings(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def release_record_path(project_root: Path) -> Path:
    return (project_root / RELEASE_RECORD_RELATIVE_PATH).resolve()


def gate_status(payload: dict[str, Any]) -> str:
    for key in ("status", "overall_status", "decision", "review_status"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def gate_is_passing(payload: dict[str, Any]) -> bool:
    return gate_status(payload) in {"pass", "approved", "ready", "ready_for_publish"}


def merge_path_history(existing: dict[str, Any], latest_path: str | None) -> list[str]:
    history = existing.get("history", {})
    values = history.get("manifest_paths") or []
    merged: list[str] = [str(item) for item in values if isinstance(item, str)]
    if latest_path:
        merged.append(latest_path)
    return dedupe_strings(merged)


def merge_result_history(existing: dict[str, Any], latest_path: str | None) -> list[str]:
    history = existing.get("history", {})
    values = history.get("result_paths") or []
    merged: list[str] = [str(item) for item in values if isinstance(item, str)]
    if latest_path:
        merged.append(latest_path)
    return dedupe_strings(merged)


def default_media_ops_root() -> Path:
    return Path(__file__).resolve().parents[4] / "data" / "media-ops"


def resolve_project_root(args: argparse.Namespace) -> Path:
    if args.project_root:
        return Path(args.project_root).resolve()
    media_ops_root = Path(args.media_ops_root).resolve() if args.media_ops_root else default_media_ops_root().resolve()
    return (media_ops_root / args.content_id).resolve()


def find_content_packet(project_root: Path) -> Path | None:
    content_dir = project_root / "content"
    if not content_dir.exists():
        return None

    candidates = sorted(content_dir.glob("*.json"))
    if not candidates:
        return None

    for suffix in ("video.json", "note.json", "content-packet.json"):
        matched = [candidate for candidate in candidates if candidate.name.endswith(suffix)]
        if matched:
            return matched[0]

    return candidates[0]


def find_latest_publish_manifest(project_root: Path) -> Path | None:
    publish_dir = project_root / "publish"
    candidates = sorted(publish_dir.glob("publish-manifest*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def is_image_asset(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS


def cover_asset_rank(path: Path) -> tuple[int, int, int, str]:
    name = path.name.lower()
    background_penalty = 1 if any(token in name for token in ("bg", "background", "plan")) else 0
    final_bonus = 0 if "cover-final" in name or "final-cover" in name else 1
    draft_penalty = 1 if "draft" in name else 0
    suffix_rank = 0 if path.suffix.lower() == ".png" else 1
    return (background_penalty, final_bonus, draft_penalty, f"{suffix_rank}:{name}")


def find_preferred_final_cover_asset(project_root: Path) -> Path | None:
    cover_dir = project_root / "assets" / "final-cover"
    if not cover_dir.exists():
        return None

    candidates = sorted((path.resolve() for path in cover_dir.iterdir() if is_image_asset(path)), key=cover_asset_rank)
    return candidates[0] if candidates else None


def thumbnail_upload_supported(platform: str, content_type: str) -> bool:
    return content_type == "video" and platform in {"xiaohongshu", "bilibili"}


def build_cover_state(
    platform: str,
    content_type: str,
    thumbnail_path: str | None,
    *,
    live_submitted: bool = False,
) -> dict[str, Any]:
    asset_ready = bool(thumbnail_path)
    upload_supported = thumbnail_upload_supported(platform, content_type)

    if not asset_ready:
        delivery_status = "missing"
    elif not upload_supported:
        delivery_status = "local_asset_only"
    elif live_submitted:
        delivery_status = "uploaded_via_cli"
    else:
        delivery_status = "pending_cli_upload"

    return {
        "asset_ready": asset_ready,
        "thumbnail_upload_supported": upload_supported,
        "delivery_status": delivery_status,
    }


def find_cover_asset(
    project_root: Path,
    existing_manifest: dict[str, Any],
    publish_metadata: dict[str, Any],
    release_record: dict[str, Any],
) -> Path | None:
    preferred_final_cover = find_preferred_final_cover_asset(project_root)
    if preferred_final_cover is not None:
        return preferred_final_cover

    release_assets = release_record.get("current_assets", {})
    release_thumbnail = release_assets.get("thumbnail_path")
    existing_thumbnail = existing_manifest.get("metadata", {}).get("thumbnail_path")
    explicit_thumbnail = publish_metadata.get("thumbnail_path") or publish_metadata.get("cover_asset")
    for raw_path in (explicit_thumbnail, release_thumbnail, existing_thumbnail):
        candidate = resolve_candidate(project_root, raw_path)
        if candidate is not None and is_image_asset(candidate):
            return candidate

    cover_dir = project_root / "assets" / "final-cover"
    candidates = sorted((path.resolve() for path in cover_dir.glob("*") if is_image_asset(path)), key=cover_asset_rank)
    return candidates[0] if candidates else None


def derive_version_label(video_path: Path) -> str:
    stem = video_path.stem
    match = re.search(r"(v\d+(?:-[a-z0-9]+)*)$", stem, re.IGNORECASE)
    if match:
        return match.group(1)
    return stem


def infer_content_type(content_packet: dict[str, Any], content_packet_path: Path | None, platform: str) -> str:
    packet_format = str(content_packet.get("format") or "").lower()
    deliverable_type = str(content_packet.get("deliverable_type") or "").lower()
    filename = content_packet_path.stem.lower() if content_packet_path else ""

    if packet_format == "note" or deliverable_type in {"note", "image-note", "graphic-note"}:
        return "note"
    if "note" in filename:
        return "note"
    if deliverable_type in {"video", "short-video", "midlong-video"}:
        return "video"
    if "video" in filename:
        return "video"
    if platform == "bilibili":
        return "video"
    return "video"


def collect_note_assets(project_root: Path, content_packet: dict[str, Any], previous_manifest: dict[str, Any]) -> list[str]:
    raw_paths: list[str] = []

    content_asset_paths = content_packet.get("asset_paths")
    if isinstance(content_asset_paths, list):
        raw_paths.extend(str(item) for item in content_asset_paths if item)

    image_plan = content_packet.get("image_plan")
    if isinstance(image_plan, list):
        for item in image_plan:
            if isinstance(item, str) and item:
                raw_paths.append(item)
            elif isinstance(item, dict):
                raw_path = item.get("path") or item.get("image_path")
                if raw_path:
                    raw_paths.append(str(raw_path))

    if not raw_paths:
        previous_assets = previous_manifest.get("asset_paths")
        if isinstance(previous_assets, list):
            raw_paths.extend(str(item) for item in previous_assets if item)

    deduped: list[str] = []
    seen: set[str] = set()
    for raw_path in raw_paths:
        candidate = resolve_candidate(project_root, raw_path)
        if candidate is None or not candidate.exists():
            continue
        resolved = relative_to_root(candidate, project_root)
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(resolved)
    return deduped


def normalize_publish_mode(mode: str | None) -> str:
    if not mode:
        return "dry_run_only"
    if mode == "immediate":
        return "immediate_live_publish"
    if mode == "scheduled":
        return "scheduled_publish"
    return mode


def is_bilibili_live_refresh_request(platform: str, publish_metadata: dict[str, Any]) -> bool:
    if platform != "bilibili":
        return False
    publish_status = str(publish_metadata.get("publish_status") or "").strip().lower()
    return publish_status == "ready_for_live_refresh"


def metadata_complete(metadata: dict[str, Any], asset_paths: list[str], platform: str, content_type: str) -> bool:
    title = bool(metadata.get("title"))
    tags = metadata.get("tags") or []
    if platform == "bilibili":
        description = bool(metadata.get("description"))
        return title and description and bool(tags) and bool(asset_paths) and bool(metadata.get("partition"))
    if platform == "xiaohongshu" and content_type == "note":
        return title and bool(metadata.get("note")) and bool(asset_paths)
    if platform == "xiaohongshu" and content_type == "video":
        return title and bool(asset_paths)
    description = bool(metadata.get("description"))
    return title and description and bool(asset_paths)


def build_release_record(
    *,
    project_root: Path,
    content_packet: dict[str, Any],
    version: str,
    content_type: str,
    deliverable_type: str,
    platform: str,
    account_name: str | None,
    approval_status: str | None,
    safe_to_publish: bool,
    decision: str,
    publish_mode: str,
    schedule: str | None,
    asset_paths: list[str],
    metadata: dict[str, Any],
    manifest_output_path: Path,
    render_context: dict[str, Any],
    previous_manifest: dict[str, Any],
    existing_record: dict[str, Any],
) -> dict[str, Any]:
    current_assets = existing_record.get("current_assets", {})
    master_path = render_context.get("final_cut") or current_assets.get("master_path")
    upload_path = asset_paths[0] if asset_paths else current_assets.get("upload_path")
    thumbnail_path = metadata.get("thumbnail_path") or current_assets.get("thumbnail_path")
    cover_state = build_cover_state(platform, content_type, thumbnail_path)
    publish_ready_manifest_path = relative_to_root(manifest_output_path, project_root)

    previous_identifiers = existing_record.get("publish", {}).get("publish_identifiers", {})
    previous_review_status = existing_record.get("publish", {}).get("review_status")
    previous_result_path = existing_record.get("publish", {}).get("latest_result_path")

    history = {
        "manifest_paths": merge_path_history(existing_record, publish_ready_manifest_path),
        "result_paths": merge_result_history(existing_record, previous_result_path),
    }

    return {
        "content_id": str(content_packet.get("content_id") or project_root.name),
        "version": version,
        "platform": platform,
        "content_type": content_type,
        "deliverable_type": deliverable_type,
        "account_name": account_name,
        "approval_status": approval_status,
        "safe_to_publish": safe_to_publish,
        "status": "manifest_prepared" if decision == "ready_for_live_publish" else "blocked",
        "current_assets": {
            "master_path": master_path,
            "upload_path": upload_path,
            "thumbnail_path": thumbnail_path,
            "publish_ready_manifest_path": publish_ready_manifest_path,
        },
        "voiceover": {
            "voiceover_audio": render_context.get("voiceover"),
            "subtitles": render_context.get("subtitles"),
        },
        "runtime": {
            "duration_seconds": render_context.get("duration_seconds"),
        },
        "metadata_snapshot": metadata,
        "publish": {
            "decision": decision,
            "mode": publish_mode,
            "schedule": schedule,
            "latest_manifest_path": publish_ready_manifest_path,
            "latest_result_path": previous_result_path,
            "publish_identifiers": previous_identifiers,
            "review_status": previous_review_status,
            "first_comment": metadata.get("pinned_comment"),
            "cover_set": cover_state["delivery_status"] == "uploaded_via_cli",
            "cover_asset_ready": cover_state["asset_ready"],
            "cover_delivery_status": cover_state["delivery_status"],
            "thumbnail_upload_supported": cover_state["thumbnail_upload_supported"],
        },
        "history": history,
        "updated_at": now_iso(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", help="Media package root directory.")
    parser.add_argument("--content-id", help="Content package id under media-ops root.")
    parser.add_argument("--media-ops-root", help="Root directory containing media packages.")
    parser.add_argument("--account-name", help="Publishing account identifier.")
    parser.add_argument("--publish-mode", default=None, help="Publish mode override.")
    parser.add_argument("--schedule", default=None, help="Schedule timestamp for delayed publishing.")
    parser.add_argument("--platform", default=None, help="Platform override.")
    parser.add_argument("--approval-status", default=None, help="Approval status override.")
    parser.add_argument(
        "--output",
        default="publish/publish-manifest-auto.json",
        help="Publish manifest output path, relative to project root.",
    )
    args = parser.parse_args()
    if not args.project_root and not args.content_id:
        parser.error("one of --project-root or --content-id is required")
    return args


def build_manifest(args: argparse.Namespace) -> tuple[dict[str, Any], Path]:
    project_root = resolve_project_root(args)
    if not project_root.exists():
        raise FileNotFoundError(f"Project root does not exist: {project_root}")

    content_packet_path = find_content_packet(project_root)
    content_packet = load_json(content_packet_path)
    deliverable_type = str(content_packet.get("deliverable_type") or "").lower()
    review_gate_path = project_root / "review" / "review-gate.json"
    review_gate = load_json(review_gate_path)
    previous_manifest_path = find_latest_publish_manifest(project_root)
    previous_manifest = load_json(previous_manifest_path)
    release_record = load_json(release_record_path(project_root))
    publish_metadata = content_packet.get("publish_metadata", {})

    platform_candidates = content_packet.get("platforms") or []
    if not platform_candidates and content_packet.get("platform"):
        platform_candidates = [content_packet.get("platform")]
    platform = args.platform or (platform_candidates[0] if platform_candidates else release_record.get("platform") or previous_manifest.get("platform"))
    if not platform:
        raise ValueError("Unable to resolve publishing platform from args/content/previous manifest.")

    content_type = infer_content_type(content_packet, content_packet_path, platform)
    account_name = (
        args.account_name
        or publish_metadata.get("account_name")
        or release_record.get("account_name")
        or previous_manifest.get("account_name")
    )
    approval_status = (
        args.approval_status
        or review_gate.get("approval_status")
        or release_record.get("approval_status")
        or previous_manifest.get("approval_status")
    )
    previous_metadata = release_record.get("metadata_snapshot") or previous_manifest.get("metadata", {})
    render_context: dict[str, Any] = {}
    auto_base_quality_status: str | None = None

    if content_type == "video":
        render_manifest_path = project_root / "content" / "postproduction" / "render-manifest.json"
        render_manifest = load_json(render_manifest_path)
        if not render_manifest:
            raise FileNotFoundError(f"Missing render manifest: {render_manifest_path}")
        render_plan_path = project_root / "content" / "postproduction" / "render-plan.json"
        render_plan = load_json(render_plan_path)
        assembly_strategy = render_plan.get("assembly_strategy")
        auto_base_plan_path = project_root / "content" / "postproduction" / "auto-base-cut-plan.json"
        auto_base_plan = load_json(auto_base_plan_path)
        auto_base_quality = auto_base_plan.get("quality") if isinstance(auto_base_plan.get("quality"), dict) else {}
        auto_base_quality_status = auto_base_quality.get("status") if isinstance(auto_base_quality.get("status"), str) else None

        final_cut_path = resolve_candidate(project_root, render_manifest.get("output", {}).get("video"))
        if final_cut_path is None or not final_cut_path.exists():
            raise FileNotFoundError("Render manifest does not point to an existing final cut.")

        cover_asset = find_cover_asset(project_root, previous_manifest, publish_metadata, release_record)
        asset_paths = [relative_to_root(final_cut_path, project_root)]
        if cover_asset is not None:
            asset_paths.append(relative_to_root(cover_asset, project_root))

        version = derive_version_label(final_cut_path)
        metadata = {
            "title": (
                content_packet.get("title")
                or (content_packet.get("title_variants") or [previous_metadata.get("title")])[0]
            ),
            "description": content_packet.get("video_description") or content_packet.get("caption") or previous_metadata.get("description"),
            "tags": (
                content_packet.get("tags")
                or content_packet.get("tag_suggestions")
                or publish_metadata.get("tags")
                or previous_metadata.get("tags")
                or []
            ),
            "cover_text": content_packet.get("cover_text") or previous_metadata.get("cover_text"),
            "partition": publish_metadata.get("partition") or previous_metadata.get("partition"),
            "partition_name": publish_metadata.get("partition_name") or previous_metadata.get("partition_name"),
            "thumbnail_path": relative_to_root(cover_asset, project_root) if cover_asset is not None else previous_metadata.get("thumbnail_path"),
            "pinned_comment": content_packet.get("pinned_comment") or content_packet.get("first_comment") or previous_metadata.get("pinned_comment"),
        }
        render_context = {
            "render_manifest": relative_to_root(render_manifest_path, project_root),
            "render_plan": relative_to_root(render_plan_path, project_root) if render_plan else None,
            "assembly_strategy": assembly_strategy,
            "final_cut": relative_to_root(final_cut_path, project_root),
            "duration_seconds": render_manifest.get("output", {}).get("duration_seconds"),
            "voiceover": render_manifest.get("inputs", {}).get("voiceover_audio"),
            "subtitles": render_manifest.get("inputs", {}).get("subtitles"),
            "auto_base_quality_status": auto_base_quality_status,
            "auto_base_quality_warnings": auto_base_quality.get("warnings") if auto_base_quality else [],
        }
        notes = [
            "自动从 render-manifest 解析当前 final cut。",
            "发布素材路径优先使用最新渲染结果，而不是手工挑选旧版文件。",
        ]
    else:
        asset_paths = collect_note_assets(project_root, content_packet, previous_manifest)
        title_variants = content_packet.get("title_variants") or []
        version = (
            release_record.get("version")
            or previous_manifest.get("version")
            or (content_packet_path.stem if content_packet_path else project_root.name)
        )
        metadata = {
            "title": content_packet.get("title") or (title_variants[0] if title_variants else previous_metadata.get("title")),
            "note": content_packet.get("note") or content_packet.get("caption") or previous_metadata.get("note"),
            "tags": (
                content_packet.get("tags")
                or content_packet.get("tag_suggestions")
                or publish_metadata.get("tags")
                or previous_metadata.get("tags")
                or []
            ),
            "cover_text": content_packet.get("cover_suggestion") or content_packet.get("cover_text") or previous_metadata.get("cover_text"),
        }
        notes = [
            "图文发布素材优先使用 content packet 的 image_plan。",
            "未提供图片时会回退到历史 publish manifest 的素材路径。",
        ]

    cover_state = build_cover_state(platform, content_type, metadata.get("thumbnail_path"))
    if platform == "bilibili" and cover_state["asset_ready"]:
        notes.append("Bilibili 原生 sau CLI 仍没有封面参数；workflow 会改走 repo-local biliup wrapper，并在 live publish 阶段附带 --cover。")

    publish_mode = normalize_publish_mode(args.publish_mode or release_record.get("publish", {}).get("mode") or previous_manifest.get("publish_mode"))
    metadata_is_complete = metadata_complete(metadata, asset_paths, platform, content_type)
    safe_to_publish = bool(review_gate.get("safe_to_publish", approval_status in {"approved", "pass"}))
    decision = "dry_run_only"
    blocking_reasons: list[str] = []

    if approval_status not in {"approved", "pass"}:
        blocking_reasons.append("approval_not_granted")
    if not metadata_is_complete:
        blocking_reasons.append("metadata_incomplete")
    if not account_name:
        blocking_reasons.append("account_missing")
    if not safe_to_publish:
        blocking_reasons.append("review_gate_not_safe")

    if content_type == "video":
        assembly_qa = load_json(project_root / "review" / "assembly-qa-report.json")
        if not assembly_qa:
            blocking_reasons.append("assembly_qa_report_missing")
        elif not gate_is_passing(assembly_qa):
            blocking_reasons.append("assembly_qa_not_passed")

        if render_context.get("assembly_strategy") == "rebuild_timeline":
            auto_base_plan = load_json(project_root / "content" / "postproduction" / "auto-base-cut-plan.json")
            auto_base_quality = auto_base_plan.get("quality") if isinstance(auto_base_plan.get("quality"), dict) else {}
            quality_status = auto_base_quality.get("status") if isinstance(auto_base_quality.get("status"), str) else None
            if not auto_base_plan:
                blocking_reasons.append("auto_base_quality_report_missing")
            elif quality_status != "pass":
                blocking_reasons.append("auto_base_quality_not_passed")

    if deliverable_type == "midlong-video":
        cognitive_gate = load_json(project_root / "planning" / "cognitive-punch-gate.json")
        if not cognitive_gate:
            blocking_reasons.append("cognitive_punch_gate_missing")
        elif not gate_is_passing(cognitive_gate):
            blocking_reasons.append("cognitive_punch_gate_not_passed")

        chapter_coverage = load_json(project_root / "sources" / "chapter-coverage-report.json")
        if not chapter_coverage:
            blocking_reasons.append("chapter_coverage_report_missing")
        elif not gate_is_passing(chapter_coverage):
            blocking_reasons.append("chapter_coverage_not_passed")

    if is_bilibili_live_refresh_request(platform, publish_metadata):
        blocking_reasons.append("bilibili_refresh_not_supported")
        notes.append("当前自动化只支持 Bilibili 新稿带封面上传，不支持对已提交稿件做原地刷新；继续 live 会有重复投稿风险。")

    if not blocking_reasons and publish_mode in {"immediate_live_publish", "scheduled_publish"}:
        decision = "ready_for_live_publish"
    elif blocking_reasons:
        decision = "dry_run_only"

    blocking_reasons = dedupe_strings(blocking_reasons)

    output_path = resolve_candidate(project_root, args.output)
    if output_path is None:
        raise ValueError("Output path must resolve to a concrete filesystem path.")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    manifest = {
        "platform": platform,
        "content_type": content_type,
        "content_id": args.content_id or project_root.name,
        "version": version,
        "account_name": account_name,
        "account_status": previous_manifest.get("account_status", "pending_check"),
        "asset_paths": asset_paths,
        "metadata": metadata,
        "approval_status": approval_status,
        "publish_mode": publish_mode,
        "schedule": args.schedule or previous_manifest.get("schedule"),
        "metadata_complete": metadata_is_complete,
        "decision": decision,
        "blocking_reasons": blocking_reasons,
        "render_context": render_context,
        "cover_state": cover_state,
        "release_record_path": RELEASE_RECORD_RELATIVE_PATH,
        "notes": notes,
    }

    record = build_release_record(
        project_root=project_root,
        content_packet=content_packet,
        version=version,
        content_type=content_type,
        deliverable_type=deliverable_type or content_type,
        platform=platform,
        account_name=account_name,
        approval_status=approval_status,
        safe_to_publish=safe_to_publish,
        decision=decision,
        publish_mode=publish_mode,
        schedule=args.schedule or release_record.get("publish", {}).get("schedule") or previous_manifest.get("schedule"),
        asset_paths=asset_paths,
        metadata=metadata,
        manifest_output_path=output_path,
        render_context=render_context,
        previous_manifest=previous_manifest,
        existing_record=release_record,
    )
    record_path = release_record_path(project_root)
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest, output_path


def main() -> int:
    args = parse_args()
    manifest, output_path = build_manifest(args)
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"publish_manifest": str(output_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
