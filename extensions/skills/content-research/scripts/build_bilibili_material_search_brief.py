#!/usr/bin/env python3
"""Build a Bilibili material-search brief before script development."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", help="Media package root directory.")
    parser.add_argument("--content-id", help="Content package id under the media-ops root.")
    parser.add_argument(
        "--media-ops-root",
        help="Root directory containing media packages. Defaults to repo-local data/media-ops.",
    )
    parser.add_argument(
        "--seed-candidates",
        default="research/bilibili-material-seeds.json",
        help="Optional manually collected candidate seeds relative to project root.",
    )
    parser.add_argument(
        "--output",
        default="research/material-search-brief.json",
        help="Output path relative to project root.",
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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def relative_to_project(path: Path, project_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_root.resolve()))
    except ValueError:
        return str(path.resolve())


def first_nonempty_string(values: list[Any], default: str = "") -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return default


def extract_keywords(value: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]{2,}", value)
    stopwords = {"为什么", "一个", "这个", "不是", "什么", "平台", "越懂你"}
    keywords: list[str] = []
    for word in words:
        if word in stopwords or word in keywords:
            continue
        keywords.append(word)
    return keywords[:8]


def normalize_candidate(item: dict[str, Any], index: int) -> dict[str, Any]:
    title = str(item.get("title") or item.get("name") or "").strip()
    url = str(item.get("url") or item.get("source_url") or item.get("page_url") or "").strip()
    video_id = str(item.get("video_id") or item.get("bvid") or item.get("bv") or "").strip()
    if not video_id:
        match = re.search(r"(BV[0-9A-Za-z]+)", url)
        if match:
            video_id = match.group(1)
    return {
        "rank": index + 1,
        "title": title or f"candidate-{index + 1}",
        "video_id": video_id or None,
        "url": url or None,
        "uploader": item.get("uploader") or item.get("author"),
        "stats": item.get("stats") if isinstance(item.get("stats"), dict) else {},
        "why_collect": item.get("why_collect") or item.get("reason") or "同题材材料或叙事参考。",
        "recommended_followup": "用 reference-video-ingest 拉取 metadata / transcript，再进入 script-polishing。",
    }


def build_queries(topic: str, core_angle: str, proof_plan: list[str]) -> list[dict[str, str]]:
    keywords = extract_keywords(" ".join([topic, core_angle, *proof_plan]))
    base = topic or core_angle or "认知 成长 机制"
    query_texts = [
        f"site:bilibili.com {base}",
        f"bilibili {base} 案例 机制",
        f"bilibili {' '.join(keywords[:4])} 爆款",
        f"bilibili {' '.join(keywords[:4])} 评论区",
    ]
    return [
        {
            "query": query,
            "intent": intent,
            "preferred_tool": "bilibili-cli / yt-dlp metadata / web search",
        }
        for query, intent in zip(
            query_texts,
            [
                "找同题材候选视频，避免只凭内部模板写稿。",
                "找可视化案例和素材钩子。",
                "找平台原生表达和标题承诺方式。",
                "找观众真实措辞、反对意见和评论区问题。",
            ],
            strict=True,
        )
    ]


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)
    topic_selection = load_json(project_root / "planning" / "topic-selection.json")
    angle_brief = load_json(project_root / "angles" / "angle-brief.json")
    content_packet = load_json(project_root / "content" / "bilibili-midform-video.json")
    seed_path = (project_root / args.seed_candidates).resolve()
    seeds = load_json(seed_path)

    selected_topic_payload = topic_selection.get("selected_topic") if isinstance(topic_selection.get("selected_topic"), dict) else {}
    selected_topic = first_nonempty_string(
        [
            selected_topic_payload.get("topic") if isinstance(selected_topic_payload, dict) else None,
            content_packet.get("title"),
            angle_brief.get("core_angle"),
        ]
    )
    core_angle = str(angle_brief.get("core_angle") or "").strip()
    proof_plan = [item for item in angle_brief.get("proof_plan", []) if isinstance(item, str)]
    raw_candidates = seeds.get("candidates") if isinstance(seeds.get("candidates"), list) else []
    candidates = [normalize_candidate(item, index) for index, item in enumerate(raw_candidates) if isinstance(item, dict)]
    has_seed_candidates = bool(candidates)
    if not candidates:
        candidates = [
            {
                "rank": 1,
                "title": f"{selected_topic or core_angle} - 待搜索同题候选",
                "video_id": None,
                "url": None,
                "uploader": None,
                "stats": {},
                "why_collect": "先建立搜索任务，避免在无外部材料输入时直接产出同质化文稿。",
                "recommended_followup": "用 bilibili-cli、yt-dlp 或手动媒体搜索补 URL/BV 后运行 reference-video-ingest。",
            }
        ]

    visual_handles = [
        {
            "handle": "same-topic-screen-language",
            "use_for": "观察同题视频如何把抽象概念落到画面，不直接照搬构图。",
        },
        {
            "handle": "comment-objection-bank",
            "use_for": "从评论区提取反对意见、自我辩护和高共鸣措辞，给中段增厚。",
        },
        {
            "handle": "case-and-contrast-material",
            "use_for": "为 B-roll、截图、AI keyart prompt 提供具体场景，而不是继续用纯文字卡。",
        },
    ]
    if shutil.which("yt-dlp"):
        available_providers = ["yt-dlp"]
    else:
        available_providers = []
    if shutil.which("bilibili"):
        available_providers.append("bilibili-cli")

    payload = {
        "content_id": project_root.name,
        "platform": "bilibili",
        "selected_topic": selected_topic,
        "core_angle": core_angle,
        "queries": build_queries(selected_topic, core_angle, proof_plan),
        "candidate_video_seeds": candidates,
        "visual_material_handles": visual_handles,
        "anti_template_findings": [
            "脚本前必须至少带入同题视频、评论区问题或案例素材之一；没有材料时只能产出调研任务，不能直接定稿。",
            "只借开头承诺、证明节奏和素材类型，不复用固定三段式段落顺序。",
            "每个中段章节至少绑定一个外部材料 handle：候选视频、评论问题、案例、截图或可生成镜头 prompt。",
        ],
        "tooling": {
            "preferred_providers": ["bilibili-cli", "yt-dlp", "web/media search", "manual seed JSON"],
            "available_local_providers": available_providers,
            "manual_seed_path": relative_to_project(seed_path, project_root),
        },
        "followups": [
            "把候选 URL/BV 写入 research/bilibili-material-seeds.json 后重跑本脚本。",
            "对最强参考视频运行 reference-video-ingest，沉淀 transcript 和 metadata。",
            "把可视化素材线索同步给 scene-asset-plan 和 visual-prebake plan。",
        ],
        "status": "pass" if has_seed_candidates else "revise",
        "reasons": [] if has_seed_candidates else ["candidate_video_seeds_missing"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    output_path = (project_root / args.output).resolve()
    write_json(output_path, payload)
    print(json.dumps({"output_path": relative_to_project(output_path, project_root), "candidate_count": len(candidates)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
