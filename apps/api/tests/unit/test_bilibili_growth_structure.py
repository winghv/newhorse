"""Tests for Bilibili growth structure workflow scripts."""

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


def make_bilibili_growth_package(project_root: Path) -> None:
    (project_root / "benchmarks").mkdir(parents=True, exist_ok=True)
    (project_root / "planning").mkdir(parents=True, exist_ok=True)
    (project_root / "angles").mkdir(parents=True, exist_ok=True)
    (project_root / "review").mkdir(parents=True, exist_ok=True)

    (project_root / "benchmarks" / "benchmark-deck.md").write_text(
        "\n".join(
            [
                "# Benchmark Deck",
                "",
                "## Reusable Patterns",
                "",
                "### 1. 痛点反转",
                "",
                "- `pattern`: 先指出大家常见做法错在哪里，再提出新方法",
                "- `why_it_works`: 用户会先代入自己的低效体验，再愿意继续看解决方案",
                "- `reusable_play`: 开头直接说“别再让 AI 替你拍板了”",
                "",
                "### 2. 结构化清单",
                "",
                "- `pattern`: 用 4-6 个步骤承载复杂信息",
                "- `why_it_works`: 观众更容易保存和回看有明确框架的中视频",
                "- `reusable_play`: 把抽象判断压成一张能截图的框架图",
                "",
                "### 3. 留评论钩子",
                "",
                "- `pattern`: 不用空泛 CTA，而是给一个具体的下一条承诺",
                "- `why_it_works`: 评论动作越具体，用户越容易顺手参与",
                "- `reusable_play`: 下一条我把停手信号模板拆开讲",
                "",
                "## Whitespace",
                "",
                "- 很多 AI 中视频只讲观点，不讲开场留存结构。",
                "- 很多内容有收藏点，但没有关注转化桥。",
                "",
                "## Anti-Patterns",
                "",
                "- 标题像功能说明书，没有冲突。",
                "- 讲了一堆概念，却没有明确下一步。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    write_json(
        project_root / "planning" / "topic-selection.json",
        {
            "objective": "做一条 B 站中视频，解释为什么越会用 AI 的人越容易决策瘫痪。",
            "platform": "bilibili",
            "selected_topic": {
                "topic": "为什么你知道得越多，反而越难做决定",
                "reason_to_choose": ["题面自带冲突和代入感。"],
            },
        },
    )

    write_json(
        project_root / "angles" / "angle-brief.json",
        {
            "platforms": ["bilibili"],
            "deliverable_type": "midlong-video",
            "core_angle": "你不是不知道，你是在不断延后拍板。",
            "hook_hypotheses": [
                "为什么越会用 AI 的人，越容易做不出决定？",
                "你不是在继续思考，你是在用 AI 延后拍板。",
            ],
            "proof_plan": [
                "先拆清楚信息题和权重题。",
                "再用相反答案案例证明继续比较不等于继续思考。",
                "最后给出四步判断框架。",
            ],
            "comment_prompt": "你最近一个什么决定，其实已经不是信息不够，而是你不肯拍板了？",
            "cta": "先把问题压回现实，再去做一次验证。",
            "backup_angles": [
                "从继续比较其实是在逃避承担切入。",
                "从 AI 更擅长信息题不擅长权重题切入。",
            ],
            "experiment_plan": "验证狠句开场 + 案例 + 框架是否能同时拉高点击、停留和收藏。",
        },
    )

    write_json(
        project_root / "review" / "competitive-scorecard.json",
        {
            "score_by_dimension": {
                "hook_strength": 5,
                "opening_hold_power": 4,
                "proof_strength": 4,
                "follow_conversion_power": 3,
            },
            "total_score": 38,
            "review_decision": "pass",
        },
    )

def test_build_bilibili_pattern_pack_extracts_growth_patterns(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "benchmark-analysis"
        / "scripts"
        / "build_bilibili_pattern_pack.py"
    )
    project_root = tmp_path / "media-ops" / "2026-03-31-bilibili-growth-pack"
    make_bilibili_growth_package(project_root)

    run_command([sys.executable, str(script_path), "--project-root", str(project_root)], repo_root)

    output_path = project_root / "benchmarks" / "bilibili-hook-patterns.json"
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["platform"] == "bilibili"
    assert payload["selected_topic"] == "为什么你知道得越多，反而越难做决定"
    assert payload["opening_patterns"][0]["label"] == "痛点反转"
    assert payload["opening_patterns"][0]["reusable_play"].startswith("开头直接说")
    assert payload["follow_conversion_patterns"][0]["trigger"].startswith("下一条")
    assert "很多内容有收藏点，但没有关注转化桥。" in payload["whitespace"]


def test_build_attention_structure_creates_opening_and_follow_hook_artifacts(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "angle-design"
        / "scripts"
        / "build_attention_structure.py"
    )
    project_root = tmp_path / "media-ops" / "2026-03-31-bilibili-growth-pack"
    make_bilibili_growth_package(project_root)

    run_command([sys.executable, str(script_path), "--project-root", str(project_root)], repo_root)

    structure_path = project_root / "angles" / "attention-structure-template.json"
    follow_hooks_path = project_root / "angles" / "follow-conversion-hooks.json"
    assert structure_path.exists()
    assert follow_hooks_path.exists()

    structure = json.loads(structure_path.read_text(encoding="utf-8"))
    follow_hooks = json.loads(follow_hooks_path.read_text(encoding="utf-8"))

    assert structure["lead_hook"] == "为什么越会用 AI 的人，越容易做不出决定？"
    assert structure["episode_completion_mode"] == "standalone"
    assert structure["opening_sequence"][0]["time_window"] == "0-3s"
    assert structure["opening_sequence"][0]["script_line"] == "为什么越会用 AI 的人，越容易做不出决定？"
    assert structure["proof_reveal_plan"][0]["proof_beat"] == "先拆清楚信息题和权重题。"
    assert structure["comment_trigger"] == "你最近一个什么决定，其实已经不是信息不够，而是你不肯拍板了？"

    assert follow_hooks["comment_prompt"] == structure["comment_trigger"]
    assert follow_hooks["follow_cta_variants"]
    assert follow_hooks["episode_completion_mode"] == "standalone"
    assert follow_hooks["series_bridge_variants"] == []
    assert all("下一条" not in item for item in follow_hooks["follow_cta_variants"])
    assert "交付可复用的交付" not in follow_hooks["save_trigger"]
    assert "从“" not in follow_hooks["follow_cta_variants"][0]
    assert "切入" not in follow_hooks["follow_cta_variants"][0]


def test_build_opening_scorecard_creates_growth_review_artifact(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    attention_script = (
        repo_root
        / "extensions"
        / "skills"
        / "angle-design"
        / "scripts"
        / "build_attention_structure.py"
    )
    review_script = (
        repo_root
        / "extensions"
        / "skills"
        / "competitive-review"
        / "scripts"
        / "build_opening_scorecard.py"
    )
    project_root = tmp_path / "media-ops" / "2026-03-31-bilibili-growth-pack"
    make_bilibili_growth_package(project_root)

    run_command([sys.executable, str(attention_script), "--project-root", str(project_root)], repo_root)
    run_command([sys.executable, str(review_script), "--project-root", str(project_root)], repo_root)

    scorecard_path = project_root / "review" / "opening-scorecard.json"
    assert scorecard_path.exists()

    payload = json.loads(scorecard_path.read_text(encoding="utf-8"))
    assert payload["opening_promise"] == "为什么越会用 AI 的人，越容易做不出决定？"
    assert payload["first_thirty_seconds"]["proof_reveal_present"] is True
    assert payload["decision"] == "pass"
    assert payload["score_by_dimension"]["opening_hold_power"] == 4
    assert payload["score_by_dimension"]["follow_conversion_power"] == 3


def test_build_opening_scorecard_can_infer_missing_growth_dimensions(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    attention_script = (
        repo_root
        / "extensions"
        / "skills"
        / "angle-design"
        / "scripts"
        / "build_attention_structure.py"
    )
    review_script = (
        repo_root
        / "extensions"
        / "skills"
        / "competitive-review"
        / "scripts"
        / "build_opening_scorecard.py"
    )
    project_root = tmp_path / "media-ops" / "2026-03-31-bilibili-growth-pack-inferred"
    make_bilibili_growth_package(project_root)

    scorecard_path = project_root / "review" / "competitive-scorecard.json"
    scorecard = json.loads(scorecard_path.read_text(encoding="utf-8"))
    scorecard["score_by_dimension"].pop("opening_hold_power", None)
    scorecard["score_by_dimension"].pop("follow_conversion_power", None)
    scorecard_path.write_text(json.dumps(scorecard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    run_command([sys.executable, str(attention_script), "--project-root", str(project_root)], repo_root)
    run_command([sys.executable, str(review_script), "--project-root", str(project_root)], repo_root)

    payload = json.loads((project_root / "review" / "opening-scorecard.json").read_text(encoding="utf-8"))
    assert payload["score_sources"]["opening_hold_power"] == "inferred"
    assert payload["score_sources"]["follow_conversion_power"] == "inferred"
    assert payload["score_by_dimension"]["opening_hold_power"] >= 4
    assert payload["score_by_dimension"]["follow_conversion_power"] >= 3
    assert payload["decision"] == "pass"
