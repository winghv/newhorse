#!/usr/bin/env python3
"""Build a structured voice performance plan for narration-driven videos."""

from __future__ import annotations

import argparse
import json
import re
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
        "--output",
        default="content/postproduction/voice-performance-plan.json",
        help="Voice performance plan output path relative to the project root.",
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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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


def segment_blocks(text: str, max_chars: int = DEFAULT_SEGMENT_MAX_CHARS) -> list[str]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
    if not blocks:
        return []

    segments: list[str] = []
    for block in blocks:
        block_segments = segment_text(block, max_chars=max_chars)
        if block_segments:
            segments.extend(block_segments)
    return segments


def detect_scene_purpose(segment: str, *, index: int, total: int) -> str:
    if index == 0 or "？" in segment or "为什么" in segment:
        return "hook"
    if any(keyword in segment for keyword in ("举个例子", "举个", "案例", "offer", "相反建议", "证明")):
        return "proof"
    if any(keyword in segment for keyword in ("框架", "来源", "反证", "约束", "试错", "第一", "第二", "第三", "第四", "信号")):
        return "framework"
    if index == total - 1 or any(keyword in segment for keyword in ("最后", "别再", "关掉", "评论区", "拍板")):
        return "cta"
    return "explanation"


def purpose_directives(scene_purpose: str, base_speed: float) -> dict[str, Any]:
    if scene_purpose == "hook":
        return {"emotion": "surprised", "speed": min(base_speed + 0.05, 1.08), "pause_after_ms": 160, "intensity": "high"}
    if scene_purpose == "proof":
        return {"emotion": "calm", "speed": base_speed, "pause_after_ms": 220, "intensity": "medium"}
    if scene_purpose == "framework":
        return {"emotion": "fluent", "speed": max(base_speed - 0.03, 0.9), "pause_after_ms": 260, "intensity": "medium"}
    if scene_purpose == "cta":
        return {"emotion": "calm", "speed": max(base_speed - 0.01, 0.9), "pause_after_ms": 300, "intensity": "medium_high"}
    return {"emotion": "calm", "speed": base_speed, "pause_after_ms": 220, "intensity": "medium"}


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)
    packet_path = detect_content_packet(project_root)
    packet = load_json(packet_path)
    primary = packet.get("content_packet") if isinstance(packet.get("content_packet"), dict) else packet

    voice_assets = primary.get("voiceover_assets") if isinstance(primary.get("voiceover_assets"), dict) else {}
    target_profile = voice_assets.get("target_profile") if isinstance(voice_assets.get("target_profile"), dict) else {}
    script_rel = voice_assets.get("script_path") or primary.get("narration_script") or primary.get("subtitle_source_script")
    if not isinstance(script_rel, str) or not script_rel:
        raise FileNotFoundError("could not resolve narration script path from content packet")

    script_path = (project_root / script_rel).resolve()
    if not script_path.exists():
        raise FileNotFoundError(f"narration script missing: {script_path}")

    raw_script = script_path.read_text(encoding="utf-8")
    cleaned_script = clean_markdown(raw_script)
    base_speed = float(target_profile.get("speed", 1.0))
    voice_name = target_profile.get("voice_name") or "Chinese (Mandarin)_Reliable_Executive"
    segments = segment_blocks(cleaned_script, max_chars=72)

    segment_payload: list[dict[str, Any]] = []
    total = len(segments)
    for index, segment in enumerate(segments):
        scene_purpose = detect_scene_purpose(segment, index=index, total=total)
        directives = purpose_directives(scene_purpose, base_speed)
        segment_payload.append(
            {
                "index": index,
                "text": segment,
                "voice_id": voice_name,
                "emotion": directives["emotion"],
                "speed": round(float(directives["speed"]), 3),
                "pause_after_ms": int(directives["pause_after_ms"]),
                "intensity": directives["intensity"],
                "scene_purpose": scene_purpose,
            }
        )

    payload = {
        "content_id": primary.get("content_id") or project_root.name,
        "platform": primary.get("platforms", ["bilibili"])[0] if isinstance(primary.get("platforms"), list) and primary.get("platforms") else "bilibili",
        "source_script": relative_to_project(script_path, project_root),
        "voice_strategy_defaults": {
            "primary_voice_id": voice_name,
            "base_speed": round(base_speed, 3),
            "default_emotion": "calm",
        },
        "segments": segment_payload,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    output_path = (project_root / args.output).resolve()
    write_json(output_path, payload)
    print(json.dumps({"output_path": str(output_path), "segment_count": len(segment_payload)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
