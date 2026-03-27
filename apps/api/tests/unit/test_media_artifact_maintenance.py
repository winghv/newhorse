"""Tests for end-to-end media artifact maintenance script."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_command(command: list[str], workdir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=workdir, check=True, capture_output=True, text=True)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_minimal_package(project_root: Path) -> None:
    (project_root / "research").mkdir(parents=True, exist_ok=True)
    (project_root / "planning").mkdir(parents=True, exist_ok=True)
    (project_root / "angles").mkdir(parents=True, exist_ok=True)
    (project_root / "content").mkdir(parents=True, exist_ok=True)
    (project_root / "review").mkdir(parents=True, exist_ok=True)
    (project_root / "publish").mkdir(parents=True, exist_ok=True)
    (project_root / "retros").mkdir(parents=True, exist_ok=True)

    (project_root / "research" / "research-brief.md").write_text("# brief\n", encoding="utf-8")
    write_json(project_root / "planning" / "topic-selection.json", {"topic": "x"})
    write_json(project_root / "angles" / "angle-brief.json", {"angle": "x"})
    write_json(
        project_root / "content" / "xiaohongshu-note.json",
        {"platform": "xiaohongshu", "format": "note", "title": "t", "note": "n"},
    )
    write_json(project_root / "review" / "competitive-scorecard.json", {"total_score": 30, "review_decision": "pass"})
    write_json(project_root / "review" / "review-gate.json", {"approval_status": "pass", "safe_to_publish": True})
    (project_root / "retros" / "retro-plan.md").write_text("# retro\n", encoding="utf-8")
    (project_root / "retros" / "performance-summary.md").write_text("# perf\n", encoding="utf-8")
    write_json(project_root / "retros" / "next-experiment-brief.json", {"id": "x"})


def make_sprawl_publish_files(project_root: Path) -> None:
    publish = project_root / "publish"
    write_json(publish / "publish-manifest.json", {"platform": "xiaohongshu", "decision": "approve_publish"})
    write_json(publish / "publish-manifest-auto.json", {"platform": "xiaohongshu", "decision": "ready_for_live_publish"})
    write_json(publish / "publish-manifest-v2.json", {"platform": "xiaohongshu", "decision": "dry_run_only"})
    write_json(publish / "publish-manifest-v3.json", {"platform": "xiaohongshu", "decision": "dry_run_only"})
    write_json(publish / "publish-result.json", {"status": "success", "mode": "live"})
    write_json(publish / "publish-result-auto.json", {"status": "submitted", "mode": "live"})
    write_json(publish / "publish-result-v2.json", {"status": "failed", "mode": "live"})


def test_run_artifact_maintenance_compacts_sprawl_and_reaudits(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "media-ops-orchestration"
        / "scripts"
        / "run_artifact_maintenance.py"
    )
    media_ops_root = tmp_path / "media-ops"
    project_root = media_ops_root / "2026-03-27-maintenance-pilot"
    make_minimal_package(project_root)
    make_sprawl_publish_files(project_root)

    result = run_command(
        [
            sys.executable,
            str(script_path),
            "--media-ops-root",
            str(media_ops_root),
            "--apply",
        ],
        repo_root,
    )

    payload = json.loads(result.stdout)
    assert payload["mode"] == "apply"
    assert payload["sprawl_package_count_before"] == 1
    assert payload["compaction_runs"] == 1

    after_registry = Path(payload["registry_after"])
    assert after_registry.exists()
    after = json.loads(after_registry.read_text(encoding="utf-8"))
    package = after["packages"][0]
    assert package["artifact_counts"]["publish_manifest_count"] <= 2
    assert package["artifact_counts"]["publish_result_count"] <= 2
    assert "publish_manifest_sprawl" not in package["warnings"]
