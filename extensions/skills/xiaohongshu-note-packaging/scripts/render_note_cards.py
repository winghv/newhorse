#!/usr/bin/env python3
"""Render Xiaohongshu note cards to PNG files from the asset brief."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path
from typing import Any


CANVAS_WIDTH = 1242
CANVAS_HEIGHT = 1660
FONT_PATH = "/System/Library/Fonts/Hiragino Sans GB.ttc"
BACKGROUND = "#f6f1e7"
INK = "#171412"
MUTED = "#6e6258"
ACCENT = "#d74a37"
ACCENT_SOFT = "#f5d9d2"
CARD = "#fffdf8"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def default_media_ops_root() -> Path:
    return Path(__file__).resolve().parents[4] / "data" / "media-ops"


def resolve_project_root(args: argparse.Namespace) -> Path:
    if args.project_root:
        return Path(args.project_root).resolve()
    media_ops_root = Path(args.media_ops_root).resolve() if args.media_ops_root else default_media_ops_root().resolve()
    return (media_ops_root / args.content_id).resolve()


def escape_drawtext_path(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace(":", r"\:")


def ensure_font() -> None:
    if not Path(FONT_PATH).exists():
        raise FileNotFoundError(f"Missing font file: {FONT_PATH}")


def char_units(char: str) -> float:
    if char.isspace():
        return 0.35
    if char.isascii():
        if char.isalnum():
            return 0.58
        return 0.45
    return 1.0


def wrap_text(text: str, max_units: float) -> str:
    stripped = text.strip()
    if not stripped:
        return ""

    lines: list[str] = []
    current_chars: list[str] = []
    current_units = 0.0
    last_breakable_index = -1

    for char in stripped:
        if char == "\n":
            lines.append("".join(current_chars).strip())
            current_chars = []
            current_units = 0.0
            last_breakable_index = -1
            continue

        units = char_units(char)
        if current_chars and current_units + units > max_units:
            if last_breakable_index >= 0:
                line = "".join(current_chars[: last_breakable_index + 1]).strip()
                remainder = current_chars[last_breakable_index + 1 :]
                lines.append(line)
                current_chars = remainder
                current_units = sum(char_units(item) for item in current_chars)
            else:
                lines.append("".join(current_chars).strip())
                current_chars = []
                current_units = 0.0
            last_breakable_index = -1

        current_chars.append(char)
        current_units += units
        if char.isspace() or char in "，。！？；：、/|-":
            last_breakable_index = len(current_chars) - 1

    if current_chars:
        lines.append("".join(current_chars).strip())
    return "\n".join(line for line in lines if line)


def make_textfile(temp_dir: Path, name: str, text: str, max_units: float) -> Path:
    wrapped = wrap_text(text, max_units)
    target = temp_dir / f"{name}.txt"
    target.write_text(wrapped, encoding="utf-8")
    return target


def page_number_color(role: str) -> str:
    if role == "cta":
        return "#f8efe4"
    return ACCENT_SOFT


def build_filter_for_page(page: dict[str, Any], temp_dir: Path) -> str:
    page_no = int(page["page"])
    role = str(page.get("role") or "")
    headline = str(page.get("headline") or "")
    overlay_lines = page.get("overlay_lines") or []
    supporting = overlay_lines[1] if len(overlay_lines) > 1 else ""
    evidence = str(page.get("evidence") or "")
    handoff_note = str(page.get("handoff_note") or "")

    headline_size = 78 if page_no == 1 else 68
    support_size = 42 if page_no == 1 else 40
    footer_size = 30
    left = 108
    top = 220
    if role == "cta":
        top = 250

    headline_file = make_textfile(temp_dir, f"page-{page_no:02d}-headline", headline, 15.5 if page_no == 1 else 18.5)
    support_file = make_textfile(temp_dir, f"page-{page_no:02d}-support", supporting, 22.0)
    evidence_file = make_textfile(temp_dir, f"page-{page_no:02d}-evidence", evidence, 28.0)
    handoff_file = make_textfile(temp_dir, f"page-{page_no:02d}-handoff", handoff_note, 30.0)

    filters = [
        f"drawbox=x=0:y=0:w={CANVAS_WIDTH}:h={CANVAS_HEIGHT}:color={BACKGROUND}:t=fill",
        f"drawbox=x=0:y=0:w={CANVAS_WIDTH}:h=92:color={ACCENT}:t=fill",
        f"drawbox=x=66:y=126:w={CANVAS_WIDTH-132}:h={CANVAS_HEIGHT-214}:color={CARD}:t=fill",
        f"drawbox=x=66:y=126:w=18:h={CANVAS_HEIGHT-214}:color={ACCENT}:t=fill",
        f"drawbox=x=96:y=150:w=104:h=104:color={page_number_color(role)}:t=fill",
        (
            "drawtext="
            f"fontfile='{escape_drawtext_path(Path(FONT_PATH))}':"
            f"text='{page_no}':fontcolor={ACCENT}:fontsize=54:"
            "x=126:y=170"
        ),
        (
            "drawtext="
            f"fontfile='{escape_drawtext_path(Path(FONT_PATH))}':"
            f"textfile='{escape_drawtext_path(headline_file)}':fontcolor={INK}:fontsize={headline_size}:"
            f"line_spacing=18:x={left}:y={top}"
        ),
        (
            "drawtext="
            f"fontfile='{escape_drawtext_path(Path(FONT_PATH))}':"
            f"textfile='{escape_drawtext_path(support_file)}':fontcolor={MUTED}:fontsize={support_size}:"
            f"line_spacing=16:x={left}:y={top + 220}"
        ),
        f"drawbox=x={left}:y={CANVAS_HEIGHT-350}:w={CANVAS_WIDTH-2*left}:h=112:color={ACCENT_SOFT}:t=fill",
        (
            "drawtext="
            f"fontfile='{escape_drawtext_path(Path(FONT_PATH))}':"
            f"textfile='{escape_drawtext_path(evidence_file)}':fontcolor={ACCENT}:fontsize={footer_size}:"
            f"line_spacing=10:x={left+26}:y={CANVAS_HEIGHT-320}"
        ),
        (
            "drawtext="
            f"fontfile='{escape_drawtext_path(Path(FONT_PATH))}':"
            f"textfile='{escape_drawtext_path(handoff_file)}':fontcolor={MUTED}:fontsize=26:"
            f"line_spacing=8:x={left}:y={CANVAS_HEIGHT-180}"
        ),
    ]

    if role == "checklist-item":
        filters.extend(
            [
                f"drawbox=x={left}:y={top + 390}:w={CANVAS_WIDTH-2*left}:h=250:color=#fbf6ef:t=fill",
                f"drawbox=x={left+24}:y={top + 428}:w=34:h=34:color={ACCENT}:t=2",
                f"drawbox=x={left+24}:y={top + 498}:w=34:h=34:color={ACCENT}:t=2",
                f"drawbox=x={left+24}:y={top + 568}:w=34:h=34:color={ACCENT}:t=2",
            ]
        )
    elif role == "operator-tip":
        filters.extend(
            [
                f"drawbox=x={left}:y={top + 360}:w={CANVAS_WIDTH-2*left}:h=280:color=#f7e9d7:t=fill",
                f"drawbox=x={left}:y={top + 360}:w=12:h=280:color={ACCENT}:t=fill",
            ]
        )
    elif role == "cta":
        filters.extend(
            [
                (
                    "drawtext="
                    f"fontfile='{escape_drawtext_path(Path(FONT_PATH))}':"
                    f"text='1 / 2 / 3':fontcolor={ACCENT_SOFT}:fontsize=170:"
                    "x=(w-text_w)/2:y=760"
                ),
                f"drawbox=x={left}:y={top + 360}:w={CANVAS_WIDTH-2*left}:h=180:color=#fff4f2:t=fill",
            ]
        )
    else:
        filters.extend(
            [
                f"drawbox=x={left}:y={top + 380}:w={CANVAS_WIDTH-2*left}:h=210:color=#fbf6ef:t=fill",
                f"drawbox=x={left+40}:y={top + 418}:w={CANVAS_WIDTH-2*left-80}:h=8:color={ACCENT}:t=fill",
                f"drawbox=x={left+40}:y={top + 488}:w={CANVAS_WIDTH-2*left-140}:h=8:color={ACCENT}:t=fill",
                f"drawbox=x={left+40}:y={top + 558}:w={CANVAS_WIDTH-2*left-220}:h=8:color={ACCENT}:t=fill",
            ]
        )

    return ",".join(filters)


def render_page(page: dict[str, Any], output_path: Path, temp_dir: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    filter_string = build_filter_for_page(page, temp_dir)
    command = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c={BACKGROUND}:s={CANVAS_WIDTH}x{CANVAS_HEIGHT}:d=1",
        "-vf",
        filter_string,
        "-frames:v",
        "1",
        str(output_path),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", help="Media package root directory.")
    parser.add_argument("--content-id", help="Content package id under media-ops root.")
    parser.add_argument("--media-ops-root", help="Root directory containing media packages.")
    args = parser.parse_args()
    if not args.project_root and not args.content_id:
        parser.error("one of --project-root or --content-id is required")
    return args


def main() -> int:
    args = parse_args()
    ensure_font()
    project_root = resolve_project_root(args)
    if not project_root.exists():
        raise FileNotFoundError(f"Project root does not exist: {project_root}")

    asset_brief_path = project_root / "assets" / "note" / "note-asset-brief.json"
    if not asset_brief_path.exists():
        raise FileNotFoundError(f"Missing asset brief: {asset_brief_path}")
    asset_brief = load_json(asset_brief_path)
    pages = asset_brief.get("pages") or []
    if not pages:
        raise SystemExit("Asset brief has no pages to render.")

    temp_dir = project_root / "assets" / "note" / ".tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    rendered_paths: list[str] = []
    for page in pages:
        output_path = project_root / str(page["output_path"])
        render_page(page, output_path, temp_dir)
        rendered_paths.append(str(output_path))

    print(json.dumps({"rendered": rendered_paths}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
