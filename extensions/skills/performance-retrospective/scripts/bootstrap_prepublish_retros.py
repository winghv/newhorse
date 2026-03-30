#!/usr/bin/env python3
"""Bootstrap retrospective planning artifacts for a package before live publish."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_WINDOWS = ["T+2h", "T+24h", "T+48h"]

CLUSTER_RULES: dict[str, dict[str, Any]] = {
    "template_request": {
        "objective": "验证这条清单版图文能否把模板索取诉求推进到明确的门禁拆解需求。",
        "branching_rule": "按评论区 `1 / 2 / 3` 的投票分布和模板索取强度，优先拆对应门禁。",
        "watch_items": [
            "评论区 `1 / 2 / 3` 的投票分布是否足够集中。",
            "是否有人继续索取可直接照抄的清单、模板或 SOP。",
        ],
        "primary_success": [
            "评论区出现具体门禁投票或模板索取，而不是泛泛好评。",
            "收藏与主页访问同时出现正向信号。",
        ],
        "secondary_success": [
            "用户愿意描述真实团队协作场景。",
            "出现可直接继续拆成下一条的追问。",
        ],
    },
    "workflow_confession": {
        "objective": "验证这条内容能否引出真实的团队失误场景，并把“谁来踩刹车”变成下一条系列入口。",
        "branching_rule": "按评论区最常出现的失误环节，优先拆对应的责任分工或否决动作。",
        "watch_items": [
            "是否有人承认团队常在发布前漏掉某一道门禁。",
            "是否出现“没人负责最终喊停”的真实表述。",
        ],
        "primary_success": [
            "评论区出现具体失误案例，而不是抽象认同。",
            "主页访问信号说明账号定位被进一步强化。",
        ],
        "secondary_success": [
            "收藏信号证明团队管理者愿意留作内部 SOP 参考。",
            "出现可直接引用的原话，用于后续案例化内容。",
        ],
    },
    "skeptical_pushback": {
        "objective": "验证这条内容能否把“门禁拖慢效率”的质疑转成对效率与风控兼容方案的需求。",
        "branching_rule": "按评论区质疑最集中的环节，优先拆对应的提效门禁模板。",
        "watch_items": [
            "是否出现“流程太重”“太慢”的直接反对意见。",
            "是否有人继续追问怎样在团队协作里压缩门禁成本。",
        ],
        "primary_success": [
            "评论区出现具体效率质疑或提效追问。",
            "收藏信号证明这条回应值得留作内部讨论素材。",
        ],
        "secondary_success": [
            "出现把内容转给团队成员的评论或反馈。",
            "主页访问能支撑后续继续做效率/风控系列。",
        ],
    },
    "default": {
        "objective": "验证这条内容是否能形成下一轮更具体的系列拆解方向。",
        "branching_rule": "按评论区最高频的具体追问决定下一条内容。",
        "watch_items": [
            "评论区是否出现可继续拆成下一条的具体问题。",
        ],
        "primary_success": [
            "出现明确的评论追问或收藏信号。",
        ],
        "secondary_success": [
            "主页访问或关注信号出现改善。",
        ],
    },
}


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def default_media_ops_root() -> Path:
    return Path(__file__).resolve().parents[4] / "data" / "media-ops"


def resolve_project_root(args: argparse.Namespace) -> Path:
    if args.project_root:
        return Path(args.project_root).resolve()
    media_ops_root = Path(args.media_ops_root).resolve() if args.media_ops_root else default_media_ops_root().resolve()
    return (media_ops_root / args.content_id).resolve()


def find_latest(directory: Path, pattern: str) -> Path | None:
    if not directory.exists():
        return None
    candidates = [path for path in directory.glob(pattern) if path.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def detect_content_packet(project_root: Path) -> Path:
    content_dir = project_root / "content"
    for pattern in ("*note.json", "*video.json", "content-packet.json", "*.json"):
        matches = sorted(path for path in content_dir.glob(pattern) if path.is_file())
        if matches:
            return matches[0]
    raise FileNotFoundError(f"Missing content packet under: {content_dir}")


def primary_packet(content_packet: dict[str, Any]) -> dict[str, Any]:
    nested = content_packet.get("content_packet")
    if isinstance(nested, dict):
        return nested
    return content_packet


def first_non_empty_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def first_non_empty_list(*values: Any) -> list[str]:
    for value in values:
        if isinstance(value, list):
            items = [str(item).strip() for item in value if str(item).strip()]
            if items:
                return items
    return []


def resolve_platform(packet: dict[str, Any], manifest: dict[str, Any], publish_result: dict[str, Any]) -> str:
    platforms = first_non_empty_list(packet.get("platforms"), manifest.get("platforms"))
    return first_non_empty_string(
        platforms[0] if platforms else None,
        packet.get("platform"),
        manifest.get("platform"),
        publish_result.get("platform"),
        "unknown",
    ) or "unknown"


def resolve_title(packet: dict[str, Any], manifest: dict[str, Any], publish_result: dict[str, Any], project_root: Path) -> str:
    metadata = manifest.get("metadata", {})
    result_metadata = publish_result.get("metadata", {})
    title_variants = packet.get("title_variants")
    if isinstance(title_variants, list) and title_variants:
        first_variant = title_variants[0]
    else:
        first_variant = None
    return (
        first_non_empty_string(
            metadata.get("title"),
            result_metadata.get("title"),
            packet.get("title"),
            first_variant,
            packet.get("cover_title"),
            project_root.name,
        )
        or project_root.name
    )


def resolve_asset_count(packet: dict[str, Any], manifest: dict[str, Any], publish_result: dict[str, Any]) -> int:
    raw_assets: list[str] = []

    asset_paths = manifest.get("asset_paths")
    if isinstance(asset_paths, list):
        raw_assets.extend(str(item) for item in asset_paths if item)

    image_plan = packet.get("image_plan")
    if isinstance(image_plan, list):
        for item in image_plan:
            if isinstance(item, dict):
                raw_path = item.get("path") or item.get("image_path")
                if raw_path:
                    raw_assets.append(str(raw_path))
            elif isinstance(item, str) and item:
                raw_assets.append(item)

    result_assets = publish_result.get("assets", {})
    if isinstance(result_assets, dict):
        images = result_assets.get("images")
        if isinstance(images, list):
            raw_assets.extend(str(item) for item in images if item)
        video = result_assets.get("video")
        if isinstance(video, str) and video:
            raw_assets.append(video)

    return len({item for item in raw_assets if item})


def source_content_id(packet: dict[str, Any], manifest: dict[str, Any]) -> str | None:
    metadata = packet.get("publish_metadata", {})
    return first_non_empty_string(
        packet.get("source_content_id"),
        metadata.get("source_content_id"),
        manifest.get("source_content_id"),
    )


def measurement_windows(project_root: Path, packet: dict[str, Any]) -> list[str]:
    existing = load_json(project_root / "retros" / "next-experiment-brief.json")
    windows = existing.get("measurement_windows")
    if isinstance(windows, list):
        values = [str(item) for item in windows if item]
        if values:
            return values

    parent_id = source_content_id(packet, {})
    if parent_id:
        source_brief = load_json(project_root.parent / parent_id / "retros" / "next-experiment-brief.json")
        source_windows = source_brief.get("measurement_windows")
        if isinstance(source_windows, list):
            values = [str(item) for item in source_windows if item]
            if values:
                return values
    return DEFAULT_WINDOWS


def cluster_rule(packet: dict[str, Any]) -> dict[str, Any]:
    cluster = first_non_empty_string(packet.get("focus_cluster"), "default") or "default"
    return CLUSTER_RULES.get(cluster, CLUSTER_RULES["default"])


def build_retro_plan(
    *,
    project_root: Path,
    packet: dict[str, Any],
    manifest: dict[str, Any],
    publish_result: dict[str, Any],
    windows: list[str],
) -> str:
    rule = cluster_rule(packet)
    platform = resolve_platform(packet, manifest, publish_result)
    title = resolve_title(packet, manifest, publish_result, project_root)
    approval_status = first_non_empty_string(load_json(project_root / "review" / "review-gate.json").get("approval_status"), "unknown")
    publish_decision = first_non_empty_string(manifest.get("decision"), "not_ready")
    follow_trigger = first_non_empty_string(packet.get("follow_trigger"))
    save_trigger = first_non_empty_string(packet.get("save_trigger"))
    comment_trigger = first_non_empty_string(packet.get("comment_trigger"))
    parent_id = source_content_id(packet, manifest)

    lines = [
        "# Retro Plan",
        "",
        "## Goal",
        "",
        rule["objective"],
        "",
        "## Current State",
        "",
        f"- `content_id`: `{project_root.name}`",
        f"- `platform`: `{platform}`",
        f"- `title`: `{title}`",
        f"- `approval_status`: `{approval_status}`",
        f"- `publish_decision`: `{publish_decision}`",
    ]
    if parent_id:
        lines.append(f"- `parent_content_id`: `{parent_id}`")

    lines.extend(
        [
            "",
            "## Measurement Windows",
            "",
        ]
    )
    lines.extend(f"- `{window}`" for window in windows)

    lines.extend(
        [
            "",
            "## What To Watch",
            "",
        ]
    )
    if save_trigger:
        lines.append(f"- 收藏信号是否真的验证“{save_trigger}”。")
    if comment_trigger:
        lines.append(f"- 评论区是否围绕“{comment_trigger}”产生具体反馈。")
    if follow_trigger:
        lines.append(f"- 主页访问与关注信号是否能支撑“{follow_trigger}”。")
    lines.extend(f"- {item}" for item in rule["watch_items"])

    lines.extend(
        [
            "",
            "## Decision Rules",
            "",
            f"- {rule['branching_rule']}",
            "- 如果收藏强于评论，继续强化可保存模板感，但要补更直接的互动钩子。",
            "- 如果评论强于收藏，下一条优先补结构化页序和更具体的保存理由。",
        ]
    )
    if follow_trigger:
        lines.append("- 如果主页访问强但关注弱，优先补账号定位和主页承接。")

    return "\n".join(lines) + "\n"


def build_performance_summary(
    *,
    project_root: Path,
    packet: dict[str, Any],
    manifest: dict[str, Any],
    publish_result: dict[str, Any],
    windows: list[str],
) -> str:
    rule = cluster_rule(packet)
    approval_status = load_json(project_root / "review" / "review-gate.json").get("approval_status") or "unknown"
    publish_decision = manifest.get("decision") or "not_ready"
    publish_mode = publish_result.get("mode") or manifest.get("publish_mode") or "not_started"
    publish_status = publish_result.get("status") or "not_started"
    account_name = first_non_empty_string(
        manifest.get("account_name"),
        publish_result.get("account", {}).get("account_name"),
        "unknown",
    ) or "unknown"
    asset_count = resolve_asset_count(packet, manifest, publish_result)
    title = resolve_title(packet, manifest, publish_result, project_root)
    windows_label = " / ".join(windows)

    lines = [
        "# Performance Summary",
        "",
        "## Status",
        "",
    ]
    if publish_mode == "dry_run" or publish_status == "not_executed":
        lines.append("当前仍处于 `dry-run` 阶段，尚未真实发布。")
    elif publish_decision == "ready_for_live_publish":
        lines.append("当前内容已进入 `ready_for_live_publish`，但仍停在人工 live 前。")
    else:
        lines.append("当前内容仍处于发布准备阶段，尚未进入真实发布。")

    lines.extend(
        [
            f"- `approval_status`: `{approval_status}`",
            f"- `publish_decision`: `{publish_decision}`",
            f"- `publish_mode`: `{publish_mode}`",
            f"- `publish_status`: `{publish_status}`",
            f"- `account_name`: `{account_name}`",
            "",
            "## Confirmed",
            "",
            f"- 《{title}》已经完成当前轮内容包、审核与发布素材准备。",
            f"- 当前可见素材数量为 `{asset_count}`，可以作为后续 live 前检查基线。",
            f"- 监测窗口默认按 `{windows_label}` 执行。",
            "",
            "## What Is Still Unproven",
            "",
            "- 真实收藏、评论、主页访问和关注信号还没有回填。",
            "- 目前还不知道用户最终会被哪一个具体门禁或场景打动。",
            "- 这条内容是否能继续拉动系列内容需求，仍需要发布后验证。",
            "",
            "## Provisional Hypotheses",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in rule["primary_success"])
    lines.extend(f"- {item}" for item in rule["secondary_success"])

    lines.extend(
        [
            "",
            "## Next Step",
            "",
        ]
    )
    if approval_status == "pass" and publish_decision == "ready_for_live_publish":
        lines.append(f"人工确认后再进入真实发布，并按 `{windows_label}` 回填真实数据。")
    else:
        lines.append(f"先完成剩余门禁或人工确认，再按 `{windows_label}` 作为发布后观测窗口。")

    return "\n".join(lines) + "\n"


def build_next_experiment_brief(
    *,
    project_root: Path,
    packet: dict[str, Any],
    manifest: dict[str, Any],
    windows: list[str],
) -> dict[str, Any]:
    rule = cluster_rule(packet)
    platform = resolve_platform(packet, manifest, {})
    parent_id = source_content_id(packet, manifest)
    focus_cluster = first_non_empty_string(packet.get("focus_cluster"))
    deliverable_type = first_non_empty_string(packet.get("deliverable_type"), packet.get("format"), "content")
    save_trigger = first_non_empty_string(packet.get("save_trigger"))
    comment_trigger = first_non_empty_string(packet.get("comment_trigger"))
    follow_trigger = first_non_empty_string(packet.get("follow_trigger"))

    primary_success = list(rule["primary_success"])
    secondary_success = list(rule["secondary_success"])
    if save_trigger:
        primary_success.insert(0, f"收藏信号能验证“{save_trigger}”。")
    if comment_trigger:
        primary_success.insert(1, f"评论区围绕“{comment_trigger}”产生具体反馈。")
    if follow_trigger:
        secondary_success.insert(0, f"主页访问或关注信号能支撑“{follow_trigger}”。")

    payload: dict[str, Any] = {
        "experiment_id": f"{project_root.name}-next",
        "source_content_id": project_root.name,
        "objective": rule["objective"],
        "platforms": [platform] if platform != "unknown" else [],
        "deliverable_type": deliverable_type,
        "primary_branching_rule": rule["branching_rule"],
        "measurement_windows": windows,
        "success_criteria": {
            "primary": primary_success,
            "secondary": secondary_success,
        },
        "next_action": f"真实发布后按 {' / '.join(windows)} 回填数据，再决定下一条拆哪一类模板或门禁。",
    }
    if parent_id:
        payload["parent_content_id"] = parent_id
    if focus_cluster:
        payload["focus_cluster"] = focus_cluster
    return payload


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

    content_packet = load_json(detect_content_packet(project_root))
    packet = primary_packet(content_packet)
    latest_manifest = load_json(find_latest(project_root / "publish", "publish-manifest*.json"))
    latest_result = load_json(find_latest(project_root / "publish", "publish-result*.json"))
    if latest_result.get("mode") == "live" and latest_result.get("status") in {"submitted", "success"}:
        raise SystemExit("Package is already live-published. Use bootstrap_post_publish_followup.py instead.")

    windows = measurement_windows(project_root, packet)
    retros_dir = project_root / "retros"
    retros_dir.mkdir(parents=True, exist_ok=True)

    retro_plan_path = retros_dir / "retro-plan.md"
    performance_summary_path = retros_dir / "performance-summary.md"
    next_experiment_path = retros_dir / "next-experiment-brief.json"

    retro_plan_path.write_text(
        build_retro_plan(
            project_root=project_root,
            packet=packet,
            manifest=latest_manifest,
            publish_result=latest_result,
            windows=windows,
        ),
        encoding="utf-8",
    )
    performance_summary_path.write_text(
        build_performance_summary(
            project_root=project_root,
            packet=packet,
            manifest=latest_manifest,
            publish_result=latest_result,
            windows=windows,
        ),
        encoding="utf-8",
    )
    write_json(
        next_experiment_path,
        build_next_experiment_brief(
            project_root=project_root,
            packet=packet,
            manifest=latest_manifest,
            windows=windows,
        ),
    )

    print(
        json.dumps(
            {
                "retro_plan": str(retro_plan_path),
                "performance_summary": str(performance_summary_path),
                "next_experiment_brief": str(next_experiment_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
