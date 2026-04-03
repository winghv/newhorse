"""Tests for reference video subtitle ingest workflow."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def run_command(command: list[str], workdir: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(command, cwd=workdir, check=True, capture_output=True, text=True, env=merged_env)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_mock_ytdlp(root: Path) -> Path:
    script_path = root / "mock-yt-dlp.py"
    script_path.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
if "--dump-single-json" in args:
    if os.environ.get("MOCK_YTDLP_FAIL_DUMP") == "1":
        raise SystemExit(1)
    metadata_path = Path(os.environ["MOCK_YTDLP_METADATA"])
    print(metadata_path.read_text(encoding="utf-8"))
    raise SystemExit(0)

if "--write-subs" in args or "--write-auto-subs" in args:
    output_pattern = args[args.index("-o") + 1]
    language = args[args.index("--sub-langs") + 1]
    subtitle_text_path = Path(os.environ["MOCK_YTDLP_SUBTITLE_TEXT"])
    base = output_pattern.replace(".%(ext)s", "")
    output_path = Path(f"{base}.{language}.srt")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(subtitle_text_path.read_text(encoding="utf-8"), encoding="utf-8")
    raise SystemExit(0)

if "--extract-audio" in args:
    output_pattern = args[args.index("-o") + 1]
    audio_bytes_path = Path(os.environ["MOCK_YTDLP_AUDIO_BYTES"])
    base = output_pattern.replace(".%(ext)s", "")
    output_path = Path(f"{base}.mp3")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(audio_bytes_path.read_bytes())
    raise SystemExit(0)

raise SystemExit(1)
""",
        encoding="utf-8",
    )
    script_path.chmod(0o755)
    return script_path


def build_mock_asr(root: Path) -> Path:
    script_path = root / "mock-asr.py"
    script_path.write_text(
        """#!/usr/bin/env python3
import os
import sys
from pathlib import Path

args = sys.argv[1:]
input_audio = Path(args[0])
output_dir = Path(args[args.index("--output_dir") + 1])
output_dir.mkdir(parents=True, exist_ok=True)
stem = input_audio.stem

srt_text = Path(os.environ["MOCK_ASR_SRT"]).read_text(encoding="utf-8")
txt_text = Path(os.environ["MOCK_ASR_TXT"]).read_text(encoding="utf-8")
(output_dir / f"{stem}.srt").write_text(srt_text, encoding="utf-8")
(output_dir / f"{stem}.txt").write_text(txt_text, encoding="utf-8")
raise SystemExit(0)
""",
        encoding="utf-8",
    )
    script_path.chmod(0o755)
    return script_path


def test_ingest_reference_video_prefers_official_subtitles(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    project_root = tmp_path / "reference-package"
    metadata_path = tmp_path / "metadata.json"
    subtitle_text_path = tmp_path / "subtitle.srt"
    yt_dlp_bin = build_mock_ytdlp(tmp_path)

    write_json(
        metadata_path,
        {
            "id": "BV1YjwyzTEHB",
            "title": "平台越懂你，为什么你越难形成独立判断",
            "uploader": "Example Creator",
            "webpage_url": "https://www.bilibili.com/video/BV1YjwyzTEHB",
            "duration": 512,
            "subtitles": {"zh-CN": [{"ext": "json3"}]},
            "automatic_captions": {"en": [{"ext": "json3"}]},
        },
    )
    subtitle_text_path.write_text(
        "1\n00:00:00,000 --> 00:00:01,500\n平台不是更懂你\n\n2\n00:00:01,500 --> 00:00:03,000\n它更懂怎么困住你\n",
        encoding="utf-8",
    )

    result = run_command(
        [
            sys.executable,
            "extensions/skills/reference-video-ingest/scripts/ingest_reference_video.py",
            "--project-root",
            str(project_root),
            "--bvid",
            "BV1YjwyzTEHB",
            "--yt-dlp-bin",
            str(yt_dlp_bin),
        ],
        workdir=repo_root,
        env={
            "MOCK_YTDLP_METADATA": str(metadata_path),
            "MOCK_YTDLP_SUBTITLE_TEXT": str(subtitle_text_path),
        },
    )

    payload = json.loads(result.stdout)
    assert payload["status"] == "pass"
    assert payload["subtitle_track_type"] == "official"
    assert payload["language"] == "zh-CN"

    metadata = json.loads((project_root / "research" / "reference-video-metadata.json").read_text(encoding="utf-8"))
    assert metadata["video_id"] == "BV1YjwyzTEHB"
    assert metadata["selected_subtitle_track_type"] == "official"

    transcript_source = json.loads((project_root / "research" / "reference-transcript-source.json").read_text(encoding="utf-8"))
    assert transcript_source["status"] == "pass"
    assert transcript_source["subtitle_track_type"] == "official"
    assert transcript_source["subtitle_path"] == "research/reference-transcript.srt"
    assert transcript_source["transcript_path"] == "research/reference-transcript.md"

    transcript_markdown = (project_root / "research" / "reference-transcript.md").read_text(encoding="utf-8")
    assert "平台不是更懂你" in transcript_markdown
    assert "它更懂怎么困住你" in transcript_markdown


def test_ingest_reference_video_marks_needs_asr_when_no_subtitles(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    project_root = tmp_path / "reference-package-no-subs"
    metadata_path = tmp_path / "metadata.json"
    subtitle_text_path = tmp_path / "subtitle.srt"
    audio_bytes_path = tmp_path / "audio.bin"
    yt_dlp_bin = build_mock_ytdlp(tmp_path)

    write_json(
        metadata_path,
        {
            "id": "BV1NOsubtitles",
            "title": "No subtitles sample",
            "uploader": "Example Creator",
            "webpage_url": "https://www.bilibili.com/video/BV1NOsubtitles",
            "duration": 222,
            "subtitles": {},
            "automatic_captions": {},
        },
    )
    subtitle_text_path.write_text("", encoding="utf-8")
    audio_bytes_path.write_bytes(b"fake-audio")

    result = run_command(
        [
            sys.executable,
            "extensions/skills/reference-video-ingest/scripts/ingest_reference_video.py",
            "--project-root",
            str(project_root),
            "--source-url",
            "https://www.bilibili.com/video/BV1NOsubtitles",
            "--yt-dlp-bin",
            str(yt_dlp_bin),
            "--disable-asr-fallback",
        ],
        workdir=repo_root,
        env={
            "MOCK_YTDLP_METADATA": str(metadata_path),
            "MOCK_YTDLP_SUBTITLE_TEXT": str(subtitle_text_path),
            "MOCK_YTDLP_AUDIO_BYTES": str(audio_bytes_path),
        },
    )

    payload = json.loads(result.stdout)
    assert payload["status"] == "needs_asr"
    assert payload["subtitle_output"] is None

    transcript_source = json.loads((project_root / "research" / "reference-transcript-source.json").read_text(encoding="utf-8"))
    assert transcript_source["status"] == "needs_asr"
    assert transcript_source["next_step"] == "asr_fallback_required"

    assert (project_root / "research" / "reference-video-metadata.json").exists()
    assert not (project_root / "research" / "reference-transcript.srt").exists()
    assert not (project_root / "research" / "reference-transcript.md").exists()


def test_ingest_reference_video_falls_back_to_asr_when_subtitles_missing(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    project_root = tmp_path / "reference-package-asr"
    metadata_path = tmp_path / "metadata.json"
    subtitle_text_path = tmp_path / "subtitle.srt"
    audio_bytes_path = tmp_path / "audio.bin"
    asr_srt_path = tmp_path / "asr-output.srt"
    asr_txt_path = tmp_path / "asr-output.txt"
    yt_dlp_bin = build_mock_ytdlp(tmp_path)
    asr_bin = build_mock_asr(tmp_path)

    write_json(
        metadata_path,
        {
            "id": "BV1ASRfallback",
            "title": "ASR fallback sample",
            "uploader": "Example Creator",
            "webpage_url": "https://www.bilibili.com/video/BV1ASRfallback",
            "duration": 180,
            "subtitles": {},
            "automatic_captions": {},
        },
    )
    subtitle_text_path.write_text("", encoding="utf-8")
    audio_bytes_path.write_bytes(b"fake-mp3-bytes")
    asr_srt_path.write_text(
        "1\n00:00:00,000 --> 00:00:01,200\n这是 ASR 生成的第一句\n\n2\n00:00:01,200 --> 00:00:02,400\n这是 ASR 生成的第二句\n",
        encoding="utf-8",
    )
    asr_txt_path.write_text("这是 ASR 生成的第一句\n这是 ASR 生成的第二句\n", encoding="utf-8")

    result = run_command(
        [
            sys.executable,
            "extensions/skills/reference-video-ingest/scripts/ingest_reference_video.py",
            "--project-root",
            str(project_root),
            "--source-url",
            "https://www.bilibili.com/video/BV1ASRfallback",
            "--yt-dlp-bin",
            str(yt_dlp_bin),
            "--asr-bin",
            str(asr_bin),
        ],
        workdir=repo_root,
        env={
            "MOCK_YTDLP_METADATA": str(metadata_path),
            "MOCK_YTDLP_SUBTITLE_TEXT": str(subtitle_text_path),
            "MOCK_YTDLP_AUDIO_BYTES": str(audio_bytes_path),
            "MOCK_ASR_SRT": str(asr_srt_path),
            "MOCK_ASR_TXT": str(asr_txt_path),
        },
    )

    payload = json.loads(result.stdout)
    assert payload["status"] == "pass"
    assert payload["subtitle_track_type"] == "asr"
    assert payload["extraction_method"] == "yt-dlp_audio_plus_asr_cli"

    transcript_source = json.loads((project_root / "research" / "reference-transcript-source.json").read_text(encoding="utf-8"))
    assert transcript_source["status"] == "pass"
    assert transcript_source["subtitle_track_type"] == "asr"
    assert transcript_source["asr_model"] == "turbo"

    transcript_markdown = (project_root / "research" / "reference-transcript.md").read_text(encoding="utf-8")
    assert "transcript_origin: asr_fallback" in transcript_markdown
    assert "这是 ASR 生成的第一句" in transcript_markdown


def test_ingest_reference_video_uses_bilibili_api_when_ytdlp_dump_is_blocked(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    project_root = tmp_path / "reference-package-bili-api"
    metadata_path = tmp_path / "metadata.json"
    subtitle_text_path = tmp_path / "subtitle.srt"
    audio_bytes_path = tmp_path / "audio.m4a"
    asr_srt_path = tmp_path / "asr-output.srt"
    asr_txt_path = tmp_path / "asr-output.txt"
    view_json_path = tmp_path / "view.json"
    player_json_path = tmp_path / "player.json"
    playurl_json_path = tmp_path / "playurl.json"
    yt_dlp_bin = build_mock_ytdlp(tmp_path)
    asr_bin = build_mock_asr(tmp_path)

    write_json(metadata_path, {"id": "unused"})
    subtitle_text_path.write_text("", encoding="utf-8")
    audio_bytes_path.write_bytes(b"fake-bili-api-audio")
    asr_srt_path.write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nB站 API 回退命中了\n",
        encoding="utf-8",
    )
    asr_txt_path.write_text("B站 API 回退命中了\n", encoding="utf-8")

    write_json(
        view_json_path,
        {
            "code": 0,
            "data": {
                "bvid": "BV13rwCzwEj2",
                "cid": 36806790408,
                "title": "存量博弈",
                "desc": "测试描述",
                "duration": 825,
                "owner": {"name": "认知便利店M"},
            },
        },
    )
    write_json(
        player_json_path,
        {
            "code": 0,
            "data": {
                "need_login_subtitle": True,
                "subtitle": {"subtitles": []},
            },
        },
    )
    write_json(
        playurl_json_path,
        {
            "code": 0,
            "data": {
                "dash": {
                    "audio": [
                        {
                            "base_url": audio_bytes_path.as_uri(),
                        }
                    ]
                }
            },
        },
    )

    result = run_command(
        [
            sys.executable,
            "extensions/skills/reference-video-ingest/scripts/ingest_reference_video.py",
            "--project-root",
            str(project_root),
            "--source-url",
            "https://www.bilibili.com/video/BV13rwCzwEj2",
            "--yt-dlp-bin",
            str(yt_dlp_bin),
            "--asr-bin",
            str(asr_bin),
        ],
        workdir=repo_root,
        env={
            "MOCK_YTDLP_METADATA": str(metadata_path),
            "MOCK_YTDLP_SUBTITLE_TEXT": str(subtitle_text_path),
            "MOCK_YTDLP_AUDIO_BYTES": str(audio_bytes_path),
            "MOCK_YTDLP_FAIL_DUMP": "1",
            "MOCK_ASR_SRT": str(asr_srt_path),
            "MOCK_ASR_TXT": str(asr_txt_path),
            "REFERENCE_VIDEO_BILIBILI_VIEW_JSON": str(view_json_path),
            "REFERENCE_VIDEO_BILIBILI_PLAYER_JSON": str(player_json_path),
            "REFERENCE_VIDEO_BILIBILI_PLAYURL_JSON": str(playurl_json_path),
        },
    )

    payload = json.loads(result.stdout)
    assert payload["status"] == "pass"
    assert payload["extraction_method"] == "bilibili_api_audio_plus_asr_cli"

    metadata = json.loads((project_root / "research" / "reference-video-metadata.json").read_text(encoding="utf-8"))
    assert metadata["video_id"] == "BV13rwCzwEj2"
    assert metadata["title"] == "存量博弈"

    transcript_source = json.loads((project_root / "research" / "reference-transcript-source.json").read_text(encoding="utf-8"))
    assert transcript_source["status"] == "pass"
    assert transcript_source["subtitle_track_type"] == "asr"
    assert transcript_source["subtitle_path"] == "research/reference-transcript.srt"
