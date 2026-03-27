#!/usr/bin/env python3
"""Render a narrated final cut from a source video, voiceover, and subtitles."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, capture_output=True, text=True)


def ffprobe_json(path: Path) -> dict[str, Any]:
    result = run_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ]
    )
    return json.loads(result.stdout)


def media_duration(path: Path) -> float:
    payload = ffprobe_json(path)
    duration = payload.get("format", {}).get("duration")
    if duration is None:
        raise ValueError(f"Unable to read duration from {path}")
    return float(duration)


def has_audio_stream(path: Path) -> bool:
    payload = ffprobe_json(path)
    streams = payload.get("streams", [])
    return any(stream.get("codec_type") == "audio" for stream in streams)


def load_plan(plan_path: Path) -> dict[str, Any]:
    return json.loads(plan_path.read_text(encoding="utf-8"))


def resolve_path(base_dir: Path, raw_path: str | None) -> Path | None:
    if not raw_path:
        return None
    path = Path(raw_path)
    return path if path.is_absolute() else (base_dir / path).resolve()


def ensure_parent(path: Path | None) -> None:
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)


def display_path(path: Path, workspace_root: Path) -> str:
    try:
        return str(path.relative_to(workspace_root))
    except ValueError:
        return str(path)


def quote_filter_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def video_stream_info(payload: dict[str, Any]) -> dict[str, Any]:
    for stream in payload.get("streams", []):
        if stream.get("codec_type") == "video":
            frame_rate = stream.get("avg_frame_rate", "0/0")
            fps = None
            if frame_rate and frame_rate != "0/0":
                numerator, denominator = frame_rate.split("/")
                fps = float(numerator) / float(denominator)
            return {
                "video_codec": stream.get("codec_name"),
                "width": stream.get("width"),
                "height": stream.get("height"),
                "fps": round(fps, 3) if fps else None,
            }
    return {}


def audio_stream_info(payload: dict[str, Any]) -> dict[str, Any]:
    for stream in payload.get("streams", []):
        if stream.get("codec_type") == "audio":
            return {
                "audio_codec": stream.get("codec_name"),
                "sample_rate": stream.get("sample_rate"),
                "channels": stream.get("channels"),
            }
    return {}


def build_filter_complex(
    plan: dict[str, Any],
    subtitles: Path | None,
    source_duration: float,
    voiceover_duration: float,
    retain_original_audio: bool,
    source_has_audio: bool,
) -> tuple[str, float]:
    retime = plan.get("retime", {})
    retime_mode = retime.get("mode", "auto_match_voiceover")
    allow_slowdown = bool(retime.get("allow_slowdown", False))
    max_speedup = float(retime.get("max_speedup", 2.0))

    if retime_mode == "disabled":
        video_pts_factor = 1.0
    elif retime_mode == "manual":
        video_pts_factor = float(retime["video_pts_factor"])
    else:
        video_pts_factor = voiceover_duration / source_duration

    if not allow_slowdown and video_pts_factor > 1.02:
        raise ValueError(
            "Voiceover is longer than source video; choose rebuild_timeline or allow_slowdown explicitly."
        )

    if video_pts_factor <= 0:
        raise ValueError("video_pts_factor must be positive.")

    speedup_ratio = 1 / video_pts_factor
    if speedup_ratio > max_speedup:
        raise ValueError(
            f"Requested retime exceeds max_speedup ({speedup_ratio:.3f} > {max_speedup:.3f})."
        )

    fps = retime.get("target_fps")
    video_chain = [f"setpts={video_pts_factor:.6f}*PTS"]
    if fps:
        video_chain.append(f"fps={int(fps)}")

    filters: list[str] = [f"[0:v]{','.join(video_chain)}[v_base]"]

    if subtitles is not None:
        subtitle_filter = f"subtitles='{quote_filter_value(str(subtitles))}'"
        subtitle_style = plan.get("subtitle_style")
        if subtitle_style:
            subtitle_filter += f":force_style='{quote_filter_value(subtitle_style)}'"
        filters.append(f"[v_base]{subtitle_filter}[vout]")
    else:
        filters.append("[v_base]null[vout]")

    mix = plan.get("mix", {})
    voiceover_gain_db = float(mix.get("voiceover_gain_db", 0))
    voiceover_delay_ms = int(mix.get("voiceover_delay_ms", 0))
    voice_chain = [f"volume={voiceover_gain_db}dB"]
    if voiceover_delay_ms > 0:
        voice_chain.append(f"adelay={voiceover_delay_ms}|{voiceover_delay_ms}")
    voice_chain.append(f"atrim=duration={voiceover_duration:.3f}")
    filters.append(f"[1:a]{','.join(voice_chain)}[voice]")

    if retain_original_audio and source_has_audio:
        original_audio_gain_db = float(mix.get("original_audio_gain_db", -24))
        original_chain = [
            f"volume={original_audio_gain_db}dB",
            f"atrim=duration={voiceover_duration:.3f}",
        ]
        filters.append(f"[0:a]{','.join(original_chain)}[bg]")
        filters.append("[bg][voice]amix=inputs=2:duration=longest:normalize=0[aout]")
    else:
        filters.append("[voice]anull[aout]")

    return ";".join(filters), video_pts_factor


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_verification(
    path: Path,
    workspace_root: Path,
    source_video: Path,
    voiceover_audio: Path,
    subtitles: Path | None,
    output_video: Path,
    assembly_strategy: str,
    video_pts_factor: float,
    output_probe: dict[str, Any],
    source_duration: float,
    voiceover_duration: float,
) -> None:
    output_duration = float(output_probe["format"]["duration"])
    video_info = video_stream_info(output_probe)
    audio_info = audio_stream_info(output_probe)
    lines = [
        "# Render Verification",
        "",
        f"- strategy: `{assembly_strategy}`",
        f"- source video: `{display_path(source_video, workspace_root)}`",
        f"- voiceover audio: `{display_path(voiceover_audio, workspace_root)}`",
        f"- subtitles: `{display_path(subtitles, workspace_root) if subtitles else 'none'}`",
        f"- output video: `{display_path(output_video, workspace_root)}`",
        f"- source duration: `{source_duration:.3f}s`",
        f"- voiceover duration: `{voiceover_duration:.3f}s`",
        f"- output duration: `{output_duration:.3f}s`",
        f"- video pts factor: `{video_pts_factor:.6f}`",
        f"- video codec: `{video_info.get('video_codec')}`",
        f"- audio codec: `{audio_info.get('audio_codec')}`",
    ]

    if video_info.get("width") and video_info.get("height"):
        lines.append(f"- resolution: `{video_info['width']}x{video_info['height']}`")
    if video_info.get("fps"):
        lines.append(f"- fps: `{video_info['fps']}`")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, help="Path to a render plan JSON file.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan_path = Path(args.plan).resolve()
    plan = load_plan(plan_path)

    workspace_root = resolve_path(plan_path.parent, plan.get("workspace_root")) or Path.cwd().resolve()
    source_video = resolve_path(workspace_root, plan.get("source_video"))
    voiceover_audio = resolve_path(workspace_root, plan.get("voiceover_audio"))
    output_video = resolve_path(workspace_root, plan.get("output_video"))
    subtitles = resolve_path(workspace_root, plan.get("subtitles"))
    render_manifest_output = resolve_path(workspace_root, plan.get("render_manifest_output"))
    verification_output = resolve_path(workspace_root, plan.get("verification_output"))
    assembly_strategy = str(plan.get("assembly_strategy", "retime_existing_cut"))

    if source_video is None or voiceover_audio is None or output_video is None:
        raise ValueError("source_video, voiceover_audio, and output_video are required.")

    ensure_parent(output_video)
    ensure_parent(render_manifest_output)
    ensure_parent(verification_output)

    source_duration = media_duration(source_video)
    voiceover_duration = media_duration(voiceover_audio)
    source_has_audio = has_audio_stream(source_video)

    mix = plan.get("mix", {})
    retain_original_audio = bool(mix.get("retain_original_audio", True))

    filter_complex, video_pts_factor = build_filter_complex(
        plan=plan,
        subtitles=subtitles,
        source_duration=source_duration,
        voiceover_duration=voiceover_duration,
        retain_original_audio=retain_original_audio,
        source_has_audio=source_has_audio,
    )

    video_codec = plan.get("video_codec", "libx264")
    audio_codec = plan.get("audio_codec", "aac")
    crf = str(plan.get("crf", 22))
    preset = str(plan.get("preset", "ultrafast"))

    ffmpeg_command = [
        "ffmpeg",
        "-y",
        "-i",
        str(source_video),
        "-i",
        str(voiceover_audio),
        "-filter_complex",
        filter_complex,
        "-map",
        "[vout]",
        "-map",
        "[aout]",
        "-c:v",
        video_codec,
        "-preset",
        preset,
        "-crf",
        crf,
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        audio_codec,
        "-movflags",
        "+faststart",
        "-shortest",
        str(output_video),
    ]
    run_command(ffmpeg_command)

    output_probe = ffprobe_json(output_video)
    output_duration = float(output_probe["format"]["duration"])
    duration_alignment_error = abs(output_duration - voiceover_duration)
    file_size_bytes = int(output_probe["format"].get("size", output_video.stat().st_size))

    manifest = {
        "plan_path": str(plan_path),
        "workspace_root": str(workspace_root),
        "assembly_strategy": assembly_strategy,
        "inputs": {
            "source_video": display_path(source_video, workspace_root),
            "voiceover_audio": display_path(voiceover_audio, workspace_root),
            "subtitles": display_path(subtitles, workspace_root) if subtitles else None,
            "source_duration_seconds": round(source_duration, 3),
            "voiceover_duration_seconds": round(voiceover_duration, 3),
        },
        "retime": {
            "mode": plan.get("retime", {}).get("mode", "auto_match_voiceover"),
            "video_pts_factor": round(video_pts_factor, 6),
            "speedup_ratio": round(1 / video_pts_factor, 6),
        },
        "mix": {
            "retain_original_audio": retain_original_audio and source_has_audio,
            "source_has_audio": source_has_audio,
            "original_audio_gain_db": mix.get("original_audio_gain_db", -24),
            "voiceover_gain_db": mix.get("voiceover_gain_db", 0),
            "voiceover_delay_ms": mix.get("voiceover_delay_ms", 0),
        },
        "subtitles": {
            "burned_in": subtitles is not None,
            "style": plan.get("subtitle_style"),
        },
        "output": {
            "video": display_path(output_video, workspace_root),
            "duration_seconds": round(output_duration, 3),
            "duration_alignment_error_seconds": round(duration_alignment_error, 3),
            "file_size_bytes": file_size_bytes,
            **video_stream_info(output_probe),
            **audio_stream_info(output_probe),
        },
        "commands": {
            "ffmpeg": ffmpeg_command,
        },
    }

    if render_manifest_output is not None:
        write_json(render_manifest_output, manifest)
    if verification_output is not None:
        write_verification(
            path=verification_output,
            workspace_root=workspace_root,
            source_video=source_video,
            voiceover_audio=voiceover_audio,
            subtitles=subtitles,
            output_video=output_video,
            assembly_strategy=assembly_strategy,
            video_pts_factor=video_pts_factor,
            output_probe=output_probe,
            source_duration=source_duration,
            voiceover_duration=voiceover_duration,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
