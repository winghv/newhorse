"""Tests for publish artifact compaction script."""

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


def make_publish_versions(project_root: Path) -> None:
    publish = project_root / "publish"
    publish.mkdir(parents=True, exist_ok=True)

    write_json(publish / "publish-manifest.json", {"decision": "published_pending_review"})
    write_json(publish / "publish-manifest-auto.json", {"decision": "ready_for_live_publish"})
    write_json(publish / "publish-manifest-v2.json", {"decision": "dry_run_only"})
    write_json(publish / "publish-manifest-v3.json", {"decision": "ready_for_live_publish"})

    write_json(publish / "publish-result.json", {"status": "success", "mode": "live"})
    write_json(publish / "publish-result-auto.json", {"status": "submitted", "mode": "live"})
    write_json(publish / "publish-result-v2.json", {"status": "failed", "mode": "live"})
    write_json(publish / "publish-result-v3.json", {"status": "submitted", "mode": "live"})


def test_compact_publish_artifacts_dry_run_and_apply(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "media-ops-orchestration"
        / "scripts"
        / "compact_publish_artifacts.py"
    )

    project_root = tmp_path / "media-package"
    make_publish_versions(project_root)

    dry_run = run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
        ],
        repo_root,
    )
    dry_payload = json.loads(dry_run.stdout)
    assert dry_payload["mode"] == "dry_run"
    assert "publish/publish-manifest-v2.json" in dry_payload["archive_candidates"]
    assert "publish/publish-result-v2.json" in dry_payload["archive_candidates"]
    assert dry_payload["moved"] == []

    apply_run = run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
            "--apply",
        ],
        repo_root,
    )
    apply_payload = json.loads(apply_run.stdout)
    assert apply_payload["mode"] == "apply"
    assert apply_payload["archive_count"] >= 2
    assert len(apply_payload["moved"]) >= 2

    publish_dir = project_root / "publish"
    assert not (publish_dir / "publish-manifest-v2.json").exists()
    assert not (publish_dir / "publish-result-v2.json").exists()
    assert (publish_dir / "publish-manifest-auto.json").exists()
    assert (publish_dir / "publish-result-auto.json").exists()

    archive_index = publish_dir / "archive" / "archive-index.json"
    assert archive_index.exists()
    index_payload = json.loads(archive_index.read_text(encoding="utf-8"))
    assert isinstance(index_payload.get("batches"), list)
    assert index_payload["batches"][-1]["moved_count"] >= 2
