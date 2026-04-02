"""Tests for project-level media publish manifest helpers."""

import json
import subprocess
import sys
from pathlib import Path
import pytest


def run_command(command: list[str], workdir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=workdir, check=True, capture_output=True, text=True)


def make_publishable_media_package(tmp_path: Path) -> Path:
    project_root = tmp_path
    (project_root / "benchmarks").mkdir(parents=True, exist_ok=True)
    (project_root / "angles").mkdir(parents=True, exist_ok=True)
    (project_root / "content" / "final-cut").mkdir(parents=True, exist_ok=True)
    (project_root / "content" / "postproduction").mkdir(parents=True, exist_ok=True)
    (project_root / "publish").mkdir(parents=True, exist_ok=True)
    (project_root / "review").mkdir(parents=True, exist_ok=True)
    (project_root / "planning").mkdir(parents=True, exist_ok=True)
    (project_root / "sources").mkdir(parents=True, exist_ok=True)
    (project_root / "assets" / "final-cover").mkdir(parents=True, exist_ok=True)
    (project_root / "assets").mkdir(parents=True, exist_ok=True)

    (project_root / "benchmarks" / "bilibili-hook-patterns.json").write_text(
        json.dumps({"opening_patterns": [], "follow_conversion_patterns": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "angles" / "attention-structure-template.json").write_text(
        json.dumps({"lead_hook": "自动化发布标题"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "angles" / "follow-conversion-hooks.json").write_text(
        json.dumps({"follow_cta_variants": ["下一条继续拆"]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    (project_root / "content" / "bilibili-midform-video.json").write_text(
        json.dumps(
            {
                "platforms": ["bilibili"],
                "deliverable_type": "midlong-video",
                "title_variants": ["自动化发布标题"],
                "cover_text": "自动化封面文案",
                "video_description": "自动化发布简介",
                "pinned_comment": "自动化首评",
                "publish_metadata": {
                    "tags": ["AI工作流", "B站运营"],
                    "partition": "231",
                    "partition_name": "计算机技术",
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "render-manifest.json").write_text(
        json.dumps(
            {
                "output": {
                    "video": "content/final-cut/pilot-v3-auto-narrated.mp4",
                    "duration_seconds": 282.183,
                },
                "inputs": {
                    "voiceover_audio": "content/postproduction/voice.mp3",
                    "subtitles": "content/postproduction/subtitles.srt",
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "render-plan.json").write_text(
        json.dumps(
            {
                "assembly_strategy": "retime_existing_cut",
                "source_video": "content/final-cut/pilot-v2.mp4",
                "output_video": "content/final-cut/pilot-v3-auto-narrated.mp4",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "final-cut" / "pilot-v3-auto-narrated.mp4").write_bytes(b"final-cut")
    (project_root / "content" / "postproduction" / "voice.mp3").write_bytes(b"voice")
    (project_root / "content" / "postproduction" / "subtitles.srt").write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nhello\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "voice-performance-plan.json").write_text(
        json.dumps({"segments": [{"emotion": "focused"}]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "voiceover-segments.json").write_text(
        json.dumps([{"text": "hello", "emotion": "focused"}], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "voiceover-profile.json").write_text(
        json.dumps({"render_targets": {"voice_performance_plan": "content/postproduction/voice-performance-plan.json"}}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "subtitle-style-pack.json").write_text(
        json.dumps({"theme": "bilibili-midform-clean"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "audio-cue-sheet.json").write_text(
        json.dumps({"bgm_tracks": [], "sfx_cues": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "scene-manifest.json").write_text(
        json.dumps({"scenes": [{"scene_id": "scene-01"}]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "transition-plan.json").write_text(
        json.dumps({"transitions": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "emphasis-fx-plan.json").write_text(
        json.dumps({"scene_fx": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "assets" / "final-cover" / "cover-v1.png").write_bytes(b"cover")
    (project_root / "assets" / "scene-asset-plan.json").write_text(
        json.dumps({"chapters": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "assets" / "visual-evidence-map.json").write_text(
        json.dumps({"chapters": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "assets" / "generation-budget.json").write_text(
        json.dumps({"quota": {"daily_limit": 2}, "approved_generation_slots": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "assets" / "visual-diversity-report.json").write_text(
        json.dumps({"status": "pass"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "assets" / "minimax-shot-plan.json").write_text(
        json.dumps({"approved_slots": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "assets" / "generation-ledger.json").write_text(
        json.dumps({"entries": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "review" / "review-gate.json").write_text(
        json.dumps({"approval_status": "approved", "safe_to_publish": True}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "review" / "opening-scorecard.json").write_text(
        json.dumps({"decision": "pass"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "review" / "assembly-qa-report.json").write_text(
        json.dumps({"status": "pass", "checks": {}}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "review" / "subtitle-quality-report.json").write_text(
        json.dumps({"status": "pass"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "review" / "scene-assembly-report.json").write_text(
        json.dumps({"status": "pass"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "planning" / "cognitive-punch-gate.json").write_text(
        json.dumps({"status": "pass", "questions": {}}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "sources" / "chapter-coverage-report.json").write_text(
        json.dumps({"overall_status": "pass", "chapters": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "publish" / "publish-manifest-v2.json").write_text(
        json.dumps(
            {
                "account_name": "creator",
                "publish_mode": "immediate_live_publish",
                "metadata": {
                    "tags": ["旧标签"],
                    "partition": "231",
                    "partition_name": "计算机技术",
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return project_root


def make_rebuild_timeline_publishable_media_package(tmp_path: Path, *, auto_base_quality_status: str) -> Path:
    project_root = make_publishable_media_package(tmp_path)
    (project_root / "content" / "postproduction" / "render-plan.json").write_text(
        json.dumps(
            {
                "assembly_strategy": "rebuild_timeline",
                "source_video": "content/postproduction/auto-base-cut.mp4",
                "output_video": "content/final-cut/pilot-v3-auto-narrated.mp4",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "auto-base-cut-plan.json").write_text(
        json.dumps(
            {
                "quality": {
                    "status": auto_base_quality_status,
                    "warnings": [] if auto_base_quality_status == "pass" else ["image_ratio_high"],
                    "metrics": {
                        "image_slot_ratio": 0.74 if auto_base_quality_status != "pass" else 0.6,
                        "video_slot_ratio": 0.18 if auto_base_quality_status != "pass" else 0.3,
                    },
                }
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return project_root


def make_publishable_xiaohongshu_note_package(tmp_path: Path) -> Path:
    project_root = tmp_path
    (project_root / "content").mkdir(parents=True, exist_ok=True)
    (project_root / "assets" / "note").mkdir(parents=True, exist_ok=True)
    (project_root / "publish").mkdir(parents=True, exist_ok=True)
    (project_root / "review").mkdir(parents=True, exist_ok=True)

    (project_root / "assets" / "note" / "step-1.png").write_bytes(b"img-1")
    (project_root / "assets" / "note" / "step-2.png").write_bytes(b"img-2")
    (project_root / "content" / "xiaohongshu-note.json").write_text(
        json.dumps(
            {
                "platform": "xiaohongshu",
                "format": "note",
                "deliverable_type": "note",
                "title": "Agent流水线不等于内容质量",
                "note": "把研究、选题、制作、审校、发布拆开之后，内容稳定性提升明显。",
                "tags": ["AI工作流", "小红书运营"],
                "image_plan": [
                    {"path": "assets/note/step-1.png", "role": "开场图"},
                    {"path": "assets/note/step-2.png", "role": "流程图"},
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
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
    (project_root / "publish" / "publish-manifest-v2.json").write_text(
        json.dumps(
            {
                "platform": "xiaohongshu",
                "account_name": "xhs-creator",
                "publish_mode": "immediate_live_publish",
                "metadata": {
                    "title": "旧标题",
                    "note": "旧正文",
                    "tags": ["旧标签"],
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return project_root


def make_publishable_xiaohongshu_video_package(tmp_path: Path) -> Path:
    project_root = tmp_path
    (project_root / "content" / "final-cut").mkdir(parents=True, exist_ok=True)
    (project_root / "content" / "postproduction").mkdir(parents=True, exist_ok=True)
    (project_root / "publish").mkdir(parents=True, exist_ok=True)
    (project_root / "review").mkdir(parents=True, exist_ok=True)
    (project_root / "assets" / "final-cover").mkdir(parents=True, exist_ok=True)

    (project_root / "content" / "xiaohongshu-short-video.json").write_text(
        json.dumps(
            {
                "platform": "xiaohongshu",
                "deliverable_type": "short-video",
                "title_variants": ["发布前3道门禁，少一道都不要live"],
                "caption": "自动化发布真正危险的不是慢，而是没有门禁就直接 live。",
                "tag_suggestions": ["AI工作流", "自动化发布", "小红书运营"],
                "cover_text": "发布前3道门禁",
                "first_comment": "想要门禁清单模板，我下一条直接拆。",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "render-manifest.json").write_text(
        json.dumps(
            {
                "output": {
                    "video": "content/final-cut/xhs-pilot-v1.mp4",
                    "duration_seconds": 36.4,
                },
                "inputs": {
                    "voiceover_audio": "content/postproduction/voice.mp3",
                    "subtitles": "content/postproduction/subtitles.srt",
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "final-cut" / "xhs-pilot-v1.mp4").write_bytes(b"xhs-video")
    (project_root / "content" / "postproduction" / "voice.mp3").write_bytes(b"voice")
    (project_root / "content" / "postproduction" / "subtitles.srt").write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nhello\n",
        encoding="utf-8",
    )
    (project_root / "assets" / "final-cover" / "cover-v1.png").write_bytes(b"cover")
    (project_root / "review" / "review-gate.json").write_text(
        json.dumps({"approval_status": "pass", "safe_to_publish": True}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "review" / "assembly-qa-report.json").write_text(
        json.dumps({"status": "pass", "checks": {}}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "publish" / "publish-manifest-v2.json").write_text(
        json.dumps(
            {
                "platform": "xiaohongshu",
                "account_name": "xhs-video-creator",
                "publish_mode": "immediate_live_publish",
                "metadata": {
                    "title": "旧视频标题",
                    "description": "旧视频正文",
                    "tags": ["旧标签"],
                    "thumbnail_path": "assets/final-cover/cover-v0.png",
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return project_root


def test_build_publish_manifest_prefers_render_manifest_output(tmp_path: Path) -> None:
    """The publish manifest builder resolves the latest final cut from render-manifest."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "multi-platform-publishing"
        / "scripts"
        / "build_publish_manifest.py"
    )

    project_root = make_publishable_media_package(tmp_path / "media-package")
    result = run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
            "--account-name",
            "creator",
        ],
        repo_root,
    )

    summary = json.loads(result.stdout)
    assert summary["publish_manifest"].endswith("publish/publish-manifest-auto.json")

    manifest_path = project_root / "publish" / "publish-manifest-auto.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    release_record = json.loads((project_root / "publish" / "release-record.json").read_text(encoding="utf-8"))
    assert manifest["platform"] == "bilibili"
    assert manifest["account_name"] == "creator"
    assert manifest["approval_status"] == "approved"
    assert manifest["decision"] == "ready_for_live_publish"
    assert manifest["asset_paths"][0] == "content/final-cut/pilot-v3-auto-narrated.mp4"
    assert manifest["metadata"]["thumbnail_path"] == "assets/final-cover/cover-v1.png"
    assert manifest["cover_state"]["delivery_status"] == "pending_cli_upload"
    assert manifest["cover_state"]["thumbnail_upload_supported"] is True
    assert manifest["metadata"]["title"] == "自动化发布标题"
    assert manifest["metadata"]["tags"] == ["AI工作流", "B站运营"]
    assert manifest["render_context"]["render_manifest"] == "content/postproduction/render-manifest.json"
    assert manifest["render_context"]["final_cut"] == "content/final-cut/pilot-v3-auto-narrated.mp4"
    assert manifest["workflow_quality_gate"]["overall_status"] == "pass"
    assert manifest["prelive_quality_summary_path"] == "publish/prelive-quality-summary.json"
    assert release_record["status"] == "manifest_prepared"
    assert release_record["current_assets"]["upload_path"] == "content/final-cut/pilot-v3-auto-narrated.mp4"
    assert release_record["publish"]["cover_set"] is False
    assert release_record["publish"]["cover_delivery_status"] == "pending_cli_upload"
    prelive_summary = json.loads((project_root / "publish" / "prelive-quality-summary.json").read_text(encoding="utf-8"))
    assert prelive_summary["decision"] == "ready_for_live_publish"
    assert prelive_summary["workflow_quality_status"] == "pass"


def test_build_publish_manifest_prefers_final_cover_asset_over_stale_draft_thumbnail(tmp_path: Path) -> None:
    """A generated final-cover asset should override stale draft cover metadata."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "multi-platform-publishing"
        / "scripts"
        / "build_publish_manifest.py"
    )

    project_root = make_publishable_media_package(tmp_path / "media-package")
    draft_cover_path = project_root / "assets" / "bilibili-cover-draft.png"
    draft_cover_path.write_bytes(b"draft-cover")

    content_packet_path = project_root / "content" / "bilibili-midform-video.json"
    content_packet = json.loads(content_packet_path.read_text(encoding="utf-8"))
    content_packet["publish_metadata"]["thumbnail_path"] = "assets/bilibili-cover-draft.png"
    content_packet["publish_metadata"]["cover_asset"] = "assets/bilibili-cover-draft.png"
    content_packet_path.write_text(json.dumps(content_packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
            "--account-name",
            "creator",
        ],
        repo_root,
    )

    manifest = json.loads((project_root / "publish" / "publish-manifest-auto.json").read_text(encoding="utf-8"))
    assert manifest["asset_paths"][1] == "assets/final-cover/cover-v1.png"
    assert manifest["metadata"]["thumbnail_path"] == "assets/final-cover/cover-v1.png"


def test_build_publish_manifest_blocks_bilibili_live_refresh_to_avoid_duplicate_submission(tmp_path: Path) -> None:
    """Bilibili live refresh requests should be blocked until an in-place edit flow exists."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "multi-platform-publishing"
        / "scripts"
        / "build_publish_manifest.py"
    )

    project_root = make_publishable_media_package(tmp_path / "media-package")
    content_packet_path = project_root / "content" / "bilibili-midform-video.json"
    content_packet = json.loads(content_packet_path.read_text(encoding="utf-8"))
    content_packet["publish_metadata"]["publish_status"] = "ready_for_live_refresh"
    content_packet_path.write_text(json.dumps(content_packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    (project_root / "publish" / "release-record.json").write_text(
        json.dumps(
            {
                "status": "live_submitted",
                "publish": {
                    "review_status": "submitted",
                    "publish_identifiers": {},
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
            "--account-name",
            "creator",
        ],
        repo_root,
    )

    manifest = json.loads((project_root / "publish" / "publish-manifest-auto.json").read_text(encoding="utf-8"))
    assert manifest["decision"] == "dry_run_only"
    assert "bilibili_refresh_not_supported" in manifest["blocking_reasons"]


def test_build_publish_manifest_blocks_rebuild_timeline_when_auto_base_quality_not_passed(tmp_path: Path) -> None:
    """Rebuild-timeline videos should not become live-ready if auto base quality is below pass."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "multi-platform-publishing"
        / "scripts"
        / "build_publish_manifest.py"
    )

    project_root = make_rebuild_timeline_publishable_media_package(
        tmp_path / "rebuild-media-package",
        auto_base_quality_status="revise",
    )
    run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
            "--account-name",
            "creator",
        ],
        repo_root,
    )

    manifest = json.loads((project_root / "publish" / "publish-manifest-auto.json").read_text(encoding="utf-8"))
    assert manifest["decision"] == "dry_run_only"
    assert "auto_base_quality_not_passed" in manifest["blocking_reasons"]
    assert manifest["render_context"]["assembly_strategy"] == "rebuild_timeline"
    assert manifest["render_context"]["auto_base_quality_status"] == "revise"


def test_build_publish_manifest_blocks_when_workflow_quality_gate_not_passed(tmp_path: Path) -> None:
    """Workflow-level quality gate should block live readiness even when local publish fields look complete."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "multi-platform-publishing"
        / "scripts"
        / "build_publish_manifest.py"
    )

    project_root = make_publishable_media_package(tmp_path / "media-package")
    (project_root / "assets" / "visual-diversity-report.json").write_text(
        json.dumps({"status": "revise"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
            "--account-name",
            "creator",
        ],
        repo_root,
    )

    manifest = json.loads((project_root / "publish" / "publish-manifest-auto.json").read_text(encoding="utf-8"))
    prelive_summary = json.loads((project_root / "publish" / "prelive-quality-summary.json").read_text(encoding="utf-8"))
    assert manifest["decision"] == "dry_run_only"
    assert "workflow_quality_gate_not_passed" in manifest["blocking_reasons"]
    assert manifest["workflow_quality_gate"]["overall_status"] == "revise"
    assert prelive_summary["workflow_quality_status"] == "revise"


def test_build_publish_manifest_supports_content_id_resolution(tmp_path: Path) -> None:
    """The publish manifest builder can resolve content packages via media-ops root plus content id."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "multi-platform-publishing"
        / "scripts"
        / "build_publish_manifest.py"
    )

    media_ops_root = tmp_path / "media-ops"
    project_root = make_publishable_media_package(media_ops_root / "pilot-content")
    run_command(
        [
            sys.executable,
            str(script_path),
            "--media-ops-root",
            str(media_ops_root),
            "--content-id",
            "pilot-content",
            "--account-name",
            "creator",
        ],
        repo_root,
    )

    manifest_path = project_root / "publish" / "publish-manifest-auto.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["content_id"] == "pilot-content"


def test_build_publish_manifest_uses_account_name_from_publish_metadata(tmp_path: Path) -> None:
    """Fresh packages can derive account name directly from content packet publish metadata."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "multi-platform-publishing"
        / "scripts"
        / "build_publish_manifest.py"
    )

    project_root = make_publishable_media_package(tmp_path / "fresh-media-package")
    (project_root / "publish" / "publish-manifest-v2.json").unlink()
    payload = json.loads((project_root / "content" / "bilibili-midform-video.json").read_text(encoding="utf-8"))
    payload["publish_metadata"]["account_name"] = "creator-from-packet"
    (project_root / "content" / "bilibili-midform-video.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
            "--publish-mode",
            "immediate_live_publish",
        ],
        repo_root,
    )

    manifest = json.loads((project_root / "publish" / "publish-manifest-auto.json").read_text(encoding="utf-8"))
    assert manifest["account_name"] == "creator-from-packet"
    assert manifest["decision"] == "ready_for_live_publish"


def test_build_publish_manifest_supports_xiaohongshu_note_without_render_manifest(tmp_path: Path) -> None:
    """The publish manifest builder supports Xiaohongshu note packages without a render manifest."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "multi-platform-publishing"
        / "scripts"
        / "build_publish_manifest.py"
    )

    project_root = make_publishable_xiaohongshu_note_package(tmp_path / "xhs-note-package")
    run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
            "--account-name",
            "xhs-creator",
        ],
        repo_root,
    )

    manifest_path = project_root / "publish" / "publish-manifest-auto.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["platform"] == "xiaohongshu"
    assert manifest["content_type"] == "note"
    assert manifest["decision"] == "ready_for_live_publish"
    assert manifest["asset_paths"] == ["assets/note/step-1.png", "assets/note/step-2.png"]
    assert manifest["metadata"]["title"] == "Agent流水线不等于内容质量"
    assert manifest["metadata"]["note"].startswith("把研究、选题")
    assert manifest["metadata"]["tags"] == ["AI工作流", "小红书运营"]


def test_build_publish_manifest_supports_xiaohongshu_short_video(tmp_path: Path) -> None:
    """The publish manifest builder supports Xiaohongshu short-video packages."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "multi-platform-publishing"
        / "scripts"
        / "build_publish_manifest.py"
    )

    project_root = make_publishable_xiaohongshu_video_package(tmp_path / "xhs-video-package")
    run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
            "--account-name",
            "xhs-video-creator",
        ],
        repo_root,
    )

    manifest_path = project_root / "publish" / "publish-manifest-auto.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["platform"] == "xiaohongshu"
    assert manifest["content_type"] == "video"
    assert manifest["decision"] == "ready_for_live_publish"
    assert manifest["asset_paths"][0] == "content/final-cut/xhs-pilot-v1.mp4"
    assert manifest["asset_paths"][1] == "assets/final-cover/cover-v1.png"
    assert manifest["metadata"]["title"] == "发布前3道门禁，少一道都不要live"
    assert manifest["metadata"]["description"].startswith("自动化发布真正危险的不是慢")
    assert manifest["metadata"]["tags"] == ["AI工作流", "自动化发布", "小红书运营"]
    assert manifest["metadata"]["thumbnail_path"] == "assets/final-cover/cover-v1.png"


def test_run_publish_workflow_writes_dry_run_result(tmp_path: Path) -> None:
    """The publish runner defaults to dry-run and writes a structured result file."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "multi-platform-publishing"
        / "scripts"
        / "run_publish_workflow.py"
    )

    project_root = make_publishable_media_package(tmp_path / "media-package")
    result = run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
            "--account-name",
            "creator",
            "--result-output",
            "publish/publish-result-auto.json",
        ],
        repo_root,
    )

    summary = json.loads(result.stdout)
    assert summary["mode"] == "dry_run"
    assert summary["publish_result"].endswith("publish/publish-result-auto.json")

    result_path = project_root / "publish" / "publish-result-auto.json"
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    release_record = json.loads((project_root / "publish" / "release-record.json").read_text(encoding="utf-8"))
    assert payload["mode"] == "dry_run"
    assert payload["status"] == "not_executed"
    assert payload["platform"] == "bilibili"
    assert payload["assets"]["video"] == "content/final-cut/pilot-v3-auto-narrated.mp4"
    assert payload["cover_state"]["delivery_status"] == "pending_cli_upload"
    assert payload["command_preview"][0] == "python3"
    assert payload["command_preview"][1].endswith("extensions/skills/bilibili-upload/scripts/upload_bilibili_video.py")
    assert "--thumbnail" in payload["command_preview"]
    assert release_record["status"] == "dry_run_ready"
    assert release_record["publish"]["cover_set"] is False
    assert release_record["publish"]["latest_result_path"] == "publish/publish-result-auto.json"


def test_run_publish_workflow_supports_xiaohongshu_note_dry_run(tmp_path: Path) -> None:
    """The publish runner can generate dry-run output for Xiaohongshu notes."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "multi-platform-publishing"
        / "scripts"
        / "run_publish_workflow.py"
    )

    project_root = make_publishable_xiaohongshu_note_package(tmp_path / "xhs-note-package")
    run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
            "--account-name",
            "xhs-creator",
            "--result-output",
            "publish/publish-result-auto.json",
        ],
        repo_root,
    )

    result_path = project_root / "publish" / "publish-result-auto.json"
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["mode"] == "dry_run"
    assert payload["status"] == "not_executed"
    assert payload["platform"] == "xiaohongshu"
    assert payload["command_preview"][:3] == ["sau", "xiaohongshu", "upload-note"]
    assert payload["assets"]["images"] == ["assets/note/step-1.png", "assets/note/step-2.png"]


def test_run_publish_workflow_supports_xiaohongshu_short_video_dry_run(tmp_path: Path) -> None:
    """The publish runner can generate dry-run output for Xiaohongshu short videos."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "multi-platform-publishing"
        / "scripts"
        / "run_publish_workflow.py"
    )

    project_root = make_publishable_xiaohongshu_video_package(tmp_path / "xhs-video-package")
    run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
            "--account-name",
            "xhs-video-creator",
            "--result-output",
            "publish/publish-result-auto.json",
        ],
        repo_root,
    )

    result_path = project_root / "publish" / "publish-result-auto.json"
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["mode"] == "dry_run"
    assert payload["status"] == "not_executed"
    assert payload["platform"] == "xiaohongshu"
    assert payload["assets"]["video"] == "content/final-cut/xhs-pilot-v1.mp4"
    assert payload["assets"]["cover"] == "assets/final-cover/cover-v1.png"
    assert payload["command_preview"][:3] == ["sau", "xiaohongshu", "upload-video"]
    assert "--thumbnail" in payload["command_preview"]


def test_run_publish_workflow_blocks_live_when_manifest_not_ready(tmp_path: Path) -> None:
    """The publish runner must refuse live execution if the manifest is not publishable."""
    repo_root = Path(__file__).resolve().parents[4]
    build_script = (
        repo_root
        / "extensions"
        / "skills"
        / "multi-platform-publishing"
        / "scripts"
        / "build_publish_manifest.py"
    )
    run_script = (
        repo_root
        / "extensions"
        / "skills"
        / "multi-platform-publishing"
        / "scripts"
        / "run_publish_workflow.py"
    )

    project_root = make_publishable_media_package(tmp_path / "media-package")
    run_command(
        [
            sys.executable,
            str(build_script),
            "--project-root",
            str(project_root),
            "--account-name",
            "creator",
        ],
        repo_root,
    )

    manifest_path = project_root / "publish" / "publish-manifest-auto.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["approval_status"] = "revise"
    manifest["decision"] = "dry_run_only"
    manifest["blocking_reasons"] = ["approval_not_granted"]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(subprocess.CalledProcessError):
        run_command(
            [
                sys.executable,
                str(run_script),
                "--project-root",
                str(project_root),
                "--account-name",
                "creator",
                "--live",
            ],
            repo_root,
        )


def test_run_publish_workflow_blocks_live_for_xiaohongshu_note_when_manifest_not_ready(tmp_path: Path) -> None:
    """The publish runner refuses Xiaohongshu live publishing when manifest decision is not ready."""
    repo_root = Path(__file__).resolve().parents[4]
    run_script = (
        repo_root
        / "extensions"
        / "skills"
        / "multi-platform-publishing"
        / "scripts"
        / "run_publish_workflow.py"
    )

    project_root = make_publishable_xiaohongshu_note_package(tmp_path / "xhs-note-package")
    manifest_path = project_root / "publish" / "publish-manifest-auto.json"
    manifest_path.write_text(
        json.dumps(
            {
                "platform": "xiaohongshu",
                "content_type": "note",
                "content_id": "xhs-note-package",
                "version": "v1",
                "account_name": "xhs-creator",
                "account_status": "pending_check",
                "asset_paths": ["assets/note/step-1.png"],
                "metadata": {
                    "title": "Agent流水线不等于内容质量",
                    "note": "正文",
                    "tags": ["AI工作流"],
                },
                "approval_status": "revise",
                "publish_mode": "immediate_live_publish",
                "metadata_complete": True,
                "decision": "dry_run_only",
                "blocking_reasons": ["approval_not_granted"],
                "notes": [],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(subprocess.CalledProcessError):
        run_command(
            [
                sys.executable,
                str(run_script),
                "--project-root",
                str(project_root),
                "--account-name",
                "xhs-creator",
                "--live",
            ],
            repo_root,
        )


def test_run_publish_workflow_blocks_live_for_xiaohongshu_short_video_when_manifest_not_ready(tmp_path: Path) -> None:
    """The publish runner refuses Xiaohongshu short-video live publishing when manifest decision is not ready."""
    repo_root = Path(__file__).resolve().parents[4]
    run_script = (
        repo_root
        / "extensions"
        / "skills"
        / "multi-platform-publishing"
        / "scripts"
        / "run_publish_workflow.py"
    )

    project_root = make_publishable_xiaohongshu_video_package(tmp_path / "xhs-video-package")
    manifest_path = project_root / "publish" / "publish-manifest-auto.json"
    manifest_path.write_text(
        json.dumps(
            {
                "platform": "xiaohongshu",
                "content_type": "video",
                "content_id": "xhs-video-package",
                "version": "v1",
                "account_name": "xhs-video-creator",
                "account_status": "pending_check",
                "asset_paths": ["content/final-cut/xhs-pilot-v1.mp4", "assets/final-cover/cover-v1.png"],
                "metadata": {
                    "title": "发布前3道门禁，少一道都不要live",
                    "description": "视频描述",
                    "tags": ["AI工作流"],
                    "thumbnail_path": "assets/final-cover/cover-v1.png",
                },
                "approval_status": "revise",
                "publish_mode": "immediate_live_publish",
                "metadata_complete": True,
                "decision": "dry_run_only",
                "blocking_reasons": ["approval_not_granted"],
                "notes": [],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(subprocess.CalledProcessError):
        run_command(
            [
                sys.executable,
                str(run_script),
                "--project-root",
                str(project_root),
                "--account-name",
                "xhs-video-creator",
                "--live",
            ],
            repo_root,
        )


def test_build_live_execution_plan_for_xiaohongshu_note(tmp_path: Path) -> None:
    """The live execution planner builds a ready-to-run plan for Xiaohongshu notes."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "multi-platform-publishing"
        / "scripts"
        / "build_live_execution_plan.py"
    )

    project_root = make_publishable_xiaohongshu_note_package(tmp_path / "xhs-note-package")
    run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
            "--account-name",
            "xhs-creator",
        ],
        repo_root,
    )

    plan_path = project_root / "publish" / "live-execution-plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["platform"] == "xiaohongshu"
    assert plan["content_type"] == "note"
    assert plan["live_ready"] is True
    assert plan["decision"] == "ready_for_live_publish"
    assert plan["manifest_path"] == "publish/publish-manifest-prelive.json"
    assert plan["account_check_command"][:3] == ["sau", "xiaohongshu", "check"]
    assert plan["publish_command_preview"][:3] == ["sau", "xiaohongshu", "upload-note"]
    assert "--live" in plan["workflow_live_command"]


def test_build_live_execution_plan_can_resolve_account_without_flag(tmp_path: Path) -> None:
    """The live execution planner can reuse the account resolved from package metadata/history."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "multi-platform-publishing"
        / "scripts"
        / "build_live_execution_plan.py"
    )

    project_root = make_publishable_xiaohongshu_note_package(tmp_path / "xhs-note-package-no-flag")
    run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
        ],
        repo_root,
    )

    plan_path = project_root / "publish" / "live-execution-plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["account_name"] == "xhs-creator"
    assert plan["live_ready"] is True
    assert "--live" in plan["workflow_live_command"]


def test_build_live_execution_plan_flags_blocked_xiaohongshu_video(tmp_path: Path) -> None:
    """The live execution planner should flag Xiaohongshu videos blocked by review gate."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "multi-platform-publishing"
        / "scripts"
        / "build_live_execution_plan.py"
    )

    project_root = make_publishable_xiaohongshu_video_package(tmp_path / "xhs-video-package")
    (project_root / "review" / "review-gate.json").write_text(
        json.dumps(
            {
                "approval_status": "revise",
                "safe_to_publish": False,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
            "--account-name",
            "xhs-video-creator",
        ],
        repo_root,
    )

    plan_path = project_root / "publish" / "live-execution-plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["platform"] == "xiaohongshu"
    assert plan["content_type"] == "video"
    assert plan["live_ready"] is False
    assert plan["decision"] == "dry_run_only"
    assert "review_gate_not_safe" in plan["blocking_reasons"]
    assert plan["publish_command_preview"][:3] == ["sau", "xiaohongshu", "upload-video"]
