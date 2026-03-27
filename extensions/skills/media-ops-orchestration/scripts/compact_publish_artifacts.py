#!/usr/bin/env python3
"""Compact publish manifests/results by archiving non-critical versions."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def resolve_project_root(args: argparse.Namespace) -> Path:
    if args.project_root:
        return Path(args.project_root).resolve()
    media_ops_root = Path(args.media_ops_root).resolve()
    return (media_ops_root / args.content_id).resolve()


def list_publish_files(publish_dir: Path, pattern: str) -> list[Path]:
    return sorted(path for path in publish_dir.glob(pattern) if path.is_file())


def counterpart_name(filename: str) -> str:
    if "publish-result" in filename:
        return filename.replace("publish-result", "publish-manifest", 1)
    if "publish-manifest" in filename:
        return filename.replace("publish-manifest", "publish-result", 1)
    return filename


def result_is_milestone(path: Path) -> bool:
    data = load_json(path)
    status = str(data.get("status") or "").lower()
    submission = data.get("submission")
    return status in {"success", "submitted"} or isinstance(submission, dict)


def manifest_is_milestone(path: Path) -> bool:
    data = load_json(path)
    decision = str(data.get("decision") or "").lower()
    return decision in {"ready_for_live_publish", "approve_publish", "published_pending_review"}


def add_keep(keep: dict[Path, str], path: Path | None, reason: str) -> None:
    if path is None:
        return
    if path not in keep:
        keep[path] = reason


def ensure_unique_destination(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    index = 2
    while True:
        candidate = path.with_name(f"{stem}-{index}{suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def append_archive_index(index_path: Path, batch_record: dict[str, Any]) -> None:
    existing: dict[str, Any] = {}
    if index_path.exists():
        try:
            existing = json.loads(index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}

    batches = existing.get("batches")
    if not isinstance(batches, list):
        batches = []

    batches.append(batch_record)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "batches": batches,
    }
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", help="Path to one media content package.")
    parser.add_argument("--content-id", help="Content package id under media-ops root.")
    parser.add_argument(
        "--media-ops-root",
        default=str(Path(__file__).resolve().parents[4] / "data" / "media-ops"),
        help="Root directory containing media packages.",
    )
    parser.add_argument("--apply", action="store_true", help="Apply changes. Without this flag the script runs in dry-run.")
    parser.add_argument(
        "--min-versions",
        type=int,
        default=4,
        help="Only compact when total publish manifest/result files exceed this number.",
    )
    args = parser.parse_args()
    if not args.project_root and not args.content_id:
        parser.error("one of --project-root or --content-id is required")
    return args


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)
    publish_dir = project_root / "publish"
    if not publish_dir.exists():
        raise FileNotFoundError(f"Missing publish directory: {publish_dir}")

    manifests = list_publish_files(publish_dir, "publish-manifest*.json")
    results = list_publish_files(publish_dir, "publish-result*.json")
    all_files = manifests + results
    if len(all_files) <= args.min_versions:
        print(
            json.dumps(
                {
                    "project_root": str(project_root),
                    "mode": "dry_run",
                    "skipped": True,
                    "reason": "below_threshold",
                    "total_files": len(all_files),
                },
                ensure_ascii=False,
            )
        )
        return 0

    latest_manifest = max(manifests, key=lambda path: path.stat().st_mtime) if manifests else None
    latest_result = max(results, key=lambda path: path.stat().st_mtime) if results else None
    manifest_lookup = {path.name: path for path in manifests}

    keep: dict[Path, str] = {}
    canonical_names = {
        "publish-manifest.json",
        "publish-manifest-auto.json",
        "publish-result.json",
        "publish-result-auto.json",
    }
    for path in all_files:
        if path.name in canonical_names:
            keep[path] = "canonical_filename"

    canonical_manifest_names = {"publish-manifest.json", "publish-manifest-auto.json"}
    canonical_result_names = {"publish-result.json", "publish-result-auto.json"}
    has_canonical_manifest = any(path.name in canonical_manifest_names for path in manifests)
    has_canonical_result = any(path.name in canonical_result_names for path in results)

    if not has_canonical_manifest:
        add_keep(keep, latest_manifest, "latest_manifest_fallback")
    if not has_canonical_result:
        add_keep(keep, latest_result, "latest_result_fallback")

    milestone_results = [path for path in results if path.name not in canonical_names and result_is_milestone(path)]
    latest_milestone_result = max(milestone_results, key=lambda path: path.stat().st_mtime) if milestone_results else None
    add_keep(keep, latest_milestone_result, "latest_milestone_result")

    if latest_milestone_result is not None:
        paired_manifest = manifest_lookup.get(counterpart_name(latest_milestone_result.name))
        if paired_manifest is not None and paired_manifest.name not in canonical_names:
            add_keep(keep, paired_manifest, "paired_with_latest_milestone_result")

    if latest_milestone_result is None:
        milestone_manifests = [
            path
            for path in manifests
            if path.name not in canonical_names and manifest_is_milestone(path)
        ]
        latest_milestone_manifest = (
            max(milestone_manifests, key=lambda path: path.stat().st_mtime) if milestone_manifests else None
        )
        add_keep(keep, latest_milestone_manifest, "latest_milestone_manifest")

    archive = [path for path in sorted(all_files) if path not in keep]

    moved: list[dict[str, str]] = []
    mode = "apply" if args.apply else "dry_run"
    batch_record: dict[str, Any] | None = None

    if args.apply and archive:
        now = datetime.now(timezone.utc)
        batch_id = now.strftime("%Y%m%dT%H%M%SZ")
        batch_dir = publish_dir / "archive" / batch_id
        batch_dir.mkdir(parents=True, exist_ok=True)

        for source in archive:
            destination = ensure_unique_destination(batch_dir / source.name)
            source.rename(destination)
            moved.append(
                {
                    "from": str(source.relative_to(project_root)),
                    "to": str(destination.relative_to(project_root)),
                }
            )

        batch_report = {
            "batch_id": batch_id,
            "created_at": now.isoformat(),
            "project_root": str(project_root),
            "moved": moved,
            "kept": [
                {"path": str(path.relative_to(project_root)), "reason": reason}
                for path, reason in sorted(keep.items(), key=lambda item: item[0].name)
            ],
        }
        (batch_dir / "archive-report.json").write_text(
            json.dumps(batch_report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        batch_record = {
            "batch_id": batch_id,
            "created_at": now.isoformat(),
            "project_root": str(project_root),
            "moved_count": len(moved),
            "kept_count": len(keep),
            "report": str((batch_dir / "archive-report.json").relative_to(project_root)),
        }
        append_archive_index(publish_dir / "archive" / "archive-index.json", batch_record)

    print(
        json.dumps(
            {
                "project_root": str(project_root),
                "mode": mode,
                "total_files": len(all_files),
                "kept_count": len(keep),
                "archive_count": len(archive),
                "kept": [
                    {"path": str(path.relative_to(project_root)), "reason": reason}
                    for path, reason in sorted(keep.items(), key=lambda item: item[0].name)
                ],
                "archive_candidates": [str(path.relative_to(project_root)) for path in archive],
                "moved": moved,
                "batch": batch_record,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
