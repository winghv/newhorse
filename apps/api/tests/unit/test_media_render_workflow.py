"""Tests for project-level media render workflow helpers."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def run_command(command: list[str], workdir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=workdir, check=True, capture_output=True, text=True)


def make_media_package(tmp_path: Path) -> Path:
    project_root = tmp_path
    (project_root / "content" / "final-cut").mkdir(parents=True, exist_ok=True)
    (project_root / "content" / "postproduction" / "minimax-output").mkdir(parents=True, exist_ok=True)
    (project_root / "review").mkdir(parents=True, exist_ok=True)

    voiceover_profile = {
        "platform": "bilibili",
        "content_id": "pilot",
        "render_targets": {
            "voiceover_audio": "content/postproduction/minimax-output/voice.mp3",
            "subtitle_draft": "content/postproduction/subtitles.srt",
        },
        "mix_defaults": {
            "bgm_target_db": -30,
            "ducking_target_db": -22,
            "narration_lufs_target": -16,
        },
    }
    (project_root / "content" / "postproduction" / "voiceover-profile.json").write_text(
        json.dumps(voiceover_profile, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "mix-notes.md").write_text(
        "# Mix Notes\n\n- test fixture\n",
        encoding="utf-8",
    )
    (project_root / "content" / "bilibili-midform-video.json").write_text(
        json.dumps({"platforms": ["bilibili"], "deliverable_type": "midlong-video"}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )

    return project_root


def test_build_render_plan_infers_paths_and_output_version(tmp_path: Path) -> None:
    """The builder infers source assets from a media package and derives a narrated output path."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "build_render_plan.py"
    )

    project_root = make_media_package(tmp_path / "media-package")
    (project_root / "content" / "final-cut" / "pilot-v1.mp4").write_bytes(b"rough-cut")
    (project_root / "content" / "final-cut" / "pilot-v2-narrated.mp4").write_bytes(b"existing-final")
    (project_root / "content" / "postproduction" / "minimax-output" / "voice.mp3").write_bytes(b"voice")
    (project_root / "content" / "postproduction" / "subtitles.srt").write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nhello\n",
        encoding="utf-8",
    )

    run_command([sys.executable, str(script_path), "--project-root", str(project_root)], repo_root)

    plan_path = project_root / "content" / "postproduction" / "render-plan.json"
    assert plan_path.exists()

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["assembly_strategy"] == "retime_existing_cut"
    assert plan["source_video"] == "content/final-cut/pilot-v1.mp4"
    assert plan["voiceover_audio"] == "content/postproduction/minimax-output/voice.mp3"
    assert plan["subtitles"] == "content/postproduction/subtitles.srt"
    assert plan["output_video"] == "content/final-cut/pilot-v2-narrated.mp4"
    assert plan["render_manifest_output"] == "content/postproduction/render-manifest.json"
    assert plan["verification_output"] == "review/render-verification-auto.md"
    assert plan["mix"]["retain_original_audio"] is True
    assert plan["mix"]["original_audio_gain_db"] == -30


def test_build_render_plan_supports_content_id_resolution(tmp_path: Path) -> None:
    """The builder can resolve a content package from media-ops root plus content id."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "build_render_plan.py"
    )

    media_ops_root = tmp_path / "media-ops"
    project_root = make_media_package(media_ops_root / "pilot-content")
    (project_root / "content" / "final-cut" / "pilot-v1.mp4").write_bytes(b"rough-cut")
    (project_root / "content" / "postproduction" / "minimax-output" / "voice.mp3").write_bytes(b"voice")
    (project_root / "content" / "postproduction" / "subtitles.srt").write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nhello\n",
        encoding="utf-8",
    )

    run_command(
        [
            sys.executable,
            str(script_path),
            "--content-id",
            "pilot-content",
            "--media-ops-root",
            str(media_ops_root),
        ],
        repo_root,
    )

    plan_path = project_root / "content" / "postproduction" / "render-plan.json"
    assert plan_path.exists()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["content_id"] == "pilot"
    assert plan["source_video"] == "content/final-cut/pilot-v1.mp4"


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg/ffprobe required")
def test_run_render_workflow_builds_plan_and_final_cut(tmp_path: Path) -> None:
    """The workflow runner writes the plan and renders the narrated cut in one step."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "run_render_workflow.py"
    )

    project_root = make_media_package(tmp_path / "media-package")
    source_video = project_root / "content" / "final-cut" / "pilot-v1.mp4"
    voiceover_audio = project_root / "content" / "postproduction" / "minimax-output" / "voice.mp3"
    subtitles = project_root / "content" / "postproduction" / "subtitles.srt"

    run_command(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=320x240:rate=30",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=330:sample_rate=48000",
            "-t",
            "2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(source_video),
        ],
        repo_root,
    )
    run_command(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=880:sample_rate=48000",
            "-t",
            "1",
            "-c:a",
            "mp3",
            str(voiceover_audio),
        ],
        repo_root,
    )
    subtitles.write_text(
        "1\n00:00:00,000 --> 00:00:00,900\nNarrated workflow test.\n",
        encoding="utf-8",
    )

    result = run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
            "--no-retain-original-audio",
        ],
        repo_root,
    )

    summary = json.loads(result.stdout)
    assert summary["project_root"] == str(project_root.resolve())
    assert summary["render_plan"].endswith("content/postproduction/render-plan.json")
    assert summary["final_cut"].endswith("content/final-cut/pilot-v2-narrated.mp4")

    assert (project_root / "content" / "postproduction" / "render-plan.json").exists()
    assert (project_root / "content" / "postproduction" / "render-manifest.json").exists()
    assert (project_root / "review" / "render-verification-auto.md").exists()
    assert (project_root / "content" / "final-cut" / "pilot-v2-narrated.mp4").exists()
