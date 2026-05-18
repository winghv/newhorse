#!/usr/bin/env python3
"""Build a project-level script polish packet from angle brief and reference patterns."""

from __future__ import annotations

import argparse
import json
import re
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
        "--reference-patterns",
        default="benchmarks/reference-script-patterns.json",
        help="Reference script pattern pack relative to the project root.",
    )
    parser.add_argument(
        "--output",
        default="content/script-polish-packet.json",
        help="Output path relative to the project root.",
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
    return str(path.resolve().relative_to(project_root.resolve()))


def first_nonempty_string(values: list[Any], default: str = "") -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return default


def derive_target_shape(platforms: list[str], deliverable_type: str) -> str:
    if "bilibili" in platforms and deliverable_type == "midlong-video":
        return "bilibili-cognition-midlong"
    if "bilibili" in platforms:
        return "bilibili-video"
    return "generic-script"


def resolve_duration_target(angle_brief: dict[str, Any], content_packet: dict[str, Any]) -> str:
    return first_nonempty_string(
        [
            angle_brief.get("duration_target"),
            content_packet.get("duration_target"),
        ],
        default="08:00-12:00",
    )


def infer_episode_completion_mode(angle_brief: dict[str, Any], content_packet: dict[str, Any]) -> str:
    for payload in (angle_brief, content_packet):
        for key in ("episode_completion_mode", "completion_mode"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().lower()
        for key in ("is_multi_part", "multipart", "explicit_series_bridge"):
            value = payload.get(key)
            if isinstance(value, bool):
                return "multipart" if value else "standalone"
    return "standalone"


def parse_timestamp_seconds(value: str) -> int | None:
    parts = [part for part in value.strip().split(":") if part]
    if not parts or not all(part.isdigit() for part in parts):
        return None
    numbers = [int(part) for part in parts]
    if len(numbers) == 2:
        minutes, seconds = numbers
        return minutes * 60 + seconds
    if len(numbers) == 3:
        hours, minutes, seconds = numbers
        return hours * 3600 + minutes * 60 + seconds
    return None


def parse_duration_target(value: str) -> tuple[int, int]:
    cleaned = value.strip()
    if not cleaned:
        return (8 * 60, 12 * 60)
    matches = re.findall(r"\d{1,2}:\d{2}(?::\d{2})?", cleaned)
    if len(matches) >= 2:
        start_seconds = parse_timestamp_seconds(matches[0])
        end_seconds = parse_timestamp_seconds(matches[1])
        if start_seconds is not None and end_seconds is not None:
            return tuple(sorted((start_seconds, end_seconds)))
    if len(matches) == 1:
        seconds = parse_timestamp_seconds(matches[0])
        if seconds is not None:
            return (seconds, seconds)
    return (8 * 60, 12 * 60)


def format_seconds(seconds: int) -> str:
    minutes = max(seconds, 0) // 60
    remainder = max(seconds, 0) % 60
    return f"{minutes:02d}:{remainder:02d}"


def build_runtime_strategy(duration_target: str) -> dict[str, Any]:
    min_seconds, max_seconds = parse_duration_target(duration_target)
    target_seconds = round((min_seconds + max_seconds) / 2)
    target_minutes = round(target_seconds / 60, 1)
    min_chars = round(target_seconds / 60 * 230)
    max_chars = round(target_seconds / 60 * 280)
    is_extended = target_seconds >= 12 * 60
    return {
        "duration_target": duration_target,
        "min_seconds": min_seconds,
        "max_seconds": max_seconds,
        "target_seconds": target_seconds,
        "target_minutes": target_minutes,
        "pacing_tier": "extended_midform" if is_extended else "standard_midform",
        "chapter_density": "expanded_middle" if is_extended else "standard_middle",
        "estimated_voiceover_chars": {
            "min": min_chars,
            "max": max_chars,
        },
        "closing_seconds": 55 if is_extended else 45,
        "opening_seconds": 35 if is_extended else 30,
    }


def build_section_blueprint(
    lead_hook: str,
    proof_plan: list[str],
    comment_prompt: str,
    cta: str,
    runtime_strategy: dict[str, Any],
    episode_completion_mode: str,
) -> list[dict[str, Any]]:
    default_first_proof = proof_plan[0] if proof_plan else "给出第一层证明。"
    second_proof = proof_plan[1] if len(proof_plan) > 1 else "把现象压成更底层的机制。"
    case_proof = proof_plan[2] if len(proof_plan) > 2 else "至少加入一个具体案例或反例。"
    framework_proof = proof_plan[-1] if proof_plan else "给出清晰框架。"
    closing_seconds = int(runtime_strategy["closing_seconds"])
    target_seconds = int(runtime_strategy["target_seconds"])
    is_extended = runtime_strategy["pacing_tier"] == "extended_midform"
    closing_goal = (
        "让观众带着一个现实动作离开，并愿意进入下一条。"
        if episode_completion_mode == "multipart"
        else "让观众带着一个现实动作离开，并在这一条里获得完整收束。"
    )

    if is_extended:
        closing_start = max(target_seconds - closing_seconds, 0)
        middle_span = max(closing_start - 35, 1)
        symptom_end = 35 + round(middle_span * 0.17)
        mechanism_end = symptom_end + round(middle_span * 0.20)
        case_end = mechanism_end + round(middle_span * 0.29)
        false_progress_end = case_end + round(middle_span * 0.15)
        framework_start = min(false_progress_end, max(closing_start - round(middle_span * 0.19), case_end + 60))
        framework_start = min(framework_start, max(closing_start - 75, case_end + 45))
        return [
            {
                "section": "opening",
                "goal": "打破旧认知并建立继续看的收益。",
                "target_runtime": f"00:00-{format_seconds(35)}",
                "must_land": [lead_hook, default_first_proof],
            },
            {
                "section": "symptom_and_stakes",
                "goal": "先把高频症状和代价讲透，让观众确认这是自己的问题。",
                "target_runtime": f"{format_seconds(35)}-{format_seconds(symptom_end)}",
                "must_land": [
                    default_first_proof,
                    "要明确点出：问题不是懒，也不是不努力，而是现实轨迹没有跟着输入一起移动。",
                ],
            },
            {
                "section": "mechanism_setup",
                "goal": "把表面现象压成机制，并拆出错觉是怎么形成的。",
                "target_runtime": f"{format_seconds(symptom_end)}-{format_seconds(mechanism_end)}",
                "must_land": [
                    second_proof,
                    "至少拆出两层错觉来源，例如理解感、掌控感、身份感。",
                ],
            },
            {
                "section": "case_and_contrast",
                "goal": "用案例、对照或反例把机制讲厚。",
                "target_runtime": f"{format_seconds(mechanism_end)}-{format_seconds(case_end)}",
                "must_land": [
                    case_proof,
                    "至少加入一个双对照：输入越来越多的人，与被现实验证的人。",
                ],
            },
            {
                "section": "false_progress_breakdown",
                "goal": "继续扩写中段，拆掉最容易自我安慰的伪进步动作。",
                "target_runtime": f"{format_seconds(case_end)}-{format_seconds(framework_start)}",
                "must_land": [
                    "拆开收藏、记笔记、问 AI、买课程为什么都容易制造成长错觉。",
                    "加入一个反例、自我辩护或现实阻力，避免中段变成单向说教。",
                ],
            },
            {
                "section": "framework_delivery",
                "goal": "交付可执行的判断框架或行动步骤。",
                "target_runtime": f"{format_seconds(framework_start)}-{format_seconds(closing_start)}",
                "must_land": [
                    framework_proof,
                    "框架至少跑一遍真实示例，避免只报四个词。",
                ],
            },
            {
                "section": "closing_bridge",
                "goal": closing_goal,
                "target_runtime": f"{format_seconds(closing_start)}-{format_seconds(target_seconds)}",
                "must_land": [comment_prompt, cta],
            },
        ]

    return [
        {
            "section": "opening",
            "goal": "打破旧认知并建立继续看的收益。",
            "target_runtime": "00:00-00:30",
            "must_land": [lead_hook, default_first_proof],
        },
        {
            "section": "mechanism_setup",
            "goal": "把现象压成一个更底层的机制问题。",
            "target_runtime": "00:30-02:00",
            "must_land": proof_plan[:2] or ["解释问题为什么不是表面现象。"],
        },
        {
            "section": "case_and_contrast",
            "goal": "用案例、对照或反例把机制讲厚。",
            "target_runtime": "02:00-06:00",
            "must_land": ["至少加入一个双对照、反例或场景推演。"],
        },
        {
            "section": "framework_delivery",
            "goal": "交付可执行的判断框架或行动步骤。",
            "target_runtime": "06:00-09:30",
            "must_land": [framework_proof],
        },
        {
            "section": "closing_bridge",
            "goal": closing_goal,
            "target_runtime": "last_45s",
            "must_land": [comment_prompt, cta],
        },
    ]


def build_audience_psychology_contract() -> dict[str, Any]:
    return {
        "primary_audience_needs": [
            "获取新知识和可迁移的认知框架，而不只是被指出问题。",
            "得到情绪托底，确认这不是单纯的个人道德缺陷或意志力失败。",
            "缓解焦虑，感觉自己被理解，而不是被高高在上地审判。",
        ],
        "tone_rules": [
            "诊断可以锋利，但不要把观众写成愚蠢、懒惰或活该被困住。",
            "每指出一种误区，尽量补一层机制解释或情绪安抚，告诉观众为什么很多人都会这样。",
            "结论要像带观众一起看清系统，而不是站在对面教训观众。",
        ],
        "macro_micro_balance": [
            "至少给一层更宏观的时代/系统解释，例如平台、课程、AI 或现代知识环境如何放大问题。",
            "至少给一层贴身的生活细节或情绪场景，让观众觉得这就是自己的日常处境。",
        ],
        "knowledge_enrichment_moves": [
            "优先补心理学、行为科学、经济学或传播学里的解释框架，而不是空泛感慨。",
            "理论、实验、历史例子或社会观察要服务于推进理解，不要堆砌名词。",
        ],
    }


def build_borrowed_plays(reference_patterns: dict[str, Any]) -> list[dict[str, Any]]:
    apply_map = {
        "question_or_counterintuition": "开场先用反直觉问题切开误区，再在 15-30 秒内补第一层证明。",
        "hard_contrast_reframe": "把常见认知改写成“你以为…其实…”的对撞句，而不是直接解释概念。",
        "framework_tease": "在开头提前承诺后面会交付清晰框架，但不要把框架提前讲完。",
        "case_or_analogy_lede": "抽象机制难讲时，优先用案例、类比或实验把概念落地。",
    }
    cards = reference_patterns.get("reference_cards") or []
    by_device: dict[str, list[str]] = {}
    for card in cards:
        if not isinstance(card, dict):
            continue
        for label in card.get("opening_devices") or []:
            by_device.setdefault(label, []).append(card.get("video_id"))

    borrowed_plays: list[dict[str, Any]] = []
    for row in reference_patterns.get("dominant_opening_devices") or []:
        label = row.get("label")
        if not isinstance(label, str):
            continue
        borrowed_plays.append(
            {
                "play": label,
                "why_it_works": row.get("description"),
                "borrow_from": [item for item in by_device.get(label, []) if item][:3],
                "apply_as": apply_map.get(label, "只借打法，不照抄句式。"),
            }
        )
    return borrowed_plays[:4]


def build_material_research_contract(material_brief: dict[str, Any], material_brief_path: Path, project_root: Path) -> dict[str, Any]:
    exists = material_brief_path.exists()
    handles = material_brief.get("visual_material_handles") if isinstance(material_brief.get("visual_material_handles"), list) else []
    candidates = material_brief.get("candidate_video_seeds") if isinstance(material_brief.get("candidate_video_seeds"), list) else []
    anti_template = material_brief.get("anti_template_findings") if isinstance(material_brief.get("anti_template_findings"), list) else []
    material_status = str(material_brief.get("status") or "").strip()
    return {
        "status": "pass" if exists and material_status == "pass" and handles and candidates else "revise",
        "source_path": relative_to_project(material_brief_path, project_root) if exists else None,
        "required_artifacts": ["research/material-search-brief.json"],
        "candidate_video_count": len(candidates),
        "visual_material_handles": handles,
        "anti_template_findings": anti_template,
        "gate": "脚本定稿前必须先完成同题视频 / 评论区 / 案例素材搜索，避免只沿用内部模板。",
    }


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)
    topic_selection = load_json(project_root / "planning" / "topic-selection.json")
    angle_brief = load_json(project_root / "angles" / "angle-brief.json")
    attention_structure = load_json(project_root / "angles" / "attention-structure-template.json")
    content_packet = load_json(project_root / "content" / "bilibili-midform-video.json")
    reference_patterns_path = (project_root / args.reference_patterns).resolve()
    reference_patterns = load_json(reference_patterns_path)
    material_brief_path = project_root / "research" / "material-search-brief.json"
    material_brief = load_json(material_brief_path)

    platforms = [item for item in angle_brief.get("platforms", []) if isinstance(item, str)]
    deliverable_type = str(angle_brief.get("deliverable_type") or content_packet.get("deliverable_type") or "")
    target_shape = derive_target_shape(platforms, deliverable_type)
    selected_topic = ""
    selected_topic_payload = topic_selection.get("selected_topic")
    if isinstance(selected_topic_payload, dict):
        selected_topic = str(selected_topic_payload.get("topic") or "")

    lead_hook = first_nonempty_string(
        [
            attention_structure.get("lead_hook"),
            *(angle_brief.get("hook_hypotheses") or []),
        ]
    )
    proof_plan = [item for item in angle_brief.get("proof_plan", []) if isinstance(item, str)]
    comment_prompt = first_nonempty_string([attention_structure.get("comment_trigger"), angle_brief.get("comment_prompt")])
    cta = first_nonempty_string([angle_brief.get("cta")], "给观众一个可执行的下一步。")
    duration_target = resolve_duration_target(angle_brief, content_packet)
    runtime_strategy = build_runtime_strategy(duration_target)
    episode_completion_mode = infer_episode_completion_mode(angle_brief, content_packet)

    output_path = (project_root / args.output).resolve()
    payload = {
        "content_id": project_root.name,
        "target_shape": target_shape,
        "selected_topic": selected_topic,
        "core_angle": angle_brief.get("core_angle"),
        "duration_target": duration_target,
        "runtime_strategy": runtime_strategy,
        "episode_completion_mode": episode_completion_mode,
        "audience_psychology_contract": build_audience_psychology_contract(),
        "source_paths": {
            "topic_selection": relative_to_project(project_root / "planning" / "topic-selection.json", project_root),
            "angle_brief": relative_to_project(project_root / "angles" / "angle-brief.json", project_root),
            "attention_structure_template": (
                relative_to_project(project_root / "angles" / "attention-structure-template.json", project_root)
                if (project_root / "angles" / "attention-structure-template.json").exists()
                else None
            ),
            "reference_script_patterns": relative_to_project(reference_patterns_path, project_root)
            if reference_patterns_path.exists()
            else None,
            "material_search_brief": relative_to_project(material_brief_path, project_root)
            if material_brief_path.exists()
            else None,
        },
        "material_research_contract": build_material_research_contract(material_brief, material_brief_path, project_root),
        "opening_contract": {
            "lead_hook": lead_hook,
            "first_thirty_seconds_goal": "前 30 秒必须完成：打破旧认知 + 给出第一层证据 + 说明继续看的收益。",
            "required_moves": [
                "先给代价感、误区或反直觉问题，不先铺背景。",
                "在 15-30 秒内交付第一层机制、数据、案例或对照。",
                "让观众知道这条视频后面会给什么框架或可执行结论。",
            ],
            "avoid": [
                "用一大段背景介绍换取信任。",
                "只给狠句，不给第一层证明。",
                "开头连续解释概念，直到 30 秒后才进入主问题。",
            ],
        },
        "hard_constraints": [
            "前 30 秒必须兑现 promise -> first proof，不允许只堆钩子。",
            "每个主要章节都要新增一种价值：机制、证据、反例、案例或可执行动作。",
            "方法论段必须可截图、可保存、可复述，不能只是态度表达。",
            (
                "结尾必须把观点落到一次现实验证或下一条桥接动作上。"
                if episode_completion_mode == "multipart"
                else "结尾必须把观点落到一次现实验证和完整收束上，不要默认把关键解释留到下一条。"
            ),
        ]
        + (
            [
                "12 分钟以上档位，中段至少出现两次新增价值扩写：一次机制拆深，一次案例/反例/对照展开。",
                "13 分钟档的框架段不能只报概念，必须至少跑一次真实示例映射。",
                "不要把问题写成观众的个人道德缺陷；要同时解释心理机制和时代环境为什么会把人推向这个误区。",
                "至少留出一处情绪托底，让观众感觉自己被理解，而不是被教训。",
            ]
            if runtime_strategy["pacing_tier"] == "extended_midform"
            else []
        ),
        "freedom_zones": [
            "中段论证顺序可以自由调整，允许先讲案例再抽机制，也允许先给机制再补案例。",
            "中段可以插入一个更长的反例、寓言或现实场景，不必被固定步骤切碎。",
            "金句句式、类比选择和案例密度可以由模型按题目张力自由发挥。",
            "长视频档可以把最强案例留给中后段，不必在 4 分钟前把所有牌出完。",
        ]
        + (
            ["13 分钟档允许单独开一段拆“伪进步动作”，用来承接更多现实细节和自我辩护。"]
            if runtime_strategy["pacing_tier"] == "extended_midform"
            else []
        ),
        "section_blueprint": build_section_blueprint(
            lead_hook=lead_hook,
            proof_plan=proof_plan,
            comment_prompt=comment_prompt,
            cta=cta,
            runtime_strategy=runtime_strategy,
            episode_completion_mode=episode_completion_mode,
        ),
        "borrowed_plays": build_borrowed_plays(reference_patterns),
        "rewrite_loop": [
            {
                "pass": "hook_tightening",
                "question": "第一句是不是已经足够反直觉、足够有代价感，而且不用背景才能成立？",
            },
            {
                "pass": "proof_frontload",
                "question": "前 30 秒的第一层证明是不是已经出现，而不是还在讲抽象判断？",
            },
            {
                "pass": "midsection_thickening",
                "question": "中段有没有新增案例、反例、机制或对照，还是只是换词重复？",
            },
            {
                "pass": "framework_screenshotability",
                "question": "方法论部分能不能被观众截图、保存、复述？",
            },
            {
                "pass": "ending_bridge",
                "question": (
                    "结尾有没有把‘听懂了’变成‘马上能做一次验证’，并且这一条本身已经完整收束？"
                    if episode_completion_mode != "multipart"
                    else "结尾有没有把‘听懂了’变成‘马上能做一次验证’？"
                ),
            },
        ],
        "delegation_contract": {
            "required_agent": "script-doctor",
            "operating_mode": "supervisor-led",
            "entrypoint": "delegate_brief_template",
            "main_agent_allowed_scope": [
                "整理参考稿件、angle brief 和 script-polish-packet 作为输入",
                "给 script-doctor 下达 stage brief",
                "审核 rewrite notes、修订脚本和是否满足 hard constraints",
                "只做术语、路径、manifest 等轻量修正",
            ],
            "main_agent_must_not": [
                "直接产出整篇中长视频母稿",
                "绕过 script-doctor 自己做大段改稿",
            ],
            "required_outputs": [
                "content/script-polish-packet.json",
                "content/voiceover-script.md 或等价母稿",
                "content/script-rewrite-notes.md 或等价修订说明",
            ],
        },
        "delegate_brief_template": (
            "agent=script-doctor\n"
            "stage=script development\n"
            "operating_mode=supervisor-led\n"
            f"objective=基于参考视频稿件，把当前选题打磨成目标约 {duration_target}、更厚、更有递进的 B 站中视频母稿\n"
            "inputs=planning/topic-selection.json, angles/angle-brief.json, angles/attention-structure-template.json, "
            "benchmarks/reference-script-patterns.json, 当前 voiceover-script 草稿（如果有）\n"
            "material_inputs=research/material-search-brief.json 中的 candidate_video_seeds、visual_material_handles、anti_template_findings\n"
            "constraints=保留 hard constraints；中段按 freedom zones 自由展开；不要把中段写成固定模版；默认单条完整收束，除非显式多集\n"
            "required_artifacts=content/script-polish-packet.json, 可选的 rewrite notes 或修订脚本\n"
            + (
                "acceptance_criteria=开头更狠、中段更厚、框架更可保存、结尾既完整收束又能推动现实动作"
                if episode_completion_mode != "multipart"
                else "acceptance_criteria=开头更狠、中段更厚、框架更可保存、结尾更能触发下一步"
            )
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(output_path, payload)
    print(
        json.dumps(
            {
                "output_path": relative_to_project(output_path, project_root),
                "target_shape": target_shape,
                "borrowed_play_count": len(payload["borrowed_plays"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
