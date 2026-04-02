#!/usr/bin/env python3
"""Build a render plan and execute the narrated-cut render workflow."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from build_render_plan import build_render_plan


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", help="Media package root directory.")
    parser.add_argument("--content-id", help="Content package id under media-ops root.")
    parser.add_argument(
        "--media-ops-root",
        help="Root directory containing media packages. Defaults to repo-local data/media-ops.",
    )
    parser.add_argument("--source-video", help="Optional explicit source video path.")
    parser.add_argument("--voiceover-audio", help="Optional explicit voiceover audio path.")
    parser.add_argument("--subtitles", help="Optional explicit subtitle path.")
    parser.add_argument("--output-video", help="Optional explicit final cut output path.")
    parser.add_argument(
        "--render-plan-output",
        default="content/postproduction/render-plan.json",
        help="Output path for the generated render plan, relative to project root.",
    )
    parser.add_argument(
        "--render-manifest-output",
        default="content/postproduction/render-manifest.json",
        help="Render manifest output path, relative to project root.",
    )
    parser.add_argument(
        "--verification-output",
        default="review/render-verification-auto.md",
        help="Verification markdown output path, relative to project root.",
    )
    parser.add_argument(
        "--qa-report-output",
        default="review/assembly-qa-report.json",
        help="Assembly QA report output path, relative to project root.",
    )
    parser.add_argument(
        "--subtitle-quality-report-output",
        default="review/subtitle-quality-report.json",
        help="Subtitle quality report output path, relative to project root.",
    )
    parser.add_argument(
        "--scene-assembly-report-output",
        default="review/scene-assembly-report.json",
        help="Scene assembly report output path, relative to project root.",
    )
    parser.add_argument(
        "--assembly-strategy",
        choices=["retime_existing_cut", "rebuild_timeline", "review_only"],
        help="Assembly strategy to record in the render plan. Defaults to content packet value or retime_existing_cut.",
    )
    parser.add_argument(
        "--max-speedup",
        type=float,
        default=2.0,
        help="Maximum retime speedup ratio allowed by the render step.",
    )
    parser.add_argument(
        "--allow-slowdown",
        action="store_true",
        help="Allow the render step to slow the source video down when narration is longer.",
    )
    parser.add_argument(
        "--no-retain-original-audio",
        action="store_true",
        help="Mute the source audio instead of mixing it under the narration.",
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Only generate render-plan.json without executing the render step.",
    )
    args = parser.parse_args()
    if not args.project_root and not args.content_id:
        parser.error("one of --project-root or --content-id is required")
    return args


def run_command(command: list[str]) -> None:
    subprocess.run(command, check=True, capture_output=True, text=True)


def main() -> int:
    args = parse_args()
    plan, render_plan_output = build_render_plan(args)
    render_plan_output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    project_root = Path(plan["workspace_root"]).resolve()
    summary = {
        "project_root": str(project_root),
        "render_plan": str(render_plan_output),
        "assembly_strategy": plan["assembly_strategy"],
    }

    if args.plan_only:
        print(json.dumps(summary, ensure_ascii=False))
        return 0

    render_script = Path(__file__).with_name("render_narrated_cut.py")
    run_command([sys.executable, str(render_script), "--plan", str(render_plan_output)])

    render_manifest_path = project_root / plan["render_manifest_output"]
    verification_path = project_root / plan["verification_output"]
    summary.update(
        {
            "render_manifest": str(render_manifest_path),
            "verification": str(verification_path),
            "qa_report": str(project_root / plan["qa_report_output"]),
            "subtitle_quality_report": str(project_root / plan["subtitle_quality_report_output"]),
            "scene_assembly_report": str(project_root / plan["scene_assembly_report_output"]),
            "final_cut": str(project_root / plan["output_video"]),
        }
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
