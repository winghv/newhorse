#!/usr/bin/env python3
"""Build a MiniMax-ready TTS handoff package from a media content packet."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SENTENCE_BREAKS = "。！？；"
CLAUSE_BREAKS = "，、："
DEFAULT_SEGMENT_MAX_CHARS = 180


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", help="Media package root directory.")
    parser.add_argument("--content-id", help="Content package id under the media-ops root.")
    parser.add_argument(
        "--media-ops-root",
        help="Root directory containing media packages. Defaults to repo-local data/media-ops.",
    )
    parser.add_argument(
        "--tts-input-output",
        default="content/postproduction/voiceover-tts-input.txt",
        help="Output path for TTS input text, relative to project root.",
    )
    parser.add_argument(
        "--segments-output",
        default="content/postproduction/voiceover-segments.json",
        help="Output path for TTS segments JSON, relative to project root.",
    )
    parser.add_argument(
        "--profile-output",
        default="content/postproduction/voiceover-profile.json",
        help="Output path for voiceover profile JSON, relative to project root.",
    )
    parser.add_argument(
        "--output-audio",
        default="content/postproduction/minimax-output/voiceover.mp3",
        help="Expected output audio path, relative to project root.",
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


def relative_to_project(path: Path, project_root: Path) -> str:
    return str(path.resolve().relative_to(project_root.resolve()))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_candidate(project_root: Path, raw_path: str | None) -> Path | None:
    if not raw_path:
        return None
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = project_root / candidate
    return candidate.resolve()


def clean_markdown(text: str) -> str:
    cleaned_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            cleaned_lines.append("")
            continue
        if line.startswith("#"):
            continue
        line = re.sub(r"`([^`]+)`", r"\1", line)
        cleaned_lines.append(line)
    cleaned = "\n".join(cleaned_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def split_oversized_sentence(sentence: str, max_chars: int) -> list[str]:
    sentence = sentence.strip()
    if not sentence:
        return []
    if len(sentence) <= max_chars:
        return [sentence]

    fragments = re.findall(rf"[^{re.escape(CLAUSE_BREAKS)}]+(?:[{re.escape(CLAUSE_BREAKS)}]+|$)", sentence)
    fragments = [fragment.strip() for fragment in fragments if fragment.strip()]
    if len(fragments) == 1 and len(fragments[0]) > max_chars:
        return [fragments[0][index : index + max_chars] for index in range(0, len(fragments[0]), max_chars)]

    chunks: list[str] = []
    current = ""
    for fragment in fragments:
        proposed = f"{current}{fragment}"
        if current and len(proposed) > max_chars:
            chunks.append(current)
            current = fragment
            continue
        current = proposed
    if current:
        chunks.append(current)
    return chunks


def sentence_units(text: str, max_chars: int) -> list[str]:
    units: list[str] = []
    blocks = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
    for block in blocks:
        sentences = re.findall(rf"[^{re.escape(SENTENCE_BREAKS)}]+(?:[{re.escape(SENTENCE_BREAKS)}]+|$)", block)
        refined = [sentence.strip() for sentence in sentences if sentence.strip()]
        if not refined:
            refined = [block]
        for sentence in refined:
            units.extend(split_oversized_sentence(sentence, max_chars=max_chars))
    return units


def segment_text(text: str, max_chars: int = DEFAULT_SEGMENT_MAX_CHARS) -> list[str]:
    units = sentence_units(text, max_chars=max_chars)
    segments: list[str] = []
    current = ""
    for block in units:
        if not current:
            current = block
            continue
        if len(current) + 1 + len(block) <= max_chars:
            current = f"{current} {block}"
            continue
        segments.append(current.strip())
        current = block
    if current:
        segments.append(current.strip())
    return segments


def ensure_voice_performance_plan(project_root: Path) -> Path | None:
    plan_path = project_root / "content" / "postproduction" / "voice-performance-plan.json"
    if plan_path.exists():
        return plan_path

    builder = Path(__file__).with_name("build_voice_performance_plan.py")
    if not builder.exists():
        return None

    subprocess.run(
        [
            sys.executable,
            str(builder),
            "--project-root",
            str(project_root),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return plan_path if plan_path.exists() else None


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)
    packet_path = detect_content_packet(project_root)
    packet = load_json(packet_path)
    primary = packet.get("content_packet") if isinstance(packet.get("content_packet"), dict) else packet

    voice_assets = primary.get("voiceover_assets") if isinstance(primary.get("voiceover_assets"), dict) else {}
    script_rel = (
        voice_assets.get("script_path")
        or primary.get("narration_script")
        or primary.get("subtitle_source_script")
    )
    if not isinstance(script_rel, str) or not script_rel:
        raise FileNotFoundError("could not resolve narration script path from content packet")
    script_path = (project_root / script_rel).resolve()
    if not script_path.exists():
        raise FileNotFoundError(f"narration script missing: {script_path}")

    raw_script = script_path.read_text(encoding="utf-8")
    tts_text = clean_markdown(raw_script)
    performance_plan_path = ensure_voice_performance_plan(project_root)
    performance_plan = load_json(performance_plan_path)

    target_profile = voice_assets.get("target_profile") if isinstance(voice_assets.get("target_profile"), dict) else {}
    voice_name = target_profile.get("voice_name") or "Chinese (Mandarin)_Reliable_Executive"
    speed = target_profile.get("speed", 1.0)

    performance_segments = performance_plan.get("segments") if isinstance(performance_plan.get("segments"), list) else []
    if performance_segments:
        segments_payload = [
            {
                "text": str(item.get("text") or ""),
                "voice_id": str(item.get("voice_id") or voice_name),
                "emotion": str(item.get("emotion") or "calm"),
                "speed": float(item.get("speed", speed)),
                "pause_after_ms": int(item.get("pause_after_ms", 220)),
                "intensity": str(item.get("intensity") or "medium"),
                "scene_purpose": str(item.get("scene_purpose") or "explanation"),
            }
            for item in performance_segments
            if isinstance(item, dict) and str(item.get("text") or "").strip()
        ]
    else:
        segments_payload = [
            {
                "text": segment,
                "voice_id": voice_name,
                "emotion": "calm",
                "speed": speed,
                "pause_after_ms": 220,
                "intensity": "medium",
                "scene_purpose": "explanation",
            }
            for segment in segment_text(tts_text)
        ]

    tts_input_path = (project_root / args.tts_input_output).resolve()
    segments_path = (project_root / args.segments_output).resolve()
    profile_path = (project_root / args.profile_output).resolve()
    output_audio_path = (project_root / args.output_audio).resolve()

    write_text(tts_input_path, tts_text + "\n")
    write_json(segments_path, segments_payload)

    default_emotion = "calm"
    delivery_profile = "tight_explanatory"
    if performance_plan.get("voice_strategy_defaults") and isinstance(performance_plan["voice_strategy_defaults"], dict):
        default_emotion = str(performance_plan["voice_strategy_defaults"].get("default_emotion") or default_emotion)
        delivery_profile = str(
            performance_plan["voice_strategy_defaults"].get("delivery_profile") or delivery_profile
        )

    profile_payload = {
        "platform": primary.get("platforms", ["bilibili"])[0] if isinstance(primary.get("platforms"), list) and primary.get("platforms") else "bilibili",
        "content_id": primary.get("content_id") or project_root.name,
        "voiceover_required": True,
        "generation_status": "handoff_ready",
        "voice_strategy": {
            "primary_voice_id": voice_name,
            "model": "speech-2.8-hd",
            "language": "zh-CN",
            "delivery_profile": delivery_profile,
            "speed": speed,
            "volume": 1.0,
            "pitch": 0,
            "emotion": default_emotion,
            "default_emotion": default_emotion,
            "segment_count": len(segments_payload),
        },
        "render_targets": {
            "voiceover_audio": relative_to_project(output_audio_path, project_root),
            "subtitle_source": relative_to_project(script_path, project_root),
            "tts_input": relative_to_project(tts_input_path, project_root),
            "segments_file": relative_to_project(segments_path, project_root),
            "subtitle_draft": primary.get("subtitle_package", {}).get("estimated_srt", "content/postproduction/subtitles.srt"),
            "voice_performance_plan": relative_to_project(performance_plan_path, project_root) if performance_plan_path else None,
        },
        "notes": [
            "本文件由 build_tts_handoff.py 自动生成。",
            "生成音频前请先确认 MINIMAX_API_KEY 和 MINIMAX_API_HOST 已配置。",
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(profile_path, profile_payload)

    print(
        json.dumps(
            {
                "tts_input": str(tts_input_path),
                "segments_file": str(segments_path),
                "profile_path": str(profile_path),
                "segment_count": len(segments_payload),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
