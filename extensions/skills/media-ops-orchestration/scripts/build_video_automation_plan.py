#!/usr/bin/env python3
"""Build an automation-first execution plan for a media video package."""

from __future__ import annotations

import argparse
import json
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
        "--json-output",
        default="review/video-automation-plan.json",
        help="JSON output path, relative to the project root.",
    )
    parser.add_argument(
        "--markdown-output",
        default="review/video-automation-plan.md",
        help="Markdown output path, relative to the project root.",
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


def detect_content_packet(project_root: Path) -> Path:
    content_dir = project_root / "content"
    prioritized = ["*video.json", "content-packet.json", "*.json"]
    for pattern in prioritized:
        matches = sorted(path for path in content_dir.glob(pattern) if path.is_file())
        if matches:
            return matches[0]
    raise FileNotFoundError(f"no content packet found under {content_dir}")


def relative_to_project(path: Path, project_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_root.resolve()))
    except ValueError:
        return str(path.resolve())


def first_path(packet: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = packet.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def build_task(
    task_id: str,
    title: str,
    status: str,
    why: str,
    command: list[str] | None,
    outputs: list[str],
    blocking: bool,
) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "title": title,
        "status": status,
        "why": why,
        "command": command,
        "outputs": outputs,
        "blocking": blocking,
    }


def command_as_string(command: list[str] | None) -> str:
    if not command:
        return "-"
    return " ".join(command)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("# Video Automation Plan")
    lines.append("")
    lines.append(f"- `content_id`: `{payload['content_id']}`")
    lines.append(f"- `generated_at`: `{payload['generated_at']}`")
    lines.append(f"- `overall_status`: `{payload['overall_status']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- `deliverable_type`: `{payload['deliverable_type']}`")
    lines.append(f"- `assembly_strategy`: `{payload.get('assembly_strategy') or 'unknown'}`")
    lines.append(f"- `graphics_svg_count`: `{payload['summary']['graphics_svg_count']}`")
    lines.append(f"- `graphics_png_count`: `{payload['summary']['graphics_png_count']}`")
    lines.append(f"- `source_manifest_hold_count`: `{payload['summary']['source_manifest_hold_count']}`")
    lines.append(f"- `chapter_coverage_status`: `{payload['summary']['chapter_coverage_status']}`")
    lines.append(f"- `scene_asset_plan_exists`: `{payload['summary']['scene_asset_plan_exists']}`")
    lines.append(f"- `visual_diversity_status`: `{payload['summary']['visual_diversity_status']}`")
    lines.append(f"- `approved_generation_slot_count`: `{payload['summary']['approved_generation_slot_count']}`")
    lines.append(f"- `voiceover_status`: `{payload['summary']['voiceover_status']}`")
    lines.append(f"- `subtitle_exists`: `{payload['summary']['subtitle_exists']}`")
    lines.append(f"- `render_manifest_exists`: `{payload['summary']['render_manifest_exists']}`")
    lines.append(f"- `final_cut_count`: `{payload['summary']['final_cut_count']}`")
    lines.append(f"- `auto_base_quality_status`: `{payload['summary']['auto_base_quality_status']}`")
    lines.append("")
    lines.append("## Tasks")
    lines.append("")
    lines.append("| task | status | blocking | outputs | command |")
    lines.append("|---|---|---|---|---|")
    for task in payload["tasks"]:
        outputs = ", ".join(task["outputs"]) if task["outputs"] else "-"
        lines.append(
            f"| {task['title']} | {task['status']} | {str(task['blocking']).lower()} | {outputs} | {command_as_string(task['command'])} |"
        )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    for note in payload["notes"]:
        lines.append(f"- {note}")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)
    packet_path = detect_content_packet(project_root)
    packet = load_json(packet_path)
    primary = packet.get("content_packet") if isinstance(packet.get("content_packet"), dict) else packet

    content_id = primary.get("content_id") or project_root.name
    deliverable_type = primary.get("deliverable_type") or "unknown"
    assembly_strategy = primary.get("assembly_strategy")
    voiceover_status = (primary.get("voiceover_assets") or {}).get("status") or "unknown"

    graphics_dir = project_root / "assets" / "graphics"
    svg_assets = sorted(path for path in graphics_dir.glob("card-*.svg") if path.is_file())
    png_assets = sorted(path for path in graphics_dir.glob("card-*.png") if path.is_file())

    root_assets_dir = project_root / "assets"
    root_svg_assets = sorted(path for path in root_assets_dir.glob("*.svg") if path.is_file())
    root_png_assets = sorted(path for path in root_assets_dir.glob("*.png") if path.is_file())

    source_manifest_path = project_root / "sources" / "source-manifest.json"
    exploration_shortlist_path = project_root / "sources" / "exploration-shortlist.json"
    exploration_ingest_path = project_root / "sources" / "exploration-ingest-manifest.json"
    source_manifest = load_json(source_manifest_path)
    license_summary = source_manifest.get("license_summary") if isinstance(source_manifest.get("license_summary"), dict) else {}
    hold_items = source_manifest.get("hold_items") if isinstance(source_manifest.get("hold_items"), list) else []

    coverage_path = project_root / "sources" / "chapter-coverage-report.json"
    coverage_report = load_json(coverage_path)
    coverage_status = coverage_report.get("overall_status") or "missing"

    prompt_proof_pack_path = project_root / "sources" / "prompt-proof-pack.json"
    graphics_export_manifest = project_root / "assets" / "export-manifest.json"
    scene_asset_plan_path = project_root / "assets" / "scene-asset-plan.json"
    visual_evidence_map_path = project_root / "assets" / "visual-evidence-map.json"
    generation_budget_path = project_root / "assets" / "generation-budget.json"
    minimax_shot_plan_path = project_root / "assets" / "minimax-shot-plan.json"
    generation_ledger_path = project_root / "assets" / "generation-ledger.json"
    visual_diversity_report_path = project_root / "assets" / "visual-diversity-report.json"
    visual_diversity_report = load_json(visual_diversity_report_path)
    workflow_quality_gate_path = project_root / "review" / "workflow-quality-gate.json"
    workflow_quality_gate = load_json(workflow_quality_gate_path)
    voiceover_profile_path = project_root / "content" / "postproduction" / "voiceover-profile.json"
    voiceover_profile = load_json(voiceover_profile_path)
    render_targets = voiceover_profile.get("render_targets") if isinstance(voiceover_profile.get("render_targets"), dict) else {}
    segments_file = render_targets.get("segments_file")
    output_audio = render_targets.get("voiceover_audio")
    subtitle_output = render_targets.get("subtitle_draft")
    minimax_cli = Path("/Users/mac/.codex/skills/minimax-multimodal-toolkit/scripts/tts/generate_voice.sh")
    tts_segments_path = (project_root / segments_file).resolve() if isinstance(segments_file, str) and segments_file else None
    voiceover_output_path = (project_root / output_audio).resolve() if isinstance(output_audio, str) and output_audio else None
    subtitle_output_path = (project_root / subtitle_output).resolve() if isinstance(subtitle_output, str) and subtitle_output else None
    render_manifest_path = project_root / "content" / "postproduction" / "render-manifest.json"
    auto_base_cut_path = project_root / "content" / "postproduction" / "auto-base-cut.mp4"
    auto_base_plan_path = project_root / "content" / "postproduction" / "auto-base-cut-plan.json"
    auto_base_plan = load_json(auto_base_plan_path)
    final_cut_paths = sorted((project_root / "content" / "final-cut").glob("*.mp4"))
    voiceover_completed = bool(voiceover_output_path and voiceover_output_path.exists())
    subtitle_completed = bool(subtitle_output_path and subtitle_output_path.exists())
    render_completed = render_manifest_path.exists() and bool(final_cut_paths)

    project_arg = relative_to_project(project_root, repo_root())
    tasks: list[dict[str, Any]] = []
    tasks.append(
        build_task(
            task_id="footage-sourcing",
            title="自动拉取合法 B-roll",
            status="completed"
            if source_manifest_path.exists() and coverage_status == "pass" and license_summary.get("approved_count", 0) > 0
            else "ready_to_run"
            if source_manifest_path.exists()
            else "required",
            why="B-roll 应由 licensed-footage-sourcing 自动完成，不应靠人工逐段找素材。",
            command=[
                "python3",
                "extensions/skills/licensed-footage-sourcing/scripts/run_external_footage_workflow.py",
                "--project-root",
                project_arg,
                "--providers",
                "auto",
                "--download-approved",
                "--download-exploration",
                "--max-results-per-query",
                "18",
                "--max-shortlist-per-chapter",
                "12",
                "--approved-per-chapter",
                "6",
                "--max-exploration-per-chapter",
                "18",
            ],
            outputs=[
                "sources/source-manifest.json",
                "sources/source-shortlist.json",
                "sources/asset-ingest-manifest.json",
                "sources/exploration-shortlist.json",
                "sources/exploration-ingest-manifest.json",
                "sources/chapter-coverage-report.json",
            ],
            blocking=coverage_status != "pass",
        )
    )
    tasks.append(
        build_task(
            task_id="svg-export",
            title="批量导出图卡和封面 PNG",
            status="completed"
            if graphics_export_manifest.exists() and (png_assets or root_png_assets)
            else "ready_to_run"
            if svg_assets or root_svg_assets
            else "not_applicable",
            why="图卡和封面应走确定性导出，不应人工逐张截图或手动导图。",
            command=[
                "python3",
                "extensions/skills/video-asset-planning/scripts/export_svg_assets.py",
                "--project-root",
                project_arg,
                "--include-root-assets",
            ],
            outputs=[
                "assets/export-manifest.json",
                "assets/graphics/*.png",
                "assets/*.png",
            ],
            blocking=False,
        )
    )
    tasks.append(
        build_task(
            task_id="workflow-quality-gate",
            title="汇总前四项 workflow 质量门禁",
            status="completed" if workflow_quality_gate_path.exists() and workflow_quality_gate.get("overall_status") == "pass" else "ready_to_run",
            why="发布前不应各看各的局部门禁，必须统一汇总 growth / voice / subtitle / visual / scene / budget 状态。",
            command=[
                "python3",
                "extensions/skills/media-ops-orchestration/scripts/build_workflow_quality_gate.py",
                "--project-root",
                project_arg,
            ],
            outputs=[
                "review/workflow-quality-gate.json",
                "review/upgrade-status-board.json",
            ],
            blocking=workflow_quality_gate_path.exists() and workflow_quality_gate.get("overall_status") not in {None, "pass"},
        )
    )
    tasks.append(
        build_task(
            task_id="scene-asset-plan",
            title="生成分章节视觉素材计划",
            status="completed" if scene_asset_plan_path.exists() and visual_evidence_map_path.exists() and generation_budget_path.exists() else "ready_to_run",
            why="每章该用什么证明、什么 B-roll、什么 fallback、哪些镜头允许生成，应先结构化，不再靠临场脑补。",
            command=[
                "python3",
                "extensions/skills/video-asset-planning/scripts/build_scene_asset_plan.py",
                "--project-root",
                project_arg,
            ],
            outputs=[
                "assets/scene-asset-plan.json",
                "assets/visual-evidence-map.json",
                "assets/generation-budget.json",
            ],
            blocking=False,
        )
    )
    tasks.append(
        build_task(
            task_id="visual-diversity-audit",
            title="审计画面多样性与重复素材风险",
            status="completed" if visual_diversity_report_path.exists() and visual_diversity_report.get("status") == "pass" else "ready_to_run",
            why="不能靠同一素材在一个视频里反复顶时长，视觉多样性需要单独门禁。",
            command=[
                "python3",
                "extensions/skills/video-asset-planning/scripts/audit_visual_diversity.py",
                "--project-root",
                project_arg,
            ],
            outputs=[
                "assets/visual-diversity-report.json",
            ],
            blocking=visual_diversity_report_path.exists() and visual_diversity_report.get("status") not in {None, "pass"},
        )
    )
    tasks.append(
        build_task(
            task_id="minimax-shot-plan",
            title="生成 MiniMax 镜头计划与调用台账",
            status="completed" if minimax_shot_plan_path.exists() and generation_ledger_path.exists() else "ready_to_run",
            why="高成本生成镜头必须先过预算门禁，并留下调用台账，不应边做边试。",
            command=[
                "python3",
                "extensions/skills/video-asset-planning/scripts/build_minimax_shot_plan.py",
                "--project-root",
                project_arg,
            ],
            outputs=[
                "assets/minimax-shot-plan.json",
                "assets/generation-ledger.json",
            ],
            blocking=False,
        )
    )
    tasks.append(
        build_task(
            task_id="proof-pack",
            title="用结构化 proof pack 替代人工录屏",
            status="completed" if prompt_proof_pack_path.exists() else "required",
            why="解释型视频的证据层应优先使用结构化 prompt proof + 图卡，不把人工录屏当成默认阻塞项。",
            command=None,
            outputs=["sources/prompt-proof-pack.json", "assets/graphics/card-04-answer-contrast.png"],
            blocking=not prompt_proof_pack_path.exists(),
        )
    )
    tasks.append(
        build_task(
            task_id="voiceover-post",
            title="生成旁白与字幕后期包",
            status="completed"
            if voiceover_completed and subtitle_completed
            else "ready_to_run"
            if tts_segments_path and minimax_cli.exists()
            else voiceover_status,
            why="配音和字幕属于自动化后期链的一部分，不应等到装配时临场补。",
            command=[
                "python3",
                "extensions/skills/minimax-narration-postproduction/scripts/build_tts_handoff.py",
                "--project-root",
                project_arg,
            ] if not tts_segments_path else [
                "bash",
                str(minimax_cli),
                "generate",
                relative_to_project(tts_segments_path, project_root),
                "-o",
                relative_to_project(voiceover_output_path, project_root) if voiceover_output_path else "content/postproduction/minimax-output/voiceover.mp3",
            ],
            outputs=[
                "content/postproduction/*.mp3",
                "content/postproduction/*.srt",
                "content/postproduction/render-plan.json",
            ],
            blocking=voiceover_status not in {"ready", "draft_ready", "pending_sample_check"} and not (tts_segments_path and minimax_cli.exists()),
        )
    )
    tasks.append(
        build_task(
            task_id="render",
            title="跑确定性装配与渲染验证",
            status="completed" if render_completed else "ready_to_run" if assembly_strategy else "required",
            why="特效、字幕、混音和最终编码应由可审计的 render workflow 产出。",
            command=[
                "python3",
                "extensions/skills/video-postproduction-assembly/scripts/run_render_workflow.py",
                "--project-root",
                project_arg,
            ],
            outputs=[
                "content/postproduction/auto-base-cut.mp4",
                "content/postproduction/render-plan.json",
                "content/postproduction/render-manifest.json",
                "review/assembly-qa-report.json",
                "content/final-cut/*.mp4",
            ],
            blocking=assembly_strategy is None,
        )
    )

    notes: list[str] = []
    if hold_items:
        notes.append(f"source manifest 仍有 {len(hold_items)} 个 hold item，需要用自动化 proof lane 或自动素材 runner 消化。")
    if coverage_status != "pass":
        notes.append("chapter coverage gate 还没 pass，自动化素材补齐后需要重跑 coverage 判断。")
    if not prompt_proof_pack_path.exists():
        notes.append("当前包缺少结构化 prompt proof pack，人工录屏已不应再作为默认依赖。")
    if visual_diversity_report.get("status") and visual_diversity_report.get("status") != "pass":
        notes.append("visual diversity gate 还没 pass，需要减少重复素材或补更多章节资产。")
    if workflow_quality_gate.get("overall_status") and workflow_quality_gate.get("overall_status") != "pass":
        notes.append("workflow quality gate 还没 pass，发布前需要先修复 revise / block 维度。")
    notes.append("自治模式下，人工录屏只允许作为 fallback，不应再作为 Production Sprint Phase 1 的默认动作。")
    notes.append("B-roll、图卡导出、后期装配三条链都已有本地 skill 或脚本入口，应先跑自动入口，再看是否需要人工干预。")

    blocking_tasks = [task for task in tasks if task["blocking"] and task["status"] not in {"ready", "draft_ready", "pending_sample_check", "ready_to_run"}]
    if render_completed:
        overall_status = "automation_completed"
    else:
        overall_status = "ready_for_automation" if not blocking_tasks else "needs_followup"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "content_id": content_id,
        "project_root": str(project_root),
        "content_packet_path": relative_to_project(packet_path, project_root),
        "deliverable_type": deliverable_type,
        "assembly_strategy": assembly_strategy,
        "overall_status": overall_status,
        "summary": {
            "graphics_svg_count": len(svg_assets) + len(root_svg_assets),
            "graphics_png_count": len(png_assets) + len(root_png_assets),
            "source_manifest_hold_count": len(hold_items),
            "approved_source_count": license_summary.get("approved_count", 0),
            "chapter_coverage_status": coverage_status,
            "scene_asset_plan_exists": scene_asset_plan_path.exists(),
            "visual_evidence_map_exists": visual_evidence_map_path.exists(),
            "visual_diversity_status": visual_diversity_report.get("status"),
            "approved_generation_slot_count": len(load_json(minimax_shot_plan_path).get("approved_slots", []))
            if minimax_shot_plan_path.exists()
            else 0,
            "generation_budget_exists": generation_budget_path.exists(),
            "workflow_quality_status": workflow_quality_gate.get("overall_status"),
            "voiceover_status": voiceover_status,
            "export_manifest_exists": graphics_export_manifest.exists(),
            "prompt_proof_pack_exists": prompt_proof_pack_path.exists(),
            "voiceover_handoff_exists": voiceover_profile_path.exists(),
            "subtitle_exists": subtitle_completed,
            "render_manifest_exists": render_manifest_path.exists(),
            "final_cut_count": len(final_cut_paths),
            "auto_base_cut_exists": auto_base_cut_path.exists(),
            "auto_base_quality_status": auto_base_plan.get("quality", {}).get("status"),
        },
        "tasks": tasks,
        "notes": notes,
    }

    json_output_path = (project_root / args.json_output).resolve()
    markdown_output_path = (project_root / args.markdown_output).resolve()
    write_json(json_output_path, payload)
    write_markdown(markdown_output_path, payload)
    print(
        json.dumps(
            {
                "json_output": str(json_output_path),
                "markdown_output": str(markdown_output_path),
                "overall_status": overall_status,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
