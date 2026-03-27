#!/usr/bin/env python3
"""Run media-ops artifact maintenance end-to-end.

Pipeline:
1) audit artifacts
2) detect packages with publish version sprawl warnings
3) compact publish artifacts for those packages (optional apply)
4) re-audit artifacts
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, capture_output=True, text=True)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_audit(
    *,
    script_path: Path,
    media_ops_root: Path,
    output_path: Path,
    summary_output_path: Path,
    fail_on_missing_required: bool,
) -> dict[str, Any]:
    command = [
        sys.executable,
        str(script_path),
        "--media-ops-root",
        str(media_ops_root),
        "--output",
        str(output_path),
        "--summary-output",
        str(summary_output_path),
    ]
    if fail_on_missing_required:
        command.append("--fail-on-missing-required")
    result = run_command(command)
    return json.loads(result.stdout)


def detect_sprawl_packages(registry_path: Path, media_ops_root: Path) -> list[Path]:
    payload = load_json(registry_path)
    packages = payload.get("packages") or []
    sprawl_paths: list[Path] = []
    for pkg in packages:
        warnings = set(pkg.get("warnings") or [])
        if "publish_manifest_sprawl" in warnings or "publish_result_sprawl" in warnings:
            package_path = pkg.get("package_path")
            if isinstance(package_path, str) and package_path:
                sprawl_paths.append((media_ops_root / package_path).resolve())
    return sprawl_paths


def run_compaction(
    *,
    script_path: Path,
    project_root: Path,
    apply_changes: bool,
    min_versions: int,
) -> dict[str, Any]:
    command = [
        sys.executable,
        str(script_path),
        "--project-root",
        str(project_root),
        "--min-versions",
        str(min_versions),
    ]
    if apply_changes:
        command.append("--apply")
    result = run_command(command)
    return json.loads(result.stdout)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--media-ops-root",
        default=str(Path(__file__).resolve().parents[4] / "data" / "media-ops"),
        help="Root directory containing media content packages.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply compaction changes. Without this flag compaction runs in dry-run mode.",
    )
    parser.add_argument(
        "--min-versions",
        type=int,
        default=4,
        help="Compaction threshold passed to compact_publish_artifacts.py.",
    )
    parser.add_argument(
        "--fail-on-missing-required",
        action="store_true",
        help="Fail when required artifacts are missing in either audit pass.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    media_ops_root = Path(args.media_ops_root).resolve()
    scripts_dir = Path(__file__).resolve().parent

    audit_script = scripts_dir / "audit_artifacts.py"
    compact_script = scripts_dir / "compact_publish_artifacts.py"
    registry_dir = media_ops_root / "_registry"
    registry_before = registry_dir / "artifact-registry.pre-maintenance.json"
    summary_before = registry_dir / "artifact-registry.pre-maintenance.md"
    registry_after = registry_dir / "artifact-registry.json"
    summary_after = registry_dir / "artifact-registry.md"

    before = run_audit(
        script_path=audit_script,
        media_ops_root=media_ops_root,
        output_path=registry_before,
        summary_output_path=summary_before,
        fail_on_missing_required=args.fail_on_missing_required,
    )
    sprawl_packages = detect_sprawl_packages(registry_before, media_ops_root)

    compaction_results: list[dict[str, Any]] = []
    for project_root in sprawl_packages:
        compaction_results.append(
            run_compaction(
                script_path=compact_script,
                project_root=project_root,
                apply_changes=args.apply,
                min_versions=args.min_versions,
            )
        )

    after = run_audit(
        script_path=audit_script,
        media_ops_root=media_ops_root,
        output_path=registry_after,
        summary_output_path=summary_after,
        fail_on_missing_required=args.fail_on_missing_required,
    )

    summary = {
        "media_ops_root": str(media_ops_root),
        "mode": "apply" if args.apply else "dry_run",
        "sprawl_package_count_before": len(sprawl_packages),
        "compaction_runs": len(compaction_results),
        "compaction_results": compaction_results,
        "audit_before": before,
        "audit_after": after,
        "registry_before": str(registry_before),
        "registry_after": str(registry_after),
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
