"""Tests for evidence-backed topic selection workflow."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_command(command: list[str], workdir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=workdir, check=True, capture_output=True, text=True)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_reference_library(root: Path) -> Path:
    library_root = root / "_reference-videos"
    samples = [
        {
            "video_id": "BV1A",
            "title": "为什么“少花钱”是最昂贵的习惯？",
            "transcript": [
                "如果你的答案是省钱就会变富,说明你已经被财富神话骗了",
                "这期视频会告诉你普通人为什么会把节省误当成积累",
                "看完你会拿到一个更接近现实的下注框架",
            ],
        },
        {
            "video_id": "BV1B",
            "title": "一万小时定律是这个时代最大的谎言",
            "transcript": [
                "看完这条视频,你会知道为什么努力学习不等于真正掌握",
                "先问你一个问题,你这些年的学习可能连学习都算不上",
                "今天我们给你一套可以立刻用的操作手册",
            ],
        },
    ]

    entries = []
    for sample in samples:
        transcript_path = library_root / "bilibili" / sample["video_id"] / "research" / "reference-transcript.md"
        transcript_text = "\n".join(
            [
                "# Reference Transcript",
                "",
                f"- title: {sample['title']}",
                "- source_url: https://www.bilibili.com/video/dummy",
                "",
                "## Transcript",
                *[f"- {line}" for line in sample["transcript"]],
            ]
        )
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        transcript_path.write_text(transcript_text + "\n", encoding="utf-8")
        entries.append(
            {
                "platform": "bilibili",
                "video_id": sample["video_id"],
                "title": sample["title"],
                "source_url": "https://www.bilibili.com/video/dummy",
                "root_path": f"bilibili/{sample['video_id']}",
                "transcript_status": "pass",
                "transcript_kind": "asr",
                "primary_transcript": f"bilibili/{sample['video_id']}/research/reference-transcript.md",
            }
        )

    write_json(
        library_root / "index.json",
        {
            "library": "reference-video-library",
            "platforms": ["bilibili"],
            "entries": entries,
        },
    )
    return library_root


def make_recent_package(project_root: Path, topic: str) -> None:
    planning_dir = project_root / "planning"
    planning_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        planning_dir / "topic-selection.json",
        {
            "selected_topic": {
                "topic": topic,
            }
        },
    )


def test_build_topic_backlog_prefers_concrete_fresh_topic(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = repo_root / "extensions" / "skills" / "topic-selection" / "scripts" / "build_topic_backlog.py"
    media_ops_root = tmp_path / "media-ops"
    reference_library_root = build_reference_library(tmp_path)

    project_root = media_ops_root / "2026-04-03-bilibili-learning-no-change-ep04"
    strategy_path = media_ops_root / "_strategy" / "bilibili-topic-pool-v2.json"
    make_recent_package(media_ops_root / "2026-03-28-bilibili-judgment-framework-ep02", "为什么你知道得越多，反而越难做决定")
    make_recent_package(media_ops_root / "2026-03-31-bilibili-platform-judgment-ep03", "平台越懂你，为什么你越难形成独立判断")

    write_json(
        strategy_path,
        {
            "date": "2026-04-03",
            "platform": "bilibili",
            "objective": "为判断力账号挑出下一条更有点击和完播潜力的中视频题目。",
            "account_thesis": "普通人总以为自己更清醒，其实只是更会解释自己。",
            "selection_context": {
                "series_name": "现实判断力",
                "mother_theme": "现代不确定性下的判断失真与自我欺骗",
                "recent_package_window": 3,
            },
            "candidates": [
                {
                    "topic": "普通人最该建立的，不是知识库，而是决策框架",
                    "series_lane": "方法论",
                    "core_conflict": "用户收藏了很多方法，但现实里还是不会判断。",
                    "proof_handle": "知识管理软件截图、框架图卡。",
                    "visual_handle": "知识库界面、流程图。",
                    "why_now": "账号之前已经讲过判断和框架。",
                    "lenses": ["AI", "成长"],
                    "production_cost": "low",
                },
                {
                    "topic": "为什么你学了很多东西，人生还是没变",
                    "series_lane": "自我改变错觉",
                    "core_conflict": "用户把输入当成成长，但现实结果几乎没有变化。",
                    "proof_handle": "课程收藏夹、稍后再看、笔记堆积、行动断层。",
                    "visual_handle": "收藏夹爆满、笔记软件、日历空白、现实场景对照。",
                    "why_now": "学习型内容消费极多，但真正变化极少，痛点广且可共鸣。",
                    "lenses": ["心理", "成长", "AI"],
                    "production_cost": "medium",
                },
                {
                    "topic": "AI 最危险的地方，不是替你做事，而是替你逃避判断",
                    "series_lane": "AI 判断外包",
                    "core_conflict": "用户以为在提效，实际上在把该自己承担的判断交出去。",
                    "proof_handle": "AI 对话、结果分歧、错误依赖案例。",
                    "visual_handle": "聊天界面、双答案对比、任务流。",
                    "why_now": "AI 使用频率高，相关讨论仍在增长。",
                    "lenses": ["AI", "心理"],
                    "production_cost": "medium",
                },
            ],
        },
    )

    run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
            "--strategy-file",
            str(strategy_path),
            "--reference-library-root",
            str(reference_library_root),
            "--media-ops-root",
            str(media_ops_root),
        ],
        repo_root,
    )

    output_path = project_root / "planning" / "topic-selection.json"
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["selected_topic"]["topic"] == "为什么你学了很多东西，人生还是没变"
    assert payload["reference_signals"]["strong_title_patterns"]
    assert any("抽象" in note for note in payload["reference_signals"]["weak_topic_patterns"])

    by_topic = {item["topic"]: item for item in payload["topic_backlog"]}
    assert by_topic["为什么你学了很多东西，人生还是没变"]["freshness_score"] > by_topic["普通人最该建立的，不是知识库，而是决策框架"]["freshness_score"]
    assert by_topic["为什么你学了很多东西，人生还是没变"]["proof_handle_score"] >= 4
    assert by_topic["普通人最该建立的，不是知识库，而是决策框架"]["repeat_risk"] >= 3


def test_build_topic_backlog_generates_selected_brief_from_current_winner(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = repo_root / "extensions" / "skills" / "topic-selection" / "scripts" / "build_topic_backlog.py"
    media_ops_root = tmp_path / "media-ops"
    reference_library_root = build_reference_library(tmp_path)

    project_root = media_ops_root / "2026-05-06-bilibili-reliable-trap-ep07"
    strategy_path = media_ops_root / "_strategy" / "bilibili-knowledge-channel-reset-v2.json"
    make_recent_package(media_ops_root / "2026-04-12-bilibili-sidehustle-cost-ep05", "被骗了很多年，副业最贵的成本从来不是学费")
    make_recent_package(media_ops_root / "2026-04-20-bilibili-decision-delay-ep06", "为什么你越想做对决定，越容易一直拖着不决定")

    write_json(
        strategy_path,
        {
            "date": "2026-05-06",
            "platform": "bilibili",
            "objective": "为知识频道挑出下一条最适合接在副业题之后的中视频。",
            "account_thesis": "我们用真实案例和反常识拆解，帮年轻人看懂社会规则、赚钱逻辑和决策误区。",
            "selection_context": {
                "series_name": "现实判断力",
                "mother_theme": "现代年轻人在职场、赚钱和自我决策中最常见的错觉、代价与破局动作。",
                "recent_package_window": 3,
            },
            "candidates": [
                {
                    "topic": "靠谱陷阱：越能扛事的人，越容易被当成理所当然",
                    "series_lane": "社会规则",
                    "core_conflict": "很多人以为能力够强、态度够稳，迟早会被组织看见；现实里，越稳定兜底的人，越容易被默认继续兜底。",
                    "proof_handle": "临时救火、默认补位、年终评价反差、可见贡献与真实贡献错位。",
                    "visual_handle": "工作群消息、任务堆积、汇报前后对照、评价指标表。",
                    "why_now": "它能承接赚钱题之后的频道辨识度建设。",
                    "lenses": ["career", "social_rules", "decision"],
                    "production_cost": "medium",
                },
                {
                    "topic": "普通人最容易亏掉的，不是钱，而是一次出手的勇气",
                    "series_lane": "决策误区",
                    "core_conflict": "很多人表面在规避风险，实际上是在把所有成长机会都交给确定性幻觉。",
                    "proof_handle": "错过转岗、错过项目窗口、观望太久后的机会成本。",
                    "visual_handle": "收益曲线、空仓等待、时间线对照。",
                    "why_now": "适合后续补强决策误区主线。",
                    "lenses": ["money", "decision", "career"],
                    "production_cost": "high",
                },
            ],
        },
    )

    run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
            "--strategy-file",
            str(strategy_path),
            "--reference-library-root",
            str(reference_library_root),
            "--media-ops-root",
            str(media_ops_root),
        ],
        repo_root,
    )

    payload = json.loads((project_root / "planning" / "topic-selection.json").read_text(encoding="utf-8"))
    selected_topic = payload["selected_topic"]

    assert selected_topic["topic"] in {
        "靠谱陷阱：越能扛事的人，越容易被当成理所当然",
        "普通人最容易亏掉的，不是钱，而是一次出手的勇气",
    }
    assert "输入堆积" not in selected_topic["next_action"]
    if selected_topic["topic"] == "靠谱陷阱：越能扛事的人，越容易被当成理所当然":
        assert "临时救火" in "".join(selected_topic["reason_to_choose"])
        assert any("兜底" in item for item in selected_topic["risks_to_watch"])
        assert "可见贡献" in selected_topic["next_action"]
    else:
        assert "观望太久" in "".join(selected_topic["reason_to_choose"])
        assert any("机会" in item or "确定性幻觉" in item for item in selected_topic["risks_to_watch"])
        assert "机会成本" in selected_topic["next_action"]
