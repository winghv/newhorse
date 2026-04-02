"""Tests for workflow quality gate aggregation."""

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


def make_quality_gate_package(project_root: Path, *, visual_status: str = "pass") -> None:
    (project_root / "benchmarks").mkdir(parents=True, exist_ok=True)
    (project_root / "angles").mkdir(parents=True, exist_ok=True)
    (project_root / "content" / "postproduction").mkdir(parents=True, exist_ok=True)
    (project_root / "review").mkdir(parents=True, exist_ok=True)
    (project_root / "assets").mkdir(parents=True, exist_ok=True)

    write_json(
        project_root / "content" / "bilibili-midform-video.json",
        {
            "content_id": project_root.name,
            "platforms": ["bilibili"],
            "deliverable_type": "midlong-video",
        },
    )
    write_json(project_root / "benchmarks" / "bilibili-hook-patterns.json", {"opening_patterns": []})
    write_json(project_root / "angles" / "attention-structure-template.json", {"lead_hook": "hook"})
    write_json(project_root / "angles" / "follow-conversion-hooks.json", {"follow_cta_variants": ["next"]})
    write_json(project_root / "review" / "opening-scorecard.json", {"decision": "pass"})
    write_json(project_root / "content" / "postproduction" / "voice-performance-plan.json", {"segments": [{"emotion": "focused"}]})
    write_json(project_root / "content" / "postproduction" / "voiceover-profile.json", {"render_targets": {}})
    write_json(project_root / "content" / "postproduction" / "voiceover-segments.json", [{"text": "hello", "emotion": "focused"}])
    write_json(project_root / "review" / "subtitle-quality-report.json", {"status": "pass"})
    write_json(project_root / "assets" / "visual-diversity-report.json", {"status": visual_status})
    write_json(project_root / "content" / "postproduction" / "scene-manifest.json", {"scenes": [{"scene_id": "scene-01"}]})
    write_json(project_root / "content" / "postproduction" / "transition-plan.json", {"transitions": []})
    write_json(project_root / "content" / "postproduction" / "emphasis-fx-plan.json", {"scene_fx": []})
    write_json(project_root / "review" / "scene-assembly-report.json", {"status": "pass"})
    write_json(project_root / "assets" / "generation-budget.json", {"approved_generation_slots": []})


def test_build_workflow_quality_gate_reports_passing_statuses(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "media-ops-orchestration"
        / "scripts"
        / "build_workflow_quality_gate.py"
    )
    project_root = tmp_path / "media-ops" / "2026-03-31-quality-pass"
    make_quality_gate_package(project_root)

    run_command([sys.executable, str(script_path), "--project-root", str(project_root)], repo_root)

    gate = json.loads((project_root / "review" / "workflow-quality-gate.json").read_text(encoding="utf-8"))
    board = json.loads((project_root / "review" / "upgrade-status-board.json").read_text(encoding="utf-8"))
    assert gate["overall_status"] == "pass"
    assert gate["dimensions"]["growth_structure_status"]["status"] == "pass"
    assert gate["dimensions"]["scene_assembly_status"]["status"] == "pass"
    assert board["rows"][0]["dimension"] == "growth_structure_status"


def test_build_workflow_quality_gate_marks_revise_dimension_when_visual_diversity_fails(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "media-ops-orchestration"
        / "scripts"
        / "build_workflow_quality_gate.py"
    )
    project_root = tmp_path / "media-ops" / "2026-03-31-quality-revise"
    make_quality_gate_package(project_root, visual_status="revise")

    run_command([sys.executable, str(script_path), "--project-root", str(project_root)], repo_root)

    gate = json.loads((project_root / "review" / "workflow-quality-gate.json").read_text(encoding="utf-8"))
    assert gate["overall_status"] == "revise"
    assert "visual_diversity_status" in gate["revise_dimensions"]
