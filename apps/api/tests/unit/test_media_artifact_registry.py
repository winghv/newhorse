"""Tests for media-ops artifact registry audit script."""

import json
import subprocess
import sys
from pathlib import Path


def run_command(command: list[str], workdir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=workdir, check=True, capture_output=True, text=True)


def make_video_package(project_root: Path) -> None:
    (project_root / "research").mkdir(parents=True, exist_ok=True)
    (project_root / "planning").mkdir(parents=True, exist_ok=True)
    (project_root / "angles").mkdir(parents=True, exist_ok=True)
    (project_root / "content" / "postproduction").mkdir(parents=True, exist_ok=True)
    (project_root / "content" / "final-cut").mkdir(parents=True, exist_ok=True)
    (project_root / "review").mkdir(parents=True, exist_ok=True)
    (project_root / "publish").mkdir(parents=True, exist_ok=True)
    (project_root / "retros").mkdir(parents=True, exist_ok=True)
    (project_root / "sources").mkdir(parents=True, exist_ok=True)

    (project_root / "research" / "research-brief.md").write_text("# brief\n", encoding="utf-8")
    (project_root / "planning" / "topic-selection.json").write_text("{}", encoding="utf-8")
    (project_root / "angles" / "angle-brief.json").write_text("{}", encoding="utf-8")
    (project_root / "content" / "bilibili-midform-video.json").write_text(
        json.dumps({"platforms": ["bilibili"], "deliverable_type": "midlong-video"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "render-manifest.json").write_text(
        json.dumps({"output": {"video": "content/final-cut/v1.mp4"}}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "final-cut" / "v1.mp4").write_bytes(b"video")
    (project_root / "review" / "competitive-scorecard.json").write_text(
        json.dumps({"total_score": 30, "review_decision": "pass"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "review" / "review-gate.json").write_text(
        json.dumps({"approval_status": "pass", "safe_to_publish": True}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "review" / "assembly-qa-report.json").write_text(
        json.dumps({"status": "pass", "checks": {}}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "planning" / "cognitive-punch-gate.json").write_text(
        json.dumps({"status": "pass", "questions": {}}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "publish" / "publish-manifest-auto.json").write_text(
        json.dumps({"platform": "bilibili", "decision": "ready_for_live_publish"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "publish" / "publish-result-auto.json").write_text(
        json.dumps({"status": "submitted", "mode": "live"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "publish" / "release-record.json").write_text(
        json.dumps({"status": "live_submitted"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "retros" / "retro-plan.md").write_text("# retro\n", encoding="utf-8")
    (project_root / "retros" / "performance-summary.md").write_text("# perf\n", encoding="utf-8")
    (project_root / "retros" / "next-experiment-brief.json").write_text("{}", encoding="utf-8")
    (project_root / "sources" / "source-manifest.json").write_text(
        json.dumps({"source_manifest": [], "license_summary": {"approved_count": 0}}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "sources" / "source-shortlist.json").write_text(
        json.dumps({"results": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "sources" / "asset-ingest-manifest.json").write_text(
        json.dumps({"ingested_assets": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "sources" / "chapter-coverage-report.json").write_text(
        json.dumps({"overall_status": "pass", "chapters": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def make_note_package_with_gaps(project_root: Path) -> None:
    (project_root / "angles").mkdir(parents=True, exist_ok=True)
    (project_root / "content").mkdir(parents=True, exist_ok=True)
    (project_root / "publish").mkdir(parents=True, exist_ok=True)

    (project_root / "angles" / "angle-brief.json").write_text("{}", encoding="utf-8")
    (project_root / "content" / "xiaohongshu-note.json").write_text(
        json.dumps(
            {
                "platform": "xiaohongshu",
                "format": "note",
                "title": "test",
                "note": "test",
                "image_plan": [{"path": "assets/note/1.png"}],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "publish" / "publish-manifest-auto.json").write_text(
        json.dumps({"platform": "xiaohongshu", "content_type": "note", "decision": "dry_run_only"}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )


def test_audit_artifacts_builds_registry_and_marks_gaps(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "media-ops-orchestration"
        / "scripts"
        / "audit_artifacts.py"
    )
    media_ops_root = tmp_path / "media-ops"

    make_video_package(media_ops_root / "2026-03-27-video-package")
    make_note_package_with_gaps(media_ops_root / "2026-03-27-note-package")

    output_path = media_ops_root / "_registry" / "artifact-registry.json"
    summary_path = media_ops_root / "_registry" / "artifact-registry.md"
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

    assert output_path.exists()
    assert summary_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["package_count"] == 2

    by_id = {pkg["content_id"]: pkg for pkg in payload["packages"]}
    video_pkg = by_id["2026-03-27-video-package"]
    note_pkg = by_id["2026-03-27-note-package"]

    assert video_pkg["lifecycle_status"] == "retros_complete"
    assert video_pkg["content_type"] == "video"
    assert video_pkg["publish"]["result_status"] == "submitted"
    assert video_pkg["missing_required"] == []
    assert video_pkg["checks"]["source_manifest"]["present"] is True
    assert video_pkg["checks"]["source_shortlist"]["present"] is True
    assert video_pkg["checks"]["asset_ingest_manifest"]["present"] is True
    assert "workflow_quality_gate" in video_pkg["missing_recommended"]
    assert "upgrade_status_board" in video_pkg["missing_recommended"]
    assert "prelive_quality_summary" in video_pkg["missing_recommended"]
    assert "voice_performance_plan" in video_pkg["missing_recommended"]
    assert "subtitle_style_pack" in video_pkg["missing_recommended"]
    assert "audio_cue_sheet" in video_pkg["missing_recommended"]
    assert "subtitle_quality_report" in video_pkg["missing_recommended"]
    assert "scene_asset_plan" in video_pkg["missing_recommended"]
    assert "visual_evidence_map" in video_pkg["missing_recommended"]
    assert "generation_budget" in video_pkg["missing_recommended"]
    assert "visual_diversity_report" in video_pkg["missing_recommended"]
    assert "minimax_shot_plan" in video_pkg["missing_recommended"]
    assert "generation_ledger" in video_pkg["missing_recommended"]
    assert "scene_manifest" in video_pkg["missing_recommended"]
    assert "transition_plan" in video_pkg["missing_recommended"]
    assert "emphasis_fx_plan" in video_pkg["missing_recommended"]
    assert "scene_assembly_report" in video_pkg["missing_recommended"]
    assert "bilibili_hook_patterns" in video_pkg["missing_recommended"]
    assert "attention_structure_template" in video_pkg["missing_recommended"]
    assert "follow_conversion_hooks" in video_pkg["missing_recommended"]
    assert "opening_scorecard" in video_pkg["missing_recommended"]

    assert note_pkg["content_type"] == "note"
    assert note_pkg["lifecycle_status"] == "in_production"
    assert "review_gate" in note_pkg["missing_required"]
    assert payload["summary"]["packages_with_missing_required"] >= 1
