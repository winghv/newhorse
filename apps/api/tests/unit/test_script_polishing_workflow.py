"""Tests for reference-driven script polishing workflow scripts."""

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
    entries = []
    samples = [
        {
            "video_id": "BV1A",
            "title": "为什么越努力越穷",
            "uploader": "认知便利店M",
            "transcript": [
                "如果你去年多干了500小时,工资却只长了15%",
                "这不是你不够努力,而是你正掉进一个被设计好的陷阱",
                "这个视频不会劝你鸡汤硬扛,而是用四个经济学框架拆开这件事",
                "看完这条视频,你会知道普通人应该把时间花在哪里",
                "先从一个农民和一亩地的例子开始",
            ],
        },
        {
            "video_id": "BV1B",
            "title": "为什么停止表演才是真正的解脱",
            "uploader": "认知便利店M",
            "transcript": [
                "如果你穿着一件很奇怪的T恤走进房间,你觉得会有多少人真正注意你",
                "你的大脑以为所有人都在看你,实际上只有百分之十二的人会留意",
                "今天这期视频会带你完成一个认知升级",
                "你会发现,你不是活在舞台中央,你只是被自己的聚光灯困住了",
                "接下来我会给你一个能立刻拿去用的判断方法",
            ],
        },
    ]

    for sample in samples:
        root_path = library_root / "bilibili" / sample["video_id"]
        transcript_path = root_path / "research" / "reference-transcript.md"
        metadata_path = root_path / "research" / "reference-video-metadata.json"

        transcript_text = "\n".join(
            [
                "# Reference Transcript",
                "",
                f"- title: {sample['title']}",
                "- source_url: https://www.bilibili.com/video/dummy",
                f"- uploader: {sample['uploader']}",
                "- subtitle_track_type: asr",
                "- language: Chinese",
                "",
                "## Transcript",
                *[f"- {line}" for line in sample["transcript"]],
            ]
        )
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        transcript_path.write_text(transcript_text + "\n", encoding="utf-8")
        write_json(
            metadata_path,
            {
                "video_id": sample["video_id"],
                "title": sample["title"],
                "uploader": sample["uploader"],
                "duration_seconds": 600,
            },
        )

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


def make_script_project(project_root: Path, duration_target: str = "08:00-12:00") -> None:
    (project_root / "planning").mkdir(parents=True, exist_ok=True)
    (project_root / "angles").mkdir(parents=True, exist_ok=True)
    (project_root / "content").mkdir(parents=True, exist_ok=True)

    write_json(
        project_root / "planning" / "topic-selection.json",
        {
            "platform": "bilibili",
            "selected_topic": {
                "topic": "平台越懂你，为什么你越难形成独立判断",
            },
        },
    )
    write_json(
        project_root / "angles" / "angle-brief.json",
        {
            "platforms": ["bilibili"],
            "deliverable_type": "midlong-video",
            "duration_target": duration_target,
            "core_angle": "平台不是在帮你判断,而是在帮你更舒服地停留在已有判断里。",
            "hook_hypotheses": [
                "平台越懂你,为什么你越难形成独立判断？",
            ],
            "proof_plan": [
                "先拆熟悉感为什么会伪装成正确。",
                "再用双 feed 对照说明平台更擅长放大既有偏好。",
                "最后给出离开 feed 的验证框架。",
            ],
            "comment_prompt": "你最近一个被平台越推越确认的判断是什么？",
            "cta": "先退出 feed,再验证一次。",
        },
    )
    write_json(
        project_root / "angles" / "attention-structure-template.json",
        {
            "lead_hook": "平台越懂你,为什么你越难形成独立判断？",
            "proof_reveal_plan": [
                {"proof_beat": "先拆熟悉感为什么会伪装成正确。"},
                {"proof_beat": "再用双 feed 对照说明平台更擅长放大既有偏好。"},
            ],
            "comment_trigger": "你最近一个被平台越推越确认的判断是什么？",
        },
    )
    write_json(
        project_root / "content" / "bilibili-midform-video.json",
        {
            "platforms": ["bilibili"],
            "deliverable_type": "midlong-video",
            "duration_target": duration_target,
        },
    )


def test_build_reference_script_patterns_and_polish_packet(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    patterns_script = (
        repo_root
        / "extensions"
        / "skills"
        / "script-polishing"
        / "scripts"
        / "build_reference_script_patterns.py"
    )
    polish_script = (
        repo_root
        / "extensions"
        / "skills"
        / "script-polishing"
        / "scripts"
        / "build_script_polish_packet.py"
    )

    project_root = tmp_path / "media-ops" / "2026-04-03-bilibili-script-polish"
    library_root = build_reference_library(tmp_path)
    make_script_project(project_root)

    run_command(
        [
            sys.executable,
            str(patterns_script),
            "--project-root",
            str(project_root),
            "--reference-library-root",
            str(library_root),
        ],
        repo_root,
    )

    patterns_path = project_root / "benchmarks" / "reference-script-patterns.json"
    assert patterns_path.exists()

    patterns = json.loads(patterns_path.read_text(encoding="utf-8"))
    assert patterns["reference_count"] == 2
    assert patterns["platform"] == "bilibili"
    assert patterns["dominant_opening_devices"]
    assert patterns["dominant_opening_devices"][0]["count"] >= 1
    assert any(item["label"] == "question_or_counterintuition" for item in patterns["dominant_opening_devices"])
    assert any(item["label"] == "promise_of_takeaway" for item in patterns["line_tactics"])
    assert len(patterns["reference_cards"]) == 2

    run_command(
        [
            sys.executable,
            str(polish_script),
            "--project-root",
            str(project_root),
        ],
        repo_root,
    )

    polish_path = project_root / "content" / "script-polish-packet.json"
    assert polish_path.exists()

    polish = json.loads(polish_path.read_text(encoding="utf-8"))
    assert polish["target_shape"] == "bilibili-cognition-midlong"
    assert polish["selected_topic"] == "平台越懂你，为什么你越难形成独立判断"
    assert polish["episode_completion_mode"] == "standalone"
    assert polish["audience_psychology_contract"]["primary_audience_needs"]
    assert polish["opening_contract"]["first_thirty_seconds_goal"]
    assert "前 30 秒" in polish["hard_constraints"][0]
    assert any("中段" in item for item in polish["freedom_zones"])
    assert polish["borrowed_plays"]
    assert polish["section_blueprint"][0]["section"] == "opening"
    assert polish["rewrite_loop"][0]["pass"] == "hook_tightening"
    assert polish["delegation_contract"]["required_agent"] == "script-doctor"
    assert polish["delegation_contract"]["operating_mode"] == "supervisor-led"
    assert "script-doctor" in polish["delegate_brief_template"]
    assert "operating_mode=supervisor-led" in polish["delegate_brief_template"]


def test_build_script_polish_packet_expands_for_13_minute_target(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    patterns_script = (
        repo_root
        / "extensions"
        / "skills"
        / "script-polishing"
        / "scripts"
        / "build_reference_script_patterns.py"
    )
    polish_script = (
        repo_root
        / "extensions"
        / "skills"
        / "script-polishing"
        / "scripts"
        / "build_script_polish_packet.py"
    )

    project_root = tmp_path / "media-ops" / "2026-04-03-bilibili-script-polish-13m"
    library_root = build_reference_library(tmp_path)
    make_script_project(project_root, duration_target="12:40-13:20")

    run_command(
        [
            sys.executable,
            str(patterns_script),
            "--project-root",
            str(project_root),
            "--reference-library-root",
            str(library_root),
        ],
        repo_root,
    )

    run_command(
        [
            sys.executable,
            str(polish_script),
            "--project-root",
            str(project_root),
        ],
        repo_root,
    )

    polish = json.loads((project_root / "content" / "script-polish-packet.json").read_text(encoding="utf-8"))
    assert polish["duration_target"] == "12:40-13:20"
    assert polish["runtime_strategy"]["pacing_tier"] == "extended_midform"
    assert polish["runtime_strategy"]["target_minutes"] == 13.0
    assert any("情绪托底" in item for item in polish["hard_constraints"])
    assert any("完整收束" in item for item in polish["hard_constraints"])
    assert any(item["section"] == "false_progress_breakdown" for item in polish["section_blueprint"])
    assert len(polish["section_blueprint"]) == 7
    assert any("12 分钟以上档位" in item for item in polish["hard_constraints"])
    assert "12:40-13:20" in polish["delegate_brief_template"]
    assert "完整收束" in polish["delegate_brief_template"]
    assert polish["delegation_contract"]["required_outputs"]
