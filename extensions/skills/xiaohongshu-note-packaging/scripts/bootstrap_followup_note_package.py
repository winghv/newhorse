#!/usr/bin/env python3
"""Bootstrap a Xiaohongshu followup note package from a published package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


CLUSTER_PRESETS: dict[str, dict[str, Any]] = {
    "template_request": {
        "topic": "把这3道门禁做成发布前检查清单",
        "objective": "把上一条的“3道门禁”进一步做成可直接照抄的发布前检查清单，承接模板索取需求。",
        "core_angle": "用户不是缺道理，而是缺一份能在发布前逐项核对的清单。",
        "hook_hypotheses": [
            "这3道门禁，过完再点发布",
            "给内容团队的发布前检查清单",
            "别急着发，先把这3道门禁过一遍",
        ],
        "comment_prompt": "如果你们团队最常漏的是其中一道，留个 1 / 2 / 3，我按票数先拆。",
        "cta": "先过清单，再点发布。",
        "title_variants": [
            "这3道门禁，过完再点发布",
            "给内容团队的3道发布前检查清单",
            "别急着发，先把这3道门禁过一遍",
        ],
        "cover_title": "发布前3道门禁检查清单",
        "cover_visual_direction": "白底黑字清单风，左侧编号 1/2/3，右侧用红色标出“别急着发”。",
        "page_plan": [
            {
                "page": 1,
                "role": "hook",
                "headline": "发布前，先过这3道门禁",
                "supporting_text": "少一道，都可能把低质量内容直接放出去。",
                "visual_direction": "大标题 + 3 个编号标签",
                "evidence": "承接上一条“3道门禁”主题",
                "handoff_note": "封面要先给清单感，而不是抽象概念。",
            },
            {
                "page": 2,
                "role": "checklist-item",
                "headline": "门禁 1：竞争审校",
                "supporting_text": "先回答：开头留不留人、证据硬不硬、平台表达原不原生。",
                "visual_direction": "三行勾选框",
                "evidence": "对应上一条里提到的竞争审校",
                "handoff_note": "把 3 个判断项做成可勾选格式。",
            },
            {
                "page": 3,
                "role": "checklist-item",
                "headline": "门禁 2：review gate",
                "supporting_text": "事实边界、表达风险、缺失项不过线，就先停。",
                "visual_direction": "风险警示卡样式",
                "evidence": "对应 review gate 的通过条件",
                "handoff_note": "强调“停”的动作感。",
            },
            {
                "page": 4,
                "role": "checklist-item",
                "headline": "门禁 3：dry-run publish",
                "supporting_text": "素材路径、标题、正文、标签、账号映射先跑一遍，再决定要不要 live。",
                "visual_direction": "流程图或勾选清单",
                "evidence": "对应 dry-run 发布检查",
                "handoff_note": "别把 dry-run 写成技术术语，要让运营看得懂。",
            },
            {
                "page": 5,
                "role": "operator-tip",
                "headline": "最容易漏的不是门禁，而是“没人负责踩刹车”",
                "supporting_text": "每次发布前要明确谁来做最终否决，而不是默认一路绿灯。",
                "visual_direction": "一句话结论 + 小字说明",
                "evidence": "承接上一条评论可能出现的团队场景",
                "handoff_note": "这一页要让团队管理者愿意收藏。",
            },
            {
                "page": 6,
                "role": "cta",
                "headline": "你们团队最常漏哪一道？",
                "supporting_text": "留言 1 / 2 / 3，我按票数继续拆具体模板。",
                "visual_direction": "大号数字互动页",
                "evidence": "用于触发评论聚类",
                "handoff_note": "评论触发要非常直接。",
            },
        ],
        "caption": "上一条讲的是为什么发布前要装刹车。\n\n这一条我把那 3 道门禁直接整理成发布前检查清单：\n\n1. 竞争审校\n先看这条内容有没有竞争力，不是能发就行。\n\n2. review gate\n事实边界、表达风险、缺失项不过线，就不要硬发。\n\n3. dry-run publish\n素材路径、标题、正文、标签、账号映射先跑一遍，再决定要不要 live。\n\n很多团队的问题不是不会写，而是发布前没有一个明确的“谁来踩刹车”。\n\n如果你也是团队协作发内容，这条建议直接收藏，发之前照着过一遍。",
        "first_comment": "你们团队最常漏的是哪一道？留个 1 / 2 / 3，我按票数继续拆下一条模板版。",
        "tag_suggestions": ["AI工作流", "自动化发布", "内容运营", "小红书运营", "发布SOP"],
        "save_trigger": "这条就是拿来发布前逐项核对的。",
        "comment_trigger": "你们团队最常漏哪一道门禁？",
        "follow_trigger": "后续会继续拆每一道门禁的执行模板。",
        "keywords": ["发布前检查", "review gate", "内容审核", "自动化发布", "运营SOP"],
    },
    "workflow_confession": {
        "topic": "为什么团队总在发布前少一道门禁",
        "objective": "把用户的团队失误场景做成 follow-up，强化“缺的是踩刹车机制”这个判断。",
        "core_angle": "很多团队的问题不是不会做内容，而是默认没人负责在发布前喊停。",
        "hook_hypotheses": [
            "团队翻车，常常是因为少了一个踩刹车的人",
            "发布前最危险的不是忙，而是默认一路绿灯",
            "很多团队漏的不是流程，是最后一道否决",
        ],
        "comment_prompt": "如果你们团队也有这种情况，留言说说最常漏哪一步。",
        "cta": "先把踩刹车的人定出来。",
        "title_variants": [
            "很多团队，发布前都少一个“踩刹车的人”",
            "内容翻车，常常不是因为写不好",
            "发布前最危险的是默认一路绿灯",
        ],
        "cover_title": "少的不是流程，是踩刹车的人",
        "cover_visual_direction": "对比型封面，左侧一路绿灯，右侧红色刹车按钮。",
        "page_plan": [],
        "caption": "",
        "first_comment": "",
        "tag_suggestions": ["内容运营", "团队协作", "AI工作流", "小红书运营", "流程管理"],
        "save_trigger": "把团队里谁负责最后喊停这件事明确下来。",
        "comment_trigger": "你们团队最常在哪一步默认一路绿灯？",
        "follow_trigger": "后续继续拆“谁来踩刹车”的执行方法。",
        "keywords": ["团队协作", "内容流程", "风控", "发布门禁"],
    },
    "skeptical_pushback": {
        "topic": "多一道门禁，不等于流程更慢",
        "objective": "回应“门禁会拖慢效率”的质疑，强调风控与效率可以同时成立。",
        "core_angle": "前面多一道门禁，往往比发出去再返工更省时间。",
        "hook_hypotheses": [
            "多一道门禁，不等于流程更慢",
            "先挡错发，反而更快",
            "别把风控和效率当对立面",
        ],
        "comment_prompt": "如果你也被说过“流程太重”，留言我看看你们卡在哪一步。",
        "cta": "先挡错发，再谈提效。",
        "title_variants": [
            "多一道门禁，不等于流程更慢",
            "先挡错发，反而更快",
            "别把风控和效率当对立面",
        ],
        "cover_title": "门禁不是拖慢，是先挡错发",
        "cover_visual_direction": "效率 vs 风控对比图，去掉对立感。",
        "page_plan": [],
        "caption": "",
        "first_comment": "",
        "tag_suggestions": ["内容运营", "自动化发布", "AI工作流", "效率提升", "风控"],
        "save_trigger": "适合给团队里只看效率的人看。",
        "comment_trigger": "你们最常被质疑“流程太重”的是哪一步？",
        "follow_trigger": "后续继续拆效率与风控如何共存。",
        "keywords": ["风控", "效率", "内容流程", "发布门禁"],
    },
}


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
    raise FileNotFoundError(f"Missing content packet under: {content_dir}")


def choose_cluster(comment_insights: dict[str, Any], explicit_cluster: str | None) -> str:
    if explicit_cluster:
        return explicit_cluster
    for item in comment_insights.get("priority_clusters", []):
        cluster = item.get("cluster")
        if isinstance(cluster, str) and cluster in CLUSTER_PRESETS:
            return cluster
    return "template_request"


def build_output_content_id(source_project_root: Path, cluster: str, explicit_id: str | None) -> str:
    if explicit_id:
        return explicit_id
    return f"{source_project_root.name}-followup-{cluster.replace('_', '-')}"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_template() -> dict[str, Any]:
    template_path = Path(__file__).resolve().parents[1] / "assets" / "xiaohongshu-note-package.template.json"
    return load_json(template_path)


def build_research_brief(
    *,
    source_project_root: Path,
    source_publish_result: dict[str, Any],
    source_content_packet: dict[str, Any],
    next_experiment_brief: dict[str, Any],
    cluster: str,
    preset: dict[str, Any],
) -> str:
    lines = [
        "# Research Brief",
        "",
        f"- `source_content_id`: `{source_project_root.name}`",
        f"- `source_title`: `{source_publish_result.get('metadata', {}).get('title') or source_content_packet.get('title') or source_project_root.name}`",
        f"- `source_publish_status`: `{source_publish_result.get('status', 'unknown')}`",
        f"- `focus_cluster`: `{cluster}`",
        "",
        "## Why This Follow-up",
        "",
        f"- 上一条发布后的下一轮目标是：{next_experiment_brief.get('objective') or preset['objective']}",
        f"- 当前优先分支：{preset['topic']}",
        f"- 选择依据：{next_experiment_brief.get('primary_branching_rule') or '按高优先级互动诉求继续拆下一条。'}",
        "",
        "## Content Direction",
        "",
        f"- `objective`: {preset['objective']}",
        f"- `core_angle`: {preset['core_angle']}",
        f"- `comment_prompt`: {preset['comment_prompt']}",
        "",
        "## Constraints",
        "",
        "- 这条 follow-up 需要比上一条更可保存、更可直接照抄。",
        "- 如果没有专门的清单/结构化视觉稿，不进入真实发布。",
        "- 评论触发必须非常具体，便于继续做系列拆解。",
        "",
    ]
    return "\n".join(lines) + "\n"


def build_topic_selection(
    *,
    cluster: str,
    preset: dict[str, Any],
    next_experiment_brief: dict[str, Any],
) -> dict[str, Any]:
    return {
        "platform": "xiaohongshu",
        "objective": next_experiment_brief.get("objective") or preset["objective"],
        "source_experiment_id": next_experiment_brief.get("experiment_id"),
        "topic_backlog": [
            {
                "topic": preset["topic"],
                "cluster": cluster,
                "business_value": 5,
                "platform_fit": 5,
                "timeliness": 4,
                "whitespace_opportunity": 4,
                "proof_handle": 4,
                "production_cost": 2,
                "risk": 2,
                "priority_score": 28,
                "why_now": "承接已发布内容的下一步互动和收藏诉求。",
            }
        ],
        "selected_topic": {
            "topic": preset["topic"],
            "cluster": cluster,
            "reason_to_choose": [
                "承接上一条已发布内容的系列语境。",
                "更具体，更容易形成收藏和评论。",
                "可以继续为下一条系列内容提供互动素材。",
            ],
            "next_action": "进入 note packaging，并补专门的视觉稿或清单卡样式。",
        },
    }


def build_angle_brief(
    *,
    cluster: str,
    preset: dict[str, Any],
    source_project_root: Path,
) -> dict[str, Any]:
    return {
        "objective": preset["objective"],
        "audience": [
            "内容运营团队",
            "在做 AI 工作流的创作者",
            "需要发布前检查机制的账号操盘手",
        ],
        "platforms": ["xiaohongshu"],
        "core_angle": preset["core_angle"],
        "hook_hypotheses": preset["hook_hypotheses"],
        "proof_plan": [
            "把抽象门禁变成可执行项。",
            "让用户能直接照着检查，而不是只听概念。",
            "通过评论问题继续获取下一条选题信号。",
        ],
        "comment_prompt": preset["comment_prompt"],
        "cta": preset["cta"],
        "focus_cluster": cluster,
        "source_content_id": source_project_root.name,
        "kill_reasons": [
            "如果封面和标题不是同一个承诺，这条会很快被划走。",
            "如果页序不能让用户直接拿去用，收藏价值不够。",
        ],
        "next_action": "完成图文发布包并补清单型视觉稿。",
    }


def build_note_packet(
    *,
    cluster: str,
    preset: dict[str, Any],
    source_project_root: Path,
) -> dict[str, Any]:
    packet = load_template()
    packet.update(
        {
            "platform": "xiaohongshu",
            "format": "note",
            "deliverable_type": "note",
            "source_content_id": source_project_root.name,
            "focus_cluster": cluster,
            "title_variants": preset["title_variants"],
            "cover_title": preset["cover_title"],
            "cover_visual_direction": preset["cover_visual_direction"],
            "page_plan": preset["page_plan"],
            "caption": preset["caption"],
            "first_comment": preset["first_comment"],
            "tag_suggestions": preset["tag_suggestions"],
            "save_trigger": preset["save_trigger"],
            "comment_trigger": preset["comment_trigger"],
            "follow_trigger": preset["follow_trigger"],
            "publish_metadata": {
                "series_name": "发布门禁系列",
                "keywords": preset["keywords"],
                "scheduled_window": "",
                "companion_video": False,
            },
        }
    )
    return packet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", help="Published source package root directory.")
    parser.add_argument("--content-id", help="Published source content id under media-ops root.")
    parser.add_argument("--media-ops-root", help="Root directory containing media packages.")
    parser.add_argument("--focus-cluster", choices=sorted(CLUSTER_PRESETS.keys()), default=None, help="Override followup cluster.")
    parser.add_argument("--output-content-id", default=None, help="Content id for the generated followup package.")
    args = parser.parse_args()
    if not args.project_root and not args.content_id:
        parser.error("one of --project-root or --content-id is required")
    return args


def main() -> int:
    args = parse_args()
    source_project_root = resolve_project_root(args)
    if not source_project_root.exists():
        raise FileNotFoundError(f"Project root does not exist: {source_project_root}")

    source_publish_result = load_json(source_project_root / "publish" / "publish-result-auto.json")
    if source_publish_result.get("mode") != "live" or source_publish_result.get("status") not in {"submitted", "success"}:
        raise SystemExit("Followup note package bootstrap requires a live-published source package.")

    next_experiment_brief = load_json(source_project_root / "retros" / "next-experiment-brief.json")
    comment_insights = load_json(source_project_root / "retros" / "comment-insights.json")
    source_content_packet = load_json(detect_content_packet(source_project_root))

    cluster = choose_cluster(comment_insights, args.focus_cluster)
    preset = CLUSTER_PRESETS[cluster]
    output_content_id = build_output_content_id(source_project_root, cluster, args.output_content_id)
    target_root = source_project_root.parent / output_content_id
    if target_root.exists():
        raise FileExistsError(f"Target package already exists: {target_root}")

    (target_root / "research").mkdir(parents=True, exist_ok=True)
    (target_root / "planning").mkdir(parents=True, exist_ok=True)
    (target_root / "angles").mkdir(parents=True, exist_ok=True)
    (target_root / "content").mkdir(parents=True, exist_ok=True)

    (target_root / "research" / "research-brief.md").write_text(
        build_research_brief(
            source_project_root=source_project_root,
            source_publish_result=source_publish_result,
            source_content_packet=source_content_packet,
            next_experiment_brief=next_experiment_brief,
            cluster=cluster,
            preset=preset,
        ),
        encoding="utf-8",
    )
    write_json(
        target_root / "planning" / "topic-selection.json",
        build_topic_selection(cluster=cluster, preset=preset, next_experiment_brief=next_experiment_brief),
    )
    write_json(
        target_root / "angles" / "angle-brief.json",
        build_angle_brief(cluster=cluster, preset=preset, source_project_root=source_project_root),
    )
    write_json(
        target_root / "content" / "xiaohongshu-note.json",
        build_note_packet(cluster=cluster, preset=preset, source_project_root=source_project_root),
    )

    print(
        json.dumps(
            {
                "project_root": str(target_root),
                "content_id": output_content_id,
                "focus_cluster": cluster,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
