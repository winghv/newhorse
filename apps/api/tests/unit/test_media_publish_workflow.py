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
    (project_root / "content" / "final-cut").mkdir(parents=True, exist_ok=True)
    (project_root / "content" / "postproduction").mkdir(parents=True, exist_ok=True)
    (project_root / "publish").mkdir(parents=True, exist_ok=True)
    (project_root / "review").mkdir(parents=True, exist_ok=True)
    (project_root / "assets" / "final-cover").mkdir(parents=True, exist_ok=True)

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
    (project_root / "content" / "final-cut" / "pilot-v3-auto-narrated.mp4").write_bytes(b"final-cut")
    (project_root / "content" / "postproduction" / "voice.mp3").write_bytes(b"voice")
    (project_root / "content" / "postproduction" / "subtitles.srt").write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nhello\n",
        encoding="utf-8",
    )
    (project_root / "assets" / "final-cover" / "cover-v1.png").write_bytes(b"cover")
    (project_root / "review" / "review-gate.json").write_text(
        json.dumps({"approval_status": "approved", "safe_to_publish": True}, ensure_ascii=False, indent=2) + "\n",
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
    assert manifest["platform"] == "bilibili"
    assert manifest["account_name"] == "creator"
    assert manifest["approval_status"] == "approved"
    assert manifest["decision"] == "ready_for_live_publish"
    assert manifest["asset_paths"][0] == "content/final-cut/pilot-v3-auto-narrated.mp4"
    assert manifest["metadata"]["thumbnail_path"] == "assets/final-cover/cover-v1.png"
    assert manifest["metadata"]["title"] == "自动化发布标题"
    assert manifest["metadata"]["tags"] == ["AI工作流", "B站运营"]
    assert manifest["render_context"]["render_manifest"] == "content/postproduction/render-manifest.json"
    assert manifest["render_context"]["final_cut"] == "content/final-cut/pilot-v3-auto-narrated.mp4"


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
    assert payload["mode"] == "dry_run"
    assert payload["status"] == "not_executed"
    assert payload["platform"] == "bilibili"
    assert payload["assets"]["video"] == "content/final-cut/pilot-v3-auto-narrated.mp4"
    assert payload["command_preview"][:3] == ["sau", "bilibili", "upload-video"]


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
