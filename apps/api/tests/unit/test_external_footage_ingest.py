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


def make_dense_midlong_package(project_root: Path) -> None:
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
                    "shot_intent": "需要更丰富的中视频 B-roll 候选池",
                    "required_coverage_seconds": 12,
                    "minimum_candidates": 3,
                    "queries": [
                        "office worker using ai on computer",
                    ],
                    "source_types": ["stock-library"],
                    "fallback": "自录操作和图卡穿插",
                }
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


def make_ytdlp_search_package(project_root: Path) -> None:
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
                    "shot_intent": "找更丰富的键盘、屏幕和办公桌 B-roll",
                    "required_coverage_seconds": 8,
                    "minimum_candidates": 2,
                    "queries": [
                        "keyboard desk setup",
                        "typing on laptop screen",
                    ],
                    "source_types": ["stock-library"],
                    "fallback": "UI 录屏和字幕打点",
                }
            ],
        },
    )


def make_provider_specific_query_package(project_root: Path) -> None:
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
                    "shot_intent": "按 provider 分开搜词，yt-dlp 应该搜更视觉化的镜头描述。",
                    "required_coverage_seconds": 8,
                    "minimum_candidates": 1,
                    "queries": [
                        "keyboard desk setup",
                        "typing on laptop screen",
                    ],
                    "provider_queries": {
                        "yt-dlp": [
                            "cinematic keyboard desk b roll",
                        ]
                    },
                    "source_types": ["stock-library"],
                    "fallback": "UI 录屏和字幕打点",
                }
            ],
        },
    )


def build_mock_catalog(root: Path, *, extra_results: int = 0) -> None:
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
            + [
                {
                    "id": f"mock-pexels-extra-{index + 1:03d}",
                    "title": f"Office worker using AI on computer variant {index + 1}",
                    "page_url": f"https://example.test/videos/mock-pexels-extra-{index + 1:03d}",
                    "download_url": video_one.as_uri(),
                    "preview_image_url": f"https://example.test/thumbs/mock-pexels-extra-{index + 1:03d}.jpg",
                    "duration_seconds": 8 + index,
                    "width": 1920,
                    "height": 1080,
                    "tags": ["office", "worker", "using", "ai", "computer", f"variant-{index + 1}"],
                }
                for index in range(extra_results)
            ],
        },
    )


def build_search_catalog(root: Path) -> None:
    videos = root / "videos"
    videos.mkdir(parents=True, exist_ok=True)
    desk_video = videos / "keyboard-desk-setup.mp4"
    typing_video = videos / "typing-on-laptop.mp4"
    desk_video.write_bytes(b"mock-keyboard-desk-video")
    typing_video.write_bytes(b"mock-typing-laptop-video")
    write_json(
        root / "catalog.json",
        {
            "results": [
                {
                    "id": "search-mock-001",
                    "title": "Keyboard desk setup with laptop screen",
                    "page_url": "https://example.test/videos/search-mock-001",
                    "download_url": desk_video.as_uri(),
                    "preview_image_url": "https://example.test/thumbs/search-mock-001.jpg",
                    "duration_seconds": 9,
                    "width": 1920,
                    "height": 1080,
                    "tags": ["keyboard", "desk", "setup", "laptop", "screen"],
                },
                {
                    "id": "search-mock-002",
                    "title": "Typing on laptop screen close up",
                    "page_url": "https://example.test/videos/search-mock-002",
                    "download_url": typing_video.as_uri(),
                    "preview_image_url": "https://example.test/thumbs/search-mock-002.jpg",
                    "duration_seconds": 8,
                    "width": 1920,
                    "height": 1080,
                    "tags": ["typing", "laptop", "screen", "desk"],
                },
            ]
        },
    )


def build_broken_catalog(root: Path) -> None:
    videos = root / "videos"
    videos.mkdir(parents=True, exist_ok=True)
    good_video = videos / "good.mp4"
    good_video.write_bytes(b"mock-good-video")
    write_json(
        root / "catalog.json",
        {
            "results": [
                {
                    "id": "good-001",
                    "title": "Office worker using AI on computer",
                    "page_url": "https://example.test/videos/good-001",
                    "download_url": good_video.as_uri(),
                    "preview_image_url": "https://example.test/thumbs/good-001.jpg",
                    "duration_seconds": 8,
                    "width": 1920,
                    "height": 1080,
                    "tags": ["office", "worker", "ai", "computer"],
                },
                {
                    "id": "bad-001",
                    "title": "Office AI broken download clip",
                    "page_url": "https://example.test/videos/bad-001",
                    "download_url": "file:///nonexistent/path/bad-001.mp4",
                    "preview_image_url": "https://example.test/thumbs/bad-001.jpg",
                    "duration_seconds": 7,
                    "width": 1920,
                    "height": 1080,
                    "tags": ["office", "ai", "broken", "computer"],
                },
            ]
        },
    )


def make_multi_chapter_overlap_package(project_root: Path) -> None:
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
                    "shot_intent": "第一章需要 office ai b-roll",
                    "required_coverage_seconds": 6,
                    "minimum_candidates": 1,
                    "queries": ["office worker ai computer"],
                    "source_types": ["stock-library"],
                    "fallback": "图卡 1",
                },
                {
                    "chapter_id": "ch2",
                    "shot_intent": "第二章需要 office ai b-roll",
                    "required_coverage_seconds": 6,
                    "minimum_candidates": 1,
                    "queries": ["office worker ai computer"],
                    "source_types": ["stock-library"],
                    "fallback": "图卡 2",
                },
                {
                    "chapter_id": "ch3",
                    "shot_intent": "第三章需要 office ai b-roll",
                    "required_coverage_seconds": 6,
                    "minimum_candidates": 1,
                    "queries": ["office worker ai computer"],
                    "source_types": ["stock-library"],
                    "fallback": "图卡 3",
                },
            ],
        },
    )


def build_overlap_catalog(root: Path) -> None:
    videos = root / "videos"
    videos.mkdir(parents=True, exist_ok=True)
    payload_results = []
    for index in range(3):
        video_path = videos / f"office-ai-{index + 1}.mp4"
        video_path.write_bytes(f"office-ai-{index + 1}".encode("utf-8"))
        payload_results.append(
            {
                "id": f"office-ai-{index + 1}",
                "title": f"Office worker AI computer variant {index + 1}",
                "page_url": f"https://example.test/videos/office-ai-{index + 1}",
                "download_url": video_path.as_uri(),
                "preview_image_url": f"https://example.test/thumbs/office-ai-{index + 1}.jpg",
                "duration_seconds": 8 + index,
                "width": 1920,
                "height": 1080,
                "tags": ["office", "worker", "ai", "computer", f"variant-{index + 1}"],
            }
        )
    write_json(root / "catalog.json", {"results": payload_results})


def build_balance_catalog(root: Path) -> None:
    videos = root / "videos"
    videos.mkdir(parents=True, exist_ok=True)
    payload_results = []
    for index in range(6):
        video_path = videos / f"office-ai-balance-{index + 1}.mp4"
        video_path.write_bytes(f"office-ai-balance-{index + 1}".encode("utf-8"))
        payload_results.append(
            {
                "id": f"office-ai-balance-{index + 1}",
                "title": f"Office worker AI computer balance variant {index + 1}",
                "page_url": f"https://example.test/videos/office-ai-balance-{index + 1}",
                "download_url": video_path.as_uri(),
                "preview_image_url": f"https://example.test/thumbs/office-ai-balance-{index + 1}.jpg",
                "duration_seconds": 8 + index,
                "width": 1920,
                "height": 1080,
                "tags": ["office", "worker", "ai", "computer", f"balance-{index + 1}"],
            }
        )
    write_json(root / "catalog.json", {"results": payload_results})


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
                "    request = args[-1]",
                "    if request.startswith('ytsearch'):",
                "        print(json.dumps({",
                "            'entries': [",
                "                {",
                "                    'id': 'search-001',",
                "                    'title': 'Keyboard Desk Setup B-roll',",
                "                    'webpage_url': 'https://video.example.test/watch/search-001',",
                "                    'duration': 17,",
                "                    'uploader': 'Creator Search A',",
                "                    'uploader_url': 'https://video.example.test/channel/search-a',",
                "                    'thumbnail': 'https://video.example.test/search-001.jpg',",
                "                    'tags': ['keyboard', 'desk', 'setup']",
                "                },",
                "                {",
                "                    'id': 'search-002',",
                "                    'title': 'Typing on Laptop Screen',",
                "                    'webpage_url': 'https://video.example.test/watch/search-002',",
                "                    'duration': 13,",
                "                    'uploader': 'Creator Search B',",
                "                    'uploader_url': 'https://video.example.test/channel/search-b',",
                "                    'thumbnail': 'https://video.example.test/search-002.jpg',",
                "                    'tags': ['typing', 'laptop', 'screen']",
                "                }",
                "            ]",
                "        }))",
                "        raise SystemExit(0)",
                "    print(json.dumps({",
                "        'id': 'official-demo-001',",
                "        'title': 'Official Product Demo',",
                "        'webpage_url': request,",
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


def build_failing_ytdlp_bin(root: Path) -> Path:
    script_path = root / "failing-yt-dlp.py"
    script_path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import sys",
                "args = sys.argv[1:]",
                "if '--version' in args:",
                "    print('test-ytdlp-1.0')",
                "    raise SystemExit(0)",
                "if '--dump-single-json' in args:",
                "    print('simulated yt-dlp query failure', file=sys.stderr)",
                "    raise SystemExit(23)",
                "raise SystemExit(0)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    script_path.chmod(0o755)
    return script_path


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


def test_run_external_footage_workflow_uses_wider_midvideo_defaults(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "licensed-footage-sourcing"
        / "scripts"
        / "run_external_footage_workflow.py"
    )

    project_root = tmp_path / "2026-03-28-bilibili-dense-footage"
    make_dense_midlong_package(project_root)

    mock_root = tmp_path / "dense-mock-provider"
    build_mock_catalog(mock_root, extra_results=5)
    completed = run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
            "--providers",
            "mock-stock",
        ],
        repo_root,
        env={
            "MOCK_STOCK_CATALOG_PATH": str(mock_root / "catalog.json"),
        },
    )

    payload = json.loads(completed.stdout)
    source_manifest = json.loads((project_root / "sources" / "source-manifest.json").read_text(encoding="utf-8"))
    source_shortlist = json.loads((project_root / "sources" / "source-shortlist.json").read_text(encoding="utf-8"))

    assert payload["provider_summary"]["mock-stock"]["results_found"] == 7
    assert len(source_shortlist["chapters"][0]["results"]) == 6
    assert len(source_manifest["source_manifest"]) == 6


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


def test_run_external_footage_workflow_builds_exploration_pool_from_ytdlp_query_search(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "licensed-footage-sourcing"
        / "scripts"
        / "run_external_footage_workflow.py"
    )

    project_root = tmp_path / "2026-03-28-bilibili-ytdlp-search"
    make_ytdlp_search_package(project_root)
    mock_root = tmp_path / "mixed-mock-provider"
    build_search_catalog(mock_root)
    ytdlp_bin, _ = build_mock_ytdlp_bin(tmp_path)

    completed = run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
            "--providers",
            "mock-stock,yt-dlp",
            "--download-approved",
            "--download-exploration",
            "--exploration-download-limit",
            "2",
            "--yt-dlp-bin",
            str(ytdlp_bin),
        ],
        repo_root,
        env={
            "MOCK_STOCK_CATALOG_PATH": str(mock_root / "catalog.json"),
        },
    )

    payload = json.loads(completed.stdout)
    exploration_shortlist = json.loads((project_root / "sources" / "exploration-shortlist.json").read_text(encoding="utf-8"))
    exploration_ingest = json.loads((project_root / "sources" / "exploration-ingest-manifest.json").read_text(encoding="utf-8"))
    source_manifest = json.loads((project_root / "sources" / "source-manifest.json").read_text(encoding="utf-8"))

    assert payload["provider_summary"]["yt-dlp"]["queries_attempted"] == 2
    assert payload["provider_summary"]["yt-dlp"]["results_found"] == 4
    assert payload["exploration_ingested_count"] == 2
    assert any(item["provider"] == "yt-dlp" for item in exploration_shortlist["results"])
    assert any(item["provider"] == "mock-stock" for item in exploration_shortlist["results"])
    assert len(exploration_ingest["ingested_assets"]) == 2
    assert source_manifest["license_summary"]["approved_count"] >= 1
    assert (project_root / exploration_ingest["ingested_assets"][0]["local_path"]).exists()


def test_run_external_footage_workflow_uses_provider_specific_queries(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "licensed-footage-sourcing"
        / "scripts"
        / "run_external_footage_workflow.py"
    )

    project_root = tmp_path / "2026-03-28-bilibili-provider-specific-queries"
    make_provider_specific_query_package(project_root)
    mock_root = tmp_path / "provider-query-mock"
    build_search_catalog(mock_root)
    ytdlp_bin, _ = build_mock_ytdlp_bin(tmp_path)

    completed = run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
            "--providers",
            "mock-stock,yt-dlp",
            "--yt-dlp-bin",
            str(ytdlp_bin),
        ],
        repo_root,
        env={
            "MOCK_STOCK_CATALOG_PATH": str(mock_root / "catalog.json"),
        },
    )

    payload = json.loads(completed.stdout)
    query_sheet = (project_root / "sources" / "clip-query-sheet.md").read_text(encoding="utf-8")

    assert payload["provider_summary"]["mock-stock"]["queries_attempted"] == 2
    assert payload["provider_summary"]["yt-dlp"]["queries_attempted"] == 1
    assert "cinematic keyboard desk b roll" in query_sheet


def test_run_external_footage_workflow_records_provider_errors_in_all_outputs(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "licensed-footage-sourcing"
        / "scripts"
        / "run_external_footage_workflow.py"
    )

    project_root = tmp_path / "2026-03-28-bilibili-provider-errors"
    make_ytdlp_search_package(project_root)
    mock_root = tmp_path / "provider-error-mock"
    build_mock_catalog(mock_root)
    failing_ytdlp = build_failing_ytdlp_bin(tmp_path)

    completed = run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
            "--providers",
            "mock-stock,yt-dlp",
            "--yt-dlp-bin",
            str(failing_ytdlp),
        ],
        repo_root,
        env={
            "MOCK_STOCK_CATALOG_PATH": str(mock_root / "catalog.json"),
        },
    )

    payload = json.loads(completed.stdout)
    source_manifest = json.loads((project_root / "sources" / "source-manifest.json").read_text(encoding="utf-8"))
    source_shortlist = json.loads((project_root / "sources" / "source-shortlist.json").read_text(encoding="utf-8"))
    exploration_shortlist = json.loads((project_root / "sources" / "exploration-shortlist.json").read_text(encoding="utf-8"))

    assert payload["provider_summary"]["mock-stock"]["results_found"] >= 1
    assert source_manifest["provider_errors"]
    assert source_shortlist["provider_errors"]
    assert exploration_shortlist["provider_errors"]
    assert all(item["provider"] == "yt-dlp" for item in source_manifest["provider_errors"])
    assert all(item["provider"] == "yt-dlp" for item in source_shortlist["provider_errors"])
    assert all(item["provider"] == "yt-dlp" for item in exploration_shortlist["provider_errors"])
    assert "returned non-zero exit status 23" in source_manifest["provider_errors"][0]["error"]


def test_run_external_footage_workflow_continues_when_downloads_fail(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "licensed-footage-sourcing"
        / "scripts"
        / "run_external_footage_workflow.py"
    )

    project_root = tmp_path / "2026-03-28-bilibili-resilient-downloads"
    make_dense_midlong_package(project_root)

    mock_root = tmp_path / "broken-mock-provider"
    build_broken_catalog(mock_root)
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
    ingest_manifest = json.loads((project_root / "sources" / "asset-ingest-manifest.json").read_text(encoding="utf-8"))
    source_manifest = json.loads((project_root / "sources" / "source-manifest.json").read_text(encoding="utf-8"))

    assert payload["ingested_count"] == 1
    assert payload["failed_download_count"] == 1
    assert len(ingest_manifest["ingested_assets"]) == 1
    assert len(ingest_manifest["download_errors"]) == 1
    assert ingest_manifest["download_errors"][0]["clip_id"] == "mock-stock-bad-001"
    assert any(entry["clip_id"] == "mock-stock-bad-001" for entry in source_manifest["source_manifest"])


def test_run_external_footage_workflow_avoids_reusing_same_clip_across_chapters_when_alternatives_exist(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "licensed-footage-sourcing"
        / "scripts"
        / "run_external_footage_workflow.py"
    )

    project_root = tmp_path / "2026-03-28-bilibili-unique-assignment"
    make_multi_chapter_overlap_package(project_root)

    mock_root = tmp_path / "overlap-provider"
    build_overlap_catalog(mock_root)
    run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
            "--providers",
            "mock-stock",
            "--approved-per-chapter",
            "1",
            "--max-shortlist-per-chapter",
            "3",
            "--max-results-per-query",
            "3",
        ],
        repo_root,
        env={
            "MOCK_STOCK_CATALOG_PATH": str(mock_root / "catalog.json"),
        },
    )

    source_manifest = json.loads((project_root / "sources" / "source-manifest.json").read_text(encoding="utf-8"))
    clip_ids = [entry["clip_id"] for entry in source_manifest["source_manifest"]]

    assert len(clip_ids) == 3
    assert len(set(clip_ids)) == 3


def test_run_external_footage_workflow_balances_exploration_downloads_across_chapters(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "extensions"
        / "skills"
        / "licensed-footage-sourcing"
        / "scripts"
        / "run_external_footage_workflow.py"
    )

    project_root = tmp_path / "2026-03-28-bilibili-balanced-exploration"
    make_multi_chapter_overlap_package(project_root)

    mock_root = tmp_path / "balanced-exploration-provider"
    build_balance_catalog(mock_root)
    run_command(
        [
            sys.executable,
            str(script_path),
            "--project-root",
            str(project_root),
            "--providers",
            "mock-stock",
            "--approved-per-chapter",
            "1",
            "--max-shortlist-per-chapter",
            "3",
            "--max-exploration-per-chapter",
            "6",
            "--max-results-per-query",
            "6",
            "--download-exploration",
            "--exploration-download-limit",
            "3",
        ],
        repo_root,
        env={
            "MOCK_STOCK_CATALOG_PATH": str(mock_root / "catalog.json"),
        },
    )

    exploration_ingest = json.loads((project_root / "sources" / "exploration-ingest-manifest.json").read_text(encoding="utf-8"))
    chapters = [item["chapter_id"] for item in exploration_ingest["ingested_assets"]]

    assert len(chapters) == 3
    assert set(chapters) == {"ch1", "ch2", "ch3"}
