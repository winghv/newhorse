#!/usr/bin/env python3
"""Compose a deterministic Bilibili cover SVG from a generated background image."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, help="Path to cover-generation-plan.json")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(project_root: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = project_root / candidate
    return candidate.resolve()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def svg_text_lines(lines: list[str], *, start_x: int, start_y: int, step_y: int, class_name: str) -> str:
    fragments: list[str] = []
    for index, line in enumerate(lines):
        y = start_y + index * step_y
        fragments.append(f'<text x="{start_x}" y="{y}" class="{class_name}">{escape_xml(line)}</text>')
    return "\n  ".join(fragments)


def chip_rects(tags: list[str]) -> str:
    base_x = 96
    y = 88
    width = 190
    gap = 18
    parts: list[str] = []
    for index, tag in enumerate(tags[:3]):
        x = base_x + index * (width + gap)
        fill = "#F2C94C" if index == 0 else "#181818"
        text_fill = "#111111" if index == 0 else "#FFF4E8"
        parts.append(f'<rect x="{x}" y="{y}" width="{width}" height="58" rx="18" fill="{fill}" opacity="0.96"/>')
        parts.append(
            f'<text x="{x + 24}" y="{y + 37}" style="fill:{text_fill};font:800 28px \'PingFang SC\', \'Microsoft YaHei\', sans-serif;">{escape_xml(tag)}</text>'
        )
    return "\n  ".join(parts)


def build_svg(plan: dict[str, Any], project_root: Path) -> str:
    generation = plan["generation"]
    background_path = resolve_path(project_root, generation["background_output"])
    if not background_path.exists():
        raise FileNotFoundError(f"Background image missing: {background_path}")

    lines = [str(line).strip() for line in plan.get("headline_lines", []) if str(line).strip()]
    if not lines:
        lines = [str(plan.get("cover_text") or plan.get("working_title") or "").strip()]
    while len(lines) < 2:
        lines.append("")

    working_title = str(plan.get("working_title") or "").strip()
    subline = working_title if len(working_title) <= 24 else working_title[:24] + "..."
    background_uri = background_path.resolve().as_uri()
    tags = [str(tag) for tag in plan.get("cover_tags", []) if str(tag).strip()]
    if not tags:
        tags = ["AI", "判断力", "职场成长"]

    first_line = escape_xml(lines[0])
    second_line = escape_xml(lines[1])
    subline_text = escape_xml(subline)

    return f"""<svg width="1920" height="1080" viewBox="0 0 1920 1080" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="leftShade" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#090909" stop-opacity="0.94"/>
      <stop offset="58%" stop-color="#0B0B0B" stop-opacity="0.82"/>
      <stop offset="100%" stop-color="#0B0B0B" stop-opacity="0.20"/>
    </linearGradient>
    <linearGradient id="bottomShade" x1="0" y1="1" x2="0" y2="0">
      <stop offset="0%" stop-color="#050505" stop-opacity="0.82"/>
      <stop offset="100%" stop-color="#050505" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <style>
    .headline-top {{ fill: #FFF6E9; font: 900 118px 'PingFang SC', 'Microsoft YaHei', sans-serif; letter-spacing: 1px; }}
    .headline-bottom {{ fill: #FFF6E9; font: 900 116px 'PingFang SC', 'Microsoft YaHei', sans-serif; letter-spacing: 1px; }}
    .subline {{ fill: #E7DAC5; font: 700 34px 'PingFang SC', 'Microsoft YaHei', sans-serif; }}
    .side-note {{ fill: #FFF0DE; font: 800 28px 'PingFang SC', 'Microsoft YaHei', sans-serif; }}
  </style>

  <image href="{background_uri}" x="0" y="0" width="1920" height="1080" preserveAspectRatio="xMidYMid slice"/>
  <rect x="0" y="0" width="1120" height="1080" fill="url(#leftShade)"/>
  <rect x="0" y="760" width="1920" height="320" fill="url(#bottomShade)"/>
  <rect x="44" y="44" width="1832" height="992" rx="32" fill="none" stroke="#F2C94C" stroke-opacity="0.28" stroke-width="4"/>
  <rect x="72" y="72" width="1776" height="936" rx="28" fill="none" stroke="#FFF4E8" stroke-opacity="0.08" stroke-width="2"/>

  {chip_rects(tags)}

  <rect x="96" y="680" width="1048" height="152" rx="32" fill="#E24A3B" opacity="0.98"/>
  <rect x="1226" y="774" width="524" height="90" rx="24" fill="#111111" opacity="0.78"/>
  <text x="1264" y="833" class="side-note">不是没答案  是不敢拍板</text>

  <text x="96" y="536" class="headline-top">{first_line}</text>
  <text x="140" y="784" class="headline-bottom">{second_line}</text>
  <text x="98" y="914" class="subline">{subline_text}</text>
</svg>
"""


def main() -> int:
    args = parse_args()
    plan_path = Path(args.plan).resolve()
    plan = load_json(plan_path)
    project_root = Path(plan["project_root"]).resolve()
    svg_path = resolve_path(project_root, plan["generation"]["final_cover_svg"])
    ensure_parent(svg_path)
    svg_payload = build_svg(plan, project_root)
    svg_path.write_text(svg_payload, encoding="utf-8")
    print(json.dumps({"cover_svg": str(svg_path), "cover_png": plan["generation"]["final_cover_png"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
