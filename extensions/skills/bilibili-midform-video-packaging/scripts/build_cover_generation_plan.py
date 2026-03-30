#!/usr/bin/env python3
"""Build a reusable Bilibili cover generation plan from a content packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", help="Media package root directory.")
    parser.add_argument("--content-id", help="Content package id under media-ops root.")
    parser.add_argument("--media-ops-root", help="Root directory containing media packages.")
    parser.add_argument(
        "--output",
        default="assets/final-cover/cover-generation-plan.json",
        help="Plan output path, relative to project root.",
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
    media_root = Path(args.media_ops_root).resolve() if args.media_ops_root else default_media_ops_root().resolve()
    return (media_root / args.content_id).resolve()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_content_packet(project_root: Path) -> Path:
    content_dir = project_root / "content"
    candidates = sorted(content_dir.glob("*video.json"))
    if not candidates:
        raise FileNotFoundError(f"No *video.json content packet found under {content_dir}")
    return candidates[0]


def relative_to_root(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def split_cover_text_lines(cover_text: str) -> list[str]:
    tokens = [token.strip() for token in cover_text.split() if token.strip()]
    if len(tokens) >= 2:
        if len(tokens) == 2:
            return tokens
        return [" ".join(tokens[: len(tokens) // 2]), " ".join(tokens[len(tokens) // 2 :])]

    compact = cover_text.replace(" ", "").strip()
    if not compact:
        return ["", ""]
    midpoint = max(2, len(compact) // 2)
    return [compact[:midpoint], compact[midpoint:]]


def sanitize_prompt_text(value: str) -> str:
    return value.replace("\n", " ").strip()


def select_cover_tags(packet: dict[str, Any]) -> list[str]:
    publish_metadata = packet.get("publish_metadata", {})
    tag_pool = publish_metadata.get("tags") or packet.get("tag_suggestions") or []
    deduped: list[str] = []
    for tag in tag_pool:
        text = str(tag).strip()
        if not text or text in deduped:
            continue
        deduped.append(text)
    return deduped[:3]


def build_background_prompt(packet: dict[str, Any]) -> str:
    cover_visual_direction = sanitize_prompt_text(str(packet.get("cover_visual_direction") or ""))
    thumbnail_options = packet.get("thumbnail_options") or []
    option_hint = sanitize_prompt_text(str(thumbnail_options[0] if thumbnail_options else ""))
    working_title = sanitize_prompt_text(str(packet.get("working_title") or packet.get("title") or ""))

    return (
        "High-contrast editorial thumbnail background for a Chinese Bilibili knowledge video, 16:9. "
        "No text, no letters, no numbers, no logos, no watermark, no subtitle. "
        "Reserve the left 45 percent as dark negative space for later typography. "
        "Focus the main subject on the right half: a stressed young East Asian professional frozen between two competing offer cards, "
        "surrounded by layered AI answer bubbles and decision overload UI cards. "
        "Cinematic lighting, black charcoal base, warning red accents, muted amber highlights, strong contrast, sharp edges, social-media thumbnail energy. "
        f"Core hook: {working_title}. "
        f"Visual direction: {cover_visual_direction}. "
        f"Preferred thumbnail angle: {option_hint}."
    )


def build_plan(project_root: Path, output_path: Path) -> dict[str, Any]:
    content_packet_path = find_content_packet(project_root)
    packet = load_json(content_packet_path)

    final_cover_dir = project_root / "assets" / "final-cover"
    final_cover_dir.mkdir(parents=True, exist_ok=True)

    background_path = final_cover_dir / "minimax-cover-bg-v1.png"
    svg_path = final_cover_dir / "bilibili-cover-final-v1.svg"
    png_path = final_cover_dir / "bilibili-cover-final-v1.png"
    lines = split_cover_text_lines(str(packet.get("cover_text") or packet.get("working_title") or ""))

    plan = {
        "project_root": str(project_root),
        "content_packet": relative_to_root(content_packet_path, project_root),
        "working_title": packet.get("working_title") or packet.get("title"),
        "cover_text": packet.get("cover_text"),
        "headline_lines": lines,
        "cover_visual_direction": packet.get("cover_visual_direction"),
        "thumbnail_options": packet.get("thumbnail_options") or [],
        "cover_tags": select_cover_tags(packet),
        "background_prompt": build_background_prompt(packet),
        "generation": {
            "model": "MiniMax image-01",
            "aspect_ratio": "16:9",
            "background_output": relative_to_root(background_path, project_root),
            "final_cover_svg": relative_to_root(svg_path, project_root),
            "final_cover_png": relative_to_root(png_path, project_root),
            "overlay_strategy": "minimax_background_plus_deterministic_svg_text",
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return plan


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)
    output_path = (project_root / args.output).resolve()
    plan = build_plan(project_root, output_path)
    print(json.dumps({"cover_generation_plan": str(output_path), "final_cover_png": plan["generation"]["final_cover_png"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
