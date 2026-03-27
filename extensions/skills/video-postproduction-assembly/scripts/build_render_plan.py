#!/usr/bin/env python3
"""Build a render plan from a media package."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_SUBTITLE_STYLE = (
    "FontName=Arial Unicode MS,FontSize=18,PrimaryColour=&H00FFFFFF,"
    "OutlineColour=&H00000000,Outline=2,Shadow=0,MarginV=32"
)
NARRATED_KEYWORDS = ("narrated", "subtitle", "subtitles", "voiceover", "dubbed", "tts")


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def relative_to_root(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


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


def derive_output_video(source_video: Path) -> Path:
    stem = source_video.stem
    suffix = source_video.suffix

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
        "--assembly-strategy",
        default="retime_existing_cut",
        choices=["retime_existing_cut", "rebuild_timeline", "review_only"],
        help="Assembly strategy to record in the render plan.",
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


def default_media_ops_root() -> Path:
    return Path(__file__).resolve().parents[4] / "data" / "media-ops"


def resolve_project_root(args: argparse.Namespace) -> Path:
    if args.project_root:
        return Path(args.project_root).resolve()

    media_ops_root = Path(args.media_ops_root).resolve() if args.media_ops_root else default_media_ops_root().resolve()
    return (media_ops_root / args.content_id).resolve()


def build_render_plan(args: argparse.Namespace) -> tuple[dict[str, Any], Path]:
    project_root = resolve_project_root(args)
    if not project_root.exists():
        raise FileNotFoundError(f"Project root does not exist: {project_root}")

    voiceover_profile_path = find_voiceover_profile(project_root)
    voiceover_profile = load_json(voiceover_profile_path)
    content_packet_path = find_content_packet(project_root)
    content_packet = load_json(content_packet_path)
    render_targets = voiceover_profile.get("render_targets", {})
    mix_defaults = voiceover_profile.get("mix_defaults", {})

    source_video = detect_source_video(project_root, args.source_video)
    voiceover_audio = find_first_existing(
        [
            existing_path(project_root, args.voiceover_audio),
            existing_path(project_root, render_targets.get("voiceover_audio")),
            *sorted((project_root / "content" / "postproduction" / "minimax-output").glob("*.mp3")),
        ]
    )
    subtitles = find_first_existing(
        [
            existing_path(project_root, args.subtitles),
            existing_path(project_root, render_targets.get("subtitle_draft")),
            *sorted((project_root / "content" / "postproduction").glob("*.srt")),
        ]
    )

    if voiceover_audio is None:
        raise FileNotFoundError("Unable to locate voiceover audio for render plan.")
    if subtitles is None:
        raise FileNotFoundError("Unable to locate subtitles for render plan.")

    output_video = resolve_candidate(project_root, args.output_video) or derive_output_video(source_video)
    render_plan_output = resolve_candidate(project_root, args.render_plan_output)
    render_manifest_output = resolve_candidate(project_root, args.render_manifest_output)
    verification_output = resolve_candidate(project_root, args.verification_output)

    if render_plan_output is None or render_manifest_output is None or verification_output is None:
        raise ValueError("Render output paths must resolve to concrete filesystem paths.")

    render_plan_output.parent.mkdir(parents=True, exist_ok=True)
    render_manifest_output.parent.mkdir(parents=True, exist_ok=True)
    verification_output.parent.mkdir(parents=True, exist_ok=True)
    output_video.parent.mkdir(parents=True, exist_ok=True)

    platforms = content_packet.get("platforms") or ([voiceover_profile.get("platform")] if voiceover_profile.get("platform") else [])
    plan = {
        "workspace_root": str(project_root),
        "content_id": voiceover_profile.get("content_id", project_root.name),
        "platforms": platforms,
        "deliverable_type": content_packet.get("deliverable_type"),
        "source_video": relative_to_root(source_video, project_root),
        "voiceover_audio": relative_to_root(voiceover_audio, project_root),
        "subtitles": relative_to_root(subtitles, project_root),
        "output_video": relative_to_root(output_video, project_root),
        "render_manifest_output": relative_to_root(render_manifest_output, project_root),
        "verification_output": relative_to_root(verification_output, project_root),
        "assembly_strategy": args.assembly_strategy,
        "retime": {
            "mode": "auto_match_voiceover",
            "allow_slowdown": args.allow_slowdown,
            "max_speedup": args.max_speedup,
        },
        "mix": {
            "retain_original_audio": not args.no_retain_original_audio,
            "original_audio_gain_db": mix_defaults.get("bgm_target_db", mix_defaults.get("ducking_target_db", -24)),
            "voiceover_gain_db": 0,
            "voiceover_delay_ms": 0,
        },
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
