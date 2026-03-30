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


def make_voice_audio_with_pauses(path: Path, *, workdir: Path) -> None:
    run_command(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=880:sample_rate=48000:duration=0.8",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=48000:cl=mono:d=0.4",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=880:sample_rate=48000:duration=0.8",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=48000:cl=mono:d=0.4",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=880:sample_rate=48000:duration=0.8",
            "-filter_complex",
            "[0:a][1:a][2:a][3:a][4:a]concat=n=5:v=0:a=1[out]",
            "-map",
            "[out]",
            "-c:a",
            "mp3",
            str(path),
        ],
        workdir,
    )


def make_audio_tone(path: Path, *, duration_seconds: float, frequency: int, workdir: Path) -> None:
    run_command(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={frequency}:sample_rate=48000",
            "-t",
            str(duration_seconds),
            "-c:a",
            "mp3",
            str(path),
        ],
        workdir,
    )


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
    qa_report_file = tmp_path / "assembly-qa-report.json"
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
                "qa_report_output": "assembly-qa-report.json",
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
    assert qa_report_file.exists()

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert manifest["assembly_strategy"] == "retime_existing_cut"
    assert manifest["subtitles"]["burned_in"] is True
    assert manifest["mix"]["retain_original_audio"] is False
    assert 0.45 <= manifest["retime"]["video_pts_factor"] <= 0.55
    assert manifest["output"]["duration_alignment_error_seconds"] <= 0.15
    assert manifest["output"]["duration_seconds"] == pytest.approx(1.0, abs=0.15)
    assert manifest["output"]["video_codec"] == "h264"
    assert manifest["output"]["audio_codec"] == "aac"
    assert manifest["qa"]["status"] == "pass"
    assert manifest["qa"]["report"] == "assembly-qa-report.json"

    qa_report = json.loads(qa_report_file.read_text(encoding="utf-8"))
    assert qa_report["status"] == "pass"
    assert qa_report["checks"]["freeze_detection"]["freeze_segments"] == []

    verification = verification_file.read_text(encoding="utf-8")
    assert "Render Verification" in verification
    assert "retime_existing_cut" in verification
    assert "qa status" in verification


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg/ffprobe required")
def test_render_narrated_cut_reports_subtitle_alignment_pass(tmp_path: Path) -> None:
    """Subtitle QA should pass when cue boundaries follow real voice pauses."""
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
    qa_report_file = tmp_path / "assembly-qa-report.json"
    plan_file = tmp_path / "render-plan.json"

    run_command(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=320x240:rate=30",
            "-t",
            "4",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(source_video),
        ],
        tmp_path,
    )
    make_voice_audio_with_pauses(voiceover_audio, workdir=tmp_path)

    subtitle_file.write_text(
        "\n".join(
            [
                "1",
                "00:00:00,000 --> 00:00:01,000",
                "第一句先把问题说透。",
                "",
                "2",
                "00:00:01,000 --> 00:00:02,200",
                "第二句补一个具体例子。",
                "",
                "3",
                "00:00:02,200 --> 00:00:03,200",
                "第三句给出下一步动作。",
                "",
            ]
        ),
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
                "qa_report_output": "assembly-qa-report.json",
                "assembly_strategy": "retime_existing_cut",
                "mix": {
                    "retain_original_audio": False,
                    "voiceover_gain_db": 0,
                },
                "retime": {
                    "mode": "auto_match_voiceover",
                    "max_speedup": 3.0,
                },
                "qa": {
                    "subtitle_alignment_noise_db": "-35dB",
                    "subtitle_alignment_min_silence_seconds": 0.12,
                    "subtitle_alignment_max_boundary_drift_seconds": 0.45,
                    "subtitle_alignment_min_matched_ratio": 0.72,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    run_command([sys.executable, str(script_path), "--plan", str(plan_file)], tmp_path)

    qa_report = json.loads(qa_report_file.read_text(encoding="utf-8"))
    assert qa_report["checks"]["subtitle_alignment"]["status"] == "pass"
    assert qa_report["checks"]["subtitle_alignment"]["matched_boundary_ratio"] >= 0.99


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg/ffprobe required")
def test_render_narrated_cut_applies_sound_design_bed(tmp_path: Path) -> None:
    """Render should mix planned BGM/SFX and report sound-design status."""
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
    bgm_audio = tmp_path / "bgm.mp3"
    subtitle_file = tmp_path / "subtitles.srt"
    output_video = tmp_path / "final.mp4"
    manifest_file = tmp_path / "render-manifest.json"
    verification_file = tmp_path / "render-verification.md"
    qa_report_file = tmp_path / "assembly-qa-report.json"
    plan_file = tmp_path / "render-plan.json"

    run_command(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=320x240:rate=30",
            "-t",
            "4",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(source_video),
        ],
        tmp_path,
    )
    make_audio_tone(voiceover_audio, duration_seconds=4.0, frequency=880, workdir=tmp_path)
    make_audio_tone(bgm_audio, duration_seconds=4.0, frequency=220, workdir=tmp_path)

    subtitle_file.write_text(
        "1\n00:00:00,000 --> 00:00:03,500\n声音设计测试。\n",
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
                "qa_report_output": "assembly-qa-report.json",
                "assembly_strategy": "retime_existing_cut",
                "mix": {
                    "retain_original_audio": False,
                    "voiceover_gain_db": 0,
                    "bg_sidechain_ducking": True,
                    "bgm_tracks": [
                        {
                            "path": "bgm.mp3",
                            "start_seconds": 0.0,
                            "end_seconds": 2.5,
                            "gain_db": -24,
                            "loop": True,
                            "fade_in_seconds": 0.1,
                            "fade_out_seconds": 0.4,
                        }
                    ],
                    "sfx_cues": [
                        {
                            "preset": "impact_hit",
                            "label": "hook_statement",
                            "start_seconds": 0.8,
                            "gain_db": -14,
                        }
                    ],
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

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    qa_report = json.loads(qa_report_file.read_text(encoding="utf-8"))
    verification = verification_file.read_text(encoding="utf-8")

    assert manifest["mix"]["sound_bed_applied"] is True
    assert manifest["mix"]["bgm_track_count"] == 1
    assert manifest["mix"]["sfx_cue_count"] == 1
    assert manifest["mix"]["bg_sidechain_ducking"] is True
    assert qa_report["checks"]["sound_design"]["status"] == "pass"
    assert qa_report["checks"]["sound_design"]["requested_bgm_track_count"] == 1
    assert qa_report["checks"]["sound_design"]["requested_sfx_cue_count"] == 1
    assert "sound design status" in verification
    assert qa_report["status"] == "pass"
    verification = verification_file.read_text(encoding="utf-8")
    assert "subtitle alignment status" in verification
