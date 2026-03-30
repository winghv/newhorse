#!/usr/bin/env python3
"""Export project SVG assets to PNG using Playwright screenshots."""

from __future__ import annotations

import argparse
import json
import subprocess
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
        "--viewport-size",
        default="1920,1080",
        help="Playwright viewport size as WIDTH,HEIGHT. Defaults to 1920,1080.",
    )
    parser.add_argument(
        "--include-root-assets",
        action="store_true",
        help="Also export SVG files directly under assets/, not just assets/graphics.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-export even when the target PNG already exists and is newer than the SVG.",
    )
    parser.add_argument(
        "--manifest-output",
        default="assets/export-manifest.json",
        help="Output path for the export manifest, relative to the project root.",
    )
    parser.add_argument(
        "--browser",
        default="chromium",
        help="Browser passed to Playwright screenshot. Defaults to chromium.",
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


def relative_to_project(path: Path, project_root: Path) -> str:
    return str(path.resolve().relative_to(project_root.resolve()))


def find_svg_assets(project_root: Path, include_root_assets: bool) -> list[Path]:
    candidates: list[Path] = []
    graphics_dir = project_root / "assets" / "graphics"
    if graphics_dir.exists():
        candidates.extend(sorted(path for path in graphics_dir.rglob("*.svg") if path.is_file()))

    if include_root_assets:
        assets_root = project_root / "assets"
        if assets_root.exists():
            root_svgs = [
                path
                for path in assets_root.glob("*.svg")
                if path.is_file()
            ]
            candidates.extend(sorted(root_svgs))
            final_cover_dir = assets_root / "final-cover"
            if final_cover_dir.exists():
                candidates.extend(sorted(path for path in final_cover_dir.rglob("*.svg") if path.is_file()))

    deduped: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(resolved)
    return deduped


def needs_export(svg_path: Path, png_path: Path, force: bool) -> bool:
    if force or not png_path.exists():
        return True
    return svg_path.stat().st_mtime > png_path.stat().st_mtime


def export_svg(svg_path: Path, png_path: Path, viewport_size: str, browser: str) -> None:
    png_path.parent.mkdir(parents=True, exist_ok=True)
    file_url = svg_path.resolve().as_uri()
    subprocess.run(
        [
            "npx",
            "playwright",
            "screenshot",
            f"--browser={browser}",
            f"--viewport-size={viewport_size}",
            file_url,
            str(png_path.resolve()),
        ],
        check=True,
    )


def write_manifest(project_root: Path, manifest_output: str, payload: dict[str, Any]) -> Path:
    output_path = (project_root / manifest_output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)
    svg_assets = find_svg_assets(project_root, include_root_assets=args.include_root_assets)

    exports: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for svg_path in svg_assets:
        png_path = svg_path.with_suffix(".png")
        record = {
            "source_path": relative_to_project(svg_path, project_root),
            "output_path": relative_to_project(png_path, project_root),
        }
        if needs_export(svg_path, png_path, force=args.force):
            export_svg(svg_path, png_path, args.viewport_size, args.browser)
            record["status"] = "exported"
            exports.append(record)
        else:
            record["status"] = "skipped_up_to_date"
            skipped.append(record)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(project_root),
        "viewport_size": args.viewport_size,
        "browser": args.browser,
        "exported_count": len(exports),
        "skipped_count": len(skipped),
        "exports": exports + skipped,
    }
    manifest_path = write_manifest(project_root, args.manifest_output, payload)
    print(json.dumps({"manifest_path": str(manifest_path), "exported_count": len(exports), "skipped_count": len(skipped)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
