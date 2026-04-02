"""Tests for project-level media render workflow helpers."""

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from importlib.machinery import SourceFileLoader

import pytest


FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def run_command(command: list[str], workdir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=workdir, check=True, capture_output=True, text=True)


def make_media_package(tmp_path: Path, *, assembly_strategy: str | None = None) -> Path:
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
    assert payload["segments"]
    assert all(segment["emotion"] for segment in payload["segments"])
    assert all("pause_after_ms" in segment for segment in payload["segments"])
    assert {segment["scene_purpose"] for segment in payload["segments"]} >= {"hook", "proof", "framework"}


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
    assert payload["theme"] == "bilibili-midform-clean"
    assert payload["burn_in_mode"] == "hardsub"
    assert payload["highlight_rules"]["priority_phrases"] == ["什么都知道，就是不敢决定", "四步框架"]
    assert "FontName=" in payload["ass_force_style"]


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
    assert payload["chapter_audio_beats"][0]["beat"] == "hook"
    assert payload["chapter_audio_beats"][1]["start_seconds"] == 140.0
    cue_labels = [cue["label"] for cue in payload["sfx_cues"]]
    assert "typing_burst_hook_1" in cue_labels
    assert "typing_burst_hook_2" in cue_labels
    assert "typing_burst_hook_3" in cue_labels
    assert "typing_burst_framework_1" in cue_labels
    assert "typing_burst_framework_2" in cue_labels
    assert "typing_burst_framework_3" in cue_labels
    assert "ordinal_first" in cue_labels
    assert "ordinal_second" in cue_labels


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

    assert white_penalty <= -90
    assert neutral_penalty == 0


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
