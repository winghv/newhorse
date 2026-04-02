"""Tests for scene manifest, transition plan, and scene assembly reporting."""

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


def make_scene_package(project_root: Path) -> None:
    (project_root / "content").mkdir(parents=True, exist_ok=True)
    (project_root / "assets").mkdir(parents=True, exist_ok=True)
    (project_root / "review").mkdir(parents=True, exist_ok=True)
    (project_root / "content" / "postproduction").mkdir(parents=True, exist_ok=True)

    write_json(
        project_root / "content" / "bilibili-midform-video.json",
        {
            "content_id": project_root.name,
            "platforms": ["bilibili"],
            "deliverable_type": "midlong-video",
            "chapter_outline": [
                {
                    "chapter_id": "ch1",
                    "title": "开场问题",
                    "chapter_goal": "先给冲突和异常点",
                    "summary": "什么都知道，却不敢决定。",
                },
                {
                    "chapter_id": "ch2",
                    "title": "案例证明",
                    "chapter_goal": "用两个 offer 的案例证明继续比较不等于继续思考",
                    "summary": "不同前提下会得到相反建议。",
                },
                {
                    "chapter_id": "ch3",
                    "title": "框架交付",
                    "chapter_goal": "把四步框架交成能带走的模板",
                    "summary": "来源、反证、约束、试错。",
                },
            ],
        },
    )

    write_json(
        project_root / "assets" / "scene-asset-plan.json",
        {
            "content_id": project_root.name,
            "chapters": [
                {
                    "chapter_id": "ch1",
                    "scene_goal": "先给冲突和异常点",
                    "proof_asset": {"path": "assets/graphics/card-01-hook.png", "type": "graphics-card"},
                    "supporting_b_roll": [{"asset_path": "assets/reused/stock-1.mp4", "clip_id": "stock-1"}],
                    "fallback_graphics": ["assets/graphics/card-01-hook.png"],
                    "approved_generation_slots": [{"slot_id": "hero-open", "generation_type": "image-to-video"}],
                },
                {
                    "chapter_id": "ch2",
                    "scene_goal": "用案例证明",
                    "proof_asset": {"path": "assets/graphics/card-02-offer.png", "type": "graphics-card"},
                    "supporting_b_roll": [{"asset_path": "assets/reused/stock-2.mp4", "clip_id": "stock-2"}],
                    "fallback_graphics": ["assets/graphics/card-02-offer.png"],
                    "approved_generation_slots": [],
                },
                {
                    "chapter_id": "ch3",
                    "scene_goal": "交付四步框架",
                    "proof_asset": {"path": "assets/graphics/card-03-framework.png", "type": "graphics-card"},
                    "supporting_b_roll": [{"asset_path": "assets/reused/stock-3.mp4", "clip_id": "stock-3"}],
                    "fallback_graphics": ["assets/graphics/card-03-framework.png"],
                    "approved_generation_slots": [],
                },
            ],
        },
    )
    write_json(
        project_root / "content" / "postproduction" / "auto-base-cut-plan.json",
        {
            "quality": {
                "status": "pass",
                "metrics": {
                    "image_slot_ratio": 0.55,
                    "image_motion_enabled_count": 6,
                },
            }
        },
    )
    write_json(
        project_root / "review" / "assembly-qa-report.json",
        {
            "status": "pass",
            "checks": {
                "freeze_detection": {"status": "pass"},
                "duration_alignment": {"status": "pass"},
                "subtitle_delivery": {"status": "pass"},
            },
        },
    )


def test_build_scene_manifest_creates_required_scene_fields(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "build_scene_manifest.py"
    )
    project_root = tmp_path / "media-ops" / "2026-03-31-scene-manifest"
    make_scene_package(project_root)

    run_command([sys.executable, str(script_path), "--project-root", str(project_root)], repo_root)

    payload = json.loads((project_root / "content" / "postproduction" / "scene-manifest.json").read_text(encoding="utf-8"))
    assert len(payload["scenes"]) == 3
    assert payload["scenes"][0]["scene_id"] == "scene-01-ch1"
    assert payload["scenes"][0]["transition_in"] == "cold_open_cut"
    assert any(effect["type"] == "typewriter_quote" for effect in payload["scenes"][0]["emphasis_fx"])
    assert payload["scenes"][1]["primary_asset"]["path"] == "assets/graphics/card-02-offer.png"
    assert payload["scenes"][2]["subtitle_mode"] == "narrated_hardsub"
    assert payload["scenes"][2]["emphasis_fx"]


def test_build_transition_plan_creates_transition_and_emphasis_outputs(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    manifest_script = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "build_scene_manifest.py"
    )
    transition_script = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "build_transition_plan.py"
    )
    project_root = tmp_path / "media-ops" / "2026-03-31-transition-plan"
    make_scene_package(project_root)

    run_command([sys.executable, str(manifest_script), "--project-root", str(project_root)], repo_root)
    run_command([sys.executable, str(transition_script), "--project-root", str(project_root)], repo_root)

    transition_plan = json.loads((project_root / "content" / "postproduction" / "transition-plan.json").read_text(encoding="utf-8"))
    emphasis_plan = json.loads((project_root / "content" / "postproduction" / "emphasis-fx-plan.json").read_text(encoding="utf-8"))

    assert len(transition_plan["transitions"]) == 2
    assert transition_plan["transitions"][0]["style"] == "proof_match_cut"
    assert emphasis_plan["scene_fx"][0]["effects"][0]["type"] == "headline_punch"
    assert any(effect["type"] == "typewriter_quote" for effect in emphasis_plan["scene_fx"][0]["effects"])
    assert emphasis_plan["scene_fx"][1]["effects"][0]["type"] == "proof_focus"


def test_render_plan_and_render_workflow_emit_scene_assembly_report(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    build_render_plan = (
        repo_root
        / "extensions"
        / "skills"
        / "video-postproduction-assembly"
        / "scripts"
        / "build_render_plan.py"
    )
    project_root = tmp_path / "media-ops" / "2026-03-31-scene-report"
    make_scene_package(project_root)

    # Minimal media package for plan-only verification.
    (project_root / "content" / "final-cut").mkdir(parents=True, exist_ok=True)
    (project_root / "content" / "postproduction" / "minimax-output").mkdir(parents=True, exist_ok=True)
    write_json(
        project_root / "content" / "postproduction" / "voiceover-profile.json",
        {
            "platform": "bilibili",
            "content_id": project_root.name,
            "render_targets": {
                "voiceover_audio": "content/postproduction/minimax-output/voice.mp3",
                "subtitle_draft": "content/postproduction/subtitles.srt",
            },
            "mix_defaults": {
                "bgm_target_db": -30,
                "ducking_target_db": -22,
                "narration_lufs_target": -16,
            },
        },
    )
    (project_root / "content" / "final-cut" / "pilot-v1.mp4").write_bytes(b"video")
    (project_root / "content" / "postproduction" / "minimax-output" / "voice.mp3").write_bytes(b"voice")
    (project_root / "content" / "postproduction" / "subtitles.srt").write_text(
        "1\n00:00:00,000 --> 00:00:00,800\ntest\n",
        encoding="utf-8",
    )

    run_command([sys.executable, str(build_render_plan), "--project-root", str(project_root)], repo_root)

    plan = json.loads((project_root / "content" / "postproduction" / "render-plan.json").read_text(encoding="utf-8"))
    assert plan["context"]["scene_manifest"] == "content/postproduction/scene-manifest.json"
    assert plan["context"]["transition_plan"] == "content/postproduction/transition-plan.json"
    assert plan["context"]["emphasis_fx_plan"] == "content/postproduction/emphasis-fx-plan.json"
    assert plan["scene_assembly_report_output"] == "review/scene-assembly-report.json"
