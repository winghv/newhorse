"""Tests for media-ops publish queue builder script."""

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


def make_ready_note_package(project_root: Path) -> None:
    (project_root / "research").mkdir(parents=True, exist_ok=True)
    (project_root / "planning").mkdir(parents=True, exist_ok=True)
    (project_root / "angles").mkdir(parents=True, exist_ok=True)
    (project_root / "content").mkdir(parents=True, exist_ok=True)
    (project_root / "assets" / "note").mkdir(parents=True, exist_ok=True)
    (project_root / "review").mkdir(parents=True, exist_ok=True)
    (project_root / "publish").mkdir(parents=True, exist_ok=True)

    (project_root / "research" / "research-brief.md").write_text("# brief\n", encoding="utf-8")
    write_json(project_root / "planning" / "topic-selection.json", {"topic": "ready note"})
    write_json(project_root / "angles" / "angle-brief.json", {"angle": "ready"})
    (project_root / "assets" / "note" / "1.png").write_bytes(b"png")
    write_json(
        project_root / "content" / "xiaohongshu-note.json",
        {
            "platform": "xiaohongshu",
            "format": "note",
            "title": "Ready note",
            "note": "Ready for live publish",
            "image_plan": [{"path": "assets/note/1.png"}],
        },
    )
    write_json(project_root / "review" / "competitive-scorecard.json", {"total_score": 31, "review_decision": "pass"})
    write_json(project_root / "review" / "review-gate.json", {"approval_status": "pass", "safe_to_publish": True})
    write_json(
        project_root / "publish" / "publish-manifest-prelive.json",
        {
            "platform": "xiaohongshu",
            "content_type": "note",
            "content_id": project_root.name,
            "account_name": "xhs-ready",
            "decision": "ready_for_live_publish",
            "publish_mode": "immediate_live_publish",
            "blocking_reasons": [],
        },
    )
    write_json(
        project_root / "publish" / "release-record.json",
        {
            "status": "manifest_prepared",
            "publish": {"latest_manifest_path": "publish/publish-manifest-prelive.json"},
        },
    )
    write_json(
        project_root / "publish" / "publish-result-auto.json",
        {
            "status": "not_executed",
            "mode": "dry_run",
        },
    )
    write_json(
        project_root / "publish" / "live-execution-plan.json",
        {
            "content_id": project_root.name,
            "platform": "xiaohongshu",
            "content_type": "note",
            "account_name": "xhs-ready",
            "manifest_path": "publish/publish-manifest-prelive.json",
            "decision": "ready_for_live_publish",
            "live_ready": True,
            "blocking_reasons": [],
            "account_check_command": ["sau", "xiaohongshu", "check", "--account", "xhs-ready"],
            "publish_command_preview": ["sau", "xiaohongshu", "upload-note"],
            "workflow_live_command": [
                "python3",
                "extensions/skills/multi-platform-publishing/scripts/run_publish_workflow.py",
                "--project-root",
                str(project_root),
                "--account-name",
                "xhs-ready",
                "--manifest",
                "publish/publish-manifest-prelive.json",
                "--live",
            ],
        },
    )


def make_blocked_video_package(project_root: Path) -> None:
    (project_root / "research").mkdir(parents=True, exist_ok=True)
    (project_root / "planning").mkdir(parents=True, exist_ok=True)
    (project_root / "angles").mkdir(parents=True, exist_ok=True)
    (project_root / "content" / "postproduction").mkdir(parents=True, exist_ok=True)
    (project_root / "content" / "final-cut").mkdir(parents=True, exist_ok=True)
    (project_root / "review").mkdir(parents=True, exist_ok=True)
    (project_root / "publish").mkdir(parents=True, exist_ok=True)

    (project_root / "research" / "research-brief.md").write_text("# brief\n", encoding="utf-8")
    write_json(project_root / "planning" / "topic-selection.json", {"topic": "blocked video"})
    write_json(project_root / "angles" / "angle-brief.json", {"angle": "blocked"})
    write_json(
        project_root / "content" / "xiaohongshu-short-video.json",
        {
            "platform": "xiaohongshu",
            "deliverable_type": "short-video",
            "title": "Blocked video",
            "video_description": "Needs fixes before publish",
            "tags": ["blocked"],
        },
    )
    (project_root / "content" / "final-cut" / "v1.mp4").write_bytes(b"video")
    write_json(
        project_root / "content" / "postproduction" / "render-manifest.json",
        {
            "output": {"video": "content/final-cut/v1.mp4"},
        },
    )
    write_json(project_root / "review" / "competitive-scorecard.json", {"total_score": 24, "review_decision": "revise"})
    write_json(project_root / "review" / "review-gate.json", {"approval_status": "revise", "safe_to_publish": False})
    write_json(project_root / "review" / "assembly-qa-report.json", {"status": "pass", "checks": {}})
    write_json(
        project_root / "publish" / "publish-manifest-prelive.json",
        {
            "platform": "xiaohongshu",
            "content_type": "video",
            "content_id": project_root.name,
            "account_name": "xhs-blocked",
            "decision": "dry_run_only",
            "publish_mode": "immediate_live_publish",
            "blocking_reasons": ["review_gate_not_safe"],
        },
    )
    write_json(
        project_root / "publish" / "release-record.json",
        {
            "status": "blocked",
            "publish": {"latest_manifest_path": "publish/publish-manifest-prelive.json"},
        },
    )
    write_json(
        project_root / "publish" / "publish-result-auto.json",
        {
            "status": "not_executed",
            "mode": "dry_run",
        },
    )
    write_json(
        project_root / "publish" / "live-execution-plan.json",
        {
            "content_id": project_root.name,
            "platform": "xiaohongshu",
            "content_type": "video",
            "account_name": "xhs-blocked",
            "manifest_path": "publish/publish-manifest-prelive.json",
            "decision": "dry_run_only",
            "live_ready": False,
            "blocking_reasons": ["review_gate_not_safe"],
            "account_check_command": ["sau", "xiaohongshu", "check", "--account", "xhs-blocked"],
            "publish_command_preview": ["sau", "xiaohongshu", "upload-video"],
            "workflow_live_command": [
                "python3",
                "extensions/skills/multi-platform-publishing/scripts/run_publish_workflow.py",
                "--project-root",
                str(project_root),
                "--account-name",
                "xhs-blocked",
                "--manifest",
                "publish/publish-manifest-prelive.json",
                "--live",
            ],
        },
    )


def make_quality_blocked_rebuild_video_package(project_root: Path) -> None:
    (project_root / "research").mkdir(parents=True, exist_ok=True)
    (project_root / "planning").mkdir(parents=True, exist_ok=True)
    (project_root / "angles").mkdir(parents=True, exist_ok=True)
    (project_root / "content" / "postproduction").mkdir(parents=True, exist_ok=True)
    (project_root / "content" / "final-cut").mkdir(parents=True, exist_ok=True)
    (project_root / "review").mkdir(parents=True, exist_ok=True)
    (project_root / "publish").mkdir(parents=True, exist_ok=True)

    (project_root / "research" / "research-brief.md").write_text("# brief\n", encoding="utf-8")
    write_json(project_root / "planning" / "topic-selection.json", {"topic": "quality blocked video"})
    write_json(project_root / "planning" / "cognitive-punch-gate.json", {"status": "pass"})
    write_json(project_root / "angles" / "angle-brief.json", {"angle": "quality-blocked"})
    write_json(
        project_root / "content" / "bilibili-midform-video.json",
        {
            "platforms": ["bilibili"],
            "deliverable_type": "midlong-video",
            "title": "Quality blocked video",
        },
    )
    (project_root / "content" / "final-cut" / "v1.mp4").write_bytes(b"video")
    write_json(
        project_root / "content" / "postproduction" / "render-manifest.json",
        {
            "output": {"video": "content/final-cut/v1.mp4"},
        },
    )
    write_json(project_root / "sources" / "source-manifest.json", {"source_manifest": []})
    write_json(project_root / "sources" / "source-shortlist.json", {"items": []})
    write_json(project_root / "sources" / "asset-ingest-manifest.json", {"items": []})
    write_json(project_root / "sources" / "chapter-coverage-report.json", {"overall_status": "pass"})
    write_json(project_root / "review" / "competitive-scorecard.json", {"total_score": 29, "review_decision": "pass"})
    write_json(project_root / "review" / "review-gate.json", {"approval_status": "pass", "safe_to_publish": True})
    write_json(project_root / "review" / "assembly-qa-report.json", {"status": "pass", "checks": {}})
    write_json(
        project_root / "publish" / "publish-manifest-prelive.json",
        {
            "platform": "bilibili",
            "content_type": "video",
            "content_id": project_root.name,
            "account_name": "bili-quality-blocked",
            "decision": "dry_run_only",
            "publish_mode": "immediate_live_publish",
            "blocking_reasons": ["auto_base_quality_not_passed"],
            "render_context": {
                "assembly_strategy": "rebuild_timeline",
                "auto_base_quality_status": "revise",
            },
        },
    )
    write_json(
        project_root / "publish" / "release-record.json",
        {
            "status": "blocked",
            "publish": {"latest_manifest_path": "publish/publish-manifest-prelive.json"},
        },
    )
def test_build_publish_queue_surfaces_ready_and_blocked_packages(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "media-ops-orchestration"
        / "scripts"
        / "build_publish_queue.py"
    )
    media_ops_root = tmp_path / "media-ops"
    make_ready_note_package(media_ops_root / "2026-03-28-xhs-ready")
    make_blocked_video_package(media_ops_root / "2026-03-28-xhs-blocked")

    output_path = media_ops_root / "_registry" / "publish-queue.json"
    summary_path = media_ops_root / "_registry" / "publish-queue.md"
    run_command(
        [
            sys.executable,
            str(script_path),
            "--media-ops-root",
            str(media_ops_root),
            "--output",
            str(output_path),
            "--summary-output",
            str(summary_path),
        ],
        repo_root,
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["ready_for_live"] == 1
    assert payload["summary"]["blocked"] == 1

    entries = payload["entries"]
    assert [entry["content_id"] for entry in entries] == [
        "2026-03-28-xhs-ready",
        "2026-03-28-xhs-blocked",
    ]

    ready_entry = entries[0]
    assert ready_entry["queue_status"] == "ready_for_live"
    assert ready_entry["account_name"] == "xhs-ready"
    assert ready_entry["next_action"] == "await_manual_live_trigger"
    assert ready_entry["workflow_live_command"][-1] == "--live"

    blocked_entry = entries[1]
    assert blocked_entry["queue_status"] == "blocked"
    assert "review_gate_not_safe" in blocked_entry["blocking_reasons"]
    assert "approval_not_granted" in blocked_entry["blocking_reasons"]
    assert blocked_entry["next_action"] == "revise_content_and_review_gate"


def test_build_publish_queue_surfaces_auto_timeline_quality_blockers(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "media-ops-orchestration"
        / "scripts"
        / "build_publish_queue.py"
    )
    media_ops_root = tmp_path / "media-ops"
    make_quality_blocked_rebuild_video_package(media_ops_root / "2026-03-29-bili-quality-blocked")

    output_path = media_ops_root / "_registry" / "publish-queue.json"
    run_command(
        [
            sys.executable,
            str(script_path),
            "--media-ops-root",
            str(media_ops_root),
            "--output",
            str(output_path),
        ],
        repo_root,
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    entry = payload["entries"][0]
    assert entry["queue_status"] == "blocked"
    assert entry["assembly_strategy"] == "rebuild_timeline"
    assert entry["auto_base_quality_status"] == "revise"
    assert "auto_base_quality_not_passed" in entry["blocking_reasons"]
    assert entry["next_action"] == "improve_auto_timeline_quality"


def test_build_publish_queue_filters_by_account_name(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "media-ops-orchestration"
        / "scripts"
        / "build_publish_queue.py"
    )
    media_ops_root = tmp_path / "media-ops"
    make_ready_note_package(media_ops_root / "2026-03-28-xhs-ready")
    make_blocked_video_package(media_ops_root / "2026-03-28-xhs-blocked")

    output_path = media_ops_root / "_registry" / "publish-queue.json"
    run_command(
        [
            sys.executable,
            str(script_path),
            "--media-ops-root",
            str(media_ops_root),
            "--account-name",
            "xhs-ready",
            "--output",
            str(output_path),
        ],
        repo_root,
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["entry_count"] == 1
    assert payload["entries"][0]["content_id"] == "2026-03-28-xhs-ready"
