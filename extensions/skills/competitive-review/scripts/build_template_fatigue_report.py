#!/usr/bin/env python3
"""Build a deterministic template-fatigue report from creative fingerprints.

替代过去"模型自报 similarity_score"的做法：本脚本抽取当期指纹，
与 _registry/creative-fingerprints.json 里最近 N 期做确定性相似度计算，
算出真实 similarity_score / dimension_overlap / violations。

硬门禁：
- similarity_score >= --block-score (默认 4) -> status=block，退出码 2
- 任一核心维度 overlap >= --core-overlap-threshold (默认 0.6) -> status=block，退出码 2
- 命中 creative-divergence-brief.json forbidden_repeats -> 计入 violations，触发 block

--register 时把当期指纹写回指纹库（默认仅评估，不污染历史）。
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from creative_fingerprint_lib import (
    CORE_DIMENSIONS,
    compare_fingerprints,
    composite_to_score,
    default_media_ops_root,
    extract_fingerprint,
    keyword_set,
    load_json,
    text_overlap,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", help="Media package root directory.")
    parser.add_argument("--content-id", help="Content package id under the media-ops root.")
    parser.add_argument("--media-ops-root", help="Root containing media packages. Defaults to repo data/media-ops.")
    parser.add_argument("--window", type=int, default=5, help="How many recent episodes to compare against.")
    parser.add_argument("--block-score", type=int, default=4, help="similarity_score >= this blocks.")
    parser.add_argument("--core-overlap-threshold", type=float, default=0.6, help="Per core dimension overlap that blocks.")
    parser.add_argument("--secondary-overlap-threshold", type=float, default=0.5, help="Per secondary dimension overlap that triggers revise.")
    parser.add_argument("--output", default="review/template-fatigue-report.json", help="Report output relative to project root.")
    parser.add_argument("--register", action="store_true", help="Append current fingerprint to the registry after evaluating.")
    args = parser.parse_args()
    if not args.project_root and not args.content_id:
        parser.error("one of --project-root or --content-id is required")
    return args


def resolve_project_root(args: argparse.Namespace) -> Path:
    if args.project_root:
        return Path(args.project_root).resolve()
    media_root = Path(args.media_ops_root).resolve() if args.media_ops_root else default_media_ops_root()
    return (media_root / args.content_id).resolve()


def fingerprint_registry_path(media_ops_root: Path) -> Path:
    return media_ops_root / "_registry" / "creative-fingerprints.json"


def load_registry(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload.get("fingerprints"), list):
        payload = {"schema_version": "1.0", "fingerprints": []}
    return payload


def recent_priors(registry: dict[str, Any], current_id: str, window: int) -> list[dict[str, Any]]:
    """取最近 window 期（不含当前），按出现顺序，排除自身。"""
    items = [fp for fp in registry.get("fingerprints", []) if isinstance(fp, dict) and fp.get("content_id") != current_id]
    return items[-window:]


def check_forbidden_repeats(
    current_fp: dict[str, Any],
    forbidden_repeats: list[str],
    threshold: float = 0.45,
) -> list[dict[str, Any]]:
    """forbidden_repeats 是脚本/模型声明的禁用打法；逐条比当期各维度文本，命中即违规。"""
    violations: list[dict[str, Any]] = []
    dim_texts = list((current_fp.get("dimensions") or {}).values())
    dim_texts += [current_fp.get("core_angle", ""), current_fp.get("mother_theme", "")]
    for rule in forbidden_repeats:
        rule = str(rule or "").strip()
        if not rule:
            continue
        best = max((text_overlap(rule, t) for t in dim_texts), default=0.0)
        # 关键词命中兜底：禁用规则的关键词大量出现在当期文本里。
        rule_kw = keyword_set(rule)
        cur_kw = set().union(*(keyword_set(t) for t in dim_texts)) if dim_texts else set()
        kw_hit = len(rule_kw & cur_kw) / len(rule_kw) if rule_kw else 0.0
        score = max(best, kw_hit)
        if score >= threshold:
            violations.append({"rule": rule, "overlap": round(score, 4)})
    return violations


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)
    media_ops_root = (
        Path(args.media_ops_root).resolve() if args.media_ops_root else default_media_ops_root()
    )
    content_id = args.content_id or project_root.name

    angle_brief = load_json(project_root / "angles" / "angle-brief.json")
    divergence_brief = load_json(project_root / "planning" / "creative-divergence-brief.json")
    topic_selection = load_json(project_root / "planning" / "topic-selection.json")

    current_fp = extract_fingerprint(content_id, angle_brief, divergence_brief, topic_selection)

    registry_path = fingerprint_registry_path(media_ops_root)
    registry = load_registry(registry_path)
    priors = recent_priors(registry, content_id, args.window)

    comparisons = [compare_fingerprints(current_fp, prior) for prior in priors]
    max_comp = max((c["composite_overlap"] for c in comparisons), default=0.0)
    similarity_score = composite_to_score(max_comp)

    # 逐核心维度跨所有 prior 取最大 overlap。
    core_overlaps = {
        dim: round(max((c["dimension_overlap"].get(dim, 0.0) for c in comparisons), default=0.0), 4)
        for dim in CORE_DIMENSIONS
    }
    core_breach = [dim for dim, val in core_overlaps.items() if val >= args.core_overlap_threshold]

    # 二级维度（用户任务/互动话术）雷同是审美疲劳的直接来源：不阻塞，但触发 revise。
    secondary_dims = ("user_task", "interaction_trigger")
    secondary_overlaps = {
        dim: round(max((c["dimension_overlap"].get(dim, 0.0) for c in comparisons), default=0.0), 4)
        for dim in secondary_dims
    }
    secondary_breach = [dim for dim, val in secondary_overlaps.items() if val >= args.secondary_overlap_threshold]

    forbidden = [str(x) for x in divergence_brief.get("forbidden_repeats", []) if str(x).strip()]
    violations = check_forbidden_repeats(current_fp, forbidden)

    blocked = bool(similarity_score >= args.block_score or core_breach or violations)
    if blocked:
        status = "block"
    elif secondary_breach or similarity_score == args.block_score - 1:
        status = "revise"
    else:
        status = "pass"

    block_reasons: list[str] = []
    if similarity_score >= args.block_score:
        block_reasons.append(f"similarity_score={similarity_score} >= {args.block_score}")
    for dim in core_breach:
        block_reasons.append(f"core dimension '{dim}' overlap={core_overlaps[dim]} >= {args.core_overlap_threshold}")
    for v in violations:
        block_reasons.append(f"forbidden_repeat hit: {v['rule']} (overlap={v['overlap']})")
    revise_reasons: list[str] = []
    for dim in secondary_breach:
        revise_reasons.append(f"secondary dimension '{dim}' overlap={secondary_overlaps[dim]} >= {args.secondary_overlap_threshold}")
    if similarity_score == args.block_score - 1:
        revise_reasons.append(f"similarity_score={similarity_score} 接近阻塞线，建议加大差异")

    report = {
        "content_id": content_id,
        "review_role": "competitive-reviewer",
        "method": "deterministic-fingerprint-jaccard",
        "status": status,
        "similarity_score": similarity_score,
        "max_composite_overlap": round(max_comp, 4),
        "core_dimension_overlap": core_overlaps,
        "secondary_dimension_overlap": secondary_overlaps,
        "recent_reference_window": [c["prior_content_id"] for c in comparisons],
        "per_prior_comparison": comparisons,
        "forbidden_repeat_violations": violations,
        "block_reasons": block_reasons,
        "revise_reasons": revise_reasons,
        "decision": "template_fatigue_block" if blocked else ("template_fatigue_revise" if status == "revise" else "no_template_fatigue_block"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    output_path = (project_root / args.output).resolve()
    write_json(output_path, report)

    if args.register:
        current_fp["registered_at"] = report["generated_at"]
        registry["fingerprints"] = [
            fp for fp in registry.get("fingerprints", []) if fp.get("content_id") != content_id
        ]
        registry["fingerprints"].append(current_fp)
        write_json(registry_path, registry)

    print(
        '{{"output": "{0}", "status": "{1}", "similarity_score": {2}, "max_overlap": {3}}}'.format(
            output_path, status, similarity_score, round(max_comp, 4)
        )
    )
    if status == "block":
        return 2
    if status == "revise":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
