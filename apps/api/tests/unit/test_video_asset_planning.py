"""Tests for video asset planning and visual diversity workflows."""

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


def make_visual_asset_package(project_root: Path) -> None:
    (project_root / "content").mkdir(parents=True, exist_ok=True)
    (project_root / "assets" / "graphics").mkdir(parents=True, exist_ok=True)
    (project_root / "sources").mkdir(parents=True, exist_ok=True)
    (project_root / "review").mkdir(parents=True, exist_ok=True)

    write_json(
        project_root / "content" / "bilibili-midform-video.json",
        {
            "content_id": project_root.name,
            "platforms": ["bilibili"],
            "deliverable_type": "midlong-video",
            "duration_target": "06:10-06:50",
            "chapter_outline": [
                {"chapter_id": "ch1", "title": "先打问题"},
                {"chapter_id": "ch2", "title": "给出案例"},
                {"chapter_id": "ch3", "title": "交付框架"},
            ],
            "clip_sourcing_brief": [
                {
                    "chapter_id": "ch1",
                    "shot_intent": "表现答案爆炸和反复比较",
                    "fallback": "图卡和 UI 录屏",
                },
                {
                    "chapter_id": "ch2",
                    "shot_intent": "表现 running example 的具体案例",
                    "fallback": "offer 对照图卡",
                },
                {
                    "chapter_id": "ch3",
                    "shot_intent": "把四步框架做成模板",
                    "fallback": "流程图卡",
                },
            ],
            "generation_budget_decision": {
                "daily_quota_limit": 2,
                "quota_snapshot": {
                    "daily_remaining": 2,
                    "daily_limit": 2,
                },
                "approved_generated_assets": [
                    {
                        "slot_id": "shot-hero-open",
                        "chapter_id": "ch1",
                        "generation_type": "image-to-video",
                        "reason": "只补开场英雄镜头",
                    }
                ],
                "blocked_generated_assets": [
                    {
                        "slot_id": "shot-mid-body",
                        "chapter_id": "ch2",
                        "generation_type": "text-to-video",
                        "reason": "已有合法 B-roll 可替代",
                    }
                ],
            },
        },
    )

    for name in ("card-01-hook.png", "card-02-offer.png", "card-03-framework.png"):
        (project_root / "assets" / "graphics" / name).write_bytes(b"png")
    (project_root / "assets" / "bilibili-cover-draft.png").write_bytes(b"png")

    write_json(
        project_root / "sources" / "source-manifest.json",
        {
            "license_summary": {"approved_count": 3},
            "source_manifest": [
                {
                    "clip_id": "stock-1",
                    "chapter_id": "ch1",
                    "license_status": "approved",
                    "source_type": "stock-library",
                    "local_asset_path": "assets/reused/stock-1.mp4",
                    "usage_notes": "开场过渡",
                },
                {
                    "clip_id": "stock-2",
                    "chapter_id": "ch2",
                    "license_status": "approved",
                    "source_type": "stock-library",
                    "local_asset_path": "assets/reused/stock-1.mp4",
                    "usage_notes": "同一资产跨章复用，后续要看重复风险",
                },
                {
                    "clip_id": "stock-3",
                    "chapter_id": "ch3",
                    "license_status": "approved",
                    "source_type": "stock-library",
                    "local_asset_path": "assets/reused/stock-3.mp4",
                    "usage_notes": "框架段补充镜头",
                },
            ],
        },
    )
    write_json(
        project_root / "sources" / "asset-ingest-manifest.json",
        {
            "ingested_assets": [
                {"clip_id": "stock-1", "chapter_id": "ch1", "local_path": "assets/reused/stock-1.mp4"},
                {"clip_id": "stock-2", "chapter_id": "ch2", "local_path": "assets/reused/stock-1.mp4"},
                {"clip_id": "stock-3", "chapter_id": "ch3", "local_path": "assets/reused/stock-3.mp4"},
            ]
        },
    )
    write_json(
        project_root / "sources" / "exploration-ingest-manifest.json",
        {
            "ingested_assets": [
                {
                    "clip_id": "explore-1",
                    "chapter_id": "ch2",
                    "provider": "yt-dlp",
                    "source_type": "exploration-platform",
                    "license_status": "hold",
                    "local_path": "assets/exploration/ch2/explore-1.mp4",
                }
            ]
        },
    )
    write_json(
        project_root / "sources" / "chapter-coverage-report.json",
        {
            "overall_status": "pass",
            "chapters": [
                {"chapter_id": "ch1", "approved_candidate_count": 1},
                {"chapter_id": "ch2", "approved_candidate_count": 1},
                {"chapter_id": "ch3", "approved_candidate_count": 1},
            ],
        },
    )
    write_json(
        project_root / "review" / "opening-scorecard.json",
        {
            "decision": "pass",
        },
    )


def test_build_scene_asset_plan_creates_visual_evidence_and_budget_artifacts(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-asset-planning"
        / "scripts"
        / "build_scene_asset_plan.py"
    )
    project_root = tmp_path / "media-ops" / "2026-03-31-visual-plan"
    make_visual_asset_package(project_root)

    run_command([sys.executable, str(script_path), "--project-root", str(project_root)], repo_root)

    scene_asset_plan = json.loads((project_root / "assets" / "scene-asset-plan.json").read_text(encoding="utf-8"))
    visual_map = json.loads((project_root / "assets" / "visual-evidence-map.json").read_text(encoding="utf-8"))
    generation_budget = json.loads((project_root / "assets" / "generation-budget.json").read_text(encoding="utf-8"))

    assert len(scene_asset_plan["chapters"]) == 3
    assert scene_asset_plan["chapters"][0]["proof_asset"]["path"].endswith("card-01-hook.png")
    assert scene_asset_plan["chapters"][1]["supporting_b_roll"][0]["clip_id"] == "stock-2"
    assert any(item["clip_id"] == "explore-1" for item in scene_asset_plan["chapters"][1]["supporting_b_roll"])
    assert scene_asset_plan["chapters"][2]["max_repeat_uses"] == 2
    assert visual_map["chapters"][0]["fallback_graphics"][0].endswith("card-01-hook.png")
    assert generation_budget["quota"]["daily_limit"] == 2
    assert generation_budget["approved_generation_slots"][0]["slot_id"] == "shot-hero-open"


def test_build_scene_asset_plan_prefers_generated_keyframes_for_chapter_proof_assets(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-asset-planning"
        / "scripts"
        / "build_scene_asset_plan.py"
    )
    project_root = tmp_path / "media-ops" / "2026-03-31-generated-keyframes"
    make_visual_asset_package(project_root)
    generated_dir = project_root / "assets" / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)
    (generated_dir / "ch2-algorithm-loop.png").write_bytes(b"png")

    run_command([sys.executable, str(script_path), "--project-root", str(project_root)], repo_root)

    scene_asset_plan = json.loads((project_root / "assets" / "scene-asset-plan.json").read_text(encoding="utf-8"))
    chapter_two = scene_asset_plan["chapters"][1]
    assert chapter_two["proof_asset"]["path"].endswith("assets/generated/ch2-algorithm-loop.png")
    assert chapter_two["proof_asset"]["type"] == "generated-keyart"
    assert any(path.endswith("assets/graphics/card-02-offer.png") for path in chapter_two["fallback_graphics"])


def test_audit_visual_diversity_flags_repeated_assets(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    scene_plan_script = (
        repo_root
        / "extensions"
        / "skills"
        / "video-asset-planning"
        / "scripts"
        / "build_scene_asset_plan.py"
    )
    diversity_script = (
        repo_root
        / "extensions"
        / "skills"
        / "video-asset-planning"
        / "scripts"
        / "audit_visual_diversity.py"
    )
    project_root = tmp_path / "media-ops" / "2026-03-31-visual-diversity"
    make_visual_asset_package(project_root)

    run_command([sys.executable, str(scene_plan_script), "--project-root", str(project_root)], repo_root)
    scene_plan_path = project_root / "assets" / "scene-asset-plan.json"
    scene_plan = json.loads(scene_plan_path.read_text(encoding="utf-8"))
    scene_plan["chapters"][1]["max_repeat_uses"] = 1
    scene_plan_path.write_text(json.dumps(scene_plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    run_command([sys.executable, str(diversity_script), "--project-root", str(project_root)], repo_root)

    report = json.loads((project_root / "assets" / "visual-diversity-report.json").read_text(encoding="utf-8"))
    assert report["status"] == "revise"
    assert report["repeated_asset_count"] == 1
    assert "assets/reused/stock-1.mp4" in report["repeated_assets"][0]["asset_path"]


def test_build_minimax_shot_plan_creates_budgeted_slots_and_ledger(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    scene_plan_script = (
        repo_root
        / "extensions"
        / "skills"
        / "video-asset-planning"
        / "scripts"
        / "build_scene_asset_plan.py"
    )
    shot_plan_script = (
        repo_root
        / "extensions"
        / "skills"
        / "video-asset-planning"
        / "scripts"
        / "build_minimax_shot_plan.py"
    )
    project_root = tmp_path / "media-ops" / "2026-03-31-minimax-plan"
    make_visual_asset_package(project_root)

    run_command([sys.executable, str(scene_plan_script), "--project-root", str(project_root)], repo_root)
    run_command([sys.executable, str(shot_plan_script), "--project-root", str(project_root)], repo_root)

    shot_plan = json.loads((project_root / "assets" / "minimax-shot-plan.json").read_text(encoding="utf-8"))
    ledger = json.loads((project_root / "assets" / "generation-ledger.json").read_text(encoding="utf-8"))

    assert shot_plan["approved_slots"][0]["slot_id"] == "shot-hero-open"
    assert shot_plan["approved_slots"][0]["generation_type"] == "image-to-video"
    assert shot_plan["blocked_slots"][0]["slot_id"] == "shot-mid-body"
    assert ledger["entries"][0]["status"] == "not_run"
    assert ledger["entries"][0]["slot_id"] == "shot-hero-open"


def test_build_video_automation_plan_includes_visual_asset_tasks(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    scene_plan_script = (
        repo_root
        / "extensions"
        / "skills"
        / "video-asset-planning"
        / "scripts"
        / "build_scene_asset_plan.py"
    )
    diversity_script = (
        repo_root
        / "extensions"
        / "skills"
        / "video-asset-planning"
        / "scripts"
        / "audit_visual_diversity.py"
    )
    shot_plan_script = (
        repo_root
        / "extensions"
        / "skills"
        / "video-asset-planning"
        / "scripts"
        / "build_minimax_shot_plan.py"
    )
    automation_script = (
        repo_root
        / "extensions"
        / "skills"
        / "media-ops-orchestration"
        / "scripts"
        / "build_video_automation_plan.py"
    )
    project_root = tmp_path / "media-ops" / "2026-03-31-automation-assets"
    make_visual_asset_package(project_root)

    run_command([sys.executable, str(scene_plan_script), "--project-root", str(project_root)], repo_root)
    run_command([sys.executable, str(diversity_script), "--project-root", str(project_root)], repo_root)
    run_command([sys.executable, str(shot_plan_script), "--project-root", str(project_root)], repo_root)
    run_command([sys.executable, str(automation_script), "--project-root", str(project_root)], repo_root)

    payload = json.loads((project_root / "review" / "video-automation-plan.json").read_text(encoding="utf-8"))
    task_ids = {task["task_id"] for task in payload["tasks"]}

    assert {"scene-asset-plan", "visual-diversity-audit", "minimax-shot-plan"} <= task_ids
    assert payload["summary"]["scene_asset_plan_exists"] is True
    assert payload["summary"]["visual_diversity_status"] == "pass"
    assert payload["summary"]["approved_generation_slot_count"] == 1
