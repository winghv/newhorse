#!/usr/bin/env python3
"""Ingest reference-video metadata and subtitles into research artifacts."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


LANGUAGE_PREFERENCE = [
    "zh-Hans",
    "zh-CN",
    "zh-Hant",
    "zh-TW",
    "zh",
    "en",
    "en-US",
]

BILIBILI_BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
    "Accept": "application/json, text/plain, */*",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", help="Media package root directory.")
    parser.add_argument("--content-id", help="Content package id under the media-ops root.")
    parser.add_argument(
        "--media-ops-root",
        help="Root directory containing media packages. Defaults to repo-local data/media-ops.",
    )
    parser.add_argument("--source-url", help="Reference video URL.")
    parser.add_argument("--bvid", help="Bilibili BV id. If set, the URL is derived automatically.")
    parser.add_argument(
        "--channel",
        default="bilibili",
        help="Reference channel name. Current supported values: bilibili.",
    )
    parser.add_argument(
        "--yt-dlp-bin",
        default=os.environ.get("YT_DLP_BIN", "yt-dlp"),
        help="yt-dlp executable path.",
    )
    parser.add_argument(
        "--ffmpeg-bin",
        default=os.environ.get("FFMPEG_BIN", "ffmpeg"),
        help="ffmpeg executable path used by the audio extraction toolchain.",
    )
    parser.add_argument(
        "--asr-bin",
        default=os.environ.get("REFERENCE_VIDEO_ASR_BIN") or shutil.which("whisper"),
        help="ASR CLI executable path. Defaults to the first whisper binary on PATH.",
    )
    parser.add_argument(
        "--asr-model",
        default=os.environ.get("REFERENCE_VIDEO_ASR_MODEL", "turbo"),
        help="ASR model name passed to the CLI fallback.",
    )
    parser.add_argument(
        "--disable-asr-fallback",
        action="store_true",
        help="Disable audio-download + ASR fallback when no subtitle track exists.",
    )
    parser.add_argument(
        "--metadata-output",
        default="research/reference-video-metadata.json",
        help="Metadata output path relative to the project root.",
    )
    parser.add_argument(
        "--subtitle-output",
        default="research/reference-transcript.srt",
        help="Subtitle output path relative to the project root.",
    )
    parser.add_argument(
        "--transcript-output",
        default="research/reference-transcript.md",
        help="Transcript markdown output path relative to the project root.",
    )
    parser.add_argument(
        "--source-output",
        default="research/reference-transcript-source.json",
        help="Source report output path relative to the project root.",
    )
    parser.add_argument(
        "--require-subtitles",
        action="store_true",
        help="Exit non-zero if no subtitles can be extracted.",
    )
    args = parser.parse_args()
    if not args.project_root and not args.content_id:
        parser.error("one of --project-root or --content-id is required")
    if not args.source_url and not args.bvid:
        parser.error("one of --source-url or --bvid is required")
    return args


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def default_media_ops_root() -> Path:
    return repo_root() / "data" / "media-ops"


def resolve_project_root(args: argparse.Namespace) -> Path:
    if args.project_root:
        return Path(args.project_root).resolve()
    media_root = Path(args.media_ops_root).resolve() if args.media_ops_root else default_media_ops_root()
    return (media_root / args.content_id).resolve()


def resolve_source_url(*, channel: str, source_url: str | None, bvid: str | None) -> str:
    if source_url:
        return source_url
    if channel != "bilibili":
        raise ValueError(f"unsupported channel for ID-based URL construction: {channel}")
    if not bvid:
        raise ValueError("missing bvid")
    normalized = bvid.strip()
    if not normalized.startswith("BV"):
        raise ValueError(f"invalid bilibili BV id: {bvid}")
    return f"https://www.bilibili.com/video/{normalized}"


def relative_to_project(path: Path, project_root: Path) -> str:
    return str(path.resolve().relative_to(project_root.resolve()))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, capture_output=True, text=True)


def run_command_with_env(command: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    merged_env.update(env)
    return subprocess.run(command, check=True, capture_output=True, text=True, env=merged_env)


def parse_json_stdout(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    payload = result.stdout.strip()
    if not payload:
        return {}
    return json.loads(payload)


def extract_bvid(source_url: str) -> str | None:
    match = re.search(r"(BV[0-9A-Za-z]+)", source_url)
    if match:
        return match.group(1)
    return None


def fetch_json_url(url: str, *, headers: dict[str, str] | None = None) -> dict[str, Any]:
    request = Request(url, headers=headers or {})
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def read_bytes_from_url(url: str, *, headers: dict[str, str] | None = None) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme == "file":
        return Path(parsed.path).read_bytes()
    request = Request(url, headers=headers or {})
    with urlopen(request, timeout=60) as response:
        return response.read()


def load_bilibili_api_json(kind: str, url: str) -> dict[str, Any]:
    override_map = {
        "view": os.environ.get("REFERENCE_VIDEO_BILIBILI_VIEW_JSON"),
        "player": os.environ.get("REFERENCE_VIDEO_BILIBILI_PLAYER_JSON"),
        "playurl": os.environ.get("REFERENCE_VIDEO_BILIBILI_PLAYURL_JSON"),
    }
    override_path = override_map.get(kind)
    if override_path:
        return json.loads(Path(override_path).read_text(encoding="utf-8"))
    return fetch_json_url(url, headers=BILIBILI_BROWSER_HEADERS)


def has_bilibili_api_overrides() -> bool:
    return any(
        os.environ.get(name)
        for name in (
            "REFERENCE_VIDEO_BILIBILI_VIEW_JSON",
            "REFERENCE_VIDEO_BILIBILI_PLAYER_JSON",
            "REFERENCE_VIDEO_BILIBILI_PLAYURL_JSON",
        )
    )


def normalize_track_map(value: Any) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, list[dict[str, Any]]] = {}
    for language, items in value.items():
        if not isinstance(language, str):
            continue
        if isinstance(items, list):
            normalized[language] = [item for item in items if isinstance(item, dict)]
    return normalized


def choose_language(track_map: dict[str, list[dict[str, Any]]]) -> str | None:
    for language in LANGUAGE_PREFERENCE:
        if language in track_map and track_map[language]:
            return language
    for language, items in track_map.items():
        if items:
            return language
    return None


def choose_subtitle_track(metadata: dict[str, Any]) -> tuple[str | None, str | None, dict[str, list[dict[str, Any]]]]:
    subtitles = normalize_track_map(metadata.get("subtitles"))
    automatic_captions = normalize_track_map(metadata.get("automatic_captions"))

    preferred_subtitles = choose_language(subtitles)
    if preferred_subtitles:
        return "official", preferred_subtitles, subtitles

    preferred_auto = choose_language(automatic_captions)
    if preferred_auto:
        return "automatic", preferred_auto, automatic_captions

    return None, None, {}


def bilibili_view_api_url(bvid: str) -> str:
    return f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"


def bilibili_player_api_url(bvid: str, cid: int | str) -> str:
    return f"https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}"


def bilibili_playurl_api_url(bvid: str, cid: int | str) -> str:
    return f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn=64&fnval=16&fnver=0&fourk=1"


def normalize_bilibili_subtitles(player_payload: dict[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, str]]:
    subtitle_section = player_payload.get("subtitle") if isinstance(player_payload.get("subtitle"), dict) else {}
    subtitle_items = subtitle_section.get("subtitles") if isinstance(subtitle_section.get("subtitles"), list) else []
    normalized: dict[str, list[dict[str, Any]]] = {}
    subtitle_urls: dict[str, str] = {}
    for item in subtitle_items:
        if not isinstance(item, dict):
            continue
        language = str(item.get("lan") or "").strip()
        subtitle_url = str(item.get("subtitle_url") or "").strip()
        if not language or not subtitle_url:
            continue
        if subtitle_url.startswith("//"):
            subtitle_url = f"https:{subtitle_url}"
        normalized.setdefault(language, []).append(item)
        subtitle_urls[language] = subtitle_url
    return normalized, subtitle_urls


def build_bilibili_metadata_from_api(*, source_url: str, bvid: str) -> dict[str, Any]:
    view_payload = load_bilibili_api_json("view", bilibili_view_api_url(bvid))
    view_data = view_payload.get("data") if isinstance(view_payload.get("data"), dict) else {}
    if not view_data:
        raise RuntimeError("bilibili view api did not return data")

    cid = view_data.get("cid")
    player_payload = load_bilibili_api_json("player", bilibili_player_api_url(bvid, cid))
    player_data = player_payload.get("data") if isinstance(player_payload.get("data"), dict) else {}
    subtitles, subtitle_urls = normalize_bilibili_subtitles(player_data)

    return {
        "id": bvid,
        "title": view_data.get("title"),
        "description": view_data.get("desc"),
        "duration": view_data.get("duration"),
        "uploader": (view_data.get("owner") or {}).get("name") if isinstance(view_data.get("owner"), dict) else None,
        "channel": (view_data.get("owner") or {}).get("name") if isinstance(view_data.get("owner"), dict) else None,
        "webpage_url": source_url,
        "cid": cid,
        "subtitles": subtitles,
        "automatic_captions": {},
        "_bilibili_api": {
            "cid": cid,
            "subtitle_urls": subtitle_urls,
            "need_login_subtitle": player_data.get("need_login_subtitle"),
        },
    }


def subtitle_download_command(
    *,
    yt_dlp_bin: str,
    source_url: str,
    track_type: str,
    language: str,
    output_pattern: str,
) -> list[str]:
    command = [
        yt_dlp_bin,
        "--skip-download",
        "--convert-subs",
        "srt",
        "--sub-langs",
        language,
        "-o",
        output_pattern,
    ]
    if track_type == "official":
        command.append("--write-subs")
    else:
        command.append("--write-auto-subs")
    command.append(source_url)
    return command


def bilibili_subtitle_to_srt(payload: dict[str, Any]) -> str:
    body = payload.get("body") if isinstance(payload.get("body"), list) else []
    entries: list[str] = []
    for index, item in enumerate(body, start=1):
        if not isinstance(item, dict):
            continue
        start = float(item.get("from") or 0.0)
        end = float(item.get("to") or start)
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        entries.extend(
            [
                str(index),
                f"{format_srt_time(start)} --> {format_srt_time(end)}",
                content,
                "",
            ]
        )
    return "\n".join(entries).strip() + "\n" if entries else ""


def format_srt_time(value: float) -> str:
    total_milliseconds = max(int(round(value * 1000)), 0)
    hours, remainder = divmod(total_milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def download_bilibili_subtitle(metadata: dict[str, Any], *, language: str, output_path: Path) -> bool:
    bilibili_api = metadata.get("_bilibili_api") if isinstance(metadata.get("_bilibili_api"), dict) else {}
    subtitle_urls = bilibili_api.get("subtitle_urls") if isinstance(bilibili_api.get("subtitle_urls"), dict) else {}
    subtitle_url = subtitle_urls.get(language)
    if not isinstance(subtitle_url, str) or not subtitle_url:
        return False
    subtitle_payload = fetch_json_url(subtitle_url, headers=BILIBILI_BROWSER_HEADERS)
    subtitle_srt = bilibili_subtitle_to_srt(subtitle_payload)
    if not subtitle_srt.strip():
        return False
    write_text(output_path, subtitle_srt)
    return True


def find_downloaded_subtitle(temp_dir: Path, language: str) -> Path | None:
    exact_matches = sorted(temp_dir.glob(f"reference*.{language}.srt"))
    if exact_matches:
        return exact_matches[0]

    generic_matches = sorted(temp_dir.glob("reference*.srt"))
    if generic_matches:
        return generic_matches[0]
    return None


def parse_srt_text(text: str) -> list[str]:
    lines = text.splitlines()
    cue_lines: list[str] = []
    current: list[str] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            if current:
                cue_lines.append(" ".join(current))
                current = []
            continue
        if line.isdigit():
            continue
        if "-->" in line:
            continue
        current.append(line)
    if current:
        cue_lines.append(" ".join(current))
    return cue_lines


def build_transcript_markdown(
    *,
    metadata: dict[str, Any],
    source_url: str,
    track_type: str | None,
    language: str | None,
    subtitle_path: Path | None,
) -> str:
    title = str(metadata.get("title") or "Untitled reference video")
    uploader = str(metadata.get("uploader") or metadata.get("channel") or "unknown")
    transcript_lines = parse_srt_text(subtitle_path.read_text(encoding="utf-8")) if subtitle_path and subtitle_path.exists() else []
    transcript_body = "\n".join(f"- {line}" for line in transcript_lines) if transcript_lines else "- Subtitle track unavailable."

    sections = [
        "# Reference Transcript",
        "",
        f"- title: {title}",
        f"- source_url: {source_url}",
        f"- uploader: {uploader}",
        f"- subtitle_track_type: {track_type or 'none'}",
        f"- language: {language or 'none'}",
        "",
        "## Transcript",
        transcript_body,
        "",
    ]
    return "\n".join(sections)


def has_asr_fallback(args: argparse.Namespace) -> bool:
    if args.disable_asr_fallback:
        return False
    if not args.asr_bin:
        return False
    return shutil.which(args.ffmpeg_bin) is not None


def build_audio_download_command(*, yt_dlp_bin: str, source_url: str, output_pattern: str) -> list[str]:
    return [
        yt_dlp_bin,
        "--extract-audio",
        "--audio-format",
        "mp3",
        "-o",
        output_pattern,
        source_url,
    ]


def download_bilibili_audio(metadata: dict[str, Any], *, output_path: Path) -> bool:
    bilibili_api = metadata.get("_bilibili_api") if isinstance(metadata.get("_bilibili_api"), dict) else {}
    cid = bilibili_api.get("cid")
    bvid = metadata.get("id")
    if not cid or not isinstance(bvid, str):
        return False
    playurl_payload = load_bilibili_api_json("playurl", bilibili_playurl_api_url(bvid, cid))
    playurl_data = playurl_payload.get("data") if isinstance(playurl_payload.get("data"), dict) else {}
    dash = playurl_data.get("dash") if isinstance(playurl_data.get("dash"), dict) else {}
    audio_items = dash.get("audio") if isinstance(dash.get("audio"), list) else []
    if not audio_items:
        return False
    first_audio = audio_items[0] if isinstance(audio_items[0], dict) else {}
    audio_url = str(first_audio.get("baseUrl") or first_audio.get("base_url") or "").strip()
    if not audio_url:
        return False
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(read_bytes_from_url(audio_url, headers=BILIBILI_BROWSER_HEADERS))
    return True


def find_downloaded_audio(temp_dir: Path) -> Path | None:
    candidates: list[Path] = []
    for pattern in ("reference*.mp3", "reference*.m4a", "reference*.wav", "reference*.webm", "reference*.mp4"):
        candidates.extend(sorted(temp_dir.glob(pattern)))
    return candidates[0] if candidates else None


def build_asr_command(*, asr_bin: str, input_audio: Path, output_dir: Path, language_hint: str | None, model: str) -> list[str]:
    command = [
        asr_bin,
        str(input_audio),
        "--task",
        "transcribe",
        "--model",
        model,
        "--output_dir",
        str(output_dir),
        "--output_format",
        "all",
        "--verbose",
        "False",
        "--fp16",
        "False",
    ]
    if language_hint:
        command.extend(["--language", language_hint])
    return command


def find_asr_output(output_dir: Path, stem: str, extension: str) -> Path | None:
    exact = output_dir / f"{stem}.{extension}"
    if exact.exists():
        return exact
    generic_matches = sorted(output_dir.glob(f"*.{extension}"))
    return generic_matches[0] if generic_matches else None


def infer_asr_language(channel: str) -> str | None:
    if channel == "bilibili":
        return "Chinese"
    return None


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)
    project_root.mkdir(parents=True, exist_ok=True)

    if shutil.which(args.yt_dlp_bin) is None:
        raise FileNotFoundError(f"yt-dlp binary not found: {args.yt_dlp_bin}")

    source_url = resolve_source_url(channel=args.channel, source_url=args.source_url, bvid=args.bvid)
    dump_command = [args.yt_dlp_bin, "--dump-single-json", "--skip-download", source_url]
    metadata: dict[str, Any]
    extraction_method = "yt-dlp"
    try:
        metadata_result = run_command(dump_command)
        metadata = parse_json_stdout(metadata_result)
    except subprocess.CalledProcessError as error:
        stderr = (error.stderr or "").strip()
        if args.channel == "bilibili" and ("412" in stderr or has_bilibili_api_overrides()):
            bvid = args.bvid or extract_bvid(source_url)
            if not bvid:
                raise
            metadata = build_bilibili_metadata_from_api(source_url=source_url, bvid=bvid)
            extraction_method = "bilibili_api"
        else:
            raise

    track_type, language, track_map = choose_subtitle_track(metadata)

    metadata_output = (project_root / args.metadata_output).resolve()
    subtitle_output = (project_root / args.subtitle_output).resolve()
    transcript_output = (project_root / args.transcript_output).resolve()
    source_output = (project_root / args.source_output).resolve()

    metadata_payload = {
        "content_id": project_root.name,
        "channel": args.channel,
        "source_url": source_url,
        "video_id": metadata.get("id"),
        "title": metadata.get("title"),
        "description": metadata.get("description"),
        "duration_seconds": metadata.get("duration"),
        "uploader": metadata.get("uploader") or metadata.get("channel"),
        "webpage_url": metadata.get("webpage_url") or source_url,
        "available_subtitle_languages": sorted(normalize_track_map(metadata.get("subtitles")).keys()),
        "available_automatic_caption_languages": sorted(normalize_track_map(metadata.get("automatic_captions")).keys()),
        "selected_subtitle_track_type": track_type,
        "selected_language": language,
        "selected_track_candidates": track_map.get(language or "", []),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(metadata_output, metadata_payload)

    subtitle_written = False
    source_payload: dict[str, Any] = {
        "content_id": project_root.name,
        "channel": args.channel,
        "source_url": source_url,
        "status": "needs_asr",
        "subtitle_track_type": track_type,
        "language": language,
        "metadata_path": relative_to_project(metadata_output, project_root),
        "subtitle_path": None,
        "transcript_path": None,
        "extraction_method": extraction_method,
        "next_step": "asr_fallback_required",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    if track_type and language:
        if extraction_method == "bilibili_api":
            subtitle_written = download_bilibili_subtitle(metadata, language=language, output_path=subtitle_output)
        else:
            with tempfile.TemporaryDirectory(prefix="reference-video-ingest-") as temp_dir_raw:
                temp_dir = Path(temp_dir_raw)
                output_pattern = str((temp_dir / "reference.%(ext)s").resolve())
                download_command = subtitle_download_command(
                    yt_dlp_bin=args.yt_dlp_bin,
                    source_url=source_url,
                    track_type=track_type,
                    language=language,
                    output_pattern=output_pattern,
                )
                run_command(download_command)
                downloaded = find_downloaded_subtitle(temp_dir, language)
                if downloaded and downloaded.exists():
                    subtitle_output.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(downloaded, subtitle_output)
                    subtitle_written = True

    if subtitle_written:
        transcript_markdown = build_transcript_markdown(
            metadata=metadata,
            source_url=source_url,
            track_type=track_type,
            language=language,
            subtitle_path=subtitle_output,
        )
        write_text(transcript_output, transcript_markdown)
        source_payload.update(
            {
                "status": "pass",
                "subtitle_path": relative_to_project(subtitle_output, project_root),
                "transcript_path": relative_to_project(transcript_output, project_root),
                "next_step": "ready_for_benchmark_or_script_review",
            }
        )
    elif has_asr_fallback(args):
        if not args.asr_bin:
            raise RuntimeError("ASR fallback marked available without an ASR binary path")
        if not Path(args.asr_bin).exists() and shutil.which(args.asr_bin) is None:
            raise FileNotFoundError(f"ASR binary not found: {args.asr_bin}")

        with tempfile.TemporaryDirectory(prefix="reference-video-asr-") as temp_dir_raw:
            temp_dir = Path(temp_dir_raw)
            if extraction_method == "bilibili_api":
                audio_file = temp_dir / "reference-audio.m4a"
                if not download_bilibili_audio(metadata, output_path=audio_file):
                    raise FileNotFoundError("bilibili api audio fallback did not produce a local audio file")
            else:
                audio_output_pattern = str((temp_dir / "reference.%(ext)s").resolve())
                audio_download_command = build_audio_download_command(
                    yt_dlp_bin=args.yt_dlp_bin,
                    source_url=source_url,
                    output_pattern=audio_output_pattern,
                )
                run_command(audio_download_command)
                audio_file = find_downloaded_audio(temp_dir)
                if audio_file is None or not audio_file.exists():
                    raise FileNotFoundError("yt-dlp audio fallback did not produce a local audio file")

            asr_output_dir = temp_dir / "asr"
            asr_output_dir.mkdir(parents=True, exist_ok=True)
            asr_command = build_asr_command(
                asr_bin=args.asr_bin,
                input_audio=audio_file,
                output_dir=asr_output_dir,
                language_hint=infer_asr_language(args.channel),
                model=args.asr_model,
            )
            run_command_with_env(
                asr_command,
                env={
                    "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS", "1"),
                    "KMP_DUPLICATE_LIB_OK": os.environ.get("KMP_DUPLICATE_LIB_OK", "TRUE"),
                },
            )

            srt_output = find_asr_output(asr_output_dir, audio_file.stem, "srt")
            if srt_output is None:
                raise FileNotFoundError("ASR fallback did not produce an SRT transcript")

            subtitle_output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(srt_output, subtitle_output)
            transcript_markdown = build_transcript_markdown(
                metadata=metadata,
                source_url=source_url,
                track_type="asr",
                language=infer_asr_language(args.channel),
                subtitle_path=subtitle_output,
            )
            transcript_markdown += "\n> transcript_origin: asr_fallback\n"
            write_text(transcript_output, transcript_markdown)
            subtitle_written = True
            track_type = "asr"
            language = infer_asr_language(args.channel)
            source_payload.update(
                {
                    "status": "pass",
                    "subtitle_track_type": "asr",
                    "language": language,
                    "subtitle_path": relative_to_project(subtitle_output, project_root),
                    "transcript_path": relative_to_project(transcript_output, project_root),
                    "extraction_method": "bilibili_api_audio_plus_asr_cli"
                    if extraction_method == "bilibili_api"
                    else "yt-dlp_audio_plus_asr_cli",
                    "next_step": "ready_for_benchmark_or_script_review",
                    "asr_model": args.asr_model,
                }
            )
    elif args.require_subtitles:
        source_payload.update({"status": "failed", "next_step": "manual_review_required"})
        write_json(source_output, source_payload)
        raise RuntimeError("no subtitle track available for this reference video")

    write_json(source_output, source_payload)
    print(
        json.dumps(
            {
                "metadata_output": str(metadata_output),
                "subtitle_output": str(subtitle_output) if subtitle_written else None,
                "transcript_output": str(transcript_output) if subtitle_written else None,
                "status": source_payload["status"],
                "subtitle_track_type": track_type,
                "language": language,
                "extraction_method": source_payload["extraction_method"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
