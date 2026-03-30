#!/usr/bin/env python3
"""Bootstrap a manual comment-ops packet for a live media package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from bootstrap_post_publish_followup import (
    detect_content_packet,
    load_json,
    measurement_windows,
    resolve_project_root,
)


def title_anchor(title: str) -> str:
    if title:
        return title
    return "这条内容"


def build_manual_observation_log(
    *,
    project_root: Path,
    publish_result: dict[str, Any],
    comment_insights: dict[str, Any],
    windows: list[str],
) -> dict[str, Any]:
    return {
        "source_content_id": project_root.name,
        "platform": publish_result.get("platform"),
        "status": "pending_collection",
        "account_name": publish_result.get("account", {}).get("account_name"),
        "measurement_windows": [
            {
                "window": window,
                "status": "pending",
                "metrics": {
                    "likes": None,
                    "comments": None,
                    "saves": None,
                    "shares": None,
                    "profile_visits": None,
                    "new_follows": None,
                },
                "top_comments": [],
                "operator_notes": "",
                "decision_prompt": "这一窗口最值得继续追打的是模板需求、案例需求，还是反质疑？",
            }
            for window in windows
        ],
        "priority_clusters": comment_insights.get("priority_clusters", []),
        "reply_lanes": comment_insights.get("reply_lanes", []),
    }


def section_title(raw_cluster: str) -> str:
    mapping = {
        "template_request": "Template Request",
        "workflow_confession": "Workflow Confession",
        "skeptical_pushback": "Skeptical Pushback",
    }
    return mapping.get(raw_cluster, raw_cluster.replace("_", " ").title())


def build_reply_playbook(
    *,
    title: str,
    content_packet: dict[str, Any],
    comment_insights: dict[str, Any],
) -> str:
    anchor = title_anchor(title)
    tags = content_packet.get("tags") or []
    title_line = content_packet.get("title") or title
    clusters = comment_insights.get("priority_clusters") or []

    lines = [
        "# Comment Reply Playbook",
        "",
        f"- `content_id`: `{comment_insights.get('source_content_id')}`",
        f"- `title_anchor`: `{anchor}`",
        f"- `tags`: `{', '.join(tags) if tags else 'n/a'}`",
        "",
        "## Guardrails",
        "",
        "- 先接具体场景，再给模板，不要一上来就营销。",
        "- 如果对方质疑流程太重，先承认效率顾虑，再解释门禁的目标是先挡错发。",
        "- 回复里尽量复用用户原话，给人被认真接住的感觉。",
        "",
        "## Ready Replies",
        "",
    ]

    for cluster in clusters:
        cluster_id = str(cluster.get("cluster") or "")
        lines.extend(
            [
                f"### {section_title(cluster_id)}",
                "",
                f"- `signal`: {cluster.get('signal') or 'n/a'}",
                f"- `action`: {cluster.get('action') or 'n/a'}",
                "",
            ]
        )
        if cluster_id == "template_request":
            lines.extend(
                [
                    f"示例回复 1：你们团队现在最容易漏的是哪一道？如果是 {anchor} 里提到的 review gate，我下一条可以直接拆成清单版。",
                    f"示例回复 2：如果你是拿来给团队落地，不建议先追求全自动，先把 3道门禁 固化成可复用检查表更稳。",
                    "",
                ]
            )
        elif cluster_id == "workflow_confession":
            lines.extend(
                [
                    "示例回复 1：这种情况很典型，很多团队不是不会做内容，而是缺一层“谁来踩刹车”的机制。",
                    f"示例回复 2：如果你愿意，我下一条就把 {title_line or anchor} 里最容易被漏掉的那一道门禁单独拆开讲。",
                    "",
                ]
            )
        elif cluster_id == "skeptical_pushback":
            lines.extend(
                [
                    "示例回复 1：确实会多一步，但比起发出去再删，前面多一道门禁的成本通常更低。",
                    "示例回复 2：不是为了把流程做重，而是先明确什么情况下不该发，这样自动化才不会放大错误。",
                    "",
                ]
            )

    lines.extend(
        [
            "## Escalation Prompts",
            "",
            "- 如果连续出现模板索取，整理成下一条图文或可下载清单。",
            "- 如果大量评论质疑效率，准备一条“门禁不等于低效”的案例向 follow-up。",
            "- 如果出现具体团队场景，优先收集原话作为下一条开头。",
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

    retros_dir = project_root / "retros"
    publish_result = load_json(project_root / "publish" / "publish-result-auto.json")
    if publish_result.get("mode") != "live" or publish_result.get("status") not in {"submitted", "success"}:
        raise SystemExit("Comment ops packet requires a live publish result.")

    comment_insights_path = retros_dir / "comment-insights.json"
    if not comment_insights_path.exists():
        raise FileNotFoundError("Missing retros/comment-insights.json. Run bootstrap_post_publish_followup.py first.")

    comment_insights = load_json(comment_insights_path)
    content_packet = load_json(detect_content_packet(project_root))
    windows = measurement_windows(project_root)
    title = publish_result.get("metadata", {}).get("title") or content_packet.get("title") or project_root.name

    observation_log_path = retros_dir / "manual-observation-log.json"
    reply_playbook_path = retros_dir / "comment-reply-playbook.md"

    observation_log_path.write_text(
        json.dumps(
            build_manual_observation_log(
                project_root=project_root,
                publish_result=publish_result,
                comment_insights=comment_insights,
                windows=windows,
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    reply_playbook_path.write_text(
        build_reply_playbook(
            title=title,
            content_packet=content_packet,
            comment_insights=comment_insights,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "manual_observation_log": str(observation_log_path),
                "comment_reply_playbook": str(reply_playbook_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
