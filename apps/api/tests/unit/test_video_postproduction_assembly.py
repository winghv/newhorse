"""Tests for the deterministic narrated-cut renderer."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def run_command(command: list[str], workdir: Path) -> None:
    subprocess.run(command, cwd=workdir, check=True, capture_output=True, text=True)


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg/ffprobe required")
def test_render_narrated_cut_outputs_manifest_and_verification(tmp_path: Path) -> None:
    """The render helper retimes the source cut and emits structured verification artifacts."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "render_narrated_cut.py"
    )

    source_video = tmp_path / "source.mp4"
    voiceover_audio = tmp_path / "voice.mp3"
    subtitle_file = tmp_path / "subtitles.srt"
    output_video = tmp_path / "final.mp4"
    manifest_file = tmp_path / "render-manifest.json"
    verification_file = tmp_path / "render-verification.md"
    plan_file = tmp_path / "render-plan.json"

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
        tmp_path,
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
        tmp_path,
    )

    subtitle_file.write_text(
        "1\n00:00:00,000 --> 00:00:00,900\nNarrated test cut.\n",
        encoding="utf-8",
    )

    plan_file.write_text(
        json.dumps(
            {
                "workspace_root": ".",
                "source_video": "source.mp4",
                "voiceover_audio": "voice.mp3",
                "subtitles": "subtitles.srt",
                "output_video": "final.mp4",
                "render_manifest_output": "render-manifest.json",
                "verification_output": "render-verification.md",
                "assembly_strategy": "retime_existing_cut",
                "mix": {
                    "retain_original_audio": False,
                    "voiceover_gain_db": 0,
                },
                "retime": {
                    "mode": "auto_match_voiceover",
                    "max_speedup": 3.0,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    run_command([sys.executable, str(script_path), "--plan", str(plan_file)], tmp_path)

    assert output_video.exists()
    assert manifest_file.exists()
    assert verification_file.exists()

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert manifest["assembly_strategy"] == "retime_existing_cut"
    assert manifest["subtitles"]["burned_in"] is True
    assert manifest["mix"]["retain_original_audio"] is False
    assert 0.45 <= manifest["retime"]["video_pts_factor"] <= 0.55
    assert manifest["output"]["duration_alignment_error_seconds"] <= 0.15
    assert manifest["output"]["duration_seconds"] == pytest.approx(1.0, abs=0.15)
    assert manifest["output"]["video_codec"] == "h264"
    assert manifest["output"]["audio_codec"] == "aac"

    verification = verification_file.read_text(encoding="utf-8")
    assert "Render Verification" in verification
    assert "retime_existing_cut" in verification
