#!/usr/bin/env python3
"""Build a render plan from a media package."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


DEFAULT_SUBTITLE_STYLE = (
    "FontName=Arial Unicode MS,FontSize=18,PrimaryColour=&H00FFFFFF,"
    "OutlineColour=&H00000000,Outline=2,Shadow=0,MarginV=32"
)
NARRATED_KEYWORDS = ("narrated", "subtitle", "subtitles", "voiceover", "dubbed", "tts")
SOUND_DESIGN_KEYWORDS = (
    {
        "label": "hook_statement",
        "keywords": ("什么都知道，就是不敢决定", "不敢决定"),
        "preset": "impact_hit",
        "gain_db": -14.0,
        "min_start_seconds": 0.0,
        "max_start_seconds": 30.0,
    },
    {
        "label": "framework_reveal",
        "keywords": ("四步框架",),
        "preset": "whoosh_riser",
        "gain_db": -17.0,
        "min_start_seconds": 60.0,
    },
    {
        "label": "stop_signal_list",
        "keywords": ("三个停手信号", "停手信号"),
        "preset": "impact_hit",
        "gain_db": -15.0,
        "min_start_seconds": 90.0,
    },
)


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def relative_to_root(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def serialize_path(path: Path, root: Path) -> str:
    try:
        return relative_to_root(path, root)
    except ValueError:
        return str(path.resolve())


def resolve_candidate(root: Path, raw_path: str | None) -> Path | None:
    if not raw_path:
        return None
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate.resolve()


def existing_path(root: Path, raw_path: str | None) -> Path | None:
    candidate = resolve_candidate(root, raw_path)
    if candidate is None or not candidate.exists():
        return None
    return candidate


def find_first_existing(paths: list[Path | None]) -> Path | None:
    for path in paths:
        if path is not None and path.exists():
            return path
    return None


def find_voiceover_profile(project_root: Path) -> Path | None:
    candidate = project_root / "content" / "postproduction" / "voiceover-profile.json"
    return candidate if candidate.exists() else None


def find_content_packet(project_root: Path) -> Path | None:
    content_dir = project_root / "content"
    json_files = sorted(content_dir.glob("*video.json"))
    return json_files[0] if json_files else None


def parse_srt_entries(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []

    entries: list[dict[str, Any]] = []
    for block in re.split(r"\n\s*\n", text):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3:
            continue
        start_raw, end_raw = lines[1].split(" --> ", maxsplit=1)
        entries.append(
            {
                "start_seconds": srt_timestamp_seconds(start_raw),
                "end_seconds": srt_timestamp_seconds(end_raw),
                "text": " ".join(lines[2:]),
            }
        )
    return entries


def srt_timestamp_seconds(value: str) -> float:
    hours, minutes, seconds_millis = value.split(":")
    seconds, millis = seconds_millis.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000


def first_matching_subtitle_time(
    entries: list[dict[str, Any]],
    *,
    keywords: tuple[str, ...],
    min_start_seconds: float = 0.0,
    max_start_seconds: float | None = None,
) -> float | None:
    fallback_match: float | None = None
    for entry in entries:
        start_seconds = float(entry["start_seconds"])
        if max_start_seconds is not None and start_seconds > max_start_seconds:
            continue
        text = str(entry["text"])
        if not any(keyword in text for keyword in keywords):
            continue
        if fallback_match is None:
            fallback_match = round(start_seconds, 3)
        if start_seconds >= min_start_seconds:
            return round(start_seconds, 3)
    return fallback_match


def default_bgm_asset() -> Path | None:
    candidates = [
        repo_root() / "remotion" / "public" / "bgm-techno.mp3",
        repo_root() / "remotion" / "public" / "bgm-deep-urban.mp3",
    ]
    return find_first_existing(candidates)


def build_sound_design_mix(
    *,
    project_root: Path,
    subtitles: Path | None,
    deliverable_type: str | None,
    mix_defaults: dict[str, Any],
) -> dict[str, Any]:
    if deliverable_type != "midlong-video":
        return {}

    bgm_asset = default_bgm_asset()
    subtitle_entries = parse_srt_entries(subtitles)
    estimated_duration = float(subtitle_entries[-1]["end_seconds"]) if subtitle_entries else 0.0

    bgm_tracks: list[dict[str, Any]] = []
    if bgm_asset is not None:
        hook_window_seconds = round(min(30.0, estimated_duration or 30.0), 3)
        hook_gain_db = max(float(mix_defaults.get("bgm_target_db", -26.0)), -24.0)
        bgm_tracks.append(
            {
                "path": serialize_path(bgm_asset, project_root),
                "role": "hook_bed",
                "start_seconds": 0.0,
                "end_seconds": hook_window_seconds,
                "gain_db": hook_gain_db,
                "loop": True,
                "fade_in_seconds": 0.25,
                "fade_out_seconds": 1.2,
            }
        )

    sfx_cues: list[dict[str, Any]] = []
    for cue_spec in SOUND_DESIGN_KEYWORDS:
        cue_time = first_matching_subtitle_time(
            subtitle_entries,
            keywords=tuple(cue_spec["keywords"]),
            min_start_seconds=float(cue_spec.get("min_start_seconds", 0.0)),
            max_start_seconds=float(cue_spec["max_start_seconds"]) if cue_spec.get("max_start_seconds") is not None else None,
        )
        if cue_time is None:
            continue
        sfx_cues.append(
            {
                "label": str(cue_spec["label"]),
                "preset": str(cue_spec["preset"]),
                "start_seconds": cue_time,
                "gain_db": float(cue_spec["gain_db"]),
            }
        )

    if not bgm_tracks and not sfx_cues:
        return {}

    return {
        "bg_sidechain_ducking": True,
        "bg_sidechain_threshold": 0.018,
        "bg_sidechain_ratio": 10,
        "bg_sidechain_attack_ms": 15,
        "bg_sidechain_release_ms": 260,
        "bgm_tracks": bgm_tracks,
        "sfx_cues": sfx_cues,
    }


def parse_source_video_from_verification(project_root: Path) -> Path | None:
    review_dir = project_root / "review"
    if not review_dir.exists():
        return None

    pattern = re.compile(r"content/final-cut/[^\s`]+\.mp4")
    matches: list[Path] = []
    for path in sorted(review_dir.glob("render-verification*.md")):
        text = path.read_text(encoding="utf-8")
        for match in pattern.findall(text):
            candidate = (project_root / match).resolve()
            if candidate.exists() and candidate not in matches:
                matches.append(candidate)

    filtered = [path for path in matches if not any(keyword in path.name.lower() for keyword in NARRATED_KEYWORDS)]
    if filtered:
        return filtered[0]
    return matches[0] if matches else None


def source_video_score(path: Path) -> tuple[int, int, int, str]:
    name = path.stem.lower()
    score = 100
    if "rough" in name:
        score -= 40
    if "draft" in name:
        score -= 20
    if "final" in name:
        score += 15
    if any(keyword in name for keyword in NARRATED_KEYWORDS):
        score += 50

    version_match = re.search(r"-v(\d+)$", name)
    version = int(version_match.group(1)) if version_match else 99
    score += version * 2
    return (score, version, len(name), path.name)


def detect_source_video(project_root: Path, override: str | None) -> Path:
    explicit = existing_path(project_root, override)
    if explicit is not None:
        return explicit

    from_verification = parse_source_video_from_verification(project_root)
    if from_verification is not None:
        return from_verification

    final_cut_dir = project_root / "content" / "final-cut"
    candidates = sorted(final_cut_dir.glob("*.mp4"))
    if not candidates:
        raise FileNotFoundError(f"No source video found under {final_cut_dir}")

    return min(candidates, key=source_video_score)


def derive_output_video(source_video: Path, project_root: Path, content_id: str) -> Path:
    stem = source_video.stem
    suffix = source_video.suffix

    final_cut_dir = (project_root / "content" / "final-cut").resolve()
    try:
        source_video.resolve().relative_to(final_cut_dir)
    except ValueError:
        final_cut_dir.mkdir(parents=True, exist_ok=True)
        return final_cut_dir / f"{content_id}-v1-narrated{suffix}"

    version_match = re.search(r"^(?P<prefix>.+)-v(?P<version>\d+)$", stem)
    if version_match:
        prefix = version_match.group("prefix")
        version = int(version_match.group("version")) + 1
        return source_video.with_name(f"{prefix}-v{version}-narrated{suffix}")

    if stem.endswith("-rough"):
        return source_video.with_name(f"{stem.removesuffix('-rough')}-narrated{suffix}")
    if stem.endswith("-draft"):
        return source_video.with_name(f"{stem.removesuffix('-draft')}-narrated{suffix}")
    if stem.endswith("-final"):
        return source_video.with_name(f"{stem.removesuffix('-final')}-narrated{suffix}")
    if any(keyword in stem.lower() for keyword in NARRATED_KEYWORDS):
        return source_video
    return source_video.with_name(f"{stem}-narrated{suffix}")


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
    args = parser.parse_args()
    if not args.project_root and not args.content_id:
        parser.error("one of --project-root or --content-id is required")
    return args


def run_command(command: list[str]) -> None:
    subprocess.run(command, check=True, capture_output=True, text=True)


def default_media_ops_root() -> Path:
    return Path(__file__).resolve().parents[4] / "data" / "media-ops"


def resolve_project_root(args: argparse.Namespace) -> Path:
    if args.project_root:
        return Path(args.project_root).resolve()

    media_ops_root = Path(args.media_ops_root).resolve() if args.media_ops_root else default_media_ops_root().resolve()
    return (media_ops_root / args.content_id).resolve()


def ensure_subtitles(
    project_root: Path,
    *,
    requested_subtitles: str | None,
    render_targets: dict[str, Any],
) -> Path | None:
    existing = find_first_existing(
        [
            existing_path(project_root, requested_subtitles),
            existing_path(project_root, render_targets.get("subtitle_draft")),
            *sorted((project_root / "content" / "postproduction").glob("*.srt")),
        ]
    )
    if existing is not None:
        return existing

    output_path = resolve_candidate(project_root, requested_subtitles) or resolve_candidate(
        project_root, render_targets.get("subtitle_draft")
    )
    if output_path is None:
        output_path = (project_root / "content" / "postproduction" / "subtitles.srt").resolve()

    subtitle_builder = (
        repo_root()
        / "extensions"
        / "skills"
        / "minimax-narration-postproduction"
        / "scripts"
        / "build_subtitles_from_segments.py"
    )
    if not subtitle_builder.exists():
        return None

    command = [
        sys.executable,
        str(subtitle_builder),
        "--project-root",
        str(project_root),
        "--output",
        relative_to_root(output_path, project_root),
    ]
    run_command(command)
    return output_path if output_path.exists() else None


def ensure_source_video(
    project_root: Path,
    *,
    requested_source_video: str | None,
    assembly_strategy: str,
    voiceover_audio: Path,
    subtitles: Path | None,
) -> Path:
    auto_base_cut = (project_root / "content" / "postproduction" / "auto-base-cut.mp4").resolve()
    if assembly_strategy == "rebuild_timeline" and requested_source_video is None and auto_base_cut.exists():
        return auto_base_cut

    try:
        return detect_source_video(project_root, requested_source_video)
    except FileNotFoundError:
        if assembly_strategy != "rebuild_timeline":
            raise

    visual_builder = Path(__file__).with_name("build_visual_timeline.py")
    if not visual_builder.exists():
        raise FileNotFoundError("No source video found and build_visual_timeline.py is unavailable.")

    output_path = auto_base_cut
    command = [
        sys.executable,
        str(visual_builder),
        "--project-root",
        str(project_root),
        "--voiceover-audio",
        relative_to_root(voiceover_audio, project_root),
        "--output-video",
        relative_to_root(output_path, project_root),
    ]
    if subtitles is not None and subtitles.exists():
        command.extend(["--subtitles", relative_to_root(subtitles, project_root)])
    run_command(command)
    if not output_path.exists():
        raise FileNotFoundError(f"Auto-built source video missing after rebuild_timeline step: {output_path}")
    return output_path


def build_render_plan(args: argparse.Namespace) -> tuple[dict[str, Any], Path]:
    project_root = resolve_project_root(args)
    if not project_root.exists():
        raise FileNotFoundError(f"Project root does not exist: {project_root}")

    voiceover_profile_path = find_voiceover_profile(project_root)
    voiceover_profile = load_json(voiceover_profile_path)
    content_packet_path = find_content_packet(project_root)
    content_packet = load_json(content_packet_path)
    primary_packet = content_packet.get("content_packet") if isinstance(content_packet.get("content_packet"), dict) else content_packet
    render_targets = voiceover_profile.get("render_targets", {})
    mix_defaults = voiceover_profile.get("mix_defaults", {})
    content_id = voiceover_profile.get("content_id") or primary_packet.get("content_id") or project_root.name
    assembly_strategy = args.assembly_strategy or primary_packet.get("assembly_strategy") or "retime_existing_cut"

    voiceover_audio = find_first_existing(
        [
            existing_path(project_root, args.voiceover_audio),
            existing_path(project_root, render_targets.get("voiceover_audio")),
            *sorted((project_root / "content" / "postproduction" / "minimax-output").glob("*.mp3")),
        ]
    )
    if voiceover_audio is None:
        raise FileNotFoundError("Unable to locate voiceover audio for render plan.")

    subtitles = ensure_subtitles(
        project_root,
        requested_subtitles=args.subtitles,
        render_targets=render_targets,
    )
    if subtitles is None:
        raise FileNotFoundError("Unable to locate subtitles for render plan.")

    source_video = ensure_source_video(
        project_root,
        requested_source_video=args.source_video,
        assembly_strategy=assembly_strategy,
        voiceover_audio=voiceover_audio,
        subtitles=subtitles,
    )
    output_video = resolve_candidate(project_root, args.output_video) or derive_output_video(
        source_video,
        project_root,
        content_id,
    )
    render_plan_output = resolve_candidate(project_root, args.render_plan_output)
    render_manifest_output = resolve_candidate(project_root, args.render_manifest_output)
    verification_output = resolve_candidate(project_root, args.verification_output)
    qa_report_output = resolve_candidate(project_root, args.qa_report_output)

    if render_plan_output is None or render_manifest_output is None or verification_output is None or qa_report_output is None:
        raise ValueError("Render output paths must resolve to concrete filesystem paths.")

    render_plan_output.parent.mkdir(parents=True, exist_ok=True)
    render_manifest_output.parent.mkdir(parents=True, exist_ok=True)
    verification_output.parent.mkdir(parents=True, exist_ok=True)
    qa_report_output.parent.mkdir(parents=True, exist_ok=True)
    output_video.parent.mkdir(parents=True, exist_ok=True)

    platforms = primary_packet.get("platforms") or ([voiceover_profile.get("platform")] if voiceover_profile.get("platform") else [])
    mix_plan = {
        "retain_original_audio": not args.no_retain_original_audio,
        "original_audio_gain_db": mix_defaults.get("bgm_target_db", mix_defaults.get("ducking_target_db", -24)),
        "voiceover_gain_db": 0,
        "voiceover_delay_ms": 0,
    }
    mix_plan.update(
        build_sound_design_mix(
            project_root=project_root,
            subtitles=subtitles,
            deliverable_type=primary_packet.get("deliverable_type"),
            mix_defaults=mix_defaults,
        )
    )
    plan = {
        "workspace_root": str(project_root),
        "content_id": content_id,
        "platforms": platforms,
        "deliverable_type": primary_packet.get("deliverable_type"),
        "source_video": relative_to_root(source_video, project_root),
        "voiceover_audio": relative_to_root(voiceover_audio, project_root),
        "subtitles": relative_to_root(subtitles, project_root),
        "output_video": relative_to_root(output_video, project_root),
        "render_manifest_output": relative_to_root(render_manifest_output, project_root),
        "verification_output": relative_to_root(verification_output, project_root),
        "qa_report_output": relative_to_root(qa_report_output, project_root),
        "assembly_strategy": assembly_strategy,
        "retime": {
            "mode": "auto_match_voiceover",
            "allow_slowdown": args.allow_slowdown,
            "max_speedup": args.max_speedup,
        },
        "qa": {
            "freeze_threshold_seconds": 2.5,
            "max_static_hold_seconds": 8.0 if assembly_strategy == "rebuild_timeline" else 2.5,
            "max_duration_alignment_error_seconds": 0.35,
            "subtitle_alignment_noise_db": "-35dB",
            "subtitle_alignment_min_silence_seconds": 0.12,
            "subtitle_alignment_max_boundary_drift_seconds": 0.45,
            "subtitle_alignment_min_matched_ratio": 0.72,
            "episodic_outro_patterns": [
                "下一条继续讲",
                "下一期继续讲",
                "下期继续讲",
                "下集见",
                "下期见",
            ],
        },
        "mix": mix_plan,
        "subtitle_style": DEFAULT_SUBTITLE_STYLE,
        "context": {
            "voiceover_profile": relative_to_root(voiceover_profile_path, project_root) if voiceover_profile_path else None,
            "content_packet": relative_to_root(content_packet_path, project_root) if content_packet_path else None,
            "mix_notes": "content/postproduction/mix-notes.md"
            if (project_root / "content" / "postproduction" / "mix-notes.md").exists()
            else None,
        },
    }
    return plan, render_plan_output


def main() -> int:
    args = parse_args()
    plan, render_plan_output = build_render_plan(args)
    render_plan_output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"render_plan": str(render_plan_output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
