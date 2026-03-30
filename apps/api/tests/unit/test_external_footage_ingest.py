"""Tests for external footage sourcing and ingestion workflow."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def run_command(command: list[str], workdir: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(command, cwd=workdir, check=True, capture_output=True, text=True, env=merged_env)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_midlong_package(project_root: Path) -> None:
    (project_root / "content").mkdir(parents=True, exist_ok=True)
    (project_root / "sources").mkdir(parents=True, exist_ok=True)
    write_json(
        project_root / "content" / "bilibili-midform-video.json",
        {
            "content_id": project_root.name,
            "platforms": ["bilibili"],
            "deliverable_type": "midlong-video",
            "clip_sourcing_brief": [
                {
                    "chapter_id": "ch1",
                    "shot_intent": "表现 AI 工具普及和使用门槛下降",
                    "required_coverage_seconds": 8,
                    "minimum_candidates": 1,
                    "queries": [
                        "office worker using ai on computer",
                        "laptop with generative ai assistant",
                    ],
                    "source_types": ["stock-library"],
                    "fallback": "自录 AI 对话界面和 UI 动效",
                },
                {
                    "chapter_id": "ch2",
                    "shot_intent": "表现答案看起来很完整但未必可靠",
                    "required_coverage_seconds": 8,
                    "minimum_candidates": 1,
                    "queries": [
                        "generated text scrolling on screen",
                    ],
                    "source_types": ["stock-library"],
                    "fallback": "字幕高亮和批注动画",
                },
            ],
        },
    )


def make_ytdlp_package(project_root: Path) -> None:
    (project_root / "content").mkdir(parents=True, exist_ok=True)
    (project_root / "sources").mkdir(parents=True, exist_ok=True)
    write_json(
        project_root / "content" / "bilibili-midform-video.json",
        {
            "content_id": project_root.name,
            "platforms": ["bilibili"],
            "deliverable_type": "midlong-video",
            "clip_sourcing_brief": [
                {
                    "chapter_id": "ch-official",
                    "shot_intent": "补充官方公开视频素材",
                    "required_coverage_seconds": 10,
                    "minimum_candidates": 1,
                    "queries": [],
                    "direct_source_urls": [
                        "https://video.example.test/watch/official-demo",
                    ],
                    "source_types": ["official-promo-footage"],
                    "fallback": "改用自制图卡和品牌录屏",
                }
            ],
        },
    )


def build_mock_catalog(root: Path) -> None:
    videos = root / "videos"
    videos.mkdir(parents=True, exist_ok=True)

    video_one = videos / "office-ai.mp4"
    video_two = videos / "generated-text.mp4"
    video_one.write_bytes(b"mock-office-ai-video")
    video_two.write_bytes(b"mock-generated-text-video")

    write_json(
        root / "catalog.json",
        {
            "results": [
                {
                    "id": "mock-pexels-001",
                    "title": "Office worker using AI",
                    "page_url": "https://example.test/videos/mock-pexels-001",
                    "download_url": video_one.as_uri(),
                    "preview_image_url": "https://example.test/thumbs/mock-pexels-001.jpg",
                    "duration_seconds": 9,
                    "width": 1920,
                    "height": 1080,
                    "tags": ["office", "ai"],
                },
                {
                    "id": "mock-pexels-002",
                    "title": "Generated text scrolling",
                    "page_url": "https://example.test/videos/mock-pexels-002",
                    "download_url": video_two.as_uri(),
                    "preview_image_url": "https://example.test/thumbs/mock-pexels-002.jpg",
                    "duration_seconds": 11,
                    "width": 1920,
                    "height": 1080,
                    "tags": ["screen", "text"],
                },
            ]
        },
    )


def build_mock_ytdlp_bin(root: Path) -> tuple[Path, Path]:
    script_path = root / "mock-yt-dlp.py"
    fixture_path = root / "official-demo.mp4"
    fixture_path.write_bytes(b"mock-ytdlp-video")
    script_path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import json",
                "import sys",
                "from pathlib import Path",
                "",
                f"fixture = Path({str(fixture_path)!r})",
                "args = sys.argv[1:]",
                "if '--dump-single-json' in args:",
                "    print(json.dumps({",
                "        'id': 'official-demo-001',",
                "        'title': 'Official Product Demo',",
                "        'webpage_url': args[-1],",
                "        'duration': 14,",
                "        'width': 1920,",
                "        'height': 1080,",
                "        'uploader': 'Official Channel',",
                "        'uploader_url': 'https://video.example.test/channel/official',",
                "        'thumbnail': 'https://video.example.test/thumb.jpg'",
                "    }))",
                "    raise SystemExit(0)",
                "output = Path(args[args.index('-o') + 1])",
                "output.parent.mkdir(parents=True, exist_ok=True)",
                "output.write_bytes(fixture.read_bytes())",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    script_path.chmod(0o755)
    return script_path, fixture_path


def test_run_external_footage_workflow_searches_and_ingests_assets(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "licensed-footage-sourcing"
        / "scripts"
        / "run_external_footage_workflow.py"
    )

    project_root = tmp_path / "2026-03-28-bilibili-footage-ingest"
    make_midlong_package(project_root)

    mock_root = tmp_path / "mock-provider"
    build_mock_catalog(mock_root)
    completed = run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
            "--providers",
            "mock-stock",
            "--download-approved",
            "--download-limit",
            "2",
        ],
        repo_root,
        env={
            "MOCK_STOCK_CATALOG_PATH": str(mock_root / "catalog.json"),
        },
    )

    payload = json.loads(completed.stdout)
    assert payload["provider_summary"]["mock-stock"]["queries_attempted"] == 3
    assert payload["provider_summary"]["mock-stock"]["results_found"] >= 2

    source_manifest_path = project_root / "sources" / "source-manifest.json"
    shortlist_path = project_root / "sources" / "source-shortlist.json"
    ingest_manifest_path = project_root / "sources" / "asset-ingest-manifest.json"
    coverage_report_path = project_root / "sources" / "chapter-coverage-report.json"
    query_sheet_path = project_root / "sources" / "clip-query-sheet.md"

    assert source_manifest_path.exists()
    assert shortlist_path.exists()
    assert ingest_manifest_path.exists()
    assert coverage_report_path.exists()
    assert query_sheet_path.exists()

    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    ingest_manifest = json.loads(ingest_manifest_path.read_text(encoding="utf-8"))
    shortlist = json.loads(shortlist_path.read_text(encoding="utf-8"))
    coverage_report = json.loads(coverage_report_path.read_text(encoding="utf-8"))

    assert len(source_manifest["clip_queries"]) == 2
    assert source_manifest["license_summary"]["approved_count"] >= 2
    assert shortlist["results"][0]["provider"] == "mock-stock"
    assert len(ingest_manifest["ingested_assets"]) == 2
    assert coverage_report["overall_status"] == "pass"
    assert all(item["status"] == "pass" for item in coverage_report["chapters"])

    first_asset = ingest_manifest["ingested_assets"][0]
    local_asset_path = project_root / first_asset["local_path"]
    assert local_asset_path.exists()
    assert local_asset_path.read_bytes() in {b"mock-office-ai-video", b"mock-generated-text-video"}
    assert "office worker using ai on computer" in query_sheet_path.read_text(encoding="utf-8")


def test_run_external_footage_workflow_ingests_direct_ytdlp_sources(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "licensed-footage-sourcing"
        / "scripts"
        / "run_external_footage_workflow.py"
    )

    project_root = tmp_path / "2026-03-28-bilibili-ytdlp-ingest"
    make_ytdlp_package(project_root)
    ytdlp_bin, _ = build_mock_ytdlp_bin(tmp_path)

    completed = run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
            "--providers",
            "yt-dlp",
            "--download-approved",
            "--download-limit",
            "1",
            "--yt-dlp-bin",
            str(ytdlp_bin),
        ],
        repo_root,
    )

    payload = json.loads(completed.stdout)
    assert payload["provider_summary"]["yt-dlp"]["queries_attempted"] == 1
    assert payload["provider_summary"]["yt-dlp"]["results_found"] == 1
    assert payload["approved_count"] == 1
    assert payload["ingested_count"] == 1

    source_manifest = json.loads((project_root / "sources" / "source-manifest.json").read_text(encoding="utf-8"))
    ingest_manifest = json.loads((project_root / "sources" / "asset-ingest-manifest.json").read_text(encoding="utf-8"))
    coverage_report = json.loads((project_root / "sources" / "chapter-coverage-report.json").read_text(encoding="utf-8"))

    assert source_manifest["source_manifest"][0]["source_name"] == "yt-dlp"
    assert source_manifest["source_manifest"][0]["license_status"] == "approved"
    assert source_manifest["source_manifest"][0]["uploader"] == "Official Channel"
    assert coverage_report["overall_status"] == "pass"
    local_path = project_root / ingest_manifest["ingested_assets"][0]["local_path"]
    assert local_path.exists()
    assert local_path.read_bytes() == b"mock-ytdlp-video"
