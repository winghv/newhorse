#!/usr/bin/env python3
"""Build a structured audio cue sheet for narrated postproduction."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HOOK_BGM_SECONDS = 18.0
HOOK_LAYER_MIN_SECONDS = 12.0
OPENING_SFX_WINDOW_SECONDS = 35.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", help="Media package root directory.")
    parser.add_argument("--content-id", help="Content package id under the media-ops root.")
    parser.add_argument(
        "--media-ops-root",
        help="Root directory containing media packages. Defaults to repo-local data/media-ops.",
    )
    parser.add_argument(
        "--output",
        default="content/postproduction/audio-cue-sheet.json",
        help="Audio cue sheet output path relative to the project root.",
    )
    args = parser.parse_args()
    if not args.project_root and not args.content_id:
        parser.error("one of --project-root or --content-id is required")
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


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def detect_content_packet(project_root: Path) -> Path:
    content_dir = project_root / "content"
    prioritized = ["*video.json", "content-packet.json", "*.json"]
    for pattern in prioritized:
        matches = sorted(path for path in content_dir.glob(pattern) if path.is_file())
        if matches:
            return matches[0]
    raise FileNotFoundError(f"no content packet found under {content_dir}")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_timestamp(value: str) -> float:
    parts = value.split(":")
    if len(parts) != 2:
        return 0.0
    minutes, seconds = parts
    return int(minutes) * 60 + float(seconds)


def parse_time_range(value: str | None) -> tuple[float, float]:
    if not isinstance(value, str) or "-" not in value:
        return 0.0, 0.0
    start_raw, end_raw = [part.strip() for part in value.split("-", maxsplit=1)]
    return parse_timestamp(start_raw), parse_timestamp(end_raw)


def parse_duration_target(value: str | None) -> float:
    if not isinstance(value, str):
        return HOOK_BGM_SECONDS
    if "-" in value:
        _, end_raw = [part.strip() for part in value.split("-", maxsplit=1)]
        return parse_timestamp(end_raw)
    return parse_timestamp(value)


def parse_srt(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    cues: list[dict[str, Any]] = []
    blocks = re.split(r"\n\s*\n", text)
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3 or "-->" not in lines[1]:
            continue
        start_raw, end_raw = [part.strip() for part in lines[1].split("-->", maxsplit=1)]
        cues.append(
            {
                "start_seconds": round(_parse_srt_timestamp(start_raw), 3),
                "end_seconds": round(_parse_srt_timestamp(end_raw), 3),
                "text": " ".join(lines[2:]),
            }
        )
    return cues


def _parse_srt_timestamp(value: str) -> float:
    hours, minutes, rest = value.split(":")
    seconds, milliseconds = rest.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000


def beat_window(start_seconds: float, end_seconds: float, *, fallback_end: float) -> tuple[float, float]:
    start = max(start_seconds, 0.0)
    end = end_seconds if end_seconds > start else fallback_end
    return round(start, 3), round(max(end, start), 3)


def load_audio_library(project_root: Path) -> dict[str, dict[str, Any]]:
    payload = load_json(project_root / "assets" / "audio" / "audio-library.json")
    tracks = payload.get("tracks") if isinstance(payload.get("tracks"), dict) else {}
    return {
        str(role): config
        for role, config in tracks.items()
        if isinstance(role, str) and isinstance(config, dict)
    }


def bgm_track_config(
    role: str,
    *,
    audio_library: dict[str, dict[str, Any]],
    fallback_path: str,
    fallback_gain_db: float,
    default_fade_in_seconds: float,
    default_fade_out_seconds: float,
) -> dict[str, Any]:
    override = audio_library.get(role, {})
    path_value = str(override.get("path") or fallback_path)
    return {
        "path": path_value,
        "role": role,
        "gain_db": float(override.get("gain_db", fallback_gain_db)),
        "loop": bool(override.get("loop", True)),
        "fade_in_seconds": float(override.get("fade_in_seconds", default_fade_in_seconds)),
        "fade_out_seconds": float(override.get("fade_out_seconds", default_fade_out_seconds)),
    }


def build_bgm_tracks(
    *,
    beat_sheet: list[dict[str, Any]],
    duration_seconds: float,
    bgm_target_db: float,
    root: Path,
    audio_library: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    techno_path = str((root / "remotion" / "public" / "bgm-techno.mp3").resolve())
    urban_path = str((root / "remotion" / "public" / "bgm-deep-urban.mp3").resolve())

    if not beat_sheet:
        hook_track = bgm_track_config(
            "hook_bed",
            audio_library=audio_library,
            fallback_path=techno_path,
            fallback_gain_db=max(float(bgm_target_db), -24.0),
            default_fade_in_seconds=0.18,
            default_fade_out_seconds=0.6,
        )
        return [
            {
                **hook_track,
                "start_seconds": 0.0,
                "end_seconds": min(HOOK_BGM_SECONDS, round(duration_seconds, 3)),
            }
        ]

    tracks: list[dict[str, Any]] = []
    for beat in beat_sheet:
        start_seconds, end_seconds = parse_time_range(str(beat.get("time_range") or ""))
        beat_name = str(beat.get("beat") or "").lower()
        purpose = str(beat.get("purpose") or "")
        combined = f"{beat_name} {purpose}"

        if "hook" in beat_name:
            hook_end_seconds = end_seconds if "bridge_bed" in audio_library else min(end_seconds, HOOK_BGM_SECONDS)
            start, end = beat_window(start_seconds, hook_end_seconds, fallback_end=HOOK_BGM_SECONDS)
            hook_track = bgm_track_config(
                "hook_bed",
                audio_library=audio_library,
                fallback_path=techno_path,
                fallback_gain_db=max(float(bgm_target_db), -24.0),
                default_fade_in_seconds=0.12,
                default_fade_out_seconds=0.45,
            )
            tracks.append(
                {
                    **hook_track,
                    "start_seconds": start,
                    "end_seconds": end,
                }
            )
            hook_duration = end - start
            if hook_duration >= HOOK_LAYER_MIN_SECONDS and "bridge_bed" in audio_library:
                bridge_layer = bgm_track_config(
                    "bridge_bed",
                    audio_library=audio_library,
                    fallback_path=urban_path,
                    fallback_gain_db=float(hook_track["gain_db"]) - 4.0,
                    default_fade_in_seconds=0.5,
                    default_fade_out_seconds=0.7,
                )
                tracks.append(
                    {
                        **bridge_layer,
                        "role": "hook_layer_bed",
                        "start_seconds": round(start + max(4.2, min(hook_duration * 0.22, 8.0)), 3),
                        "end_seconds": end,
                    }
                )
            continue

        if any(keyword in combined for keyword in ("proof", "案例", "证明", "反转", "对照")):
            start, end = beat_window(start_seconds, end_seconds, fallback_end=min(start_seconds + 18.0, duration_seconds))
            proof_track = bgm_track_config(
                "proof_bed",
                audio_library=audio_library,
                fallback_path=urban_path,
                fallback_gain_db=float(bgm_target_db) + 1.0,
                default_fade_in_seconds=0.22,
                default_fade_out_seconds=0.7,
            )
            tracks.append(
                {
                    **proof_track,
                    "start_seconds": start,
                    "end_seconds": end,
                }
            )
            continue

        if any(keyword in combined for keyword in ("framework", "框架", "模板", "步骤")):
            start, end = beat_window(start_seconds, end_seconds, fallback_end=min(start_seconds + 20.0, duration_seconds))
            framework_track = bgm_track_config(
                "framework_bed",
                audio_library=audio_library,
                fallback_path=urban_path,
                fallback_gain_db=float(bgm_target_db) + 2.0,
                default_fade_in_seconds=0.18,
                default_fade_out_seconds=0.8,
            )
            tracks.append(
                {
                    **framework_track,
                    "start_seconds": start,
                    "end_seconds": end,
                }
            )
            continue

        if any(keyword in combined for keyword in ("action", "cta", "outro", "signal", "停手信号")):
            start, end = beat_window(start_seconds, end_seconds, fallback_end=min(start_seconds + 14.0, duration_seconds))
            action_track = bgm_track_config(
                "action_bed",
                audio_library=audio_library,
                fallback_path=urban_path,
                fallback_gain_db=float(bgm_target_db) + 1.0,
                default_fade_in_seconds=0.2,
                default_fade_out_seconds=0.8,
            )
            tracks.append(
                {
                    **action_track,
                    "start_seconds": start,
                    "end_seconds": end,
                }
            )

    if tracks:
        sorted_tracks = sorted(tracks, key=lambda item: (float(item.get("start_seconds", 0.0)), float(item.get("end_seconds", 0.0))))
        if "bridge_bed" not in audio_library:
            return sorted_tracks
        bridged_tracks: list[dict[str, Any]] = []
        for index, track in enumerate(sorted_tracks):
            bridged_tracks.append(track)
            if index == len(sorted_tracks) - 1:
                continue
            current_end = float(track.get("end_seconds", 0.0))
            next_start = float(sorted_tracks[index + 1].get("start_seconds", current_end))
            gap_duration = next_start - current_end
            if gap_duration < 18.0:
                continue
            bridge_track = bgm_track_config(
                "bridge_bed",
                audio_library=audio_library,
                fallback_path=urban_path,
                fallback_gain_db=float(bgm_target_db) - 1.0,
                default_fade_in_seconds=0.35,
                default_fade_out_seconds=1.0,
            )
            bridged_tracks.append(
                {
                    **bridge_track,
                    "start_seconds": round(current_end, 3),
                    "end_seconds": round(next_start, 3),
                }
            )
        return sorted(bridged_tracks, key=lambda item: (float(item.get("start_seconds", 0.0)), float(item.get("end_seconds", 0.0))))

    hook_track = bgm_track_config(
        "hook_bed",
        audio_library=audio_library,
        fallback_path=techno_path,
        fallback_gain_db=max(float(bgm_target_db), -24.0),
        default_fade_in_seconds=0.18,
        default_fade_out_seconds=0.6,
    )
    return [
        {
            **hook_track,
            "start_seconds": 0.0,
            "end_seconds": min(HOOK_BGM_SECONDS, round(duration_seconds, 3)),
        }
    ]


def build_sfx_cues(beat_sheet: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cues: list[dict[str, Any]] = []
    for beat in beat_sheet:
        start_seconds, end_seconds = parse_time_range(str(beat.get("time_range") or ""))
        beat_duration = max(end_seconds - start_seconds, 0.0)
        beat_name = str(beat.get("beat") or "")
        purpose = str(beat.get("purpose") or "")
        text = f"{beat_name} {purpose}"
        if "hook" in beat_name:
            cues.append(
                {
                    "label": "hook_braam",
                    "preset": "braam_hit",
                    "start_seconds": round(start_seconds, 3),
                    "gain_db": -6.2,
                }
            )
            cues.append(
                {
                    "label": "hook_statement",
                    "preset": "sub_hit",
                    "start_seconds": round(start_seconds, 3),
                    "gain_db": -5.8,
                }
            )
            if beat_duration >= 10.0:
                cues.append(
                    {
                        "label": "hook_turn_reveal",
                        "preset": "reverse_suck",
                        "start_seconds": round(start_seconds + min(8.2, beat_duration - 0.35), 3),
                        "gain_db": -10.0,
                    }
                )
            if beat_duration >= 12.0:
                cues.append(
                    {
                        "label": "hook_turn_land",
                        "preset": "sub_hit",
                        "start_seconds": round(start_seconds + min(8.45, beat_duration - 0.1), 3),
                        "gain_db": -6.9,
                    }
                )
            if beat_duration >= 20.0:
                cues.append(
                    {
                        "label": "hook_pressure_swell",
                        "preset": "whoosh_riser",
                        "start_seconds": round(start_seconds + min(21.4, beat_duration - 0.8), 3),
                        "gain_db": -10.5,
                    }
                )
        if any(keyword in text for keyword in ("framework", "框架")):
            cues.append(
                {
                    "label": "framework_reveal",
                    "preset": "whoosh_riser",
                    "start_seconds": round(start_seconds, 3),
                    "gain_db": -7.2,
                }
            )
        if any(keyword in text for keyword in ("停手信号", "signal", "action")):
            cues.append(
                {
                    "label": "stop_signal_list",
                    "preset": "sub_hit",
                    "start_seconds": round(start_seconds, 3),
                    "gain_db": -6.2,
                }
            )
    return cues


def build_ordinal_sfx_cues(subtitle_cues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    patterns = (
        ("ordinal_first", "第一"),
        ("ordinal_second", "第二"),
        ("ordinal_third", "第三"),
        ("ordinal_fourth", "第四"),
    )
    cues: list[dict[str, Any]] = []
    seen_labels: set[str] = set()
    for cue in subtitle_cues:
        text = str(cue.get("text") or "")
        for label, token in patterns:
            if label in seen_labels:
                continue
            if token not in text:
                continue
            seen_labels.add(label)
            cues.append(
                {
                    "label": label,
                    "preset": "ordinal_tick",
                    "start_seconds": round(float(cue.get("start_seconds", 0.0)), 3),
                    "gain_db": -6.4,
                }
            )
    return cues


def build_opening_phrase_cues(
    subtitle_cues: list[dict[str, Any]],
    *,
    beat_sheet: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not any("hook" in str(beat.get("beat") or "").lower() for beat in beat_sheet):
        return []
    opening_cues = [
        cue
        for cue in subtitle_cues
        if float(cue.get("start_seconds", 0.0)) < OPENING_SFX_WINDOW_SECONDS
    ]
    if not opening_cues:
        return []

    cues: list[dict[str, Any]] = []
    seen_starts: set[float] = set()

    def append_once(*, label: str, preset: str, start_seconds: float, gain_db: float) -> None:
        rounded_start = round(max(start_seconds, 0.0), 3)
        if rounded_start in seen_starts:
            return
        seen_starts.add(rounded_start)
        cues.append(
            {
                "label": label,
                "preset": preset,
                "start_seconds": rounded_start,
                "gain_db": gain_db,
            }
        )

    question_cue = next(
        (
            cue
            for cue in opening_cues
            if any(token in str(cue.get("text") or "") for token in ("？", "?"))
        ),
        None,
    )
    if question_cue is not None:
        append_once(
            label="opening_question_braam",
            preset="braam_hit",
            start_seconds=float(question_cue.get("start_seconds", 0.0)),
            gain_db=-8.2,
        )

    reveal_cue = next(
        (
            cue
            for cue in opening_cues
            if any(token in str(cue.get("text") or "") for token in ("：", ":", "答案", "更扎心"))
        ),
        None,
    )
    if reveal_cue is not None:
        reveal_start = float(reveal_cue.get("start_seconds", 0.0))
        append_once(
            label="opening_reveal_suck",
            preset="reverse_suck",
            start_seconds=max(reveal_start - 0.18, 0.0),
            gain_db=-9.8,
        )
        append_once(
            label="opening_reveal_stab",
            preset="glitch_stab",
            start_seconds=reveal_start,
            gain_db=-8.4,
        )

    after_twenty_seconds_cue = next(
        (
            cue
            for cue in opening_cues
            if float(cue.get("start_seconds", 0.0)) >= 20.0
        ),
        None,
    )
    if after_twenty_seconds_cue is not None:
        append_once(
            label="opening_pressure_land",
            preset="impact_hit",
            start_seconds=float(after_twenty_seconds_cue.get("start_seconds", 0.0)),
            gain_db=-8.0,
        )

    return cues


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)
    packet_path = detect_content_packet(project_root)
    packet = load_json(packet_path)
    primary = packet.get("content_packet") if isinstance(packet.get("content_packet"), dict) else packet
    voiceover_profile = load_json(project_root / "content" / "postproduction" / "voiceover-profile.json")
    mix_defaults = voiceover_profile.get("mix_defaults") if isinstance(voiceover_profile.get("mix_defaults"), dict) else {}
    render_targets = voiceover_profile.get("render_targets") if isinstance(voiceover_profile.get("render_targets"), dict) else {}

    beat_sheet = [item for item in primary.get("beat_sheet", []) if isinstance(item, dict)]
    duration_seconds = parse_duration_target(primary.get("duration_target") or primary.get("runtime_target"))
    subtitle_draft = render_targets.get("subtitle_draft") if isinstance(render_targets.get("subtitle_draft"), str) else None
    subtitle_path = (project_root / subtitle_draft).resolve() if subtitle_draft else None
    subtitle_cues = parse_srt(subtitle_path)
    audio_library = load_audio_library(project_root)
    bgm_tracks = build_bgm_tracks(
        beat_sheet=beat_sheet,
        duration_seconds=duration_seconds,
        bgm_target_db=float(mix_defaults.get("bgm_target_db", -30.0)),
        root=repo_root(),
        audio_library=audio_library,
    )

    chapter_audio_beats = []
    for beat in beat_sheet:
        start_seconds, end_seconds = parse_time_range(str(beat.get("time_range") or ""))
        chapter_audio_beats.append(
            {
                "beat": beat.get("beat"),
                "start_seconds": round(start_seconds, 3),
                "end_seconds": round(end_seconds, 3),
                "purpose": beat.get("purpose"),
            }
        )

    payload = {
        "content_id": primary.get("content_id") or project_root.name,
        "platform": primary.get("platforms", ["bilibili"])[0] if isinstance(primary.get("platforms"), list) and primary.get("platforms") else "bilibili",
        "estimated_duration_seconds": round(duration_seconds, 3),
        "bgm_tracks": bgm_tracks,
        "sfx_cues": build_sfx_cues(beat_sheet) + build_ordinal_sfx_cues(subtitle_cues),
        "ducking_rules": {
            "bg_sidechain_ducking": True,
            "bg_sidechain_threshold": 0.018,
            "bg_sidechain_ratio": 10,
            "bg_sidechain_attack_ms": 15,
            "bg_sidechain_release_ms": 260,
            "sound_bed_gain_db": 0.0,
            "sfx_stem_gain_db": 7.8,
        },
        "chapter_audio_beats": chapter_audio_beats,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    payload["sfx_cues"] = [
        *payload["sfx_cues"],
        *build_opening_phrase_cues(subtitle_cues, beat_sheet=beat_sheet),
    ]

    output_path = (project_root / args.output).resolve()
    write_json(output_path, payload)
    print(
        json.dumps(
            {
                "output_path": str(output_path),
                "bgm_track_count": len(payload["bgm_tracks"]),
                "sfx_cue_count": len(payload["sfx_cues"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
