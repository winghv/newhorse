#!/usr/bin/env python3
"""Bootstrap post-publish monitoring artifacts for a media package."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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


def detect_content_packet(project_root: Path) -> Path | None:
    content_dir = project_root / "content"
    if not content_dir.exists():
        return None
    prioritized = ["*video.json", "*note.json", "content-packet.json"]
    for pattern in prioritized:
        matches = sorted(path for path in content_dir.glob(pattern) if path.is_file())
        if matches:
            return matches[0]
    fallback = sorted(path for path in content_dir.glob("*.json") if path.is_file())
    return fallback[0] if fallback else None


def relative_to_root(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def iso_timestamp(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def measurement_windows(project_root: Path) -> list[str]:
    next_experiment = load_json(project_root / "retros" / "next-experiment-brief.json")
    raw_windows = next_experiment.get("measurement_windows")
    if isinstance(raw_windows, list):
        windows = [str(item) for item in raw_windows if item]
        if windows:
            return windows
    return ["T+2h", "T+24h", "T+48h"]


def build_performance_summary(
    *,
    project_root: Path,
    publish_result: dict[str, Any],
    publish_result_path: Path,
    content_packet: dict[str, Any],
    windows: list[str],
) -> str:
    metadata = publish_result.get("metadata", {})
    title = metadata.get("title") or content_packet.get("title") or project_root.name
    tags = metadata.get("tags") or content_packet.get("tags") or []
    windows_label = " / ".join(windows)
    published_at = iso_timestamp(publish_result_path)
    account_name = publish_result.get("account", {}).get("account_name") or "unknown"

    lines = [
        "# Performance Summary",
        "",
        "## Status",
        "",
        "这条内容已真实发布。",
        f"- `published_at`: `{published_at}`",
        f"- `platform`: `{publish_result.get('platform', 'unknown')}`",
        f"- `published_mode`: `{publish_result.get('mode', 'unknown')}`",
        f"- `publish_status`: `{publish_result.get('status', 'unknown')}`",
        f"- `account_name`: `{account_name}`",
        "",
        "## What Is Confirmed",
        "",
        f"- 《{title}》已真实发布，当前平台回执为 `{publish_result.get('status', 'unknown')}`",
        f"- 已进入监测窗口 `T+2h / T+24h / T+48h`" if windows == ["T+2h", "T+24h", "T+48h"] else f"- 已进入监测窗口 `{windows_label}`",
        "- 当前先记录平台已提交，不提前把表现判断写死。",
        "",
        "## What Needs Collection",
        "",
        "- 评论区高频追问与模板索取强度",
        "- 收藏、主页访问、关注转化是否一起改善",
        "- 用户到底对哪一道门禁最有感知",
        "",
        "## Current Hypotheses",
        "",
        "- 如果评论集中索取检查清单，说明“门禁模板化”优先级最高",
        "- 如果收藏明显强于评论，说明信息价值成立，但互动钩子还可以加强",
        "- 如果主页访问与关注转化同步提升，说明账号定位开始变清晰",
        "",
        "## Metadata Snapshot",
        "",
        f"- `title`: `{title}`",
        f"- `tags`: `{', '.join(tags) if tags else 'n/a'}`",
        "",
        "## Next Measurement Step",
        "",
        f"按 `{windows_label}` 回填真实数据，再决定下一条优先拆模板、review gate，还是 dry-run 检查项。",
        "",
    ]
    return "\n".join(lines)


def build_comment_insights(
    *,
    project_root: Path,
    publish_result: dict[str, Any],
    publish_result_path: Path,
    windows: list[str],
) -> dict[str, Any]:
    title = publish_result.get("metadata", {}).get("title") or project_root.name
    return {
        "source_content_id": project_root.name,
        "platform": publish_result.get("platform"),
        "status": "pending_collection",
        "published_at": iso_timestamp(publish_result_path),
        "title": title,
        "measurement_windows": [
            {
                "window": window,
                "status": "pending",
                "questions": [
                    "是否有人索取具体模板或清单？",
                    "高频追问集中在哪一道门禁？",
                    "是否出现可直接转成 follow-up 的真实场景？",
                ],
            }
            for window in windows
        ],
        "priority_clusters": [
            {
                "cluster": "template_request",
                "signal": "用户直接索取检查清单、模板或 SOP",
                "action": "优先整理成下一条可下载/可照抄内容",
            },
            {
                "cluster": "workflow_confession",
                "signal": "用户承认自己团队漏掉某一道门禁",
                "action": "抽取真实表述，沉淀成 follow-up 开头素材",
            },
            {
                "cluster": "skeptical_pushback",
                "signal": "用户质疑门禁是否拖慢效率",
                "action": "准备效率与风控并存的回应版本",
            },
        ],
        "reply_lanes": [
            {
                "lane": "template_request",
                "goal": "把泛泛点赞转成具体需求",
                "reply_style": "先确认场景，再追问对方最常漏掉哪一道门禁",
            },
            {
                "lane": "skepticism",
                "goal": "回应“流程太重”的质疑",
                "reply_style": "强调门禁的目的是先把不该发的内容挡住",
            },
        ],
        "comments": [],
    }


def build_profile_visit_signal(
    *,
    project_root: Path,
    publish_result: dict[str, Any],
    publish_result_path: Path,
    windows: list[str],
) -> dict[str, Any]:
    return {
        "source_content_id": project_root.name,
        "platform": publish_result.get("platform"),
        "status": "pending_collection",
        "published_at": iso_timestamp(publish_result_path),
        "measurement_windows": [
            {"window": window, "profile_visits": None, "visit_rate": None, "status": "pending"}
            for window in windows
        ],
        "interpretation_rules": [
            "如果主页访问增长但关注不涨，优先检查账号定位和主页承接。",
            "如果主页访问和关注一起涨，说明这条内容与账号定位一致。",
        ],
    }


def build_follow_conversion_readout(
    *,
    project_root: Path,
    publish_result: dict[str, Any],
    publish_result_path: Path,
    windows: list[str],
) -> dict[str, Any]:
    return {
        "source_content_id": project_root.name,
        "platform": publish_result.get("platform"),
        "status": "pending_collection",
        "published_at": iso_timestamp(publish_result_path),
        "measurement_windows": [
            {"window": window, "new_follows": None, "follow_conversion_rate": None, "status": "pending"}
            for window in windows
        ],
        "decision_rules": [
            "如果关注转化弱于收藏，下一条先加强账号关注理由。",
            "如果关注转化强于评论，说明主题成立但评论触发还不够具体。",
        ],
    }


def build_live_monitoring_checklist(
    *,
    project_root: Path,
    publish_result: dict[str, Any],
    windows: list[str],
) -> str:
    lines = [
        "# Live Monitoring Checklist",
        "",
        f"- `content_id`: `{project_root.name}`",
        f"- `platform`: `{publish_result.get('platform', 'unknown')}`",
        f"- `mode`: `{publish_result.get('mode', 'unknown')}`",
        f"- `status`: `{publish_result.get('status', 'unknown')}`",
        "",
        "## Immediate",
        "",
        "- 确认笔记已成功出现在账号内容列表。",
        "- 记录首批评论，尤其是索取模板、质疑效率和分享给团队的表述。",
        "- 如出现明显错别字或素材顺序异常，第一时间登记修复策略。",
        "",
        "## Measurement Windows",
        "",
    ]
    for window in windows:
        lines.extend(
            [
                f"### {window}",
                "",
                "- 回填评论量、收藏量、主页访问和新增关注。",
                "- 把评论区高频问题归类到 `comment-insights.json`。",
                "- 判断下一条优先做模板、案例还是门禁拆解。",
                "",
            ]
        )
    return "\n".join(lines)


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

    publish_result_path = find_latest(project_root / "publish", "publish-result*.json")
    if publish_result_path is None:
        raise FileNotFoundError("Missing publish result artifact.")
    publish_result = load_json(publish_result_path)
    if publish_result.get("mode") != "live" or publish_result.get("status") not in {"submitted", "success"}:
        raise SystemExit("Post-publish followup can only bootstrap from a successful live publish result.")

    content_packet = load_json(detect_content_packet(project_root))
    windows = measurement_windows(project_root)
    retros_dir = project_root / "retros"
    retros_dir.mkdir(parents=True, exist_ok=True)

    performance_summary_path = retros_dir / "performance-summary.md"
    comment_insights_path = retros_dir / "comment-insights.json"
    profile_visit_path = retros_dir / "profile-visit-signal.json"
    follow_conversion_path = retros_dir / "follow-conversion-readout.json"
    checklist_path = retros_dir / "live-monitoring-checklist.md"

    performance_summary_path.write_text(
        build_performance_summary(
            project_root=project_root,
            publish_result=publish_result,
            publish_result_path=publish_result_path,
            content_packet=content_packet,
            windows=windows,
        ),
        encoding="utf-8",
    )
    comment_insights_path.write_text(
        json.dumps(
            build_comment_insights(
                project_root=project_root,
                publish_result=publish_result,
                publish_result_path=publish_result_path,
                windows=windows,
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    profile_visit_path.write_text(
        json.dumps(
            build_profile_visit_signal(
                project_root=project_root,
                publish_result=publish_result,
                publish_result_path=publish_result_path,
                windows=windows,
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    follow_conversion_path.write_text(
        json.dumps(
            build_follow_conversion_readout(
                project_root=project_root,
                publish_result=publish_result,
                publish_result_path=publish_result_path,
                windows=windows,
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    checklist_path.write_text(
        build_live_monitoring_checklist(
            project_root=project_root,
            publish_result=publish_result,
            windows=windows,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "performance_summary": str(performance_summary_path),
                "comment_insights": str(comment_insights_path),
                "profile_visit_signal": str(profile_visit_path),
                "follow_conversion_readout": str(follow_conversion_path),
                "live_monitoring_checklist": str(checklist_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
