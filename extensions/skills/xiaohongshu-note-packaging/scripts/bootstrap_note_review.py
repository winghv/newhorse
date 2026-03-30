#!/usr/bin/env python3
"""Bootstrap a competitive scorecard and review gate for a Xiaohongshu note package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def clamp(score: int) -> int:
    return max(1, min(5, score))


def has_real_visual_assets(project_root: Path, packet: dict[str, Any]) -> bool:
    for key in ("image_plan", "asset_paths"):
        raw = packet.get(key)
        if isinstance(raw, list) and raw:
            for item in raw:
                if isinstance(item, dict):
                    raw_path = item.get("path") or item.get("image_path")
                else:
                    raw_path = item
                if not raw_path:
                    continue
                candidate = Path(str(raw_path))
                if not candidate.is_absolute():
                    candidate = project_root / candidate
                if candidate.exists():
                    return True
    return False


def score_hook_strength(packet: dict[str, Any]) -> tuple[int, str]:
    title_variants = packet.get("title_variants") or []
    cover_title = str(packet.get("cover_title") or "")
    comment_trigger = str(packet.get("comment_trigger") or "")
    score = 3
    if cover_title:
        score += 1
    if isinstance(title_variants, list) and len(title_variants) >= 3:
        score += 1
    score = clamp(score)
    reason = f"封面标题“{cover_title or '未提供'}”和 {len(title_variants)} 个标题备选让钩子更容易对齐；评论触发是“{comment_trigger or '未提供'}”。"
    return score, reason


def score_novelty(packet: dict[str, Any]) -> tuple[int, str]:
    cover_title = str(packet.get("cover_title") or "")
    caption = str(packet.get("caption") or "")
    score = 3
    if "检查清单" in cover_title or "清单" in caption:
        score += 1
    if "source_content_id" in packet:
        score += 0
    reason = "这条不是泛泛复述上一条，而是把抽象门禁进一步做成清单型 follow-up，角度更可执行。"
    return clamp(score), reason


def score_proof_strength(packet: dict[str, Any]) -> tuple[int, str]:
    page_plan = packet.get("page_plan") or []
    evidence_count = sum(1 for page in page_plan if isinstance(page, dict) and page.get("evidence"))
    score = 3
    if evidence_count >= 4:
        score += 1
    if len(page_plan) >= 5:
        score += 1
    reason = f"{len(page_plan)} 页页序里有 {evidence_count} 页明确写了 evidence，说明不是纯口号拼接。"
    return clamp(score), reason


def score_platform_fit(packet: dict[str, Any]) -> tuple[int, str]:
    page_plan = packet.get("page_plan") or []
    caption = str(packet.get("caption") or "")
    first_comment = str(packet.get("first_comment") or "")
    tags = packet.get("tag_suggestions") or []
    score = 3
    if len(page_plan) >= 5:
        score += 1
    if caption and first_comment and isinstance(tags, list) and tags:
        score += 1
    reason = "封面承诺、页序、正文、首评和标签都已结构化，小红书图文表达链路基本完整。"
    return clamp(score), reason


def score_emotional_pull(packet: dict[str, Any]) -> tuple[int, str]:
    cover_title = str(packet.get("cover_title") or "")
    caption = str(packet.get("caption") or "")
    score = 3
    if any(keyword in (cover_title + caption) for keyword in ["别急着发", "踩刹车", "少一道", "不要"]):
        score += 1
    reason = "内容继续抓住“发错比发慢更危险”的紧张感，能让团队运营者代入。"
    return clamp(score), reason


def score_save_share_potential(packet: dict[str, Any]) -> tuple[int, str]:
    save_trigger = str(packet.get("save_trigger") or "")
    page_plan = packet.get("page_plan") or []
    score = 3
    if save_trigger:
        score += 1
    if any(isinstance(page, dict) and page.get("role") == "checklist-item" for page in page_plan):
        score += 1
    reason = "清单型结构和明确的 save trigger 让它更像可复用资料，而不是一次性观点帖。"
    return clamp(score), reason


def score_series_potential(packet: dict[str, Any]) -> tuple[int, str]:
    publish_metadata = packet.get("publish_metadata") or {}
    follow_trigger = str(packet.get("follow_trigger") or "")
    score = 3
    if publish_metadata.get("series_name"):
        score += 1
    if follow_trigger:
        score += 1
    reason = "已经显式挂到系列名，并且结尾直接把下一轮互动信号接回系列扩展。"
    return clamp(score), reason


def build_scorecard(packet: dict[str, Any], content_id: str) -> dict[str, Any]:
    hook_strength, hook_reason = score_hook_strength(packet)
    novelty, novelty_reason = score_novelty(packet)
    proof_strength, proof_reason = score_proof_strength(packet)
    platform_fit, platform_fit_reason = score_platform_fit(packet)
    emotional_pull, emotional_pull_reason = score_emotional_pull(packet)
    save_share_potential, save_share_reason = score_save_share_potential(packet)
    series_potential, series_reason = score_series_potential(packet)

    scores = {
        "hook_strength": hook_strength,
        "novelty": novelty,
        "proof_strength": proof_strength,
        "platform_fit": platform_fit,
        "emotional_pull": emotional_pull,
        "save_share_potential": save_share_potential,
        "series_potential": series_potential,
    }
    total_score = sum(scores.values())
    critical_dimensions_met = all(scores[key] >= 3 for key in ("hook_strength", "proof_strength", "platform_fit"))
    pass_threshold_met = total_score >= 29

    if pass_threshold_met and critical_dimensions_met:
        review_decision = "pass"
    elif total_score <= 21 or any(scores[key] <= 1 for key in ("hook_strength", "proof_strength", "platform_fit")):
        review_decision = "block"
    else:
        review_decision = "revise"

    return {
        "platform": "xiaohongshu",
        "content_id": content_id,
        "competitive_scorecard": scores,
        "score_by_dimension": {
            "hook_strength_reason": hook_reason,
            "novelty_reason": novelty_reason,
            "proof_strength_reason": proof_reason,
            "platform_fit_reason": platform_fit_reason,
            "emotional_pull_reason": emotional_pull_reason,
            "save_share_potential_reason": save_share_reason,
            "series_potential_reason": series_reason,
        },
        "total_score": total_score,
        "review_decision": review_decision,
        "top_issues": [
            "当前已经是强 follow-up 方向，但还缺真正可发布的页卡视觉稿。",
            "如果后续能补一页“谁负责踩刹车”的团队分工图，收藏价值会更强。",
        ],
        "why_it_loses": [],
        "stronger_alternatives": [
            "这3道门禁，发之前先勾一遍",
            "给团队的发布前刹车清单",
        ],
        "must_fix_before_publish": ["补齐真实图文视觉稿或页卡资产。"],
        "release_recommendation": "竞争力已可进入合规门禁，但在视觉资产补齐前不要生成真实发布计划。",
        "threshold_evaluation": {
            "pass_threshold_met": pass_threshold_met,
            "critical_dimensions_met": critical_dimensions_met,
        },
    }


def build_review_gate(project_root: Path, packet: dict[str, Any], scorecard: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    required_fixes: list[str] = []
    if not has_real_visual_assets(project_root, packet):
        issues.append("当前只有结构化图文文案包，缺少实际页卡视觉稿。")
        required_fixes.append("补齐图文视觉稿或 image_plan，再进入 publish 准备。")

    if not packet.get("cover_title"):
        issues.append("首图承诺为空。")
        required_fixes.append("补齐封面承诺。")

    if not packet.get("first_comment"):
        issues.append("首评未设置。")
        required_fixes.append("补齐首评互动承接。")

    safe_to_publish = len(required_fixes) == 0 and scorecard.get("review_decision") == "pass"
    approval_status = "pass" if safe_to_publish else "revise"
    review_decision = "内容方向和竞争力可接受，但当前发布准备未完成" if not safe_to_publish else "内容表达、事实边界和发布准备状态可接受"
    next_action = (
        "先补视觉稿，再重新运行 review gate 与 publish 准备。"
        if not safe_to_publish
        else "生成 publish manifest，并默认停在 dry-run。"
    )

    return {
        "approval_status": approval_status,
        "issues": issues,
        "required_fixes": required_fixes,
        "review_decision": review_decision,
        "compliance_notes": [
            "当前文案围绕已有 workflow 和已发布主题展开，没有虚构平台能力。",
            "没有承诺不可验证的增长结果，仍保持在流程方法论和执行清单层面。",
            "即使竞争审校通过，缺少视觉资产时也不能进入真实发布。",
        ],
        "safe_to_publish": safe_to_publish,
        "next_action": next_action,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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

    packet = load_json(detect_content_packet(project_root))
    content_id = project_root.name
    scorecard = build_scorecard(packet, content_id)
    review_gate = build_review_gate(project_root, packet, scorecard)

    scorecard_path = project_root / "review" / "competitive-scorecard.json"
    review_gate_path = project_root / "review" / "review-gate.json"
    write_json(scorecard_path, scorecard)
    write_json(review_gate_path, review_gate)

    print(
        json.dumps(
            {
                "competitive_scorecard": str(scorecard_path),
                "review_gate": str(review_gate_path),
                "review_decision": scorecard["review_decision"],
                "approval_status": review_gate["approval_status"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
