#!/usr/bin/env python3
"""Render a narrated final cut from a source video, voiceover, and subtitles."""

from __future__ import annotations

import argparse
import functools
import json
import re
import subprocess
from pathlib import Path
from typing import Any


DEFAULT_SUBTITLE_ALIGNMENT_NOISE_DB = "-35dB"
DEFAULT_SUBTITLE_ALIGNMENT_MIN_SILENCE_SECONDS = 0.12
DEFAULT_SUBTITLE_ALIGNMENT_MAX_BOUNDARY_DRIFT_SECONDS = 0.45
DEFAULT_SUBTITLE_ALIGNMENT_MIN_MATCHED_RATIO = 0.72
DEFAULT_SOUND_BED_GAIN_DB = 0.0
DEFAULT_HOOK_BGM_MIN_SECONDS = 10.0


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, capture_output=True, text=True)


@functools.lru_cache(maxsize=None)
def ffmpeg_filter_available(filter_name: str) -> bool:
    try:
        result = run_command(["ffmpeg", "-hide_banner", "-filters"])
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False
    pattern = re.compile(rf"^\s*[\.A-Z]+\s+{re.escape(filter_name)}(?:\s|$)", flags=re.MULTILINE)
    return bool(pattern.search(result.stdout))


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


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


def procedural_sfx_duration(preset: str) -> float:
    if preset == "impact_hit":
        return 0.42
    if preset == "sub_hit":
        return 0.28
    if preset == "whoosh_riser":
        return 0.82
    if preset == "typing_burst":
        return 0.48
    if preset == "typewriter_clack":
        return 0.14
    if preset == "typewriter_key":
        return 0.105
    if preset == "typewriter_key_soft":
        return 0.095
    if preset == "typewriter_key_tail":
        return 0.135
    if preset == "glitch_stab":
        return 0.22
    if preset == "reverse_suck":
        return 0.44
    if preset == "braam_hit":
        return 0.96
    if preset == "ordinal_tick":
        return 0.19
    raise ValueError(f"Unsupported procedural SFX preset: {preset}")


def render_procedural_sfx(preset: str, output_path: Path) -> float:
    duration_seconds = procedural_sfx_duration(preset)
    ensure_parent(output_path)

    if preset == "impact_hit":
        command = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"anoisesrc=color=white:amplitude=0.28:duration={duration_seconds:.3f}:r=48000",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=86:duration={duration_seconds:.3f}:sample_rate=48000",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=176:duration={duration_seconds:.3f}:sample_rate=48000",
            "-filter_complex",
            (
                "[0:a]highpass=f=800,lowpass=f=9000,volume=0.7,"
                "afade=t=in:st=0:d=0.005,afade=t=out:st=0.11:d=0.31[noise];"
                "[1:a]volume=1.0,afade=t=in:st=0:d=0.003,afade=t=out:st=0.05:d=0.37[sub];"
                "[2:a]volume=0.28,afade=t=in:st=0:d=0.002,afade=t=out:st=0.04:d=0.24[presence];"
                "[noise][sub][presence]amix=inputs=3:normalize=0[aout]"
            ),
            "-map",
            "[aout]",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]
    elif preset == "sub_hit":
        command = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"anoisesrc=color=white:amplitude=0.22:duration={duration_seconds:.3f}:r=48000",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=74:duration={duration_seconds:.3f}:sample_rate=48000",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=148:duration={duration_seconds:.3f}:sample_rate=48000",
            "-filter_complex",
            (
                "[0:a]highpass=f=640,lowpass=f=5400,volume=0.58,"
                "afade=t=in:st=0:d=0.001,afade=t=out:st=0.05:d=0.16[noise];"
                "[1:a]volume=1.05,afade=t=in:st=0:d=0.001,afade=t=out:st=0.03:d=0.22[sub];"
                "[2:a]volume=0.22,afade=t=in:st=0:d=0.001,afade=t=out:st=0.03:d=0.16[harmonic];"
                "[noise][sub][harmonic]amix=inputs=3:normalize=0,alimiter=limit=0.97[aout]"
            ),
            "-map",
            "[aout]",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]
    elif preset == "whoosh_riser":
        command = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"anoisesrc=color=pink:amplitude=0.22:duration={duration_seconds:.3f}:r=48000",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=520:duration={duration_seconds:.3f}:sample_rate=48000",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=1240:duration={duration_seconds:.3f}:sample_rate=48000",
            "-filter_complex",
            (
                "[0:a]highpass=f=220,lowpass=f=6400,volume=0.55,"
                "afade=t=in:st=0:d=0.24,afade=t=out:st=0.49:d=0.33[noise];"
                "[1:a]volume=0.16,afade=t=in:st=0:d=0.26,afade=t=out:st=0.5:d=0.3[tone_lo];"
                "[2:a]volume=0.12,afade=t=in:st=0:d=0.34,afade=t=out:st=0.58:d=0.22[tone_hi];"
                "[noise][tone_lo][tone_hi]amix=inputs=3:normalize=0[aout]"
            ),
            "-map",
            "[aout]",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]
    elif preset == "typing_burst":
        command = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"anoisesrc=color=white:amplitude=0.16:duration={duration_seconds:.3f}:r=48000",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=2860:duration={duration_seconds:.3f}:sample_rate=48000",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=1710:duration={duration_seconds:.3f}:sample_rate=48000",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=820:duration={duration_seconds:.3f}:sample_rate=48000",
            "-filter_complex",
            (
                "[0:a]highpass=f=1800,lowpass=f=9000,volume=0.62,"
                "afade=t=in:st=0:d=0.001,afade=t=out:st=0.08:d=0.07[noise];"
                "[1:a]volume=0.38,afade=t=in:st=0:d=0.001,afade=t=out:st=0.05:d=0.05[tone_hi];"
                "[2:a]volume=0.22,afade=t=in:st=0:d=0.001,afade=t=out:st=0.07:d=0.06[tone_lo];"
                "[3:a]volume=0.14,afade=t=in:st=0:d=0.001,afade=t=out:st=0.06:d=0.08[body];"
                "[noise][tone_hi][tone_lo][body]amix=inputs=4:normalize=0[aout]"
            ),
            "-map",
            "[aout]",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]
    elif preset == "typewriter_clack":
        command = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"anoisesrc=color=white:amplitude=0.2:duration={duration_seconds:.3f}:r=48000",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=2380:duration={duration_seconds:.3f}:sample_rate=48000",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=1160:duration={duration_seconds:.3f}:sample_rate=48000",
            "-filter_complex",
            (
                "[0:a]highpass=f=2600,lowpass=f=9800,volume=0.9,"
                "afade=t=in:st=0:d=0.0008,afade=t=out:st=0.028:d=0.03[noise];"
                "[1:a]volume=0.28,afade=t=in:st=0:d=0.0008,afade=t=out:st=0.02:d=0.025[tone_hi];"
                "[2:a]volume=0.14,afade=t=in:st=0:d=0.0008,afade=t=out:st=0.024:d=0.032[tone_lo];"
                "[noise][tone_hi][tone_lo]amix=inputs=3:normalize=0[aout]"
            ),
            "-map",
            "[aout]",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]
    elif preset == "typewriter_key":
        command = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"anoisesrc=color=white:amplitude=0.18:duration={duration_seconds:.3f}:r=48000",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=2140:duration={duration_seconds:.3f}:sample_rate=48000",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=980:duration={duration_seconds:.3f}:sample_rate=48000",
            "-filter_complex",
            (
                "[0:a]highpass=f=3000,lowpass=f=10800,volume=0.86,"
                "afade=t=in:st=0:d=0.0006,afade=t=out:st=0.014:d=0.024[click];"
                "[1:a]volume=0.18,afade=t=in:st=0:d=0.0006,afade=t=out:st=0.010:d=0.018[metal];"
                "[2:a]volume=0.14,afade=t=in:st=0:d=0.0006,afade=t=out:st=0.016:d=0.028[body];"
                "[click][metal][body]amix=inputs=3:normalize=0[aout]"
            ),
            "-map",
            "[aout]",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]
    elif preset == "typewriter_key_soft":
        command = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"anoisesrc=color=white:amplitude=0.14:duration={duration_seconds:.3f}:r=48000",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=1760:duration={duration_seconds:.3f}:sample_rate=48000",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=820:duration={duration_seconds:.3f}:sample_rate=48000",
            "-filter_complex",
            (
                "[0:a]highpass=f=2600,lowpass=f=9200,volume=0.7,"
                "afade=t=in:st=0:d=0.0006,afade=t=out:st=0.012:d=0.022[click];"
                "[1:a]volume=0.12,afade=t=in:st=0:d=0.0006,afade=t=out:st=0.010:d=0.016[metal];"
                "[2:a]volume=0.1,afade=t=in:st=0:d=0.0006,afade=t=out:st=0.012:d=0.024[body];"
                "[click][metal][body]amix=inputs=3:normalize=0[aout]"
            ),
            "-map",
            "[aout]",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]
    elif preset == "typewriter_key_tail":
        command = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"anoisesrc=color=white:amplitude=0.2:duration={duration_seconds:.3f}:r=48000",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=2280:duration={duration_seconds:.3f}:sample_rate=48000",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=1040:duration={duration_seconds:.3f}:sample_rate=48000",
            "-filter_complex",
            (
                "[0:a]highpass=f=2800,lowpass=f=10800,volume=0.92,"
                "afade=t=in:st=0:d=0.0006,afade=t=out:st=0.016:d=0.03[click];"
                "[1:a]volume=0.2,afade=t=in:st=0:d=0.0006,afade=t=out:st=0.012:d=0.024[metal];"
                "[2:a]volume=0.16,afade=t=in:st=0:d=0.0006,afade=t=out:st=0.018:d=0.036[body];"
                "[click][metal][body]amix=inputs=3:normalize=0[aout]"
            ),
            "-map",
            "[aout]",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]
    elif preset == "glitch_stab":
        command = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"anoisesrc=color=white:amplitude=0.18:duration={duration_seconds:.3f}:r=48000",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=1980:duration={duration_seconds:.3f}:sample_rate=48000",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=120:duration={duration_seconds:.3f}:sample_rate=48000",
            "-filter_complex",
            (
                "[0:a]highpass=f=1400,lowpass=f=8600,volume=0.72,"
                "afade=t=in:st=0:d=0.001,afade=t=out:st=0.05:d=0.09[noise];"
                "[1:a]volume=0.34,afade=t=in:st=0:d=0.001,afade=t=out:st=0.04:d=0.06[tone_hi];"
                "[2:a]volume=0.36,afade=t=in:st=0:d=0.001,afade=t=out:st=0.03:d=0.16[sub];"
                "[noise][tone_hi][sub]amix=inputs=3:normalize=0[aout]"
            ),
            "-map",
            "[aout]",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]
    elif preset == "reverse_suck":
        command = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"anoisesrc=color=pink:amplitude=0.15:duration={duration_seconds:.3f}:r=48000",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=840:duration={duration_seconds:.3f}:sample_rate=48000",
            "-filter_complex",
            (
                "[0:a]highpass=f=420,lowpass=f=7600,volume=0.5,"
                "afade=t=in:st=0:d=0.24,afade=t=out:st=0.3:d=0.14[noise];"
                "[1:a]volume=0.1,afade=t=in:st=0:d=0.24,afade=t=out:st=0.32:d=0.12[tone];"
                "[noise][tone]amix=inputs=2:normalize=0[aout]"
            ),
            "-map",
            "[aout]",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]
    elif preset == "braam_hit":
        command = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"anoisesrc=color=pink:amplitude=0.2:duration={duration_seconds:.3f}:r=48000",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=58:duration={duration_seconds:.3f}:sample_rate=48000",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=116:duration={duration_seconds:.3f}:sample_rate=48000",
            "-filter_complex",
            (
                "[0:a]highpass=f=220,lowpass=f=5400,volume=0.42,"
                "afade=t=in:st=0:d=0.005,afade=t=out:st=0.34:d=0.56[noise];"
                "[1:a]volume=1.05,afade=t=in:st=0:d=0.003,afade=t=out:st=0.18:d=0.72[sub];"
                "[2:a]volume=0.24,afade=t=in:st=0:d=0.003,afade=t=out:st=0.15:d=0.48[harmonic];"
                "[noise][sub][harmonic]amix=inputs=3:normalize=0[aout]"
            ),
            "-map",
            "[aout]",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]
    elif preset == "ordinal_tick":
        command = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"anoisesrc=color=pink:amplitude=0.12:duration={duration_seconds:.3f}:r=48000",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=1640:duration={duration_seconds:.3f}:sample_rate=48000",
            "-filter_complex",
            (
                "[0:a]highpass=f=1600,lowpass=f=6800,volume=0.56,"
                "afade=t=in:st=0:d=0.003,afade=t=out:st=0.055:d=0.08[noise];"
                "[1:a]volume=0.28,afade=t=in:st=0:d=0.002,afade=t=out:st=0.045:d=0.07[tone];"
                "[noise][tone]amix=inputs=2:normalize=0[aout]"
            ),
            "-map",
            "[aout]",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]
    else:
        raise ValueError(f"Unsupported procedural SFX preset: {preset}")

    run_command(command)
    return duration_seconds


def normalize_bgm_track(track: Any, *, workspace_root: Path, total_duration: float, default_gain_db: float) -> dict[str, Any]:
    if isinstance(track, str):
        raw_path = track
        start_seconds = 0.0
        end_seconds = total_duration
        gain_db = default_gain_db
        loop = True
        fade_in_seconds = 0.25
        fade_out_seconds = 1.2
        role = "background_bed"
    elif isinstance(track, dict):
        raw_path = track.get("path")
        start_seconds = float(track.get("start_seconds", 0.0))
        end_seconds = float(track.get("end_seconds", total_duration))
        gain_db = float(track.get("gain_db", default_gain_db))
        loop = bool(track.get("loop", True))
        fade_in_seconds = float(track.get("fade_in_seconds", 0.25))
        fade_out_seconds = float(track.get("fade_out_seconds", 1.2))
        role = track.get("role", "background_bed")
    else:
        raise ValueError(f"Unsupported bgm track config: {track!r}")

    path = resolve_path(workspace_root, raw_path)
    if path is None or not path.exists():
        raise FileNotFoundError(f"BGM asset not found: {raw_path}")

    start_seconds = clamp(start_seconds, 0.0, total_duration)
    end_seconds = clamp(end_seconds, start_seconds, total_duration)
    if end_seconds <= start_seconds:
        raise ValueError(f"BGM track window is empty for asset: {path}")

    return {
        "path": path,
        "start_seconds": round(start_seconds, 3),
        "end_seconds": round(end_seconds, 3),
        "duration_seconds": round(end_seconds - start_seconds, 3),
        "gain_db": gain_db,
        "loop": loop,
        "fade_in_seconds": max(fade_in_seconds, 0.0),
        "fade_out_seconds": max(fade_out_seconds, 0.0),
        "role": role,
    }


def normalize_sfx_cue(
    cue: Any,
    *,
    workspace_root: Path,
    total_duration: float,
    sound_design_dir: Path,
    index: int,
) -> dict[str, Any]:
    if not isinstance(cue, dict):
        raise ValueError(f"Unsupported sfx cue config: {cue!r}")

    start_seconds = clamp(float(cue.get("start_seconds", 0.0)), 0.0, total_duration)
    gain_db = float(cue.get("gain_db", -15.0))
    label = str(cue.get("label", f"sfx_{index:02d}"))
    raw_path = cue.get("path")
    preset = cue.get("preset")
    duration_seconds = cue.get("duration_seconds")

    if raw_path:
        path = resolve_path(workspace_root, str(raw_path))
        if path is None or not path.exists():
            raise FileNotFoundError(f"SFX asset not found: {raw_path}")
        normalized_duration = float(duration_seconds) if duration_seconds is not None else None
    elif preset:
        path = sound_design_dir / f"sfx-{index:02d}-{preset}.wav"
        normalized_duration = render_procedural_sfx(str(preset), path)
    else:
        raise ValueError(f"SFX cue requires either path or preset: {cue!r}")

    if duration_seconds is not None:
        normalized_duration = float(duration_seconds)

    return {
        "path": path,
        "start_seconds": round(start_seconds, 3),
        "gain_db": gain_db,
        "label": label,
        "preset": preset,
        "duration_seconds": round(float(normalized_duration), 3) if normalized_duration is not None else None,
    }


def build_sound_bed(
    *,
    plan: dict[str, Any],
    workspace_root: Path,
    output_video: Path,
    voiceover_duration: float,
) -> tuple[Path | None, Path | None, dict[str, Any]]:
    mix = plan.get("mix", {})
    raw_bgm_tracks = list(mix.get("bgm_tracks", []))
    raw_sfx_cues = list(mix.get("sfx_cues", []))
    sound_bed_gain_db = float(mix.get("sound_bed_gain_db", DEFAULT_SOUND_BED_GAIN_DB))
    summary: dict[str, Any] = {
        "requested_bgm_track_count": len(raw_bgm_tracks),
        "requested_sfx_cue_count": len(raw_sfx_cues),
        "applied_bgm_track_count": 0,
        "applied_sfx_cue_count": 0,
        "sound_bed_applied": False,
        "bgm_tracks": [],
        "sfx_cues": [],
        "hook_bgm_window_seconds": 0.0,
        "sound_bed_gain_db": sound_bed_gain_db,
        "command": None,
    }
    if not raw_bgm_tracks and not raw_sfx_cues:
        return None, None, summary

    sound_design_dir = output_video.parent / ".render-temp" / "sound-design"
    sound_design_dir.mkdir(parents=True, exist_ok=True)

    default_gain_db = float(mix.get("bgm_default_gain_db", -26.0))
    bgm_tracks = [
        normalize_bgm_track(track, workspace_root=workspace_root, total_duration=voiceover_duration, default_gain_db=default_gain_db)
        for track in raw_bgm_tracks
    ]
    sfx_cues = [
        normalize_sfx_cue(
            cue,
            workspace_root=workspace_root,
            total_duration=voiceover_duration,
            sound_design_dir=sound_design_dir,
            index=index,
        )
        for index, cue in enumerate(raw_sfx_cues)
    ]

    summary["applied_bgm_track_count"] = len(bgm_tracks)
    summary["applied_sfx_cue_count"] = len(sfx_cues)
    summary["bgm_tracks"] = [
        {
            "path": str(track["path"]),
            "start_seconds": track["start_seconds"],
            "end_seconds": track["end_seconds"],
            "role": track["role"],
        }
        for track in bgm_tracks
    ]
    summary["sfx_cues"] = [
        {
            "path": str(cue["path"]),
            "label": cue["label"],
            "preset": cue["preset"],
            "start_seconds": cue["start_seconds"],
        }
        for cue in sfx_cues
    ]
    summary["hook_bgm_window_seconds"] = round(
        max(
            (
                track["duration_seconds"]
                for track in bgm_tracks
                if track["start_seconds"] <= 0.5
            ),
            default=0.0,
        ),
        3,
    )

    def render_stem(
        *,
        items: list[dict[str, Any]],
        item_type: str,
        output_path: Path,
    ) -> tuple[Path | None, list[str] | None]:
        if not items:
            return None, None
        command: list[str] = ["ffmpeg", "-y"]
        filters: list[str] = []
        mixed_inputs: list[str] = []
        input_index = 0

        for item_index, item in enumerate(items):
            if item_type == "bgm" and item["loop"]:
                command.extend(["-stream_loop", "-1"])
            command.extend(["-i", str(item["path"])])

            chain = [
                "asetpts=PTS-STARTPTS",
                "aformat=sample_rates=48000:channel_layouts=stereo",
                f"volume={item['gain_db']}dB",
            ]
            if item_type == "bgm":
                chain.append(f"atrim=duration={item['duration_seconds']:.3f}")
                if item["fade_in_seconds"] > 0:
                    chain.append(f"afade=t=in:st=0:d={min(item['fade_in_seconds'], item['duration_seconds']):.3f}")
                if item["fade_out_seconds"] > 0:
                    fade_out_duration = min(item["fade_out_seconds"], item["duration_seconds"])
                    fade_out_start = max(item["duration_seconds"] - fade_out_duration, 0.0)
                    chain.append(f"afade=t=out:st={fade_out_start:.3f}:d={fade_out_duration:.3f}")
            elif item["duration_seconds"] is not None:
                chain.append(f"atrim=duration={item['duration_seconds']:.3f}")

            delay_ms = int(round(item["start_seconds"] * 1000))
            if delay_ms > 0:
                chain.append(f"adelay={delay_ms}|{delay_ms}")

            label = f"{item_type}_{item_index}"
            filters.append(f"[{input_index}:a]{','.join(chain)}[{label}]")
            mixed_inputs.append(f"[{label}]")
            input_index += 1

        if len(mixed_inputs) == 1:
            filters.append(
                f"{mixed_inputs[0]}volume={sound_bed_gain_db}dB,atrim=duration={voiceover_duration:.3f}[bed]"
            )
        else:
            filters.append(
                f"{''.join(mixed_inputs)}amix=inputs={len(mixed_inputs)}:duration=longest:normalize=0,"
                f"volume={sound_bed_gain_db}dB,atrim=duration={voiceover_duration:.3f}[bed]"
            )

        command.extend(
            [
                "-filter_complex",
                ";".join(filters),
                "-map",
                "[bed]",
                "-c:a",
                "pcm_s16le",
                str(output_path),
            ]
        )
        run_command(command)
        return output_path, command

    bgm_bed_path = sound_design_dir / "bgm-bed.wav"
    sfx_bed_path = sound_design_dir / "sfx-bed.wav"
    bgm_stem_path, bgm_command = render_stem(items=bgm_tracks, item_type="bgm", output_path=bgm_bed_path)
    sfx_stem_path, sfx_command = render_stem(items=sfx_cues, item_type="sfx", output_path=sfx_bed_path)

    summary["sound_bed_applied"] = bgm_stem_path is not None or sfx_stem_path is not None
    summary["bgm_stem_applied"] = bgm_stem_path is not None
    summary["sfx_stem_applied"] = sfx_stem_path is not None
    summary["command"] = {
        "bgm": bgm_command,
        "sfx": sfx_command,
    }
    return bgm_stem_path, sfx_stem_path, summary


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


def parse_srt_blocks(path: Path | None) -> list[str]:
    if path is None or not path.exists():
        return []
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    blocks = re.split(r"\n\s*\n", text)
    lines: list[str] = []
    for block in blocks:
        block_lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(block_lines) >= 3:
            lines.append(" ".join(block_lines[2:]))
    return lines


def parse_srt_block_lines(path: Path | None) -> list[list[str]]:
    if path is None or not path.exists():
        return []
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    blocks = re.split(r"\n\s*\n", text)
    parsed: list[list[str]] = []
    for block in blocks:
        block_lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(block_lines) >= 3:
            parsed.append(block_lines[2:])
    return parsed


def parse_srt_entries(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []

    entries: list[dict[str, Any]] = []
    blocks = re.split(r"\n\s*\n", text)
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3:
            continue
        start_raw, end_raw = lines[1].split(" --> ", maxsplit=1)
        entries.append(
            {
                "start_seconds": srt_timestamp_seconds(start_raw),
                "end_seconds": srt_timestamp_seconds(end_raw),
                "text": " ".join(lines[2:]),
            }
        )
    return entries


def srt_timestamp_seconds(value: str) -> float:
    hours, minutes, seconds_millis = value.split(":")
    seconds, millis = seconds_millis.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000


def detect_silence_ranges(path: Path, *, noise_db: str, min_silence_seconds: float) -> list[tuple[float, float]]:
    command = [
        "ffmpeg",
        "-hide_banner",
        "-i",
        str(path),
        "-af",
        f"silencedetect=noise={noise_db}:d={min_silence_seconds}",
        "-f",
        "null",
        "-",
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    stderr = result.stderr or ""

    starts = [float(match.group(1)) for match in re.finditer(r"silence_start:\s*([0-9.]+)", stderr)]
    ends = [float(match.group(1)) for match in re.finditer(r"silence_end:\s*([0-9.]+)", stderr)]
    ranges: list[tuple[float, float]] = []
    for start, end in zip(starts, ends):
        if end <= start:
            continue
        ranges.append((start, end))
    return ranges


def match_subtitle_boundaries_to_silences(
    *,
    boundaries: list[float],
    silence_midpoints: list[float],
    max_boundary_drift_seconds: float,
) -> tuple[list[dict[str, float]], list[dict[str, float]]]:
    matched: list[dict[str, float]] = []
    unmatched: list[dict[str, float]] = []
    silence_index = 0

    for boundary in boundaries:
        while silence_index < len(silence_midpoints) and silence_midpoints[silence_index] < boundary - max_boundary_drift_seconds:
            silence_index += 1

        candidate_indexes = []
        if silence_index > 0:
            candidate_indexes.append(silence_index - 1)

        look_ahead = silence_index
        while look_ahead < len(silence_midpoints) and silence_midpoints[look_ahead] <= boundary + max_boundary_drift_seconds:
            candidate_indexes.append(look_ahead)
            look_ahead += 1

        best_index = -1
        best_drift = None
        for candidate_index in candidate_indexes:
            drift = abs(silence_midpoints[candidate_index] - boundary)
            if best_drift is None or drift < best_drift:
                best_drift = drift
                best_index = candidate_index

        if best_index >= 0 and best_drift is not None and best_drift <= max_boundary_drift_seconds:
            matched.append(
                {
                    "boundary_seconds": round(boundary, 3),
                    "silence_midpoint_seconds": round(silence_midpoints[best_index], 3),
                    "drift_seconds": round(best_drift, 3),
                }
            )
            silence_index = max(best_index + 1, silence_index)
            continue

        unmatched.append({"boundary_seconds": round(boundary, 3)})

    return matched, unmatched


def evaluate_subtitle_alignment(
    *,
    subtitles: Path | None,
    voiceover_audio: Path,
    qa_settings: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    if subtitles is None or not subtitles.exists():
        return (
            {
                "status": "block",
                "reason": "subtitles_missing",
                "boundary_count": 0,
                "silence_count": 0,
            },
            warnings,
        )

    entries = parse_srt_entries(subtitles)
    boundaries = [float(entry["end_seconds"]) for entry in entries[:-1]]
    if not boundaries:
        warnings.append("subtitle_alignment_not_enough_boundaries")
        return (
            {
                "status": "pass",
                "reason": "not_enough_boundaries",
                "boundary_count": len(boundaries),
                "silence_count": 0,
                "matched_boundary_count": 0,
                "unmatched_boundary_count": 0,
                "matched_boundary_ratio": 1.0,
                "average_boundary_drift_seconds": 0.0,
                "max_boundary_drift_seconds": 0.0,
            },
            warnings,
        )

    noise_db = str(qa_settings.get("subtitle_alignment_noise_db", DEFAULT_SUBTITLE_ALIGNMENT_NOISE_DB))
    min_silence_seconds = float(
        qa_settings.get("subtitle_alignment_min_silence_seconds", DEFAULT_SUBTITLE_ALIGNMENT_MIN_SILENCE_SECONDS)
    )
    max_boundary_drift_seconds = float(
        qa_settings.get(
            "subtitle_alignment_max_boundary_drift_seconds",
            DEFAULT_SUBTITLE_ALIGNMENT_MAX_BOUNDARY_DRIFT_SECONDS,
        )
    )
    min_matched_ratio = float(
        qa_settings.get("subtitle_alignment_min_matched_ratio", DEFAULT_SUBTITLE_ALIGNMENT_MIN_MATCHED_RATIO)
    )

    silence_ranges = detect_silence_ranges(
        voiceover_audio,
        noise_db=noise_db,
        min_silence_seconds=min_silence_seconds,
    )
    silence_midpoints = [round((start + end) / 2.0, 3) for start, end in silence_ranges]
    if not silence_midpoints:
        warnings.append("subtitle_alignment_signal_insufficient")
        return (
            {
                "status": "pass",
                "reason": "no_silence_detected",
                "boundary_count": len(boundaries),
                "silence_count": 0,
                "matched_boundary_count": 0,
                "unmatched_boundary_count": 0,
                "matched_boundary_ratio": 1.0,
                "average_boundary_drift_seconds": 0.0,
                "max_boundary_drift_seconds": 0.0,
                "max_allowed_boundary_drift_seconds": max_boundary_drift_seconds,
                "min_required_matched_ratio": min_matched_ratio,
            },
            warnings,
        )

    matched, unmatched = match_subtitle_boundaries_to_silences(
        boundaries=boundaries,
        silence_midpoints=silence_midpoints,
        max_boundary_drift_seconds=max_boundary_drift_seconds,
    )
    matched_ratio = len(matched) / len(boundaries)
    drifts = [item["drift_seconds"] for item in matched]
    average_drift = round(sum(drifts) / len(drifts), 3) if drifts else 0.0
    max_drift = round(max(drifts), 3) if drifts else 0.0
    status = "pass" if matched_ratio >= min_matched_ratio and max_drift <= max_boundary_drift_seconds else "revise"
    if status != "pass":
        warnings.append("subtitle_alignment_drift_detected")

    return (
        {
            "status": status,
            "boundary_count": len(boundaries),
            "silence_count": len(silence_midpoints),
            "matched_boundary_count": len(matched),
            "unmatched_boundary_count": len(unmatched),
            "matched_boundary_ratio": round(matched_ratio, 3),
            "average_boundary_drift_seconds": average_drift,
            "max_boundary_drift_seconds": max_drift,
            "max_allowed_boundary_drift_seconds": max_boundary_drift_seconds,
            "min_required_matched_ratio": min_matched_ratio,
            "matched_boundaries_sample": matched[:10],
            "unmatched_boundaries_sample": unmatched[:10],
        },
        warnings,
    )


def detect_freeze_segments(output_video: Path, threshold_seconds: float) -> list[dict[str, float]]:
    command = [
        "ffmpeg",
        "-hide_banner",
        "-i",
        str(output_video),
        "-vf",
        f"freezedetect=n=-60dB:d={threshold_seconds}",
        "-f",
        "null",
        "-",
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    stderr = result.stderr or ""

    freeze_starts = [float(match.group(1)) for match in re.finditer(r"freeze_start:\s*([0-9.]+)", stderr)]
    freeze_ends = [float(match.group(1)) for match in re.finditer(r"freeze_end:\s*([0-9.]+)", stderr)]
    freeze_durations = [float(match.group(1)) for match in re.finditer(r"freeze_duration:\s*([0-9.]+)", stderr)]

    segments: list[dict[str, float]] = []
    for index, start in enumerate(freeze_starts):
        end = freeze_ends[index] if index < len(freeze_ends) else start
        duration = freeze_durations[index] if index < len(freeze_durations) else max(end - start, 0.0)
        segments.append(
            {
                "start_seconds": round(start, 3),
                "end_seconds": round(end, 3),
                "duration_seconds": round(duration, 3),
            }
        )
    return segments


def evaluate_sound_design(
    *,
    sound_design_summary: dict[str, Any],
    output_duration: float,
) -> tuple[dict[str, Any], list[str], list[str]]:
    requested_bgm_track_count = int(sound_design_summary.get("requested_bgm_track_count", 0))
    requested_sfx_cue_count = int(sound_design_summary.get("requested_sfx_cue_count", 0))
    applied_bgm_track_count = int(sound_design_summary.get("applied_bgm_track_count", 0))
    applied_sfx_cue_count = int(sound_design_summary.get("applied_sfx_cue_count", 0))
    hook_bgm_window_seconds = float(sound_design_summary.get("hook_bgm_window_seconds", 0.0))

    warnings: list[str] = []
    blocking_issues: list[str] = []
    total_requested = requested_bgm_track_count + requested_sfx_cue_count
    if total_requested == 0:
        return (
            {
                "status": "pass",
                "reason": "not_requested",
                "requested_bgm_track_count": 0,
                "requested_sfx_cue_count": 0,
                "applied_bgm_track_count": 0,
                "applied_sfx_cue_count": 0,
                "hook_bgm_window_seconds": 0.0,
            },
            warnings,
            blocking_issues,
        )

    if not bool(sound_design_summary.get("sound_bed_applied")):
        blocking_issues.append("sound_design_bed_missing")
        return (
            {
                "status": "block",
                "reason": "sound_bed_missing",
                "requested_bgm_track_count": requested_bgm_track_count,
                "requested_sfx_cue_count": requested_sfx_cue_count,
                "applied_bgm_track_count": applied_bgm_track_count,
                "applied_sfx_cue_count": applied_sfx_cue_count,
                "hook_bgm_window_seconds": round(hook_bgm_window_seconds, 3),
            },
            warnings,
            blocking_issues,
        )

    status = "pass"
    if requested_bgm_track_count != applied_bgm_track_count or requested_sfx_cue_count != applied_sfx_cue_count:
        blocking_issues.append("sound_design_asset_count_mismatch")
        status = "block"
    elif (
        requested_bgm_track_count > 0
        and output_duration >= 30.0
        and hook_bgm_window_seconds < DEFAULT_HOOK_BGM_MIN_SECONDS
    ):
        warnings.append("hook_bgm_window_too_short")
        status = "revise"

    return (
        {
            "status": status,
            "requested_bgm_track_count": requested_bgm_track_count,
            "requested_sfx_cue_count": requested_sfx_cue_count,
            "applied_bgm_track_count": applied_bgm_track_count,
            "applied_sfx_cue_count": applied_sfx_cue_count,
            "hook_bgm_window_seconds": round(hook_bgm_window_seconds, 3),
        },
        warnings,
        blocking_issues,
    )


def build_qa_report(
    *,
    plan: dict[str, Any],
    subtitles: Path | None,
    voiceover_audio: Path,
    output_video: Path,
    duration_alignment_error: float,
    sound_design_summary: dict[str, Any],
) -> dict[str, Any]:
    qa_settings = plan.get("qa", {})
    freeze_threshold_seconds = float(qa_settings.get("freeze_threshold_seconds", 2.5))
    max_static_hold_seconds = float(qa_settings.get("max_static_hold_seconds", freeze_threshold_seconds))
    max_duration_alignment_error_seconds = float(qa_settings.get("max_duration_alignment_error_seconds", 0.35))
    freeze_segments = detect_freeze_segments(output_video, freeze_threshold_seconds)
    disallowed_freeze_segments = [
        segment for segment in freeze_segments if float(segment["duration_seconds"]) > max_static_hold_seconds
    ]
    subtitle_lines = parse_srt_blocks(subtitles)
    subtitle_alignment, subtitle_alignment_warnings = evaluate_subtitle_alignment(
        subtitles=subtitles,
        voiceover_audio=voiceover_audio,
        qa_settings=qa_settings,
    )
    output_duration = media_duration(output_video)
    sound_design, sound_design_warnings, sound_design_blocking_issues = evaluate_sound_design(
        sound_design_summary=sound_design_summary,
        output_duration=output_duration,
    )
    ending_lines = subtitle_lines[-3:]
    episodic_patterns = [str(item) for item in qa_settings.get("episodic_outro_patterns", []) if item]
    matched_outro_patterns = [
        pattern for pattern in episodic_patterns if any(pattern in line for line in ending_lines)
    ]

    freeze_status = "pass" if not disallowed_freeze_segments else "revise"
    duration_status = "pass" if duration_alignment_error <= max_duration_alignment_error_seconds else "block"
    outro_status = "pass" if not matched_outro_patterns else "revise"
    subtitle_status = "pass" if subtitles is not None else "block"

    overall_status = "pass"
    for status in (
        freeze_status,
        outro_status,
        duration_status,
        subtitle_status,
        subtitle_alignment["status"],
        sound_design["status"],
    ):
        if status == "block":
            overall_status = "block"
            break
        if status == "revise":
            overall_status = "revise"

    blocking_issues: list[str] = []
    warnings: list[str] = []
    if disallowed_freeze_segments:
        warnings.append("freeze_segments_detected")
    elif freeze_segments:
        warnings.append("allowed_static_segments_detected")
    if matched_outro_patterns:
        warnings.append("episodic_outro_language_detected")
    if duration_status == "block":
        blocking_issues.append("duration_alignment_exceeds_threshold")
    if subtitle_status == "block":
        blocking_issues.append("subtitle_delivery_missing")
    blocking_issues.extend(sound_design_blocking_issues)
    warnings.extend(subtitle_alignment_warnings)
    warnings.extend(sound_design_warnings)

    return {
        "status": overall_status,
        "checks": {
            "freeze_detection": {
                "status": freeze_status,
                "threshold_seconds": freeze_threshold_seconds,
                "max_static_hold_seconds": max_static_hold_seconds,
                "freeze_segments": freeze_segments,
                "disallowed_freeze_segments": disallowed_freeze_segments,
            },
            "duration_alignment": {
                "status": duration_status,
                "error_seconds": round(duration_alignment_error, 3),
                "max_allowed_error_seconds": max_duration_alignment_error_seconds,
            },
            "episodic_outro": {
                "status": outro_status,
                "matched_patterns": matched_outro_patterns,
                "checked_lines": ending_lines,
            },
            "subtitle_delivery": {
                "status": subtitle_status,
                "mode": "burned_in" if subtitles is not None else "missing",
            },
            "subtitle_alignment": subtitle_alignment,
            "sound_design": sound_design,
        },
        "blocking_issues": blocking_issues,
        "warnings": warnings,
    }


def build_subtitle_quality_report(
    *,
    plan: dict[str, Any],
    qa_report: dict[str, Any],
    workspace_root: Path,
    subtitles: Path | None,
) -> dict[str, Any]:
    subtitle_delivery = qa_report.get("checks", {}).get("subtitle_delivery", {})
    subtitle_alignment = qa_report.get("checks", {}).get("subtitle_alignment", {})
    style_pack_raw = plan.get("context", {}).get("subtitle_style_pack")
    style_pack_path = resolve_path(workspace_root, style_pack_raw)
    style_pack = load_json(style_pack_path)
    style_pack_present = bool(style_pack_path and style_pack_path.exists())
    style_pack_required = bool(style_pack_raw)
    translation_required = bool(style_pack.get("translation_required"))
    subtitle_block_lines = parse_srt_block_lines(subtitles)
    bilingual_cue_count = sum(1 for block in subtitle_block_lines if len(block) >= 2 and any(re.search(r"[A-Za-z]", line) for line in block[1:]))
    subtitle_cue_count = len(subtitle_block_lines)
    bilingual_ratio = (bilingual_cue_count / subtitle_cue_count) if subtitle_cue_count else 0.0

    status = "pass"
    if subtitle_delivery.get("status") == "block" or subtitle_alignment.get("status") == "block":
        status = "block"
    elif subtitle_delivery.get("status") == "revise" or subtitle_alignment.get("status") == "revise" or (
        style_pack_required and not style_pack_present
    ):
        status = "revise"
    if translation_required and bilingual_ratio < 0.95:
        status = "revise" if status == "pass" else status

    return {
        "status": status,
        "inputs": {
            "subtitles": display_path(subtitles, workspace_root) if subtitles else None,
            "subtitle_style_pack": display_path(style_pack_path, workspace_root) if style_pack_path else None,
            "style": plan.get("subtitle_style"),
        },
        "checks": {
            "subtitle_delivery": subtitle_delivery,
            "subtitle_alignment": subtitle_alignment,
            "style_pack_present": {
                "status": "pass" if (style_pack_present or not style_pack_required) else "revise",
                "present": style_pack_present,
                "required": style_pack_required,
            },
            "bilingual_delivery": {
                "status": "pass" if (not translation_required or bilingual_ratio >= 0.95) else "revise",
                "required": translation_required,
                "cue_count": subtitle_cue_count,
                "bilingual_cue_count": bilingual_cue_count,
                "bilingual_ratio": round(bilingual_ratio, 3),
            },
        },
    }


def build_scene_assembly_report(
    *,
    plan: dict[str, Any],
    workspace_root: Path,
    qa_report: dict[str, Any],
) -> dict[str, Any]:
    context = plan.get("context", {}) if isinstance(plan.get("context"), dict) else {}
    scene_manifest_path = resolve_path(workspace_root, context.get("scene_manifest"))
    transition_plan_path = resolve_path(workspace_root, context.get("transition_plan"))
    emphasis_fx_plan_path = resolve_path(workspace_root, context.get("emphasis_fx_plan"))
    auto_base_plan_path = workspace_root / "content" / "postproduction" / "auto-base-cut-plan.json"

    scene_manifest = load_json(scene_manifest_path)
    transition_plan = load_json(transition_plan_path)
    emphasis_fx_plan = load_json(emphasis_fx_plan_path)
    auto_base_plan = load_json(auto_base_plan_path if auto_base_plan_path.exists() else None)

    scene_count = len(scene_manifest.get("scenes", [])) if isinstance(scene_manifest.get("scenes"), list) else 0
    scenes = scene_manifest.get("scenes", []) if isinstance(scene_manifest.get("scenes"), list) else []
    transition_count = len(transition_plan.get("transitions", [])) if isinstance(transition_plan.get("transitions"), list) else 0
    fx_scene_count = len(emphasis_fx_plan.get("scene_fx", [])) if isinstance(emphasis_fx_plan.get("scene_fx"), list) else 0
    image_slot_ratio = auto_base_plan.get("quality", {}).get("metrics", {}).get("image_slot_ratio")
    auto_base_quality_status = auto_base_plan.get("quality", {}).get("status")
    pure_text_primary_scene_ids = [
        str(scene.get("scene_id") or "")
        for scene in scenes
        if isinstance(scene, dict)
        and isinstance(scene.get("primary_asset"), dict)
        and (
            str(scene["primary_asset"].get("type") or "") in {"graphics-card", "text-card", "text-only-card"}
            or Path(str(scene["primary_asset"].get("path") or "")).name.startswith("card-")
        )
    ]
    bilingual_scene_count = sum(
        1
        for scene in scenes
        if isinstance(scene, dict) and str(scene.get("subtitle_mode") or "").startswith("bilingual")
    )

    status = "pass"
    if scene_manifest_path and not scene_manifest_path.exists():
        status = "revise"
    if transition_plan_path and not transition_plan_path.exists():
        status = "revise"
    if emphasis_fx_plan_path and not emphasis_fx_plan_path.exists():
        status = "revise"
    if pure_text_primary_scene_ids and status == "pass":
        status = "revise"
    if scene_count and bilingual_scene_count < scene_count and status == "pass":
        status = "revise"
    if qa_report.get("status") == "block":
        status = "block"
    elif qa_report.get("status") == "revise" and status == "pass":
        status = "revise"

    return {
        "status": status,
        "inputs": {
            "scene_manifest": display_path(scene_manifest_path, workspace_root) if scene_manifest_path else None,
            "transition_plan": display_path(transition_plan_path, workspace_root) if transition_plan_path else None,
            "emphasis_fx_plan": display_path(emphasis_fx_plan_path, workspace_root) if emphasis_fx_plan_path else None,
            "auto_base_cut_plan": display_path(auto_base_plan_path, workspace_root) if auto_base_plan_path.exists() else None,
        },
        "metrics": {
            "scene_count": scene_count,
            "transition_count": transition_count,
            "fx_scene_count": fx_scene_count,
            "auto_base_quality_status": auto_base_quality_status,
            "image_slot_ratio": image_slot_ratio,
            "pure_text_primary_scene_count": len(pure_text_primary_scene_ids),
            "bilingual_scene_ratio": round((bilingual_scene_count / scene_count) if scene_count else 1.0, 3),
        },
        "checks": {
            "scene_manifest_present": {
                "status": "pass" if (scene_manifest_path and scene_manifest_path.exists()) or scene_manifest_path is None else "revise",
                "present": bool(scene_manifest_path and scene_manifest_path.exists()),
            },
            "transition_plan_present": {
                "status": "pass" if (transition_plan_path and transition_plan_path.exists()) or transition_plan_path is None else "revise",
                "present": bool(transition_plan_path and transition_plan_path.exists()),
            },
            "emphasis_fx_plan_present": {
                "status": "pass" if (emphasis_fx_plan_path and emphasis_fx_plan_path.exists()) or emphasis_fx_plan_path is None else "revise",
                "present": bool(emphasis_fx_plan_path and emphasis_fx_plan_path.exists()),
            },
            "plain_text_cards_removed": {
                "status": "pass" if not pure_text_primary_scene_ids else "revise",
                "scene_ids": pure_text_primary_scene_ids,
            },
            "bilingual_subtitle_mode": {
                "status": "pass" if (scene_count == 0 or bilingual_scene_count == scene_count) else "revise",
                "scene_count": scene_count,
                "bilingual_scene_count": bilingual_scene_count,
            },
        },
    }


def build_filter_complex(
    plan: dict[str, Any],
    subtitles: Path | None,
    source_duration: float,
    source_video_fps: float | None,
    voiceover_duration: float,
    retain_original_audio: bool,
    source_has_audio: bool,
    bgm_bed_present: bool,
    sfx_bed_present: bool,
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
        target_fps = int(fps)
        if (
            source_video_fps
            and float(source_video_fps) + 0.25 < target_fps
            and ffmpeg_filter_available("minterpolate")
        ):
            video_chain.append(f"minterpolate=fps={target_fps}:mi_mode=mci:mc_mode=aobmc:vsbmc=1")
        else:
            video_chain.append(f"fps={target_fps}")

    filters: list[str] = [f"[0:v]{','.join(video_chain)}[v_base]"]

    if subtitles is not None and ffmpeg_filter_available("subtitles"):
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
    voice_chain = [
        "asetpts=PTS-STARTPTS",
        f"volume={voiceover_gain_db}dB",
    ]
    if voiceover_delay_ms > 0:
        voice_chain.append(f"adelay={voiceover_delay_ms}|{voiceover_delay_ms}")
    voice_chain.append(f"atrim=duration={voiceover_duration:.3f}")
    filters.append(f"[1:a]{','.join(voice_chain)}[voice_raw]")

    background_labels: list[str] = []
    if retain_original_audio and source_has_audio:
        original_audio_gain_db = float(mix.get("original_audio_gain_db", -24))
        original_chain = [
            "asetpts=PTS-STARTPTS",
            f"volume={original_audio_gain_db}dB",
            f"atrim=duration={voiceover_duration:.3f}",
        ]
        filters.append(f"[0:a]{','.join(original_chain)}[bg_source]")
        background_labels.append("[bg_source]")

    next_audio_input_index = 2
    if bgm_bed_present:
        sound_bed_gain_db = float(mix.get("sound_bed_gain_db", DEFAULT_SOUND_BED_GAIN_DB))
        bed_chain = [
            "asetpts=PTS-STARTPTS",
            f"volume={sound_bed_gain_db}dB",
            f"atrim=duration={voiceover_duration:.3f}",
        ]
        filters.append(f"[{next_audio_input_index}:a]{','.join(bed_chain)}[bg_bed]")
        background_labels.append("[bg_bed]")
        next_audio_input_index += 1

    sfx_mix_label: str | None = None
    if sfx_bed_present:
        sfx_stem_gain_db = float(mix.get("sfx_stem_gain_db", 6.0))
        sfx_chain = [
            "asetpts=PTS-STARTPTS",
            f"volume={sfx_stem_gain_db}dB",
            f"atrim=duration={voiceover_duration:.3f}",
        ]
        filters.append(f"[{next_audio_input_index}:a]{','.join(sfx_chain)}[sfx_bed]")
        sfx_mix_label = "[sfx_bed]"

    if background_labels:
        bg_sidechain_ducking = bool(mix.get("bg_sidechain_ducking", False))
        if bg_sidechain_ducking:
            filters.append("[voice_raw]asplit=2[voice_mix][voice_sidechain]")
            voice_mix_label = "[voice_mix]"
            voice_sidechain_label = "[voice_sidechain]"
        else:
            voice_mix_label = "[voice_raw]"
            voice_sidechain_label = "[voice_raw]"

        if len(background_labels) == 1:
            background_mix_label = background_labels[0]
        else:
            filters.append(
                f"{''.join(background_labels)}amix=inputs={len(background_labels)}:duration=longest:normalize=0[bg_raw]"
            )
            background_mix_label = "[bg_raw]"

        if bg_sidechain_ducking:
            threshold = float(mix.get("bg_sidechain_threshold", 0.018))
            ratio = float(mix.get("bg_sidechain_ratio", 10.0))
            attack = int(mix.get("bg_sidechain_attack_ms", 15))
            release = int(mix.get("bg_sidechain_release_ms", 260))
            filters.append(
                f"{background_mix_label}{voice_sidechain_label}"
                f"sidechaincompress=threshold={threshold}:ratio={ratio}:attack={attack}:release={release}[bg_duck]"
            )
            background_mix_label = "[bg_duck]"

        filters.append(f"{background_mix_label}{voice_mix_label}amix=inputs=2:duration=longest:normalize=0[program]")
    else:
        filters.append("[voice_raw]anull[program]")

    if sfx_mix_label is not None:
        filters.append(f"[program]{sfx_mix_label}amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.97[aout]")
    else:
        filters.append("[program]alimiter=limit=0.95[aout]")

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
    qa_report: dict[str, Any],
    sound_design_summary: dict[str, Any],
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
        f"- qa status: `{qa_report.get('status')}`",
        f"- subtitle alignment status: `{qa_report.get('checks', {}).get('subtitle_alignment', {}).get('status')}`",
        f"- sound design status: `{qa_report.get('checks', {}).get('sound_design', {}).get('status')}`",
        f"- sound bed applied: `{sound_design_summary.get('sound_bed_applied')}`",
        f"- bgm track count: `{sound_design_summary.get('applied_bgm_track_count', 0)}`",
        f"- sfx cue count: `{sound_design_summary.get('applied_sfx_cue_count', 0)}`",
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
    qa_report_output = resolve_path(workspace_root, plan.get("qa_report_output"))
    subtitle_quality_report_output = resolve_path(workspace_root, plan.get("subtitle_quality_report_output"))
    scene_assembly_report_output = resolve_path(workspace_root, plan.get("scene_assembly_report_output"))
    assembly_strategy = str(plan.get("assembly_strategy", "retime_existing_cut"))

    if source_video is None or voiceover_audio is None or output_video is None:
        raise ValueError("source_video, voiceover_audio, and output_video are required.")

    ensure_parent(output_video)
    ensure_parent(render_manifest_output)
    ensure_parent(verification_output)
    ensure_parent(qa_report_output)
    ensure_parent(subtitle_quality_report_output)
    ensure_parent(scene_assembly_report_output)

    source_probe = ffprobe_json(source_video)
    source_video_metadata = video_stream_info(source_probe)
    source_duration = media_duration(source_video)
    voiceover_duration = media_duration(voiceover_audio)
    source_has_audio = has_audio_stream(source_video)

    mix = plan.get("mix", {})
    retain_original_audio = bool(mix.get("retain_original_audio", True))
    bgm_bed_path, sfx_bed_path, sound_design_summary = build_sound_bed(
        plan=plan,
        workspace_root=workspace_root,
        output_video=output_video,
        voiceover_duration=voiceover_duration,
    )

    filter_complex, video_pts_factor = build_filter_complex(
        plan=plan,
        subtitles=subtitles,
        source_duration=source_duration,
        source_video_fps=source_video_metadata.get("fps"),
        voiceover_duration=voiceover_duration,
        retain_original_audio=retain_original_audio,
        source_has_audio=source_has_audio,
        bgm_bed_present=bgm_bed_path is not None,
        sfx_bed_present=sfx_bed_path is not None,
    )

    video_codec = plan.get("video_codec", "libx264")
    audio_codec = plan.get("audio_codec", "aac")
    crf = str(plan.get("crf", 22))
    preset = str(plan.get("preset", "veryfast"))

    ffmpeg_command = [
        "ffmpeg",
        "-y",
        "-i",
        str(source_video),
        "-i",
        str(voiceover_audio),
    ]
    if bgm_bed_path is not None:
        ffmpeg_command.extend(["-i", str(bgm_bed_path)])
    if sfx_bed_path is not None:
        ffmpeg_command.extend(["-i", str(sfx_bed_path)])
    ffmpeg_command.extend(
        [
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
            "-t",
            f"{voiceover_duration:.3f}",
            str(output_video),
        ]
    )
    run_command(ffmpeg_command)

    output_probe = ffprobe_json(output_video)
    output_duration = float(output_probe["format"]["duration"])
    duration_alignment_error = abs(output_duration - voiceover_duration)
    file_size_bytes = int(output_probe["format"].get("size", output_video.stat().st_size))
    qa_report = build_qa_report(
        plan=plan,
        subtitles=subtitles,
        voiceover_audio=voiceover_audio,
        output_video=output_video,
        duration_alignment_error=duration_alignment_error,
        sound_design_summary=sound_design_summary,
    )
    subtitle_quality_report = build_subtitle_quality_report(
        plan=plan,
        qa_report=qa_report,
        workspace_root=workspace_root,
        subtitles=subtitles,
    )
    scene_assembly_report = build_scene_assembly_report(
        plan=plan,
        workspace_root=workspace_root,
        qa_report=qa_report,
    )

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
            "bg_sidechain_ducking": bool(mix.get("bg_sidechain_ducking", False)),
            "sound_bed_applied": bool(sound_design_summary.get("sound_bed_applied")),
            "bgm_track_count": int(sound_design_summary.get("applied_bgm_track_count", 0)),
            "sfx_cue_count": int(sound_design_summary.get("applied_sfx_cue_count", 0)),
        },
        "subtitles": {
            "burned_in": subtitles is not None,
            "style": plan.get("subtitle_style"),
            "quality_report": display_path(subtitle_quality_report_output, workspace_root)
            if subtitle_quality_report_output
            else None,
        },
        "scene_assembly": {
            "status": scene_assembly_report["status"],
            "report": display_path(scene_assembly_report_output, workspace_root) if scene_assembly_report_output else None,
        },
        "output": {
            "video": display_path(output_video, workspace_root),
            "duration_seconds": round(output_duration, 3),
            "duration_alignment_error_seconds": round(duration_alignment_error, 3),
            "file_size_bytes": file_size_bytes,
            **video_stream_info(output_probe),
            **audio_stream_info(output_probe),
        },
        "qa": {
            "status": qa_report["status"],
            "report": display_path(qa_report_output, workspace_root) if qa_report_output else None,
        },
        "commands": {
            "sound_bed_ffmpeg": sound_design_summary.get("command"),
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
            qa_report=qa_report,
            sound_design_summary=sound_design_summary,
        )
    if qa_report_output is not None:
        write_json(qa_report_output, qa_report)
    if subtitle_quality_report_output is not None:
        write_json(subtitle_quality_report_output, subtitle_quality_report)
    if scene_assembly_report_output is not None:
        write_json(scene_assembly_report_output, scene_assembly_report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
