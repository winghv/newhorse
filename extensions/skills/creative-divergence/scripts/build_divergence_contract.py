#!/usr/bin/env python3
"""Build a creative-divergence contract by rotating away recently-used devices.

把"反同质化"从模型自觉变成脚本硬机制：
1. 读 _registry/creative-fingerprints.json 算出最近 N 期已用的叙事装置/视觉语法/证据类型/开场原型
2. 读 _strategy/rotation-pools.json，强制排除已用项，给出本期"可选池"和"推荐项"
3. 产出 planning/creative-divergence-brief.json：forbidden_repeats 由脚本算出，不再靠模型填
4. --commit 时把推荐项回写 rotation-pools.json 的 last_used_episode

模型只能在脚本框定的"剩余自由区"内发挥，从根上避免换词复用。
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# 复用 competitive-review 的指纹库（单一真源，不复制逻辑）。
_COMPETITIVE_SCRIPTS = (
    Path(__file__).resolve().parents[2] / "competitive-review" / "scripts"
)
sys.path.insert(0, str(_COMPETITIVE_SCRIPTS))

from creative_fingerprint_lib import (  # noqa: E402
    default_media_ops_root,
    load_json,
    text_overlap,
    write_json,
)

# rotation-pools.json 里的池 -> divergence_dimensions 维度名映射。
POOL_TO_DIMENSION = {
    "narrative_devices": "narrative_device",
    "visual_grammars": "visual_language",
    "evidence_types": "evidence_type",
    "opening_archetypes": "opening",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", help="Media package root directory.")
    parser.add_argument("--content-id", help="Content package id under the media-ops root.")
    parser.add_argument("--media-ops-root", help="Root containing media packages. Defaults to repo data/media-ops.")
    parser.add_argument("--window", type=int, default=5, help="Recent episodes to treat as exhausted.")
    parser.add_argument("--output", default="planning/creative-divergence-brief.json", help="Output relative to project root.")
    parser.add_argument("--commit", action="store_true", help="Write recommended picks back to rotation-pools last_used_episode.")
    args = parser.parse_args()
    if not args.project_root and not args.content_id:
        parser.error("one of --project-root or --content-id is required")
    return args


def resolve_project_root(args: argparse.Namespace) -> Path:
    if args.project_root:
        return Path(args.project_root).resolve()
    media_root = Path(args.media_ops_root).resolve() if args.media_ops_root else default_media_ops_root()
    return (media_root / args.content_id).resolve()


def recent_used_texts(registry: dict[str, Any], current_id: str, window: int) -> dict[str, list[str]]:
    """从最近 N 期指纹收集每个维度已用过的文本，用于匹配池里的已用项。"""
    priors = [
        fp for fp in registry.get("fingerprints", [])
        if isinstance(fp, dict) and fp.get("content_id") != current_id
    ][-window:]
    used: dict[str, list[str]] = {dim: [] for dim in set(POOL_TO_DIMENSION.values())}
    recent_ids = [fp.get("content_id", "") for fp in priors]
    for fp in priors:
        dims = fp.get("dimensions") or {}
        for dim in used:
            text = str(dims.get(dim) or "").strip()
            if text:
                used[dim].append(text)
    return {"by_dimension": used, "recent_ids": recent_ids}


def pick_pool_items(
    pool: list[dict[str, Any]],
    dimension: str,
    used_texts: list[str],
    recent_ids: list[str],
) -> dict[str, Any]:
    """从一个池里区分 available / exhausted，并给出推荐项。

    判定已用：last_used_episode 落在最近窗口内，或该项摘要与近期已用文本高度重叠。
    """
    available: list[dict[str, Any]] = []
    exhausted: list[dict[str, Any]] = []
    for item in pool:
        if not isinstance(item, dict):
            continue
        last_used = str(item.get("last_used_episode") or "")
        summary = str(item.get("summary") or item.get("name") or "")
        recently_flagged = last_used in recent_ids and last_used != ""
        overlap_hit = any(text_overlap(summary, t) >= 0.5 for t in used_texts)
        entry = {"id": item.get("id"), "name": item.get("name"), "last_used_episode": last_used}
        if recently_flagged or overlap_hit:
            entry["exhausted_reason"] = "recent_last_used" if recently_flagged else "summary_overlap"
            exhausted.append(entry)
        else:
            available.append(entry)
    # 推荐：优先从未用过(last_used 为空)的项里取第一个。
    never_used = [e for e in available if not e["last_used_episode"]]
    recommended = (never_used or available or [None])[0]
    return {
        "dimension": dimension,
        "available": available,
        "exhausted": exhausted,
        "recommended": recommended,
    }


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)
    media_ops_root = (
        Path(args.media_ops_root).resolve() if args.media_ops_root else default_media_ops_root()
    )
    content_id = args.content_id or project_root.name

    pools_path = media_ops_root / "_strategy" / "rotation-pools.json"
    pools = load_json(pools_path)
    if not pools.get("narrative_devices"):
        # 运行时副本缺失：从 skill 种子初始化（种子入库，运行时副本随产物目录）。
        seed_path = Path(__file__).resolve().parents[1] / "assets" / "rotation-pools.seed.json"
        pools = load_json(seed_path)
        if pools.get("narrative_devices"):
            write_json(pools_path, pools)
    registry = load_json(media_ops_root / "_registry" / "creative-fingerprints.json")

    used = recent_used_texts(registry, content_id, args.window)
    recent_ids = used["recent_ids"]

    rotation_plan: dict[str, Any] = {}
    forbidden_repeats: list[str] = []
    recommended_ids: dict[str, str] = {}
    for pool_key, dim in POOL_TO_DIMENSION.items():
        pool = [p for p in pools.get(pool_key, []) if isinstance(p, dict)]
        picked = pick_pool_items(pool, dim, used["by_dimension"].get(dim, []), recent_ids)
        rotation_plan[pool_key] = picked
        for ex in picked["exhausted"]:
            forbidden_repeats.append(
                f"不要复用最近 {args.window} 期已用的{POOL_LABELS.get(pool_key, pool_key)}：{ex['name']}"
            )
        if picked["recommended"]:
            recommended_ids[pool_key] = picked["recommended"]["id"]

    brief = {
        "content_id": content_id,
        "status": "pass",
        "method": "rotation-pool-contract",
        "series_name": pools.get("series_name", ""),
        "rotation_window": args.window,
        "recent_reference_window": recent_ids,
        "rotation_plan": rotation_plan,
        "forbidden_repeats": forbidden_repeats,
        "recommended_picks": recommended_ids,
        "freedom_note": "以上为脚本算出的硬性差异约束；模型须在 available 池内选择装置/语法/证据/开场，并在 divergence_dimensions 中具体落地。",
        "divergence_dimensions": {
            "user_task": "",
            "evidence_type": "",
            "narrative_device": "",
            "visual_language": "",
            "interaction_trigger": "",
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    output_path = (project_root / args.output).resolve()
    write_json(output_path, brief)

    if args.commit and recommended_ids:
        for pool_key, rec_id in recommended_ids.items():
            for item in pools.get(pool_key, []):
                if isinstance(item, dict) and item.get("id") == rec_id:
                    item["last_used_episode"] = content_id
        write_json(pools_path, pools)

    print(
        '{{"output": "{0}", "forbidden_count": {1}, "recommended": {2}}}'.format(
            output_path, len(forbidden_repeats), len(recommended_ids)
        )
    )
    return 0


POOL_LABELS = {
    "narrative_devices": "叙事装置",
    "visual_grammars": "视觉语法",
    "evidence_types": "证据类型",
    "opening_archetypes": "开场原型",
}


if __name__ == "__main__":
    raise SystemExit(main())
