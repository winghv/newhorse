#!/usr/bin/env python3
"""Bootstrap a page-level asset brief for a Xiaohongshu note package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


GLOBAL_STYLE = {
    "visual_language": "清单型知识卡，白底黑字，红色作为风险和禁止提示色。",
    "layout_system": "每页一个主要信息点，大标题 + 1-3 条辅助信息，不堆长段落。",
    "typography": "标题要像可直接执行的命令，正文保持简短、可扫读。",
    "tone": "像交给团队直接执行的发布前检查卡，而不是泛泛方法论。",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def default_media_ops_root() -> Path:
    return Path(__file__).resolve().parents[4] / "data" / "media-ops"


def resolve_project_root(args: argparse.Namespace) -> Path:
    if args.project_root:
        return Path(args.project_root).resolve()
    media_ops_root = Path(args.media_ops_root).resolve() if args.media_ops_root else default_media_ops_root().resolve()
    return (media_ops_root / args.content_id).resolve()


def detect_content_packet(project_root: Path) -> Path:
    content_dir = project_root / "content"
    for pattern in ("*note.json", "content-packet.json", "*.json"):
        matches = sorted(path for path in content_dir.glob(pattern) if path.is_file())
        if matches:
            return matches[0]
    raise FileNotFoundError(f"Missing note packet under: {content_dir}")


def slug_for_page(page: dict[str, Any]) -> str:
    role = str(page.get("role") or "page").lower().replace("_", "-")
    if role == "hook":
        return "cover"
    return role


def overlay_lines(page: dict[str, Any]) -> list[str]:
    lines = [str(page.get("headline") or "").strip()]
    supporting = str(page.get("supporting_text") or "").strip()
    if supporting:
        lines.append(supporting)
    return [line for line in lines if line]


def output_path_for_page(page_number: int, page: dict[str, Any]) -> str:
    return f"assets/note/page-{page_number:02d}-{slug_for_page(page)}.png"


def build_asset_page(page_number: int, page: dict[str, Any], cover_title: str) -> dict[str, Any]:
    overlay = overlay_lines(page)
    headline = str(page.get("headline") or "").strip()
    visual_direction = str(page.get("visual_direction") or "").strip()
    evidence = str(page.get("evidence") or "").strip()
    handoff_note = str(page.get("handoff_note") or "").strip()

    design_goal = headline or cover_title
    if page_number == 1 and cover_title:
        design_goal = cover_title

    return {
        "page": page_number,
        "role": page.get("role"),
        "output_path": output_path_for_page(page_number, page),
        "headline": headline,
        "overlay_lines": overlay,
        "visual_direction": visual_direction,
        "design_goal": design_goal,
        "evidence": evidence,
        "handoff_note": handoff_note,
        "status": "pending_design",
    }


def build_asset_brief(project_root: Path, packet: dict[str, Any]) -> dict[str, Any]:
    page_plan = packet.get("page_plan") or []
    cover_title = str(packet.get("cover_title") or "")
    pages = [build_asset_page(index, page, cover_title) for index, page in enumerate(page_plan, start=1) if isinstance(page, dict)]
    return {
        "content_id": project_root.name,
        "platform": "xiaohongshu",
        "format": "note",
        "series_name": (packet.get("publish_metadata") or {}).get("series_name"),
        "cover_title": cover_title,
        "cover_visual_direction": packet.get("cover_visual_direction"),
        "global_style": GLOBAL_STYLE,
        "pages": pages,
        "delivery_checklist": [
            "每页导出为 3:4 竖版 PNG",
            "封面承诺和标题必须一致",
            "结尾页必须保留明确评论触发",
        ],
    }


def build_prompt_doc(project_root: Path, packet: dict[str, Any], asset_brief: dict[str, Any]) -> str:
    lines = [
        "# Xiaohongshu Note Asset Prompts",
        "",
        f"- `content_id`: `{project_root.name}`",
        f"- `cover_title`: `{packet.get('cover_title') or ''}`",
        f"- `series_name`: `{(packet.get('publish_metadata') or {}).get('series_name') or ''}`",
        "",
        "## Global Style",
        "",
        f"- {GLOBAL_STYLE['visual_language']}",
        f"- {GLOBAL_STYLE['layout_system']}",
        f"- {GLOBAL_STYLE['typography']}",
        f"- {GLOBAL_STYLE['tone']}",
        "",
    ]

    for page in asset_brief["pages"]:
        lines.extend(
            [
                f"## Page {page['page']}",
                "",
                f"- `output_path`: `{page['output_path']}`",
                f"- `role`: `{page.get('role') or ''}`",
                f"- `headline`: `{page.get('headline') or ''}`",
                f"- `design_goal`: `{page.get('design_goal') or ''}`",
                f"- `visual_direction`: {page.get('visual_direction') or ''}",
                f"- `evidence`: {page.get('evidence') or ''}",
                f"- `handoff_note`: {page.get('handoff_note') or ''}",
                "- `text_overlay`:",
            ]
        )
        overlay_lines_list = page.get("overlay_lines") or []
        if overlay_lines_list:
            lines.extend([f"  - {line}" for line in overlay_lines_list])
        else:
            lines.append("  - n/a")
        lines.append("")
    return "\n".join(lines) + "\n"


def update_note_packet(packet: dict[str, Any], asset_brief: dict[str, Any]) -> dict[str, Any]:
    updated = dict(packet)
    updated["image_plan"] = [
        {
            "path": page["output_path"],
            "role": f"第 {page['page']} 页，{page.get('role') or 'page'}",
        }
        for page in asset_brief["pages"]
    ]
    existing_checklist = [str(item) for item in (packet.get("asset_checklist") or []) if item]
    extra_items = [
        f"{len(asset_brief['pages'])} 张页卡 PNG",
        "封面页卡和内页页卡同一视觉系统",
        "评论触发页单独检查可读性",
    ]
    deduped: list[str] = []
    seen: set[str] = set()
    for item in existing_checklist + extra_items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    updated["asset_checklist"] = deduped
    updated["asset_brief_path"] = "assets/note/note-asset-brief.json"
    return updated


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
    project_root = resolve_project_root(args)
    if not project_root.exists():
        raise FileNotFoundError(f"Project root does not exist: {project_root}")

    packet_path = detect_content_packet(project_root)
    packet = load_json(packet_path)
    asset_brief = build_asset_brief(project_root, packet)

    assets_dir = project_root / "assets" / "note"
    asset_brief_path = assets_dir / "note-asset-brief.json"
    prompt_doc_path = assets_dir / "image-prompts.md"
    write_json(asset_brief_path, asset_brief)
    write_text(prompt_doc_path, build_prompt_doc(project_root, packet, asset_brief))

    updated_packet = update_note_packet(packet, asset_brief)
    write_json(packet_path, updated_packet)

    print(
        json.dumps(
            {
                "asset_brief": str(asset_brief_path),
                "prompt_doc": str(prompt_doc_path),
                "content_packet": str(packet_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
