"""Tests for project-level media render workflow helpers."""

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional
from importlib.machinery import SourceFileLoader

import pytest


FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def run_command(command: list[str], workdir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=workdir, check=True, capture_output=True, text=True)


def make_media_package(tmp_path: Path, *, assembly_strategy: Optional[str] = None) -> Path:
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
    content_packet = {"platforms": ["bilibili"], "deliverable_type": "midlong-video"}
    if assembly_strategy is not None:
        content_packet["assembly_strategy"] = assembly_strategy
    (project_root / "content" / "bilibili-midform-video.json").write_text(
        json.dumps(content_packet, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return project_root


def write_voiceover_segments(project_root: Path, segments: list[str]) -> None:
    payload = [{"text": text, "voice_id": "narrator", "emotion": ""} for text in segments]
    (project_root / "content" / "postproduction" / "voiceover-segments.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def make_audio(path: Path, *, duration_seconds: float, frequency: int, workdir: Path) -> None:
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


def make_audio_with_silences(path: Path, *, speech_frequency: int, workdir: Path) -> None:
    run_command(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={speech_frequency}:sample_rate=48000:duration=0.8",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=48000:cl=mono:d=0.4",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={speech_frequency}:sample_rate=48000:duration=0.8",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=48000:cl=mono:d=0.4",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={speech_frequency}:sample_rate=48000:duration=0.8",
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


def make_crossfaded_audio(output_path: Path, first_path: Path, second_path: Path, *, crossfade_seconds: float, workdir: Path) -> None:
    run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(first_path),
            "-i",
            str(second_path),
            "-filter_complex",
            f"[0:a][1:a]acrossfade=d={crossfade_seconds}[out]",
            "-map",
            "[out]",
            "-c:a",
            "mp3",
            str(output_path),
        ],
        workdir,
    )


def write_fake_tts_cli(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'text=""',
                'output=""',
                'if [[ $# -gt 0 && \"$1\" == \"tts\" ]]; then',
                "  shift",
                "fi",
                'if [[ $# -gt 0 ]]; then',
                '  text=\"$1\"',
                "  shift",
                "fi",
                'while [[ $# -gt 0 ]]; do',
                '  case \"$1\" in',
                "    -o|--output) output=\"$2\"; shift 2 ;;",
                "    *) shift ;;",
                "  esac",
                "done",
                'mkdir -p \"$(dirname \"$output\")\"',
                'ffmpeg -y -f lavfi -i \"sine=frequency=660:sample_rate=32000\" -t 1.0 -c:a mp3 \"$output\" >/dev/null 2>&1',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def write_pitch_validating_tts_cli(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'output=""',
                'pitch=""',
                'text=""',
                'if [[ $# -gt 0 && \"$1\" == \"tts\" ]]; then',
                "  shift",
                "fi",
                'if [[ $# -gt 0 ]]; then',
                '  text=\"$1\"',
                "  shift",
                "fi",
                'while [[ $# -gt 0 ]]; do',
                '  case \"$1\" in',
                "    -o|--output) output=\"$2\"; shift 2 ;;",
                "    --pitch) pitch=\"$2\"; shift 2 ;;",
                "    *) shift ;;",
                "  esac",
                "done",
                'if [[ \"$pitch\" == *\".0\" ]]; then',
                '  echo \"pitch must be an integer string, got: $pitch\" >&2',
                "  exit 23",
                "fi",
                'if [[ \"$text\" == *$\'\\n\'* ]]; then',
                '  echo \"text must not contain raw newlines\" >&2',
                "  exit 24",
                "fi",
                'mkdir -p \"$(dirname \"$output\")\"',
                'ffmpeg -y -f lavfi -i \"sine=frequency=660:sample_rate=32000\" -t 0.5 -c:a mp3 \"$output\" >/dev/null 2>&1',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def write_failing_tts_cli(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'echo "unexpected TTS invocation" >&2',
                "exit 19",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def make_color_png(path: Path, *, color: str, workdir: Path) -> None:
    run_command(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s=640x360",
            "-frames:v",
            "1",
            str(path),
        ],
        workdir,
    )


def make_video(path: Path, *, color: str, duration_seconds: float, workdir: Path) -> None:
    run_command(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s=640x360:rate=30",
            "-t",
            str(duration_seconds),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        workdir,
    )


def parse_srt_boundaries(path: Path) -> list[tuple[float, float, str]]:
    payload = path.read_text(encoding="utf-8").strip()
    blocks = [block for block in re.split(r"\n\s*\n", payload) if block.strip()]
    entries: list[tuple[float, float, str]] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3:
            continue
        start_raw, end_raw = lines[1].split(" --> ", maxsplit=1)
        entries.append((parse_srt_time(start_raw), parse_srt_time(end_raw), "".join(lines[2:])))
    return entries


def ffprobe_duration(path: Path, workdir: Path) -> float:
    result = run_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nk=1:nw=1",
            str(path),
        ],
        workdir,
    )
    return float(result.stdout.strip())


def parse_srt_time(raw_time: str) -> float:
    hours, minutes, rest = raw_time.split(":")
    seconds, milliseconds = rest.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000


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
    assert plan["qa_report_output"] == "review/assembly-qa-report.json"
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


def test_build_render_plan_adds_sound_design_defaults_for_midform(tmp_path: Path) -> None:
    """Midform plans should include reusable BGM and keyword-driven SFX cues."""
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
    (project_root / "content" / "postproduction" / "minimax-output" / "voice.mp3").write_bytes(b"voice")
    (project_root / "content" / "postproduction" / "subtitles.srt").write_text(
        "\n".join(
            [
                "1",
                "00:00:00,000 --> 00:00:02,000",
                "什么都知道，就是不敢决定。",
                "",
                "2",
                "00:00:12,000 --> 00:00:14,000",
                "这时候四步框架才有用。",
                "",
                "3",
                "00:00:26,000 --> 00:00:28,000",
                "最后给你三个停手信号。",
                "",
            ]
        ),
        encoding="utf-8",
    )

    run_command([sys.executable, str(script_path), "--project-root", str(project_root)], repo_root)

    plan = json.loads((project_root / "content" / "postproduction" / "render-plan.json").read_text(encoding="utf-8"))
    bgm_tracks = plan["mix"]["bgm_tracks"]
    sfx_cues = plan["mix"]["sfx_cues"]

    assert len(bgm_tracks) == 1
    assert bgm_tracks[0]["path"].endswith("remotion/public/bgm-techno.mp3")
    assert bgm_tracks[0]["start_seconds"] == 0.0
    assert bgm_tracks[0]["end_seconds"] == 18.0
    assert bgm_tracks[0]["loop"] is True
    assert plan["mix"]["bg_sidechain_ducking"] is True

    cue_labels = [cue["label"] for cue in sfx_cues]
    assert cue_labels == ["hook_statement", "framework_reveal", "stop_signal_list"]
    assert sfx_cues[0]["start_seconds"] == 0.0
    assert sfx_cues[1]["start_seconds"] == 12.0
    assert sfx_cues[2]["start_seconds"] == 26.0
    assert all(cue["preset"] for cue in sfx_cues)


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
    assert summary["qa_report"].endswith("review/assembly-qa-report.json")
    assert summary["subtitle_quality_report"].endswith("review/subtitle-quality-report.json")
    assert summary["scene_assembly_report"].endswith("review/scene-assembly-report.json")

    assert (project_root / "content" / "postproduction" / "render-plan.json").exists()
    assert (project_root / "content" / "postproduction" / "render-manifest.json").exists()
    assert (project_root / "review" / "assembly-qa-report.json").exists()
    assert (project_root / "review" / "subtitle-quality-report.json").exists()
    assert (project_root / "review" / "scene-assembly-report.json").exists()
    assert (project_root / "review" / "render-verification-auto.md").exists()
    assert (project_root / "content" / "final-cut" / "pilot-v2-narrated.mp4").exists()


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg/ffprobe required")
def test_build_render_plan_autogenerates_subtitles_when_missing(tmp_path: Path) -> None:
    """The builder should create subtitle drafts from voiceover segments when no SRT exists yet."""
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
    voiceover_audio = project_root / "content" / "postproduction" / "minimax-output" / "voice.mp3"
    segment_audio_dir = project_root / "content" / "postproduction" / "minimax-output" / "tmp"
    segment_audio_dir.mkdir(parents=True, exist_ok=True)
    write_voiceover_segments(
        project_root,
        [
            "什么都知道，就是不敢决定。",
            "你不是在继续思考，你是在继续比较。",
        ],
    )

    make_audio(voiceover_audio, duration_seconds=2.4, frequency=880, workdir=repo_root)
    make_audio(segment_audio_dir / "segment_0000.mp3", duration_seconds=1.1, frequency=660, workdir=repo_root)
    make_audio(segment_audio_dir / "segment_0001.mp3", duration_seconds=1.3, frequency=770, workdir=repo_root)

    run_command([sys.executable, str(script_path), "--project-root", str(project_root)], repo_root)

    subtitle_path = project_root / "content" / "postproduction" / "subtitles.srt"
    plan_path = project_root / "content" / "postproduction" / "render-plan.json"
    assert subtitle_path.exists()
    assert plan_path.exists()

    subtitle_text = subtitle_path.read_text(encoding="utf-8")
    assert "什么都知道，就是不敢决定。" in subtitle_text
    assert "你不是在继续思考，你是在继续比较。" in subtitle_text

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["subtitles"] == "content/postproduction/subtitles.srt"


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg/ffprobe required")
def test_build_render_plan_regenerates_stale_subtitles_when_voiceover_is_newer(tmp_path: Path) -> None:
    """Stale subtitle drafts should be replaced when a newer voiceover has been generated."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "build_render_plan.py"
    )

    project_root = make_media_package(tmp_path / "media-package-stale-subtitles")
    (project_root / "content" / "final-cut" / "pilot-v1.mp4").write_bytes(b"rough-cut")
    voiceover_audio = project_root / "content" / "postproduction" / "minimax-output" / "voice.mp3"
    segment_audio_dir = project_root / "content" / "postproduction" / "minimax-output" / "tmp"
    segment_audio_dir.mkdir(parents=True, exist_ok=True)
    subtitle_path = project_root / "content" / "postproduction" / "subtitles.srt"

    write_voiceover_segments(
        project_root,
        [
            "新的口播已经改过这一句了。",
            "所以字幕也必须跟着最新版本走。",
        ],
    )
    subtitle_path.write_text(
        "1\n00:00:00,000 --> 00:00:01,000\n这是旧字幕。\n",
        encoding="utf-8",
    )
    make_audio(voiceover_audio, duration_seconds=2.6, frequency=880, workdir=repo_root)
    make_audio(segment_audio_dir / "segment_0000.mp3", duration_seconds=1.2, frequency=660, workdir=repo_root)
    make_audio(segment_audio_dir / "segment_0001.mp3", duration_seconds=1.4, frequency=770, workdir=repo_root)
    os.utime(subtitle_path, (1_700_000_000, 1_700_000_000))
    os.utime(project_root / "content" / "postproduction" / "voiceover-segments.json", (1_700_000_100, 1_700_000_100))
    os.utime(voiceover_audio, (1_700_000_100, 1_700_000_100))

    run_command([sys.executable, str(script_path), "--project-root", str(project_root)], repo_root)

    subtitle_text = subtitle_path.read_text(encoding="utf-8")
    assert "新的口播已经改过这一句了。" in subtitle_text
    assert "这是旧字幕。" not in subtitle_text


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg/ffprobe required")
def test_build_subtitles_prefers_detected_silence_boundaries(tmp_path: Path) -> None:
    """Subtitle cue boundaries should snap to real pauses when segment audio contains usable silences."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "minimax-narration-postproduction"
        / "scripts"
        / "build_subtitles_from_segments.py"
    )

    project_root = make_media_package(tmp_path / "subtitle-package")
    voiceover_audio = project_root / "content" / "postproduction" / "minimax-output" / "voice.mp3"
    segment_audio_dir = project_root / "content" / "postproduction" / "minimax-output" / "tmp"
    segment_audio_dir.mkdir(parents=True, exist_ok=True)
    write_voiceover_segments(
        project_root,
        [
            "第一句先把问题说透。第二句补一个具体例子。第三句给出下一步动作。",
        ],
    )
    make_audio_with_silences(voiceover_audio, speech_frequency=880, workdir=repo_root)
    make_audio_with_silences(segment_audio_dir / "segment_0000.mp3", speech_frequency=880, workdir=repo_root)

    run_command([sys.executable, str(script_path), "--project-root", str(project_root)], repo_root)

    subtitle_path = project_root / "content" / "postproduction" / "subtitles.srt"
    entries = parse_srt_boundaries(subtitle_path)
    assert len(entries) == 3
    assert entries[0][2] == "第一句先把问题说透。"
    assert entries[1][2] == "第二句补一个具体例子。"
    assert entries[2][2] == "第三句给出下一步动作。"
    assert entries[0][1] == pytest.approx(1.0, abs=0.18)
    assert entries[1][1] == pytest.approx(2.2, abs=0.18)


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg/ffprobe required")
def test_build_subtitles_uses_segment_audio_timeline_when_crossfaded(tmp_path: Path) -> None:
    """Segment audio timings should survive merged-audio crossfade instead of being evenly rescaled."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "minimax-narration-postproduction"
        / "scripts"
        / "build_subtitles_from_segments.py"
    )

    project_root = make_media_package(tmp_path / "subtitle-crossfade-package")
    voiceover_audio = project_root / "content" / "postproduction" / "minimax-output" / "voice.mp3"
    segment_audio_dir = project_root / "content" / "postproduction" / "minimax-output" / "tmp"
    segment_audio_dir.mkdir(parents=True, exist_ok=True)
    first_segment = segment_audio_dir / "segment_0000.mp3"
    second_segment = segment_audio_dir / "segment_0001.mp3"

    write_voiceover_segments(
        project_root,
        [
            "第一句。",
            "第二句。",
        ],
    )
    make_audio(first_segment, duration_seconds=1.0, frequency=660, workdir=repo_root)
    make_audio(second_segment, duration_seconds=1.0, frequency=770, workdir=repo_root)
    make_crossfaded_audio(voiceover_audio, first_segment, second_segment, crossfade_seconds=0.2, workdir=repo_root)

    result = run_command([sys.executable, str(script_path), "--project-root", str(project_root)], repo_root)

    subtitle_path = project_root / "content" / "postproduction" / "subtitles.srt"
    entries = parse_srt_boundaries(subtitle_path)
    summary = json.loads(result.stdout)

    assert len(entries) == 2
    assert entries[0][2] == "第一句。"
    assert entries[1][2] == "第二句。"
    assert entries[1][0] == pytest.approx(0.8, abs=0.12)
    assert summary["alignment_mode"] == "segment_audio_forced"
    assert summary["inferred_crossfade_seconds"] == pytest.approx(0.2, abs=0.08)


def test_build_tts_handoff_segments_long_script_by_sentences() -> None:
    """Long narration should be segmented by sentence clusters rather than oversized paragraph blocks."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "minimax-narration-postproduction"
        / "scripts"
        / "build_tts_handoff.py"
    )
    module = SourceFileLoader("build_tts_handoff_test", str(script_path)).load_module()

    text = (
        "第一句先立结论。"
        "第二句补机制。"
        "第三句给例子。"
        "第四句继续延展。"
        "第五句再补一个反转。"
        "第六句回到行动。"
        "第七句继续推进。"
        "第八句收口。"
    )
    segments = module.segment_text(text, max_chars=18)

    assert len(segments) >= 4
    assert all(len(segment) <= 18 for segment in segments)
    assert segments[0].endswith("。")
    assert "第五句再补一个反转。" in "".join(segments)


def test_build_voice_performance_plan_outputs_segment_directives(tmp_path: Path) -> None:
    """Voice performance planner should turn narration into per-segment delivery directives."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "minimax-narration-postproduction"
        / "scripts"
        / "build_voice_performance_plan.py"
    )

    project_root = make_media_package(tmp_path / "voice-performance-package")
    content_packet = {
        "platforms": ["bilibili"],
        "deliverable_type": "midlong-video",
        "narration_script": "content/voiceover-script.md",
        "subtitle_source_script": "content/voiceover-script.md",
        "voiceover_assets": {
            "target_profile": {
                "voice_name": "Chinese (Mandarin)_Reliable_Executive",
                "speed": 0.98,
            }
        },
    }
    (project_root / "content" / "bilibili-midform-video.json").write_text(
        json.dumps(content_packet, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "voiceover-script.md").write_text(
        "\n".join(
            [
                "# 旁白",
                "",
                "为什么越会用 AI 的人，越容易做不出决定？",
                "",
                "举个具体例子。两个 offer，AI 在不同前提下会给出相反建议。",
                "",
                "最后给你四步框架：来源、反证、约束、试错。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    run_command([sys.executable, str(script_path), "--project-root", str(project_root)], repo_root)

    output_path = project_root / "content" / "postproduction" / "voice-performance-plan.json"
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["voice_strategy_defaults"]["primary_voice_id"] == "Chinese (Mandarin)_Reliable_Executive"
    assert payload["voice_strategy_defaults"]["delivery_profile"] == "tight_explanatory"
    assert payload["voice_strategy_defaults"]["default_pause_profile"] == "tight"
    assert payload["segments"]
    assert all(segment["emotion"] for segment in payload["segments"])
    assert all("pause_after_ms" in segment for segment in payload["segments"])
    assert {segment["scene_purpose"] for segment in payload["segments"]} >= {"hook", "proof", "framework"}
    assert payload["segments"][0]["pause_after_ms"] <= 120


def test_build_voice_performance_plan_keeps_ordinal_framework_list_on_consistent_delivery(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "minimax-narration-postproduction"
        / "scripts"
        / "build_voice_performance_plan.py"
    )

    project_root = make_media_package(tmp_path / "voice-ordinal-framework-package")
    content_packet = {
        "platforms": ["bilibili"],
        "deliverable_type": "midlong-video",
        "narration_script": "content/voiceover-script.md",
        "subtitle_source_script": "content/voiceover-script.md",
        "voiceover_assets": {
            "target_profile": {
                "voice_name": "Chinese (Mandarin)_Reliable_Executive",
                "speed": 1.03,
            }
        },
    }
    (project_root / "content" / "bilibili-midform-video.json").write_text(
        json.dumps(content_packet, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "voiceover-script.md").write_text(
        "\n".join(
            [
                "这条视频我想讲清三件事。",
                "",
                "第一，为什么输入会制造一种非常强的成长错觉。",
                "",
                "第二，为什么课程、笔记软件、尤其是 AI，会把这种错觉放得更大。",
                "",
                "第三，怎样用一套可以直接拿去验证的动作，把“我学过了”逼成“我真的变了”。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    run_command([sys.executable, str(script_path), "--project-root", str(project_root)], repo_root)

    payload = json.loads((project_root / "content" / "postproduction" / "voice-performance-plan.json").read_text(encoding="utf-8"))
    ordinal_segments = [
        segment
        for segment in payload["segments"]
        if segment["text"].startswith(("第一", "第二", "第三"))
    ]

    assert len(ordinal_segments) == 3
    assert {segment["scene_purpose"] for segment in ordinal_segments} == {"framework"}
    assert len({segment["emotion"] for segment in ordinal_segments}) == 1
    assert len({segment["speed"] for segment in ordinal_segments}) == 1
    assert len({segment["pause_after_ms"] for segment in ordinal_segments}) == 1


def test_build_tts_handoff_autogenerates_voice_performance_plan_and_enriched_segments(tmp_path: Path) -> None:
    """TTS handoff should auto-generate and consume voice performance directives."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "minimax-narration-postproduction"
        / "scripts"
        / "build_tts_handoff.py"
    )

    project_root = make_media_package(tmp_path / "tts-handoff-package")
    content_packet = {
        "platforms": ["bilibili"],
        "deliverable_type": "midlong-video",
        "narration_script": "content/voiceover-script.md",
        "subtitle_source_script": "content/voiceover-script.md",
        "voiceover_assets": {
            "target_profile": {
                "voice_name": "Chinese (Mandarin)_Reliable_Executive",
                "speed": 0.97,
            }
        },
        "subtitle_package": {
            "estimated_srt": "content/postproduction/subtitles.srt",
        },
    }
    (project_root / "content" / "bilibili-midform-video.json").write_text(
        json.dumps(content_packet, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "voiceover-script.md").write_text(
        "\n".join(
            [
                "什么都知道，就是不敢决定。",
                "",
                "举个例子，两个 offer 在不同前提下会得出相反建议。",
                "",
                "最后给你四步框架，把问题压回现实。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    run_command([sys.executable, str(script_path), "--project-root", str(project_root)], repo_root)

    performance_path = project_root / "content" / "postproduction" / "voice-performance-plan.json"
    segments_path = project_root / "content" / "postproduction" / "voiceover-segments.json"
    profile_path = project_root / "content" / "postproduction" / "voiceover-profile.json"

    assert performance_path.exists()
    segments = json.loads(segments_path.read_text(encoding="utf-8"))
    profile = json.loads(profile_path.read_text(encoding="utf-8"))

    assert all(segment["emotion"] for segment in segments)
    assert all("pause_after_ms" in segment for segment in segments)
    assert all("intensity" in segment for segment in segments)
    assert all("scene_purpose" in segment for segment in segments)
    assert profile["render_targets"]["voice_performance_plan"] == "content/postproduction/voice-performance-plan.json"
    assert profile["voice_strategy"]["default_emotion"]
    assert profile["voice_strategy"]["delivery_profile"] == "tight_explanatory"


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg/ffprobe required")
def test_generate_voiceover_with_timing_applies_pause_profile_and_keeps_subtitles_in_sync(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    generator_script = (
        repo_root
        / "extensions"
        / "skills"
        / "minimax-narration-postproduction"
        / "scripts"
        / "generate_voiceover_with_timing.py"
    )
    subtitle_script = (
        repo_root
        / "extensions"
        / "skills"
        / "minimax-narration-postproduction"
        / "scripts"
        / "build_subtitles_from_segments.py"
    )

    project_root = make_media_package(tmp_path / "voiceover-timing-package")
    fake_tts = tmp_path / "fake_tts.sh"
    write_fake_tts_cli(fake_tts)
    segments_path = project_root / "content" / "postproduction" / "voiceover-segments.json"
    profile_path = project_root / "content" / "postproduction" / "voiceover-profile.json"
    output_audio = project_root / "content" / "postproduction" / "minimax-output" / "voice.mp3"

    segments_path.write_text(
        json.dumps(
            [
                {"text": "第一句。", "voice_id": "narrator", "speed": 1.05, "pause_after_ms": 300},
                {"text": "第二句。", "voice_id": "narrator", "speed": 1.04, "pause_after_ms": 120},
            ],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    profile_path.write_text(
        json.dumps(
            {
                "render_targets": {
                    "segments_file": "content/postproduction/voiceover-segments.json",
                    "voiceover_audio": "content/postproduction/minimax-output/voice.mp3",
                    "subtitle_draft": "content/postproduction/subtitles.srt",
                }
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_command(
        [
            sys.executable,
            str(generator_script),
            "--project-root",
            str(project_root),
            "--tts-cli",
            str(fake_tts),
        ],
        repo_root,
    )
    summary = json.loads(result.stdout)
    assert summary["total_pause_ms"] == 300
    assert output_audio.exists()
    assert ffprobe_duration(output_audio, repo_root) == pytest.approx(2.3, abs=0.2)

    subtitle_result = run_command([sys.executable, str(subtitle_script), "--project-root", str(project_root)], repo_root)
    subtitle_summary = json.loads(subtitle_result.stdout)
    subtitle_entries = parse_srt_boundaries(project_root / "content" / "postproduction" / "subtitles.srt")

    assert subtitle_summary["alignment_mode"] == "segment_audio_forced"
    assert subtitle_summary["total_pause_seconds"] == pytest.approx(0.3, abs=0.05)
    assert subtitle_entries[1][0] == pytest.approx(1.3, abs=0.12)


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg/ffprobe required")
def test_generate_voiceover_with_timing_normalizes_default_pitch_for_minimax_cli(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    generator_script = (
        repo_root
        / "extensions"
        / "skills"
        / "minimax-narration-postproduction"
        / "scripts"
        / "generate_voiceover_with_timing.py"
    )

    project_root = make_media_package(tmp_path / "voiceover-pitch-package")
    validating_tts = tmp_path / "pitch_validating_tts.sh"
    write_pitch_validating_tts_cli(validating_tts)
    segments_path = project_root / "content" / "postproduction" / "voiceover-segments.json"
    profile_path = project_root / "content" / "postproduction" / "voiceover-profile.json"

    segments_path.write_text(
        json.dumps(
            [
                {"text": "第一句。\n第二句。", "voice_id": "narrator", "speed": 1.05, "pause_after_ms": 120},
            ],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    profile_path.write_text(
        json.dumps(
            {
                "render_targets": {
                    "segments_file": "content/postproduction/voiceover-segments.json",
                    "voiceover_audio": "content/postproduction/minimax-output/voice.mp3",
                }
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
            str(generator_script),
            "--project-root",
            str(project_root),
            "--tts-cli",
            str(validating_tts),
        ],
        repo_root,
    )

    assert (project_root / "content" / "postproduction" / "minimax-output" / "voice.mp3").exists()


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg/ffprobe required")
def test_generate_voiceover_with_timing_reuses_existing_segment_audio_for_resume(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    generator_script = (
        repo_root
        / "extensions"
        / "skills"
        / "minimax-narration-postproduction"
        / "scripts"
        / "generate_voiceover_with_timing.py"
    )

    project_root = make_media_package(tmp_path / "voiceover-resume-package")
    failing_tts = tmp_path / "failing_tts.sh"
    write_failing_tts_cli(failing_tts)
    segments_path = project_root / "content" / "postproduction" / "voiceover-segments.json"
    profile_path = project_root / "content" / "postproduction" / "voiceover-profile.json"
    temp_dir = project_root / "content" / "postproduction" / "minimax-output" / "tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    make_audio(temp_dir / "segment_0000.mp3", duration_seconds=0.6, frequency=550, workdir=repo_root)

    segments_path.write_text(
        json.dumps(
            [
                {"text": "第一句。", "voice_id": "narrator", "speed": 1.05, "pause_after_ms": 0},
            ],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    profile_path.write_text(
        json.dumps(
            {
                "render_targets": {
                    "segments_file": "content/postproduction/voiceover-segments.json",
                    "voiceover_audio": "content/postproduction/minimax-output/voice.mp3",
                }
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
            str(generator_script),
            "--project-root",
            str(project_root),
            "--tts-cli",
            str(failing_tts),
        ],
        repo_root,
    )

    assert (project_root / "content" / "postproduction" / "minimax-output" / "voice.mp3").exists()


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg/ffprobe required")
def test_generate_voiceover_with_timing_regenerates_when_segment_signature_changes(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    generator_script = (
        repo_root
        / "extensions"
        / "skills"
        / "minimax-narration-postproduction"
        / "scripts"
        / "generate_voiceover_with_timing.py"
    )

    project_root = make_media_package(tmp_path / "voiceover-signature-package")
    tts_cli = tmp_path / "validating_tts.sh"
    write_pitch_validating_tts_cli(tts_cli)
    segments_path = project_root / "content" / "postproduction" / "voiceover-segments.json"
    profile_path = project_root / "content" / "postproduction" / "voiceover-profile.json"
    temp_dir = project_root / "content" / "postproduction" / "minimax-output" / "tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    make_audio(temp_dir / "segment_0000.mp3", duration_seconds=0.6, frequency=550, workdir=repo_root)
    (temp_dir / "segment_0000.json").write_text(
        json.dumps({"signature": "stale-signature"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    segments_path.write_text(
        json.dumps(
            [
                {"text": "第一句。", "voice_id": "narrator", "speed": 1.05, "pause_after_ms": 0},
            ],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    profile_path.write_text(
        json.dumps(
            {
                "render_targets": {
                    "segments_file": "content/postproduction/voiceover-segments.json",
                    "voiceover_audio": "content/postproduction/minimax-output/voice.mp3",
                }
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
            str(generator_script),
            "--project-root",
            str(project_root),
            "--tts-cli",
            str(tts_cli),
        ],
        repo_root,
    )

    manifest = json.loads((project_root / "content" / "postproduction" / "voiceover-generation-manifest.json").read_text(encoding="utf-8"))
    assert manifest["segments"][0]["signature"]
    sidecar = json.loads((temp_dir / "segment_0000.json").read_text(encoding="utf-8"))
    assert sidecar["signature"] == manifest["segments"][0]["signature"]


def test_build_subtitle_style_pack_creates_ass_style_and_highlights(tmp_path: Path) -> None:
    """Subtitle style pack should expose burn-in style and emphasis rules."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "minimax-narration-postproduction"
        / "scripts"
        / "build_subtitle_style_pack.py"
    )

    project_root = make_media_package(tmp_path / "subtitle-style-package")
    content_packet = {
        "platforms": ["bilibili"],
        "deliverable_type": "midlong-video",
        "subtitle_package": {
            "style": "简体中文，按意群断句，单行 14-20 字优先",
            "notes": [
                "关键句上屏：什么都知道，就是不敢决定",
                "关键句上屏：四步框架",
            ],
        },
    }
    (project_root / "content" / "bilibili-midform-video.json").write_text(
        json.dumps(content_packet, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "subtitles.srt").write_text(
        "\n".join(
            [
                "1",
                "00:00:00,000 --> 00:00:01,000",
                "第一，先打狠句。",
                "",
                "2",
                "00:03:40,000 --> 00:03:41,000",
                "第二，交付四步框架。",
                "",
            ]
        ),
        encoding="utf-8",
    )

    run_command([sys.executable, str(script_path), "--project-root", str(project_root)], repo_root)

    output_path = project_root / "content" / "postproduction" / "subtitle-style-pack.json"
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["theme"] == "bilibili-midform-bilingual"
    assert payload["burn_in_mode"] == "hardsub"
    assert payload["subtitle_mode"] == "bilingual_hardsub"
    assert payload["translation_required"] is True
    assert payload["highlight_rules"]["priority_phrases"] == ["什么都知道，就是不敢决定", "四步框架"]
    assert "FontName=" in payload["ass_force_style"]


def test_build_subtitles_from_segments_outputs_bilingual_cues_when_translations_exist(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "minimax-narration-postproduction"
        / "scripts"
        / "build_subtitles_from_segments.py"
    )

    project_root = make_media_package(tmp_path / "bilingual-subtitle-package")
    (project_root / "content" / "bilibili-midform-video.json").write_text(
        json.dumps(
            {
                "content_id": "pilot",
                "platforms": ["bilibili"],
                "deliverable_type": "midlong-video",
                "subtitle_package": {
                    "translation_required": True,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "voiceover-segments.json").write_text(
        json.dumps(
            [
                {
                    "text": "平台不是更懂你。它更懂怎么留住你。",
                    "translation_en": "The platform does not know you better. It knows better how to keep you.",
                    "duration_seconds": 4.0,
                },
                {
                    "text": "先退出feed，再做判断。",
                    "translation_en": "Step out of the feed before you decide.",
                    "duration_seconds": 3.0,
                },
            ],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_command([sys.executable, str(script_path), "--project-root", str(project_root)], repo_root)

    payload = json.loads(result.stdout)
    srt_output = (project_root / "content" / "postproduction" / "subtitles.srt").read_text(encoding="utf-8")
    assert payload["bilingual_enabled"] is True
    assert payload["translated_cue_count"] >= 2
    assert payload["missing_translation_segment_count"] == 0
    assert "平台不是更懂你。" in srt_output
    assert "The platform does not know you better." in srt_output
    assert "Step out of the feed before you decide." in srt_output


def test_build_subtitle_quality_report_revises_when_bilingual_cues_are_missing(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "render_narrated_cut.py"
    )
    module = SourceFileLoader("render_narrated_cut_subtitle_quality_test", str(script_path)).load_module()

    project_root = make_media_package(tmp_path / "subtitle-quality-bilingual-package")
    subtitles = project_root / "content" / "postproduction" / "subtitles.srt"
    style_pack = project_root / "content" / "postproduction" / "subtitle-style-pack.json"
    subtitles.write_text(
        "\n".join(
            [
                "1",
                "00:00:00,000 --> 00:00:01,000",
                "只有中文这一行。",
                "",
            ]
        ),
        encoding="utf-8",
    )
    style_pack.write_text(
        json.dumps({"translation_required": True}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    report = module.build_subtitle_quality_report(
        plan={
            "subtitle_style": "FontName=Arial Unicode MS",
            "context": {
                "subtitle_style_pack": "content/postproduction/subtitle-style-pack.json",
            },
        },
        qa_report={
            "checks": {
                "subtitle_delivery": {"status": "pass", "mode": "burned_in"},
                "subtitle_alignment": {"status": "pass"},
            }
        },
        workspace_root=project_root,
        subtitles=subtitles,
    )

    assert report["status"] == "revise"
    assert report["checks"]["bilingual_delivery"]["status"] == "revise"
    assert report["checks"]["bilingual_delivery"]["bilingual_cue_count"] == 0


def test_generate_segment_translations_populates_missing_translation_en(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "minimax-narration-postproduction"
        / "scripts"
        / "generate_segment_translations.py"
    )

    project_root = make_media_package(tmp_path / "translation-package")
    segments_path = project_root / "content" / "postproduction" / "voiceover-segments.json"
    segments_path.write_text(
        json.dumps(
            [
                {"text": "平台不是更懂你。它更懂怎么留住你。"},
                {"text": "先退出 feed，再做判断。", "translation_en": "Keep this existing translation."},
                {"text": ""},
            ],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    module = SourceFileLoader("generate_segment_translations_test", str(script_path)).load_module()

    calls: list[str] = []

    class StubResponse:
        def __init__(self, payload: dict[str, object]) -> None:
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return json.dumps(self.payload, ensure_ascii=False).encode("utf-8")

    def fake_urlopen(request, timeout=0):
        body = json.loads(request.data.decode("utf-8"))
        calls.append(request.full_url)
        assert body["model"] == "M2.7-highspeed"
        return StubResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                [
                                    {
                                        "index": 0,
                                        "translation_en": "The platform does not know you better. It knows how to keep you.",
                                    }
                                ],
                                ensure_ascii=False,
                            )
                        }
                    }
                ],
                "base_resp": {"status_code": 0, "status_msg": ""},
            }
        )

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("MINIMAX_API_HOST", "https://api.minimaxi.com")
    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")
    monkeypatch.setattr(sys, "argv", [str(script_path), "--project-root", str(project_root)])

    assert module.main() == 0
    assert len(calls) == 1

    updated_segments = json.loads(segments_path.read_text(encoding="utf-8"))
    assert updated_segments[0]["translation_en"].startswith("The platform does not know you better")
    assert updated_segments[1]["translation_en"] == "Keep this existing translation."


def test_generate_segment_translations_falls_back_when_default_model_is_unsupported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "minimax-narration-postproduction"
        / "scripts"
        / "generate_segment_translations.py"
    )

    project_root = make_media_package(tmp_path / "translation-fallback-package")
    segments_path = project_root / "content" / "postproduction" / "voiceover-segments.json"
    segments_path.write_text(
        json.dumps([{"text": "先退出 feed，再做判断。"}], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    module = SourceFileLoader("generate_segment_translations_fallback_test", str(script_path)).load_module()

    requested_models: list[str] = []

    class StubResponse:
        def __init__(self, payload: dict[str, object]) -> None:
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return json.dumps(self.payload, ensure_ascii=False).encode("utf-8")

    def fake_urlopen(request, timeout=0):
        body = json.loads(request.data.decode("utf-8"))
        requested_models.append(body["model"])
        if body["model"] in {"M2.7-highspeed", "MiniMax-M2.7-highspeed"}:
            return StubResponse({"choices": None, "base_resp": {"status_code": 2013, "status_msg": "unknown model"}})
        return StubResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                [{"index": 0, "translation_en": "Step out of the feed before you decide."}],
                                ensure_ascii=False,
                            ),
                        }
                    }
                ],
                "base_resp": {"status_code": 0, "status_msg": ""},
            }
        )

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("MINIMAX_API_HOST", "https://api.minimaxi.com")
    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")
    monkeypatch.setattr(sys, "argv", [str(script_path), "--project-root", str(project_root)])

    assert module.main() == 0
    assert requested_models[:3] == ["M2.7-highspeed", "MiniMax-M2.7-highspeed", "MiniMax-M2.5"]
    updated_segments = json.loads(segments_path.read_text(encoding="utf-8"))
    assert updated_segments[0]["translation_en"] == "Step out of the feed before you decide."


def test_render_narrated_cut_skips_subtitle_filter_when_ffmpeg_lacks_support(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "render_narrated_cut.py"
    )
    module = SourceFileLoader("render_narrated_cut_filter_fallback_test", str(script_path)).load_module()
    module.ffmpeg_filter_available.cache_clear()
    original_probe = module.ffmpeg_filter_available
    module.ffmpeg_filter_available = lambda filter_name: False

    try:
        filter_complex, _ = module.build_filter_complex(
            plan={"mix": {}},
            subtitles=tmp_path / "subtitles.srt",
            source_duration=2.0,
            source_video_fps=None,
            voiceover_duration=1.5,
            retain_original_audio=False,
            source_has_audio=False,
            bgm_bed_present=False,
            sfx_bed_present=False,
        )
    finally:
        module.ffmpeg_filter_available = original_probe

    assert "[v_base]null[vout]" in filter_complex
    assert "subtitles='" not in filter_complex


def test_render_narrated_cut_uses_minterpolate_when_target_fps_exceeds_source() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "render_narrated_cut.py"
    )
    module = SourceFileLoader("render_narrated_cut_minterpolate_test", str(script_path)).load_module()
    module.ffmpeg_filter_available.cache_clear()
    original_probe = module.ffmpeg_filter_available
    module.ffmpeg_filter_available = lambda filter_name: filter_name in {"subtitles", "minterpolate"}

    try:
        filter_complex, _ = module.build_filter_complex(
            plan={"mix": {}, "retime": {"target_fps": 60}},
            subtitles=None,
            source_duration=2.0,
            source_video_fps=30.0,
            voiceover_duration=1.8,
            retain_original_audio=False,
            source_has_audio=False,
            bgm_bed_present=False,
            sfx_bed_present=False,
        )
    finally:
        module.ffmpeg_filter_available = original_probe

    assert "minterpolate=fps=60" in filter_complex


def test_build_scene_assembly_report_flags_plain_text_card_primary_assets(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "render_narrated_cut.py"
    )
    module = SourceFileLoader("render_narrated_cut_scene_assembly_test", str(script_path)).load_module()

    project_root = make_media_package(tmp_path / "scene-assembly-bilingual-package")
    (project_root / "content" / "postproduction" / "scene-manifest.json").write_text(
        json.dumps(
            {
                "scenes": [
                    {
                        "scene_id": "scene-01-ch1",
                        "chapter_id": "ch1",
                        "primary_asset": {"path": "assets/graphics/card-01-hook.png", "type": "graphics-card"},
                        "subtitle_mode": "narrated_hardsub",
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
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

    report = module.build_scene_assembly_report(
        plan={
            "context": {
                "scene_manifest": "content/postproduction/scene-manifest.json",
                "transition_plan": "content/postproduction/transition-plan.json",
                "emphasis_fx_plan": "content/postproduction/emphasis-fx-plan.json",
            }
        },
        workspace_root=project_root,
        qa_report={"status": "pass"},
    )

    assert report["status"] == "revise"
    assert report["checks"]["plain_text_cards_removed"]["status"] == "revise"
    assert report["checks"]["bilingual_subtitle_mode"]["status"] == "revise"


def test_build_audio_cue_sheet_creates_chapter_beats_and_mix_rules(tmp_path: Path) -> None:
    """Audio cue sheet should turn beat structure into reusable BGM/SFX instructions."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "build_audio_cue_sheet.py"
    )

    project_root = make_media_package(tmp_path / "audio-cue-package")
    content_packet = {
        "platforms": ["bilibili"],
        "deliverable_type": "midlong-video",
        "duration_target": "06:10-06:50",
        "beat_sheet": [
            {"time_range": "00:00-00:40", "beat": "hook", "purpose": "先打狠句。"},
            {"time_range": "02:20-03:40", "beat": "proof", "purpose": "用相反答案案例证明。"},
            {"time_range": "03:40-05:20", "beat": "framework", "purpose": "交付四步框架。"},
        ],
        "chapter_outline": [
            {"chapter_id": "ch1", "title": "信息题和权重题"},
            {"chapter_id": "ch2", "title": "四步框架"},
        ],
    }
    (project_root / "content" / "bilibili-midform-video.json").write_text(
        json.dumps(content_packet, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "subtitles.srt").write_text(
        "\n".join(
            [
                "1",
                "00:00:00,000 --> 00:00:01,000",
                "第一，先打狠句。",
                "",
                "2",
                "00:03:40,000 --> 00:03:41,000",
                "第二，交付四步框架。",
                "",
            ]
        ),
        encoding="utf-8",
    )

    run_command([sys.executable, str(script_path), "--project-root", str(project_root)], repo_root)

    output_path = project_root / "content" / "postproduction" / "audio-cue-sheet.json"
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["bgm_tracks"]
    assert len(payload["bgm_tracks"]) == 3
    assert [track["role"] for track in payload["bgm_tracks"]] == ["hook_bed", "proof_bed", "framework_bed"]
    assert payload["bgm_tracks"][0]["start_seconds"] == 0.0
    assert payload["bgm_tracks"][0]["end_seconds"] == 18.0
    assert payload["bgm_tracks"][1]["start_seconds"] == 140.0
    assert payload["bgm_tracks"][1]["end_seconds"] == 220.0
    assert payload["bgm_tracks"][2]["start_seconds"] == 220.0
    assert payload["bgm_tracks"][2]["end_seconds"] == 320.0
    assert payload["sfx_cues"]
    assert payload["ducking_rules"]["bg_sidechain_ducking"] is True
    assert payload["ducking_rules"]["sfx_stem_gain_db"] == 7.8
    assert payload["chapter_audio_beats"][0]["beat"] == "hook"
    assert payload["chapter_audio_beats"][1]["start_seconds"] == 140.0
    cue_labels = [cue["label"] for cue in payload["sfx_cues"]]
    assert "hook_braam" in cue_labels
    assert "hook_statement" in cue_labels
    assert "framework_reveal" in cue_labels
    assert "ordinal_first" in cue_labels
    assert "ordinal_second" in cue_labels


def test_build_audio_cue_sheet_uses_package_audio_library_overrides(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "build_audio_cue_sheet.py"
    )

    project_root = make_media_package(tmp_path / "audio-library-package")
    (project_root / "assets" / "audio").mkdir(parents=True, exist_ok=True)
    (project_root / "content" / "bilibili-midform-video.json").write_text(
        json.dumps(
            {
                "platforms": ["bilibili"],
                "deliverable_type": "midlong-video",
                "duration_target": "02:40-03:00",
                "beat_sheet": [
                    {"time_range": "00:00-00:20", "beat": "hook", "purpose": "冷开场。"},
                    {"time_range": "01:00-01:40", "beat": "framework", "purpose": "交付框架。"},
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "assets" / "audio" / "custom-hook.mp3").write_bytes(b"hook")
    (project_root / "assets" / "audio" / "custom-framework.mp3").write_bytes(b"framework")
    (project_root / "assets" / "audio" / "audio-library.json").write_text(
        json.dumps(
            {
                "tracks": {
                    "hook_bed": {"path": "assets/audio/custom-hook.mp3", "gain_db": -19.5},
                    "framework_bed": {"path": "assets/audio/custom-framework.mp3", "gain_db": -20.0},
                }
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    run_command([sys.executable, str(script_path), "--project-root", str(project_root)], repo_root)

    payload = json.loads((project_root / "content" / "postproduction" / "audio-cue-sheet.json").read_text(encoding="utf-8"))
    assert payload["bgm_tracks"][0]["path"] == "assets/audio/custom-hook.mp3"
    assert payload["bgm_tracks"][0]["gain_db"] == -19.5
    assert payload["bgm_tracks"][1]["path"] == "assets/audio/custom-framework.mp3"


def test_build_audio_cue_sheet_layers_bridge_bed_under_long_hook_when_available(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "build_audio_cue_sheet.py"
    )

    project_root = make_media_package(tmp_path / "audio-hook-layer-package")
    (project_root / "assets" / "audio").mkdir(parents=True, exist_ok=True)
    (project_root / "content" / "bilibili-midform-video.json").write_text(
        json.dumps(
            {
                "platforms": ["bilibili"],
                "deliverable_type": "midlong-video",
                "duration_target": "01:20-01:40",
                "beat_sheet": [
                    {"time_range": "00:00-00:28", "beat": "hook", "purpose": "冷开场。"},
                    {"time_range": "00:28-01:10", "beat": "framework", "purpose": "交付框架。"},
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "assets" / "audio" / "custom-hook.mp3").write_bytes(b"hook")
    (project_root / "assets" / "audio" / "custom-bridge.mp3").write_bytes(b"bridge")
    (project_root / "assets" / "audio" / "audio-library.json").write_text(
        json.dumps(
            {
                "tracks": {
                    "hook_bed": {"path": "assets/audio/custom-hook.mp3", "gain_db": -15.0},
                    "bridge_bed": {"path": "assets/audio/custom-bridge.mp3", "gain_db": -18.0},
                }
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    run_command([sys.executable, str(script_path), "--project-root", str(project_root)], repo_root)

    payload = json.loads((project_root / "content" / "postproduction" / "audio-cue-sheet.json").read_text(encoding="utf-8"))
    hook_roles = [track["role"] for track in payload["bgm_tracks"]]
    assert "hook_bed" in hook_roles
    assert "hook_layer_bed" in hook_roles
    layered_track = next(track for track in payload["bgm_tracks"] if track["role"] == "hook_layer_bed")
    assert layered_track["path"] == "assets/audio/custom-bridge.mp3"
    assert layered_track["start_seconds"] >= 4.0


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg/ffprobe required")
def test_build_visual_timeline_places_opening_typewriter_on_cover_slot(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "build_visual_timeline.py"
    )

    project_root = make_media_package(tmp_path / "opening-typewriter-package", assembly_strategy="rebuild_timeline")
    voiceover_audio = project_root / "content" / "postproduction" / "minimax-output" / "voice.mp3"
    subtitles = project_root / "content" / "postproduction" / "subtitles.srt"
    graphics_dir = project_root / "assets" / "graphics"
    graphics_dir.mkdir(parents=True, exist_ok=True)

    make_audio(voiceover_audio, duration_seconds=2.2, frequency=880, workdir=repo_root)
    make_color_png(project_root / "assets" / "bilibili-cover-draft.png", color="black", workdir=repo_root)
    make_color_png(graphics_dir / "card-01-hook.png", color="red", workdir=repo_root)
    subtitles.write_text(
        "\n".join(
            [
                "1",
                "00:00:00,000 --> 00:00:02,200",
                "平台不是更懂你，它更懂怎么把你困在像你",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (project_root / "content" / "bilibili-midform-video.json").write_text(
        json.dumps(
            {
                "content_id": "pilot",
                "platforms": ["bilibili"],
                "deliverable_type": "midlong-video",
                "chapter_outline": [
                    {
                        "chapter_id": "ch1",
                        "title": "开场问题",
                        "chapter_goal": "先给冲突和异常点",
                        "summary": "平台不是更懂你。",
                    }
                ],
                "hook_hypotheses": ["平台不是更懂你，它更懂怎么把你困在“像你”的东西里。"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "assets" / "scene-asset-plan.json").write_text(
        json.dumps(
            {
                "chapters": [
                    {
                        "chapter_id": "ch1",
                        "proof_asset": {"path": "assets/graphics/card-01-hook.png", "type": "graphics-card"},
                        "supporting_b_roll": [],
                        "fallback_graphics": ["assets/graphics/card-01-hook.png"],
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction").mkdir(parents=True, exist_ok=True)
    (project_root / "content" / "postproduction" / "scene-manifest.json").write_text(
        json.dumps(
            {
                "scenes": [
                    {
                        "scene_id": "scene-01-ch1",
                        "chapter_id": "ch1",
                        "scene_title": "开场问题",
                        "scene_goal": "先给冲突和异常点",
                        "primary_asset": {"path": "assets/graphics/card-01-hook.png", "type": "graphics-card"},
                        "supporting_assets": [],
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "emphasis-fx-plan.json").write_text(
        json.dumps(
            {
                "scene_fx": [
                    {
                        "scene_id": "scene-01-ch1",
                        "effects": [
                            {
                                "type": "typewriter_quote",
                                "text": "平台不是更懂你，它更懂怎么把你困在“像你”的东西里。",
                                "anchor": "upper_left",
                                "chars_per_second": 12,
                                "start_offset_seconds": 0.0,
                                "duration_seconds": 2.0,
                            }
                        ],
                    }
                ]
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
            "--voiceover-audio",
            "content/postproduction/minimax-output/voice.mp3",
            "--subtitles",
            "content/postproduction/subtitles.srt",
        ],
        repo_root,
    )

    payload = json.loads((project_root / "content" / "postproduction" / "auto-base-cut-plan.json").read_text(encoding="utf-8"))
    assert payload["sequence"][0]["target_chapter"] == "opening"
    assert payload["sequence"][0]["typewriter_text"] == "平台不是更懂你，它更懂怎么把你困在“像你”的东西里。"


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg/ffprobe required")
def test_build_visual_timeline_prefers_generated_keyart_and_falls_back_to_scene_manifest_fx(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "build_visual_timeline.py"
    )

    project_root = make_media_package(tmp_path / "generated-keyart-package", assembly_strategy="rebuild_timeline")
    voiceover_audio = project_root / "content" / "postproduction" / "minimax-output" / "voice.mp3"
    subtitles = project_root / "content" / "postproduction" / "subtitles.srt"
    graphics_dir = project_root / "assets" / "graphics"
    generated_dir = project_root / "assets" / "generated"
    graphics_dir.mkdir(parents=True, exist_ok=True)
    generated_dir.mkdir(parents=True, exist_ok=True)

    make_audio(voiceover_audio, duration_seconds=8.8, frequency=880, workdir=repo_root)
    make_color_png(project_root / "assets" / "bilibili-cover-draft.png", color="black", workdir=repo_root)
    make_color_png(graphics_dir / "card-01-hook.png", color="red", workdir=repo_root)
    make_color_png(generated_dir / "ch1-hero.png", color="green", workdir=repo_root)
    subtitles.write_text(
        "\n".join(
            [
                "1",
                "00:00:00,000 --> 00:00:02,200",
                "平台不是更懂你。",
                "",
                "2",
                "00:00:02,200 --> 00:00:04,400",
                "它更懂怎么把你困在像你的东西里。",
                "",
                "3",
                "00:00:04,400 --> 00:00:06,600",
                "你越刷，越像在确认自己。",
                "",
                "4",
                "00:00:06,600 --> 00:00:08,800",
                "但你看到的样本却越来越窄。",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (project_root / "content" / "bilibili-midform-video.json").write_text(
        json.dumps(
            {
                "content_id": "pilot",
                "platforms": ["bilibili"],
                "deliverable_type": "midlong-video",
                "chapter_outline": [
                    {
                        "chapter_id": "ch1",
                        "title": "开场问题",
                        "chapter_goal": "先给冲突和异常点",
                        "summary": "平台不是更懂你。",
                    }
                ],
                "hook_hypotheses": ["平台不是更懂你。"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "assets" / "scene-asset-plan.json").write_text(
        json.dumps(
            {
                "chapters": [
                    {
                        "chapter_id": "ch1",
                        "proof_asset": {"path": "assets/generated/ch1-hero.png", "type": "generated-keyart"},
                        "supporting_b_roll": [],
                        "fallback_graphics": [
                            "assets/generated/ch1-hero.png",
                            "assets/graphics/card-01-hook.png",
                        ],
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction").mkdir(parents=True, exist_ok=True)
    (project_root / "content" / "postproduction" / "scene-manifest.json").write_text(
        json.dumps(
            {
                "scenes": [
                    {
                        "scene_id": "scene-01-ch1",
                        "chapter_id": "ch1",
                        "scene_title": "开场问题",
                        "scene_goal": "先给冲突和异常点",
                        "primary_asset": {"path": "assets/generated/ch1-hero.png", "type": "generated-keyart"},
                        "supporting_assets": [],
                        "emphasis_fx": [
                            {
                                "type": "typewriter_quote",
                                "text": "平台不是更懂你",
                                "anchor": "upper_center",
                                "chars_per_second": 8,
                                "start_offset_seconds": 0.0,
                                "duration_seconds": 2.2,
                                "target_role": "keyart",
                            }
                        ],
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "emphasis-fx-plan.json").write_text(
        json.dumps({"scene_fx": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
            "--voiceover-audio",
            "content/postproduction/minimax-output/voice.mp3",
            "--subtitles",
            "content/postproduction/subtitles.srt",
        ],
        repo_root,
    )

    payload = json.loads((project_root / "content" / "postproduction" / "auto-base-cut-plan.json").read_text(encoding="utf-8"))
    typewriter_slots = [item for item in payload["sequence"] if item["typewriter_text"] == "平台不是更懂你"]
    assert typewriter_slots
    assert typewriter_slots[0]["asset_path"] in {"assets/generated/ch1-hero.png", "assets/bilibili-cover-draft.png"}
    card_slots = [item for item in payload["sequence"] if item["asset_path"] == "assets/graphics/card-01-hook.png"]
    assert not card_slots or all(item["motion_preset"] == "static_hold" for item in card_slots)


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg/ffprobe required")
def test_build_render_plan_autogenerates_design_artifacts_and_uses_them(tmp_path: Path) -> None:
    """Render plan should auto-create and consume subtitle/audio design artifacts."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "build_render_plan.py"
    )

    project_root = make_media_package(tmp_path / "render-design-package")
    source_video = project_root / "content" / "final-cut" / "pilot-v1.mp4"
    voiceover_audio = project_root / "content" / "postproduction" / "minimax-output" / "voice.mp3"
    subtitles = project_root / "content" / "postproduction" / "subtitles.srt"

    content_packet = {
        "platforms": ["bilibili"],
        "deliverable_type": "midlong-video",
        "duration_target": "06:10-06:50",
        "subtitle_package": {
            "style": "简体中文，按意群断句，单行 14-20 字优先",
            "notes": ["关键句上屏：四步框架"],
        },
        "beat_sheet": [
            {"time_range": "00:00-00:40", "beat": "hook", "purpose": "先打狠句。"},
            {"time_range": "03:40-05:20", "beat": "framework", "purpose": "交付四步框架。"},
        ],
        "chapter_outline": [
            {"chapter_id": "ch1", "title": "四步框架"},
        ],
    }
    (project_root / "content" / "bilibili-midform-video.json").write_text(
        json.dumps(content_packet, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

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
            "4",
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
            "4",
            "-c:a",
            "mp3",
            str(voiceover_audio),
        ],
        repo_root,
    )
    subtitles.write_text(
        "\n".join(
            [
                "1",
                "00:00:00,000 --> 00:00:01,500",
                "什么都知道，就是不敢决定。",
                "",
                "2",
                "00:00:01,500 --> 00:00:03,500",
                "这时候四步框架才有用。",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "audio-cue-sheet.json").write_text(
        json.dumps({"bgm_tracks": [], "sfx_cues": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "scene-manifest.json").write_text(
        json.dumps(
            {
                "scenes": [
                    {
                        "scene_id": "scene-01-ch1",
                        "chapter_id": "ch1",
                        "scene_title": "四步框架",
                        "scene_goal": "交付四步框架",
                        "primary_asset": {"path": "assets/graphics/card-01.png", "type": "graphics-card"},
                        "supporting_assets": [],
                        "emphasis_fx": [{"type": "typewriter_quote", "text": "四步框架"}],
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "emphasis-fx-plan.json").write_text(
        json.dumps({"scene_fx": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "transition-plan.json").write_text(
        json.dumps({"transitions": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "auto-base-cut-plan.json").write_text(
        json.dumps(
            {
                "sequence": [
                    {
                        "slot_index": 0,
                        "slot_start": 0.0,
                        "slot_end": 2.0,
                        "asset_path": "assets/graphics/card-01.png",
                        "typewriter_text": "开头狠句",
                        "typewriter_start_offset_seconds": 0.0,
                    },
                    {
                        "slot_index": 1,
                        "slot_start": 2.3,
                        "slot_end": 4.0,
                        "asset_path": "assets/graphics/card-02.png",
                        "typewriter_text": "四步框架",
                        "typewriter_start_offset_seconds": 0.1,
                    },
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    run_command([sys.executable, str(script_path), "--project-root", str(project_root)], repo_root)

    style_pack = json.loads((project_root / "content" / "postproduction" / "subtitle-style-pack.json").read_text(encoding="utf-8"))
    cue_sheet = json.loads((project_root / "content" / "postproduction" / "audio-cue-sheet.json").read_text(encoding="utf-8"))
    plan = json.loads((project_root / "content" / "postproduction" / "render-plan.json").read_text(encoding="utf-8"))
    emphasis_plan = json.loads((project_root / "content" / "postproduction" / "emphasis-fx-plan.json").read_text(encoding="utf-8"))

    assert plan["subtitle_style"] == style_pack["ass_force_style"]
    assert plan["mix"]["bgm_tracks"] == cue_sheet["bgm_tracks"]
    assert plan["mix"]["sfx_cues"][: len(cue_sheet["sfx_cues"])] == cue_sheet["sfx_cues"]
    assert plan["context"]["subtitle_style_pack"] == "content/postproduction/subtitle-style-pack.json"
    assert plan["context"]["audio_cue_sheet"] == "content/postproduction/audio-cue-sheet.json"
    assert "target_fps" in plan["retime"]
    assert plan["preset"] in {"medium", "veryfast"}
    assert plan["crf"] in {20, 21}
    assert cue_sheet["bgm_tracks"]
    assert cue_sheet["sfx_cues"]
    assert emphasis_plan["scene_fx"]
    assert any(cue["label"].startswith("typewriter_") for cue in plan["mix"]["sfx_cues"])


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg/ffprobe required")
def test_build_render_plan_rebuilds_stale_auto_base_cut_in_rebuild_timeline_mode(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "build_render_plan.py"
    )

    project_root = make_media_package(tmp_path / "stale-auto-base-cut-package", assembly_strategy="rebuild_timeline")
    source_video = project_root / "content" / "final-cut" / "pilot-v1.mp4"
    auto_base_cut = project_root / "content" / "postproduction" / "auto-base-cut.mp4"
    voiceover_audio = project_root / "content" / "postproduction" / "minimax-output" / "voice.mp3"
    subtitles = project_root / "content" / "postproduction" / "subtitles.srt"
    graphics_dir = project_root / "assets" / "graphics"
    graphics_dir.mkdir(parents=True, exist_ok=True)

    run_command(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=320x240:rate=30",
            "-t",
            "4",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
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
            "color=c=black:s=320x240:rate=30",
            "-t",
            "4",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(auto_base_cut),
        ],
        repo_root,
    )
    make_audio(voiceover_audio, duration_seconds=4.0, frequency=880, workdir=repo_root)
    make_color_png(project_root / "assets" / "bilibili-cover-draft.png", color="black", workdir=repo_root)
    make_color_png(graphics_dir / "card-01-hook.png", color="red", workdir=repo_root)
    subtitles.write_text(
        "\n".join(
            [
                "1",
                "00:00:00,000 --> 00:00:02,000",
                "平台不是更懂你。",
                "",
                "2",
                "00:00:02,000 --> 00:00:04,000",
                "它只是更会让你停下来看。",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (project_root / "assets" / "scene-asset-plan.json").write_text(
        json.dumps(
            {
                "chapters": [
                    {
                        "chapter_id": "ch1",
                        "proof_asset": {"path": "assets/graphics/card-01-hook.png", "type": "graphics-card"},
                        "supporting_b_roll": [],
                        "fallback_graphics": ["assets/graphics/card-01-hook.png"],
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "auto-base-cut-plan.json").write_text(
        json.dumps({"sequence": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    old_timestamp = time.time() - 30
    os.utime(auto_base_cut, (old_timestamp, old_timestamp))
    os.utime(project_root / "content" / "postproduction" / "auto-base-cut-plan.json", (old_timestamp, old_timestamp))
    (project_root / "content" / "postproduction" / "scene-manifest.json").write_text(
        json.dumps(
            {
                "scenes": [
                    {
                        "scene_id": "scene-01-ch1",
                        "chapter_id": "ch1",
                        "scene_title": "开场问题",
                        "scene_goal": "先给冲突和异常点",
                        "primary_asset": {"path": "assets/graphics/card-01-hook.png", "type": "graphics-card"},
                        "supporting_assets": [],
                        "emphasis_fx": [{"type": "typewriter_quote", "text": "平台不是更懂你"}],
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "emphasis-fx-plan.json").write_text(
        json.dumps({"scene_fx": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "transition-plan.json").write_text(
        json.dumps({"transitions": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "audio-cue-sheet.json").write_text(
        json.dumps({"bgm_tracks": [], "sfx_cues": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    run_command([sys.executable, str(script_path), "--project-root", str(project_root)], repo_root)

    plan = json.loads((project_root / "content" / "postproduction" / "render-plan.json").read_text(encoding="utf-8"))
    assert plan["source_video"] == "content/postproduction/auto-base-cut.mp4"


def test_build_visual_timeline_filter_helpers_do_not_add_default_fades() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "build_visual_timeline.py"
    )
    module = SourceFileLoader("build_visual_timeline_test", str(script_path)).load_module()

    image_filter = module.image_filter(
        asset_path="assets/graphics/card-01.png",
        width=1920,
        height=1080,
        fps=30,
        duration=4.0,
        motion_preset="static_hold",
        motion_zoom_ratio=1.0,
        typewriter_text=None,
        typewriter_anchor=None,
        typewriter_chars_per_second=None,
        typewriter_start_offset_seconds=None,
        typewriter_duration_seconds=None,
    )
    video_filter = module.video_filter(
        width=1920,
        height=1080,
        fps=30,
        duration=4.0,
        motion_preset="push_left",
        motion_zoom_ratio=1.08,
        typewriter_text=None,
        typewriter_anchor=None,
        typewriter_chars_per_second=None,
        typewriter_start_offset_seconds=None,
        typewriter_duration_seconds=None,
    )

    assert "fade=t=in" not in image_filter
    assert "fade=t=out" not in image_filter
    assert "fade=t=in" not in video_filter
    assert "fade=t=out" not in video_filter


def test_build_visual_timeline_image_motion_oversamples_before_blend() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "build_visual_timeline.py"
    )
    module = SourceFileLoader("build_visual_timeline_image_motion_test", str(script_path)).load_module()

    moving_image_filter = module.image_filter(
        asset_path="assets/generated/ch1-hero.png",
        width=1920,
        height=1080,
        fps=30,
        duration=5.2,
        motion_preset="push_left",
        motion_zoom_ratio=1.08,
        typewriter_text=None,
        typewriter_anchor=None,
        typewriter_chars_per_second=None,
        typewriter_start_offset_seconds=None,
        typewriter_duration_seconds=None,
    )

    assert "fps=60" in moving_image_filter
    assert "tmix=frames=2:weights='1 1'" in moving_image_filter


def test_build_visual_timeline_skips_typewriter_overlay_when_drawtext_unavailable() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "build_visual_timeline.py"
    )
    module = SourceFileLoader("build_visual_timeline_drawtext_test", str(script_path)).load_module()
    module.ffmpeg_filter_available.cache_clear()
    original_probe = module.ffmpeg_filter_available
    module.ffmpeg_filter_available = lambda filter_name: False

    try:
        filters = module.typewriter_drawtext_filters(
            text="平台不是更懂你",
            duration=2.0,
            anchor="upper_left",
            chars_per_second=12,
            start_offset_seconds=0.0,
            duration_seconds=1.8,
        )
    finally:
        module.ffmpeg_filter_available = original_probe

    assert filters == []


def test_motion_profile_rotates_keyart_and_proof_presets_without_overzoom() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "build_visual_timeline.py"
    )
    module = SourceFileLoader("build_visual_timeline_motion_test", str(script_path)).load_module()

    keyart_profiles = [
        module.motion_profile(
            index,
            "keyart",
            5.2,
            asset_type="image",
            asset_path=Path(f"/tmp/ch1-hero-{index}.png"),
            effects=[],
        )
        for index in range(6)
    ]
    proof_profiles = [
        module.motion_profile(
            index,
            "proof",
            7.4,
            asset_type="image",
            asset_path=Path(f"/tmp/ch2-proof-{index}.png"),
            effects=[],
        )
        for index in range(6)
    ]

    assert len({profile["preset"] for profile in keyart_profiles}) >= 3
    assert len({profile["preset"] for profile in proof_profiles}) >= 3
    assert all(profile["zoom_ratio"] <= 1.115 for profile in [*keyart_profiles, *proof_profiles])


def test_build_visual_timeline_penalizes_white_background_demo_clips() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "build_visual_timeline.py"
    )
    module = SourceFileLoader("build_visual_timeline_penalty_test", str(script_path)).load_module()

    white_penalty = module.low_value_video_penalty(
        title="a black iphone with a white screen and a white background",
        page_url="https://www.pexels.com/video/a-black-iphone-with-a-white-screen-and-a-white-background-5083551/",
        tags=[],
    )
    neutral_penalty = module.low_value_video_penalty(
        title="person reacting to content on smartphone",
        page_url="https://www.pexels.com/video/person-reacting-to-content-on-smartphone/",
        tags=["phone", "reaction"],
    )
    melodrama_penalty = module.low_value_video_penalty(
        title="a sad man in front of a computer with message on screen",
        page_url="https://www.pexels.com/video/a-sad-man-in-front-of-a-computer-with-message-on-screen-9831692/",
        tags=[],
        query="sad man in front of a computer with message on screen",
        preview_image_url="https://images.pexels.com/videos/9831692/achievement-adult-ageism-alone-9831692.jpeg",
    )

    assert white_penalty <= -90
    assert neutral_penalty == 0
    assert melodrama_penalty <= -70


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg/ffprobe required")
def test_build_visual_timeline_prefers_generated_opening_video_when_cover_duplicates_keyart(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "build_visual_timeline.py"
    )

    project_root = make_media_package(tmp_path / "generated-opening-video-package", assembly_strategy="rebuild_timeline")
    voiceover_audio = project_root / "content" / "postproduction" / "minimax-output" / "voice.mp3"
    subtitles = project_root / "content" / "postproduction" / "subtitles.srt"
    prebake_dir = project_root / "content" / "postproduction" / "minimax-output" / "visual-prebake" / "images"
    prebake_video_dir = project_root / "content" / "postproduction" / "minimax-output" / "visual-prebake" / "videos"
    (project_root / "assets").mkdir(parents=True, exist_ok=True)
    prebake_dir.mkdir(parents=True, exist_ok=True)
    prebake_video_dir.mkdir(parents=True, exist_ok=True)

    make_audio(voiceover_audio, duration_seconds=4.2, frequency=880, workdir=repo_root)
    make_color_png(project_root / "assets" / "bilibili-cover-draft.png", color="black", workdir=repo_root)
    cover_bytes = (project_root / "assets" / "bilibili-cover-draft.png").read_bytes()
    (prebake_dir / "001_hook.jpg").write_bytes(cover_bytes)
    make_video(prebake_video_dir / "hero-open.mp4", color="blue", duration_seconds=5.5, workdir=repo_root)
    subtitles.write_text(
        "\n".join(
            [
                "1",
                "00:00:00,000 --> 00:00:04,200",
                "平台不是更懂你，它更懂怎么把你困在像你的东西里。",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (project_root / "content" / "bilibili-midform-video.json").write_text(
        json.dumps(
            {
                "content_id": "pilot",
                "platforms": ["bilibili"],
                "deliverable_type": "midlong-video",
                "chapter_outline": [
                    {
                        "chapter_id": "ch1",
                        "title": "开场问题",
                        "summary": "平台不是更懂你。",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "assets" / "scene-asset-plan.json").write_text(
        json.dumps(
            {
                "chapters": [
                    {
                        "chapter_id": "ch1",
                        "proof_asset": {
                            "path": "content/postproduction/minimax-output/visual-prebake/images/001_hook.jpg",
                            "type": "generated-keyart",
                        },
                        "supporting_b_roll": [],
                        "fallback_graphics": ["content/postproduction/minimax-output/visual-prebake/images/001_hook.jpg"],
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "assets" / "generation-ledger.json").write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "slot_id": "shot-hero-open",
                        "chapter_id": "ch1",
                        "generation_type": "image-to-video",
                        "status": "success",
                        "asset_path": "content/postproduction/minimax-output/visual-prebake/videos/hero-open.mp4",
                        "duration_seconds": 5.5,
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "scene-manifest.json").write_text(
        json.dumps({"scenes": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "emphasis-fx-plan.json").write_text(
        json.dumps({"scene_fx": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
            "--voiceover-audio",
            "content/postproduction/minimax-output/voice.mp3",
            "--subtitles",
            "content/postproduction/subtitles.srt",
        ],
        repo_root,
    )

    payload = json.loads((project_root / "content" / "postproduction" / "auto-base-cut-plan.json").read_text(encoding="utf-8"))
    assert payload["sequence"][0]["asset_type"] == "video"
    assert payload["sequence"][0]["asset_source"] == "generation-ledger"
    assert payload["sequence"][0]["asset_path"].endswith("content/postproduction/minimax-output/visual-prebake/videos/hero-open.mp4")


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg/ffprobe required")
def test_build_visual_timeline_aligns_typewriter_to_matching_subtitle_slot(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "build_visual_timeline.py"
    )

    project_root = make_media_package(tmp_path / "typewriter-alignment-package", assembly_strategy="rebuild_timeline")
    voiceover_audio = project_root / "content" / "postproduction" / "minimax-output" / "voice.mp3"
    subtitles = project_root / "content" / "postproduction" / "subtitles.srt"
    graphics_dir = project_root / "assets" / "graphics"
    generated_dir = project_root / "assets" / "generated"
    graphics_dir.mkdir(parents=True, exist_ok=True)
    generated_dir.mkdir(parents=True, exist_ok=True)

    make_audio(voiceover_audio, duration_seconds=8.8, frequency=880, workdir=repo_root)
    make_color_png(project_root / "assets" / "bilibili-cover-draft.png", color="black", workdir=repo_root)
    make_color_png(graphics_dir / "card-01-hook.png", color="red", workdir=repo_root)
    make_color_png(generated_dir / "ch1-hero.png", color="green", workdir=repo_root)
    subtitles.write_text(
        "\n".join(
            [
                "1",
                "00:00:00,000 --> 00:00:02,000",
                "先给背景。",
                "",
                "2",
                "00:00:02,000 --> 00:00:04,200",
                "继续铺垫。",
                "",
                "3",
                "00:00:04,200 --> 00:00:06,400",
                "你就会发现，平台没有在帮你逼近真相。",
                "",
                "4",
                "00:00:06,400 --> 00:00:08,800",
                "后面继续展开。",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (project_root / "content" / "bilibili-midform-video.json").write_text(
        json.dumps(
            {
                "content_id": "pilot",
                "platforms": ["bilibili"],
                "deliverable_type": "midlong-video",
                "chapter_outline": [
                    {
                        "chapter_id": "ch1",
                        "title": "开场问题",
                        "chapter_goal": "先给冲突和异常点",
                        "summary": "平台没有在帮你逼近真相。",
                    }
                ],
                "hook_hypotheses": ["平台不是更懂你。"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "assets" / "scene-asset-plan.json").write_text(
        json.dumps(
            {
                "chapters": [
                    {
                        "chapter_id": "ch1",
                        "proof_asset": {"path": "assets/generated/ch1-hero.png", "type": "generated-keyart"},
                        "supporting_b_roll": [],
                        "fallback_graphics": ["assets/generated/ch1-hero.png", "assets/graphics/card-01-hook.png"],
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction").mkdir(parents=True, exist_ok=True)
    (project_root / "content" / "postproduction" / "scene-manifest.json").write_text(
        json.dumps(
            {
                "scenes": [
                    {
                        "scene_id": "scene-01-ch1",
                        "chapter_id": "ch1",
                        "scene_title": "开场问题",
                        "scene_goal": "先给冲突和异常点",
                        "primary_asset": {"path": "assets/generated/ch1-hero.png", "type": "generated-keyart"},
                        "supporting_assets": [],
                        "emphasis_fx": [
                            {
                                "type": "typewriter_quote",
                                "text": "平台没有在帮你逼近真相",
                                "anchor": "upper_center",
                                "chars_per_second": 8,
                                "start_offset_seconds": 0.0,
                                "duration_seconds": 2.5,
                                "target_role": "keyart",
                            }
                        ],
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "emphasis-fx-plan.json").write_text(
        json.dumps({"scene_fx": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
            "--voiceover-audio",
            "content/postproduction/minimax-output/voice.mp3",
            "--subtitles",
            "content/postproduction/subtitles.srt",
        ],
        repo_root,
    )

    payload = json.loads((project_root / "content" / "postproduction" / "auto-base-cut-plan.json").read_text(encoding="utf-8"))
    typewriter_slots = [item for item in payload["sequence"] if item["typewriter_text"] == "平台没有在帮你逼近真相"]
    assert typewriter_slots
    slot = typewriter_slots[0]
    assert slot["slot_start"] <= 4.2 <= slot["slot_end"]
    assert slot["typewriter_start_offset_seconds"] > (4.2 - slot["slot_start"])


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg/ffprobe required")
def test_build_visual_timeline_keeps_typewriter_alignment_within_chapter_window(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "build_visual_timeline.py"
    )

    project_root = make_media_package(tmp_path / "typewriter-chapter-window-package", assembly_strategy="rebuild_timeline")
    voiceover_audio = project_root / "content" / "postproduction" / "minimax-output" / "voice.mp3"
    subtitles = project_root / "content" / "postproduction" / "subtitles.srt"
    generated_dir = project_root / "assets" / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)

    make_audio(voiceover_audio, duration_seconds=8.4, frequency=770, workdir=repo_root)
    make_color_png(generated_dir / "ch1-proof.png", color="purple", workdir=repo_root)
    make_color_png(generated_dir / "ch2-proof.png", color="orange", workdir=repo_root)
    subtitles.write_text(
        "\n".join(
            [
                "1",
                "00:00:00,000 --> 00:00:02,100",
                "前面先讲输出动作，但还没有框架。",
                "",
                "2",
                "00:00:02,100 --> 00:00:04,200",
                "继续解释为什么人会误判自己快会了。",
                "",
                "3",
                "00:00:04,200 --> 00:00:06,300",
                "这时候再给你输出、暴露、反馈、结果四层。",
                "",
                "4",
                "00:00:06,300 --> 00:00:08,400",
                "最后把它压成一次真实验证。",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (project_root / "content" / "bilibili-midform-video.json").write_text(
        json.dumps(
            {
                "content_id": "pilot",
                "platforms": ["bilibili"],
                "deliverable_type": "midlong-video",
                "chapter_outline": [
                    {"chapter_id": "ch1", "title": "前半段", "chapter_goal": "先讲症状", "summary": "症状"},
                    {"chapter_id": "ch2", "title": "框架段", "chapter_goal": "再讲四层框架", "summary": "框架"},
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "assets" / "scene-asset-plan.json").write_text(
        json.dumps(
            {
                "chapters": [
                    {
                        "chapter_id": "ch1",
                        "proof_asset": {"path": "assets/generated/ch1-proof.png", "type": "generated-keyart"},
                        "supporting_b_roll": [],
                        "fallback_graphics": ["assets/generated/ch1-proof.png"],
                    },
                    {
                        "chapter_id": "ch2",
                        "proof_asset": {"path": "assets/generated/ch2-proof.png", "type": "generated-keyart"},
                        "supporting_b_roll": [],
                        "fallback_graphics": ["assets/generated/ch2-proof.png"],
                    },
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction").mkdir(parents=True, exist_ok=True)
    (project_root / "content" / "postproduction" / "scene-manifest.json").write_text(
        json.dumps(
            {
                "scenes": [
                    {
                        "scene_id": "scene-01-ch1",
                        "chapter_id": "ch1",
                        "scene_title": "前半段",
                        "scene_goal": "先讲症状",
                        "primary_asset": {"path": "assets/generated/ch1-proof.png", "type": "generated-keyart"},
                        "supporting_assets": [],
                        "emphasis_fx": [],
                    },
                    {
                        "scene_id": "scene-02-ch2",
                        "chapter_id": "ch2",
                        "scene_title": "框架段",
                        "scene_goal": "再讲四层框架",
                        "primary_asset": {"path": "assets/generated/ch2-proof.png", "type": "generated-keyart"},
                        "supporting_assets": [],
                        "emphasis_fx": [
                            {
                                "type": "typewriter_quote",
                                "text": "输出 / 暴露 / 反馈 / 结果",
                                "anchor": "upper_center",
                                "chars_per_second": 9,
                                "start_offset_seconds": 0.0,
                                "duration_seconds": 2.8,
                            }
                        ],
                    },
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "postproduction" / "emphasis-fx-plan.json").write_text(
        json.dumps({"scene_fx": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
            "--voiceover-audio",
            "content/postproduction/minimax-output/voice.mp3",
            "--subtitles",
            "content/postproduction/subtitles.srt",
        ],
        repo_root,
    )

    payload = json.loads((project_root / "content" / "postproduction" / "auto-base-cut-plan.json").read_text(encoding="utf-8"))
    typewriter_slots = [item for item in payload["sequence"] if item["typewriter_text"] == "输出 / 暴露 / 反馈 / 结果"]
    assert typewriter_slots
    slot = typewriter_slots[0]
    assert slot["slot_start"] >= 4.0
    assert slot["slot_start"] <= 6.3


def test_build_visual_timeline_prefers_chapter_markers_for_target_allocation(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "build_visual_timeline.py"
    )
    module = SourceFileLoader("build_visual_timeline_markers_test", str(script_path)).load_module()

    project_root = make_media_package(tmp_path / "chapter-marker-package", assembly_strategy="rebuild_timeline")
    (project_root / "content" / "bilibili-midform-video.json").write_text(
        json.dumps(
            {
                "content_id": "pilot",
                "platforms": ["bilibili"],
                "deliverable_type": "midlong-video",
                "chapter_outline": [
                    {"chapter_id": "ch1", "title": "第一章"},
                    {"chapter_id": "ch2", "title": "第二章"},
                ],
                "chapter_markers": [
                    {"timecode": "00:00", "title": "开场"},
                    {"timecode": "00:10", "title": "第一章"},
                    {"timecode": "00:20", "title": "第二章"},
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    slots = [
        {"start": 0.0, "end": 6.0, "duration": 6.0},
        {"start": 10.0, "end": 15.0, "duration": 5.0},
        {"start": 20.0, "end": 25.0, "duration": 5.0},
    ]
    targets = module.build_chapter_targets(
        slots,
        ["ch1", "ch2"],
        [],
        has_cover=True,
        project_root=project_root,
    )

    assert targets == ["opening", "ch1", "ch2"]


def test_build_visual_timeline_infers_chapter_markers_from_voiceover_script_and_subtitles(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "build_visual_timeline.py"
    )
    module = SourceFileLoader("build_visual_timeline_script_markers_test", str(script_path)).load_module()

    project_root = make_media_package(tmp_path / "script-marker-package", assembly_strategy="rebuild_timeline")
    (project_root / "content" / "bilibili-midform-video.json").write_text(
        json.dumps(
            {
                "content_id": "pilot",
                "platforms": ["bilibili"],
                "deliverable_type": "midlong-video",
                "chapter_outline": [
                    {"chapter_id": "ch1", "title": "第一章"},
                    {"chapter_id": "ch2", "title": "第二章"},
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "voiceover-script.md").write_text(
        "\n".join(
            [
                "# Voiceover Script",
                "",
                "## Opening",
                "",
                "开场问题。",
                "",
                "## Chapter 1",
                "",
                "第一章第一句，",
                "这是完整说明。",
                "",
                "## Chapter 2",
                "",
                "第二章开头，",
                "进入下一段。",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    slots = [
        {"start": 0.0, "end": 6.0, "duration": 6.0},
        {"start": 10.0, "end": 15.0, "duration": 5.0},
        {"start": 20.0, "end": 25.0, "duration": 5.0},
    ]
    subtitle_cues = [
        {"start": 0.0, "end": 2.0, "duration": 2.0, "text": "开场问题。"},
        {"start": 10.0, "end": 12.0, "duration": 2.0, "text": "第一章第一句，这是完整说明。"},
        {"start": 20.0, "end": 22.0, "duration": 2.0, "text": "第二章开头，进入下一段。"},
    ]
    targets = module.build_chapter_targets(
        slots,
        ["ch1", "ch2"],
        [],
        has_cover=True,
        project_root=project_root,
        subtitle_cues=subtitle_cues,
    )

    assert targets == ["opening", "ch1", "ch2"]


def test_build_visual_timeline_offsets_script_chapters_after_opening_without_cover(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "build_visual_timeline.py"
    )
    module = SourceFileLoader("build_visual_timeline_script_markers_no_cover_test", str(script_path)).load_module()

    project_root = make_media_package(tmp_path / "script-marker-no-cover-package", assembly_strategy="rebuild_timeline")
    (project_root / "content" / "bilibili-midform-video.json").write_text(
        json.dumps(
            {
                "content_id": "pilot",
                "platforms": ["bilibili"],
                "deliverable_type": "midlong-video",
                "chapter_outline": [
                    {"chapter_id": "ch1", "title": "开场反直觉"},
                    {"chapter_id": "ch2", "title": "症状与代价"},
                    {"chapter_id": "ch3", "title": "三层错觉机制"},
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "content" / "voiceover-script.md").write_text(
        "\n".join(
            [
                "# Voiceover Script",
                "",
                "## Opening",
                "",
                "开场问题。",
                "",
                "## Chapter 1",
                "",
                "第一章第一句，",
                "这是完整说明。",
                "",
                "## Chapter 2",
                "",
                "第二章开头，",
                "进入下一段。",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    slots = [
        {"start": 0.0, "end": 6.0, "duration": 6.0},
        {"start": 10.0, "end": 15.0, "duration": 5.0},
        {"start": 20.0, "end": 25.0, "duration": 5.0},
    ]
    subtitle_cues = [
        {"start": 0.0, "end": 2.0, "duration": 2.0, "text": "开场问题。"},
        {"start": 10.0, "end": 12.0, "duration": 2.0, "text": "第一章第一句，这是完整说明。"},
        {"start": 20.0, "end": 22.0, "duration": 2.0, "text": "第二章开头，进入下一段。"},
    ]
    targets = module.build_chapter_targets(
        slots,
        ["ch1", "ch2", "ch3"],
        [],
        has_cover=False,
        project_root=project_root,
        subtitle_cues=subtitle_cues,
    )

    assert targets == ["ch1", "ch2", "ch3"]


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg/ffprobe required")
def test_collect_video_assets_includes_generation_ledger_outputs(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "build_visual_timeline.py"
    )
    module = SourceFileLoader("build_visual_timeline_generation_ledger_test", str(script_path)).load_module()

    project_root = make_media_package(tmp_path / "generation-ledger-video-package", assembly_strategy="rebuild_timeline")
    video_path = project_root / "content" / "postproduction" / "minimax-output" / "visual-prebake" / "videos" / "ch1-hero.mp4"
    video_path.parent.mkdir(parents=True, exist_ok=True)
    (project_root / "assets").mkdir(parents=True, exist_ok=True)
    make_video(video_path, color="blue", duration_seconds=1.2, workdir=repo_root)
    (project_root / "assets" / "generation-ledger.json").write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "slot_id": "shot-hook-hero",
                        "chapter_id": "ch1",
                        "generation_type": "image-to-video",
                        "status": "success",
                        "reason": "AI hero shot",
                        "asset_path": "content/postproduction/minimax-output/visual-prebake/videos/ch1-hero.mp4",
                        "duration_seconds": 1.2,
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "sources" / "source-manifest.json").parent.mkdir(parents=True, exist_ok=True)
    (project_root / "sources" / "source-manifest.json").write_text(json.dumps({"source_manifest": []}) + "\n", encoding="utf-8")
    (project_root / "sources" / "source-shortlist.json").write_text(json.dumps({"results": []}) + "\n", encoding="utf-8")
    (project_root / "sources" / "exploration-shortlist.json").write_text(json.dumps({"results": []}) + "\n", encoding="utf-8")
    (project_root / "sources" / "exploration-ingest-manifest.json").write_text(json.dumps({"ingested_assets": []}) + "\n", encoding="utf-8")
    (project_root / "assets" / "scene-asset-plan.json").write_text(json.dumps({"chapters": []}) + "\n", encoding="utf-8")

    assets = module.collect_video_assets(project_root)

    assert any(item["source"] == "generation-ledger" and item["clip_id"] == "shot-hook-hero" for item in assets)


def test_licensed_footage_workflow_resolves_ytdlp_to_absolute_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "licensed-footage-sourcing"
        / "scripts"
        / "run_external_footage_workflow.py"
    )
    module = SourceFileLoader("licensed_footage_workflow_ytdlp_test", str(script_path)).load_module()

    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir(parents=True, exist_ok=True)
    fake_binary = fake_bin_dir / "yt-dlp"
    fake_binary.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    fake_binary.chmod(0o755)
    monkeypatch.setenv("PATH", str(fake_bin_dir))

    provider = module.YtDlpProvider(binary="yt-dlp")

    assert provider._binary == str(fake_binary.resolve())


def test_licensed_footage_workflow_preserves_clip_coverage_requirements() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "licensed-footage-sourcing"
        / "scripts"
        / "run_external_footage_workflow.py"
    )
    module = SourceFileLoader("licensed_footage_workflow_coverage_test", str(script_path)).load_module()

    content_packet = {
        "clip_sourcing_brief": [
            {
                "chapter_id": "ch1",
                "shot_intent": "测试章节",
                "queries": ["focused desk late night pressure"],
                "required_coverage_seconds": 8,
                "minimum_candidates": 3,
                "max_single_asset_seconds": 6,
                "minimum_match_score": 0.72,
                "fallback": "回退到 visual-prebake。",
            }
        ]
    }

    normalized = module.normalize_clip_briefs(content_packet)

    assert normalized[0]["required_coverage_seconds"] == 8.0
    assert normalized[0]["minimum_candidates"] == 3
    assert normalized[0]["max_single_asset_seconds"] == 6.0
    assert normalized[0]["minimum_match_score"] == 0.72


def test_licensed_footage_workflow_penalizes_ytdlp_tutorial_titles_for_broll() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "licensed-footage-sourcing"
        / "scripts"
        / "run_external_footage_workflow.py"
    )
    module = SourceFileLoader("licensed_footage_workflow_scoring_test", str(script_path)).load_module()

    chapter = {
        "chapter_id": "ch1",
        "shot_intent": "测试视觉素材相关性",
        "queries": ["keyboard desk setup"],
        "provider_queries": {"yt-dlp": ["cinematic keyboard desk b roll"]},
        "must_have_terms": ["keyboard", "desk"],
        "avoid_terms": [],
        "fallback": "fallback",
        "minimum_match_score": 0.0,
    }
    tutorial_result = module.SearchResult(
        provider="yt-dlp",
        provider_asset_id="tutorial-001",
        title="Keyboard desk setup tutorial with creator tips",
        page_url="https://video.example.test/watch/tutorial-001",
        download_url="https://video.example.test/watch/tutorial-001",
        preview_image_url=None,
        duration_seconds=11,
        width=1920,
        height=1080,
        tags=["keyboard", "desk", "setup", "tutorial", "tips"],
        source_type="unknown-license",
        license_status="hold",
        license_basis="test",
        attribution_required=True,
        attribution_text="test",
        usage_notes="test",
    )
    broll_result = module.SearchResult(
        provider="yt-dlp",
        provider_asset_id="broll-001",
        title="Cinematic keyboard desk b roll",
        page_url="https://video.example.test/watch/broll-001",
        download_url="https://video.example.test/watch/broll-001",
        preview_image_url=None,
        duration_seconds=11,
        width=1920,
        height=1080,
        tags=["cinematic", "keyboard", "desk", "b", "roll"],
        source_type="unknown-license",
        license_status="hold",
        license_basis="test",
        attribution_required=True,
        attribution_text="test",
        usage_notes="test",
    )

    tutorial_score = module.score_result("cinematic keyboard desk b roll", tutorial_result, chapter)
    broll_score = module.score_result("cinematic keyboard desk b roll", broll_result, chapter)

    assert broll_score > tutorial_score


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg/ffprobe required")
def test_run_render_workflow_rebuilds_timeline_without_existing_source_video(tmp_path: Path) -> None:
    """The workflow runner can auto-build a base cut when rebuild_timeline has no rough cut input."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "run_render_workflow.py"
    )

    project_root = make_media_package(tmp_path / "media-package", assembly_strategy="rebuild_timeline")
    voiceover_audio = project_root / "content" / "postproduction" / "minimax-output" / "voice.mp3"
    segment_audio_dir = project_root / "content" / "postproduction" / "minimax-output" / "tmp"
    segment_audio_dir.mkdir(parents=True, exist_ok=True)
    write_voiceover_segments(
        project_root,
        [
            "先把问题压回现实。",
            "不要再把继续比较误当成继续思考。",
        ],
    )

    make_audio(voiceover_audio, duration_seconds=2.2, frequency=880, workdir=repo_root)
    make_audio(segment_audio_dir / "segment_0000.mp3", duration_seconds=1.0, frequency=620, workdir=repo_root)
    make_audio(segment_audio_dir / "segment_0001.mp3", duration_seconds=1.2, frequency=720, workdir=repo_root)

    graphics_dir = project_root / "assets" / "graphics"
    graphics_dir.mkdir(parents=True, exist_ok=True)
    make_color_png(graphics_dir / "card-01-hook.png", color="red", workdir=repo_root)
    make_color_png(graphics_dir / "card-02-framework.png", color="blue", workdir=repo_root)
    (project_root / "assets" / "graphics" / "graphics-asset-brief.json").write_text(
        json.dumps(
            {
                "cards": [
                    {"card": 1, "output_path": "assets/graphics/card-01-hook.png", "evidence": "Chapter 1"},
                    {"card": 2, "output_path": "assets/graphics/card-02-framework.png", "evidence": "Chapter 2"},
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    stock_clip = project_root / "stock-ch1.mp4"
    make_video(stock_clip, color="green", duration_seconds=2.6, workdir=repo_root)
    (project_root / "sources").mkdir(parents=True, exist_ok=True)
    (project_root / "sources" / "source-manifest.json").write_text(
        json.dumps(
            {
                "source_manifest": [
                    {
                        "clip_id": "stock-1",
                        "chapter_id": "ch1",
                        "license_status": "approved",
                        "duration_seconds": 2.6,
                        "local_asset_path": str(stock_clip),
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
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
    assert summary["assembly_strategy"] == "rebuild_timeline"
    assert summary["final_cut"].endswith("content/final-cut/pilot-v1-narrated.mp4")

    auto_base_cut = project_root / "content" / "postproduction" / "auto-base-cut.mp4"
    auto_base_plan = project_root / "content" / "postproduction" / "auto-base-cut-plan.json"
    subtitles = project_root / "content" / "postproduction" / "subtitles.srt"
    final_cut = project_root / "content" / "final-cut" / "pilot-v1-narrated.mp4"

    assert auto_base_cut.exists()
    assert auto_base_plan.exists()
    assert subtitles.exists()
    assert final_cut.exists()

    render_plan = json.loads((project_root / "content" / "postproduction" / "render-plan.json").read_text(encoding="utf-8"))
    qa_report = json.loads((project_root / "review" / "assembly-qa-report.json").read_text(encoding="utf-8"))
    auto_base_payload = json.loads(auto_base_plan.read_text(encoding="utf-8"))
    assert render_plan["assembly_strategy"] == "rebuild_timeline"
    assert render_plan["source_video"] == "content/postproduction/auto-base-cut.mp4"
    assert render_plan["output_video"] == "content/final-cut/pilot-v1-narrated.mp4"
    assert render_plan["retime"]["target_fps"] == 60
    assert render_plan["preset"] == "medium"
    assert render_plan["crf"] == 20
    assert qa_report["status"] == "pass"
    assert auto_base_payload["quality"]["status"] == "pass"
    image_slot_count = auto_base_payload["quality"]["metrics"]["image_slot_count"]
    if image_slot_count:
        assert auto_base_payload["quality"]["metrics"]["image_motion_enabled_count"] == image_slot_count
        assert all(
            item["motion_preset"]
            for item in auto_base_payload["sequence"]
            if item["asset_type"] == "image"
        )
    else:
        assert auto_base_payload["quality"]["metrics"]["video_slot_count"] >= 1
    assert any(
        item.get("motion_preset")
        for item in auto_base_payload["sequence"]
        if item["asset_type"] == "video"
    )
