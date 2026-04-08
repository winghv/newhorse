#!/usr/bin/env python3
"""Search approved external footage providers and optionally ingest assets locally."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import httpx


ALLOWED_SOURCE_TYPES = [
    "public-domain",
    "stock-library",
    "brand-owned",
    "official-promo-footage",
]

BLOCKED_SOURCE_TYPES = [
    "unauthorized-creator-reupload",
    "unknown-license",
    "pirated-compilation",
]

DEFAULT_MAX_RESULTS_PER_QUERY = 12
DEFAULT_MAX_SHORTLIST_PER_CHAPTER = 12
DEFAULT_APPROVED_PER_CHAPTER = 6
DEFAULT_MAX_EXPLORATION_PER_CHAPTER = 18
DEFAULT_MIN_PRODUCTION_MATCH_SCORE = 0.55
PROVIDER_PRIORITY = {
    "pexels": 4,
    "pixabay": 4,
    "mock-stock": 4,
    "yt-dlp": 1,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", help="Media package root directory.")
    parser.add_argument("--content-id", help="Content package id under the media-ops root.")
    parser.add_argument(
        "--media-ops-root",
        help="Root directory containing media packages. Defaults to repo-local data/media-ops.",
    )
    parser.add_argument(
        "--providers",
        default="auto",
        help="Comma-separated provider list. Supported: auto, pexels, pixabay, mock-stock, yt-dlp.",
    )
    parser.add_argument(
        "--max-results-per-query",
        type=int,
        default=DEFAULT_MAX_RESULTS_PER_QUERY,
        help="Maximum provider results fetched for each search query.",
    )
    parser.add_argument(
        "--max-shortlist-per-chapter",
        type=int,
        default=DEFAULT_MAX_SHORTLIST_PER_CHAPTER,
        help="Maximum shortlisted results kept for each chapter.",
    )
    parser.add_argument(
        "--approved-per-chapter",
        type=int,
        default=DEFAULT_APPROVED_PER_CHAPTER,
        help="Maximum approved manifest entries kept for each chapter.",
    )
    parser.add_argument(
        "--max-exploration-per-chapter",
        type=int,
        default=DEFAULT_MAX_EXPLORATION_PER_CHAPTER,
        help="Maximum exploration-pool results kept for each chapter.",
    )
    parser.add_argument(
        "--download-approved",
        action="store_true",
        help="Download approved assets into assets/external and write an ingest manifest.",
    )
    parser.add_argument(
        "--download-exploration",
        action="store_true",
        help="Download exploration-pool assets into assets/exploration and write a separate ingest manifest.",
    )
    parser.add_argument(
        "--download-limit",
        type=int,
        default=0,
        help="Maximum number of approved assets to download. 0 means no explicit limit.",
    )
    parser.add_argument(
        "--exploration-download-limit",
        type=int,
        default=0,
        help="Maximum number of exploration assets to download. 0 means no explicit limit.",
    )
    parser.add_argument(
        "--yt-dlp-bin",
        default=os.environ.get("YT_DLP_BIN", "yt-dlp"),
        help="yt-dlp executable path used for direct-source ingest.",
    )
    parser.add_argument(
        "--source-manifest-output",
        default="sources/source-manifest.json",
        help="Output path for the source manifest, relative to the project root.",
    )
    parser.add_argument(
        "--source-shortlist-output",
        default="sources/source-shortlist.json",
        help="Output path for the flattened source shortlist, relative to the project root.",
    )
    parser.add_argument(
        "--asset-ingest-output",
        default="sources/asset-ingest-manifest.json",
        help="Output path for the asset ingest manifest, relative to the project root.",
    )
    parser.add_argument(
        "--exploration-shortlist-output",
        default="sources/exploration-shortlist.json",
        help="Output path for the exploration shortlist, relative to the project root.",
    )
    parser.add_argument(
        "--exploration-ingest-output",
        default="sources/exploration-ingest-manifest.json",
        help="Output path for the exploration ingest manifest, relative to the project root.",
    )
    parser.add_argument(
        "--coverage-report-output",
        default="sources/chapter-coverage-report.json",
        help="Output path for the chapter coverage gate report, relative to the project root.",
    )
    parser.add_argument(
        "--query-sheet-output",
        default="sources/clip-query-sheet.md",
        help="Output path for the clip query sheet, relative to the project root.",
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


def prefer_http_proxy_over_all_proxy() -> None:
    http_proxy = os.environ.get("http_proxy") or os.environ.get("HTTP_PROXY")
    https_proxy = os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY")
    all_proxy = os.environ.get("all_proxy") or os.environ.get("ALL_PROXY")
    if not all_proxy:
        return
    if not str(all_proxy).lower().startswith("socks"):
        return
    if not (http_proxy or https_proxy):
        return
    os.environ.pop("all_proxy", None)
    os.environ.pop("ALL_PROXY", None)


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def detect_content_packet(project_root: Path) -> Path:
    content_dir = project_root / "content"
    if not content_dir.exists():
        raise FileNotFoundError(f"missing content directory under {project_root}")

    prioritized = ["*video.json", "content-packet.json", "*.json"]
    for pattern in prioritized:
        matches = sorted(path for path in content_dir.glob(pattern) if path.is_file())
        if matches:
            return matches[0]
    raise FileNotFoundError(f"no content packet found under {content_dir}")


def primary_packet(content_packet: dict[str, Any]) -> dict[str, Any]:
    nested = content_packet.get("content_packet")
    return nested if isinstance(nested, dict) else content_packet


def slugify(value: str) -> str:
    lowered = value.lower().strip()
    normalized = re.sub(r"[^a-z0-9]+", "-", lowered)
    return normalized.strip("-") or "asset"


def tokenize(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]{2,}", value.lower())
        if len(token) >= 2
    }


def relative_to_project(path: Path, project_root: Path) -> str:
    return str(path.resolve().relative_to(project_root.resolve()))


def read_bytes_from_url(url: str) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme == "file":
        return Path(unquote(parsed.path)).read_bytes()
    if parsed.scheme in {"http", "https"}:
        response = httpx.get(url, follow_redirects=True, timeout=30.0)
        response.raise_for_status()
        return response.content
    return Path(url).read_bytes()


def resolve_executable_path(binary: str, *, display_name: str) -> str:
    candidate = str(binary or "").strip()
    if not candidate:
        raise ValueError(f"{display_name} binary is required")
    candidate_path = Path(candidate).expanduser()
    resolved = str(candidate_path.resolve()) if candidate_path.is_file() else shutil.which(candidate)
    if not resolved:
        raise ValueError(f"{display_name} binary not found: {binary}")
    try:
        subprocess.run([resolved, "--version"], check=False, capture_output=True, text=True)
    except OSError as exc:
        raise ValueError(f"{display_name} binary is not runnable: {resolved} ({exc})") from exc
    return resolved


@dataclass(frozen=True)
class SearchResult:
    provider: str
    provider_asset_id: str
    title: str
    page_url: str
    download_url: str
    preview_image_url: str | None
    duration_seconds: int | None
    width: int | None
    height: int | None
    tags: list[str]
    source_type: str
    license_status: str
    license_basis: str
    attribution_required: bool
    attribution_text: str
    usage_notes: str
    uploader: str | None = None
    uploader_url: str | None = None


class FootageProvider:
    name = ""

    def search(self, query: str, limit: int) -> list[SearchResult]:
        raise NotImplementedError


class MockStockProvider(FootageProvider):
    name = "mock-stock"

    def __init__(self) -> None:
        catalog_path = os.environ.get("MOCK_STOCK_CATALOG_PATH")
        if not catalog_path:
            raise ValueError("MOCK_STOCK_CATALOG_PATH is required for mock-stock provider")
        self._catalog_path = Path(catalog_path).resolve()

    def search(self, query: str, limit: int) -> list[SearchResult]:
        payload = load_json(self._catalog_path)
        results = payload.get("results")
        if not isinstance(results, list):
            return []
        normalized: list[SearchResult] = []
        for item in results[:limit]:
            normalized.append(
                SearchResult(
                    provider=self.name,
                    provider_asset_id=str(item.get("id") or ""),
                    title=str(item.get("title") or f"Mock asset {item.get('id') or ''}"),
                    page_url=str(item.get("page_url") or ""),
                    download_url=str(item.get("download_url") or ""),
                    preview_image_url=str(item.get("preview_image_url") or "") or None,
                    duration_seconds=_int_or_none(item.get("duration_seconds")),
                    width=_int_or_none(item.get("width")),
                    height=_int_or_none(item.get("height")),
                    tags=_string_list(item.get("tags")),
                    source_type="stock-library",
                    license_status="approved",
                    license_basis="Mock stock catalog for local workflow tests.",
                    attribution_required=False,
                    attribution_text="",
                    usage_notes="Mock provider result used for workflow verification.",
                )
            )
        return normalized


class PexelsProvider(FootageProvider):
    name = "pexels"

    def __init__(self) -> None:
        api_key = os.environ.get("PEXELS_API_KEY")
        if not api_key:
            raise ValueError("PEXELS_API_KEY is required for pexels provider")
        self._api_key = api_key
        self._base_url = os.environ.get("PEXELS_API_BASE_URL", "https://api.pexels.com/videos/search")

    def search(self, query: str, limit: int) -> list[SearchResult]:
        response = httpx.get(
            self._base_url,
            headers={"Authorization": self._api_key},
            params={"query": query, "per_page": limit},
            timeout=30.0,
        )
        response.raise_for_status()
        payload = response.json()
        videos = payload.get("videos")
        if not isinstance(videos, list):
            return []
        normalized: list[SearchResult] = []
        for item in videos[:limit]:
            download_url = _pick_pexels_download_url(item.get("video_files"))
            if not download_url:
                continue
            video_id = str(item.get("id") or "")
            normalized.append(
                SearchResult(
                    provider=self.name,
                    provider_asset_id=video_id,
                    title=str(item.get("url") or f"Pexels video {video_id}"),
                    page_url=str(item.get("url") or ""),
                    download_url=download_url,
                    preview_image_url=str(item.get("image") or "") or None,
                    duration_seconds=_int_or_none(item.get("duration")),
                    width=_int_or_none(item.get("width")),
                    height=_int_or_none(item.get("height")),
                    tags=[],
                    source_type="stock-library",
                    license_status="approved",
                    license_basis="Pexels stock footage via official API; verify current license before live publish.",
                    attribution_required=True,
                    attribution_text="Credit Pexels and creator when practical.",
                    usage_notes="Keep the source URL in the manifest and review current Pexels API terms before publishing.",
                )
            )
        return normalized


class PixabayProvider(FootageProvider):
    name = "pixabay"

    def __init__(self) -> None:
        api_key = os.environ.get("PIXABAY_API_KEY")
        if not api_key:
            raise ValueError("PIXABAY_API_KEY is required for pixabay provider")
        self._api_key = api_key
        self._base_url = os.environ.get("PIXABAY_API_BASE_URL", "https://pixabay.com/api/videos/")

    def search(self, query: str, limit: int) -> list[SearchResult]:
        response = httpx.get(
            self._base_url,
            params={"key": self._api_key, "q": query, "per_page": limit, "safesearch": "true"},
            timeout=30.0,
        )
        response.raise_for_status()
        payload = response.json()
        hits = payload.get("hits")
        if not isinstance(hits, list):
            return []
        normalized: list[SearchResult] = []
        for item in hits[:limit]:
            download_url, width, height = _pick_pixabay_download(item.get("videos"))
            if not download_url:
                continue
            video_id = str(item.get("id") or "")
            normalized.append(
                SearchResult(
                    provider=self.name,
                    provider_asset_id=video_id,
                    title=str(item.get("tags") or f"Pixabay video {video_id}"),
                    page_url=str(item.get("pageURL") or ""),
                    download_url=download_url,
                    preview_image_url=str(item.get("picture_id") or "") or None,
                    duration_seconds=_int_or_none(item.get("duration")),
                    width=width,
                    height=height,
                    tags=_comma_list(item.get("tags")),
                    source_type="stock-library",
                    license_status="approved",
                    license_basis="Pixabay stock footage via official API; verify current license before live publish.",
                    attribution_required=True,
                    attribution_text="Credit Pixabay and creator when practical.",
                    usage_notes="Keep the source URL in the manifest and review current Pixabay API terms before publishing.",
                )
            )
        return normalized


class YtDlpProvider(FootageProvider):
    name = "yt-dlp"

    def __init__(self, *, binary: str) -> None:
        self._binary = resolve_executable_path(binary, display_name="yt-dlp")

    def search(self, query: str, limit: int) -> list[SearchResult]:
        command = [
            self._binary,
            "--dump-single-json",
            "--flat-playlist",
            "--no-warnings",
            f"ytsearch{limit}:{query}",
        ]
        completed = subprocess.run(command, check=True, capture_output=True, text=True)
        payload = json.loads(completed.stdout)
        entries = payload.get("entries")
        if not isinstance(entries, list):
            return []
        normalized: list[SearchResult] = []
        for item in entries[:limit]:
            if not isinstance(item, dict):
                continue
            video_id = str(item.get("id") or "")
            page_url = str(item.get("webpage_url") or item.get("url") or "")
            title = str(item.get("title") or video_id or query)
            uploader = str(item.get("uploader") or item.get("channel") or "")
            uploader_url = str(item.get("uploader_url") or item.get("channel_url") or "")
            normalized.append(
                SearchResult(
                    provider=self.name,
                    provider_asset_id=video_id or slugify(title),
                    title=title,
                    page_url=page_url,
                    download_url=page_url,
                    preview_image_url=str(item.get("thumbnail") or "") or None,
                    duration_seconds=_int_or_none(item.get("duration")),
                    width=_int_or_none(item.get("width")),
                    height=_int_or_none(item.get("height")),
                    tags=_string_list(item.get("tags")),
                    source_type="unknown-license",
                    license_status="hold",
                    license_basis="yt-dlp query expansion pool result; keep in exploration only until explicitly promoted.",
                    attribution_required=True,
                    attribution_text="Record uploader/channel and add attribution if the source requires it.",
                    usage_notes="Query-searched yt-dlp results expand the candidate pool but do not auto-enter the production manifest.",
                    uploader=uploader or None,
                    uploader_url=uploader_url or None,
                )
            )
        return normalized

    def inspect_url(self, url: str, source_types: list[str]) -> SearchResult:
        command = [self._binary, "--dump-single-json", "--no-warnings", url]
        completed = subprocess.run(command, check=True, capture_output=True, text=True)
        payload = json.loads(completed.stdout)

        trusted = bool(set(source_types) & {"official-promo-footage", "brand-owned", "public-domain"})
        license_status = "approved" if trusted else "hold"
        license_basis = (
            "Direct-source ingest via yt-dlp with trusted source type declared in the content brief; verify reuse rights before live publish."
            if trusted
            else "Creator-platform footage ingested via yt-dlp requires manual license review before it can enter the production chain."
        )
        source_type = source_types[0] if source_types else "unknown-license"
        title = str(payload.get("title") or payload.get("id") or url)
        uploader = str(payload.get("uploader") or payload.get("channel") or "")
        uploader_url = str(payload.get("uploader_url") or payload.get("channel_url") or "")
        width = _int_or_none(payload.get("width"))
        height = _int_or_none(payload.get("height"))
        return SearchResult(
            provider=self.name,
            provider_asset_id=str(payload.get("id") or slugify(title)),
            title=title,
            page_url=str(payload.get("webpage_url") or payload.get("original_url") or url),
            download_url=str(payload.get("webpage_url") or payload.get("original_url") or url),
            preview_image_url=str(payload.get("thumbnail") or "") or None,
            duration_seconds=_int_or_none(payload.get("duration")),
            width=width,
            height=height,
            tags=_string_list(payload.get("tags")),
            source_type=source_type,
            license_status=license_status,
            license_basis=license_basis,
            attribution_required=True,
            attribution_text="Record uploader/channel and add attribution if the source requires it.",
            usage_notes="yt-dlp ingest is opt-in and must keep the original source URL in the manifest.",
            uploader=uploader or None,
            uploader_url=uploader_url or None,
        )


def _comma_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return []


GENERIC_FOOTAGE_TOKENS = {
    "abstract",
    "background",
    "bokeh",
    "particles",
    "loop",
    "seamless",
    "template",
    "animation",
    "motion",
    "graphic",
    "business",
    "corporate",
    "technology",
    "digital",
    "success",
    "teamwork",
    "dinosaur",
    "prehistoric",
    "chroma",
    "greenscreen",
    "green",
    "screen",
    "3d",
    "cartoon",
    "animated",
    "sleep",
    "relaxing",
    "reddit",
    "story",
    "stories",
    "lookbook",
}

YT_DLP_NON_BROLL_TOKENS = {
    "tips",
    "tip",
    "tutorial",
    "how",
    "guide",
    "explained",
    "explain",
    "podcast",
    "interview",
    "lecture",
    "course",
    "review",
    "reaction",
    "talk",
    "speech",
    "music",
    "song",
    "mix",
    "livestream",
    "webinar",
    "reddit",
    "stories",
    "story",
    "sleep",
    "relaxing",
    "white noise",
    "tedx",
    "lookbook",
    "compilation",
}


def _int_or_none(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _pick_pexels_download_url(video_files: Any) -> str:
    if not isinstance(video_files, list):
        return ""
    candidates = [item for item in video_files if isinstance(item, dict) and str(item.get("file_type") or "").endswith("mp4")]
    if not candidates:
        return ""
    ranked = sorted(candidates, key=lambda item: int(item.get("width") or 0), reverse=True)
    return str(ranked[0].get("link") or "")


def _pick_pixabay_download(videos: Any) -> tuple[str, int | None, int | None]:
    if not isinstance(videos, dict):
        return "", None, None
    candidates: list[tuple[str, int | None, int | None]] = []
    for key in ("medium", "large", "small", "tiny"):
        item = videos.get(key)
        if isinstance(item, dict) and item.get("url"):
            candidates.append((str(item["url"]), _int_or_none(item.get("width")), _int_or_none(item.get("height"))))
    if not candidates:
        return "", None, None
    ranked = sorted(candidates, key=lambda item: item[1] or 0, reverse=True)
    return ranked[0]


def instantiate_providers(raw_names: str, *, yt_dlp_bin: str) -> list[FootageProvider]:
    requested_names = [name.strip() for name in raw_names.split(",") if name.strip()] if raw_names != "auto" else []
    available_factories = {
        "pexels": PexelsProvider,
        "pixabay": PixabayProvider,
        "mock-stock": MockStockProvider,
        "yt-dlp": lambda: YtDlpProvider(binary=yt_dlp_bin),
    }

    provider_names = requested_names or [name for name in ("pexels", "pixabay", "mock-stock", "yt-dlp")]
    providers: list[FootageProvider] = []
    missing: list[str] = []
    for name in provider_names:
        factory = available_factories.get(name)
        if factory is None:
            raise ValueError(f"unsupported provider: {name}")
        try:
            providers.append(factory())
        except ValueError:
            if requested_names:
                raise
            missing.append(name)
    if not providers:
        missing_text = ", ".join(missing) if missing else raw_names
        raise ValueError(f"no configured providers available for {missing_text}")
    return providers


def normalize_clip_briefs(content_packet: dict[str, Any]) -> list[dict[str, Any]]:
    packet = primary_packet(content_packet)
    raw_entries = packet.get("clip_sourcing_brief")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise ValueError("content packet is missing clip_sourcing_brief")

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(raw_entries, start=1):
        if not isinstance(item, dict):
            continue
        chapter_id = str(item.get("chapter_id") or f"chapter-{index}")
        queries = (
            _string_list(item.get("queries"))
            or _string_list(item.get("english_queries"))
            or _string_list(item.get("search_queries"))
        )
        direct_source_urls = _string_list(item.get("direct_source_urls"))
        raw_provider_queries = item.get("provider_queries") or item.get("queries_by_provider")
        provider_queries: dict[str, list[str]] = {}
        if isinstance(raw_provider_queries, dict):
            for provider_name, provider_query_list in raw_provider_queries.items():
                normalized_queries = _string_list(provider_query_list)
                if normalized_queries:
                    provider_queries[str(provider_name).strip()] = normalized_queries
        if not queries and not direct_source_urls:
            continue
        normalized.append(
            {
                "chapter_id": chapter_id,
                "shot_intent": str(item.get("shot_intent") or ""),
                "queries": queries,
                "provider_queries": provider_queries,
                "direct_source_urls": direct_source_urls,
                "source_types": _string_list(item.get("source_types")),
                "must_have_terms": _string_list(item.get("must_have_terms")),
                "avoid_terms": _string_list(item.get("avoid_terms")),
                "fallback": str(item.get("fallback") or ""),
                "required_coverage_seconds": float(item.get("required_coverage_seconds") or item.get("chapter_duration_seconds") or 0),
                "minimum_candidates": int(item.get("minimum_candidates") or 2),
                "max_single_asset_seconds": float(item.get("max_single_asset_seconds") or 30),
                "minimum_match_score": float(item.get("minimum_match_score") or DEFAULT_MIN_PRODUCTION_MATCH_SCORE),
            }
        )
    if not normalized:
        raise ValueError("clip_sourcing_brief contains no usable query entries")
    return normalized


def score_result(query: str, result: SearchResult, chapter: dict[str, Any]) -> float:
    query_tokens = tokenize(query)
    haystack_tokens = tokenize(" ".join([result.title, *result.tags, result.page_url]))
    if not query_tokens:
        return 0.0
    overlap = len(query_tokens & haystack_tokens)
    exact_bonus = 0.25 if query.lower() in " ".join([result.title, " ".join(result.tags)]).lower() else 0.0
    score = (overlap / len(query_tokens)) + exact_bonus

    must_have_terms = [term.lower().strip() for term in chapter.get("must_have_terms", []) if str(term).strip()]
    avoid_terms = [term.lower().strip() for term in chapter.get("avoid_terms", []) if str(term).strip()]
    title_and_tags = " ".join([result.title, " ".join(result.tags)]).lower()
    matched_must_have = sum(1 for term in must_have_terms if term in title_and_tags)
    if must_have_terms:
        score += 0.18 * matched_must_have
        if matched_must_have == 0:
            score -= 0.4

    matched_avoid = sum(1 for term in avoid_terms if term in title_and_tags)
    if matched_avoid:
        score -= 0.35 * matched_avoid

    generic_overlap = len(GENERIC_FOOTAGE_TOKENS & haystack_tokens)
    if generic_overlap >= 2 and overlap <= 1:
        score -= 0.35

    if result.provider == "yt-dlp":
        non_broll_hits = sum(1 for token in YT_DLP_NON_BROLL_TOKENS if token in title_and_tags)
        if non_broll_hits:
            score -= 0.14 * non_broll_hits

    if result.width and result.height:
        aspect_ratio = result.width / max(result.height, 1)
        if aspect_ratio >= 1.45:
            score += 0.05
        elif aspect_ratio < 1.0:
            score -= 0.18

    if result.duration_seconds:
        if 4 <= result.duration_seconds <= 12:
            score += 0.08
        elif result.duration_seconds < 2:
            score -= 0.12

    return round(max(score, 0.0), 4)


def candidate_payload(chapter: dict[str, Any], query: str, result: SearchResult) -> dict[str, Any]:
    return {
        "chapter_id": chapter["chapter_id"],
        "shot_purpose": chapter["shot_intent"],
        "query": query,
        "match_score": score_result(query, result, chapter),
        "minimum_match_score": float(chapter.get("minimum_match_score") or DEFAULT_MIN_PRODUCTION_MATCH_SCORE),
        "provider": result.provider,
        "provider_asset_id": result.provider_asset_id,
        "title": result.title,
        "page_url": result.page_url,
        "download_url": result.download_url,
        "preview_image_url": result.preview_image_url,
        "duration_seconds": result.duration_seconds,
        "width": result.width,
        "height": result.height,
        "tags": result.tags,
        "source_type": result.source_type,
        "license_status": result.license_status,
        "license_basis": result.license_basis,
        "attribution_required": result.attribution_required,
        "attribution_text": result.attribution_text,
        "usage_notes": result.usage_notes,
        "fallback_query": chapter["fallback"] or query,
        "uploader": result.uploader,
        "uploader_url": result.uploader_url,
    }


def candidate_key(item: dict[str, Any]) -> str:
    return f"{item['provider']}:{item['provider_asset_id']}"


def is_production_eligible(item: dict[str, Any]) -> bool:
    minimum_match_score = float(item.get("minimum_match_score") or DEFAULT_MIN_PRODUCTION_MATCH_SCORE)
    return item.get("match_score", 0) >= minimum_match_score and item.get("license_status") == "approved"


def provider_priority(name: str | None) -> int:
    return PROVIDER_PRIORITY.get(str(name or "").strip(), 2)


def chapter_queries_for_provider(chapter: dict[str, Any], provider_name: str) -> list[str]:
    raw_provider_queries = chapter.get("provider_queries")
    if isinstance(raw_provider_queries, dict):
        provider_specific = raw_provider_queries.get(provider_name)
        if isinstance(provider_specific, list) and provider_specific:
            return provider_specific
    return list(chapter.get("queries") or [])


def diversify_ranked_candidates(
    ranked: list[dict[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    if limit <= 0 or not ranked:
        return []

    provider_buckets: dict[str, list[dict[str, Any]]] = {}
    for item in ranked:
        provider_buckets.setdefault(str(item.get("provider") or "unknown"), []).append(item)

    provider_order = sorted(
        provider_buckets,
        key=lambda name: (
            provider_priority(name),
            max(float(item.get("match_score", 0.0)) for item in provider_buckets[name]),
            len(provider_buckets[name]),
        ),
        reverse=True,
    )

    diversified: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    while len(diversified) < limit:
        progressed = False
        for provider_name in provider_order:
            bucket = provider_buckets.get(provider_name, [])
            while bucket and candidate_key(bucket[0]) in seen_keys:
                bucket.pop(0)
            if not bucket:
                continue
            candidate = bucket.pop(0)
            key = candidate_key(candidate)
            if key in seen_keys:
                continue
            diversified.append(candidate)
            seen_keys.add(key)
            progressed = True
            if len(diversified) >= limit:
                break
        if not progressed:
            break

    return diversified


def distribute_candidates_by_chapter(
    *,
    clip_briefs: list[dict[str, Any]],
    chapter_candidates: dict[str, list[dict[str, Any]]],
    limit: int,
) -> list[dict[str, Any]]:
    if limit <= 0:
        return [
            item
            for chapter in clip_briefs
            for item in chapter_candidates.get(chapter["chapter_id"], [])
        ]

    chapter_order = [chapter["chapter_id"] for chapter in clip_briefs]
    positions = {chapter_id: 0 for chapter_id in chapter_order}
    selected: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    while len(selected) < limit:
        progressed = False
        for chapter_id in chapter_order:
            items = chapter_candidates.get(chapter_id, [])
            index = positions.get(chapter_id, 0)
            while index < len(items):
                candidate = items[index]
                index += 1
                key = candidate_key(candidate)
                if key in seen_keys:
                    continue
                selected.append(candidate)
                seen_keys.add(key)
                positions[chapter_id] = index
                progressed = True
                break
            else:
                positions[chapter_id] = index
            if len(selected) >= limit:
                break
        if not progressed:
            break

    return selected


def error_payload(
    *,
    provider: str,
    chapter_id: str,
    stage: str,
    target: str,
    exc: Exception,
    clip_id: str | None = None,
) -> dict[str, Any]:
    payload = {
        "provider": provider,
        "chapter_id": chapter_id,
        "stage": stage,
        "target": target,
        "error": str(exc),
    }
    if clip_id:
        payload["clip_id"] = clip_id
    return payload


def choose_chapter_approved_candidates(
    *,
    clip_briefs: list[dict[str, Any]],
    chapter_shortlists: dict[str, list[dict[str, Any]]],
    approved_per_chapter: int,
) -> dict[str, list[dict[str, Any]]]:
    selected: dict[str, list[dict[str, Any]]] = {}
    globally_used_candidate_keys: set[str] = set()

    for chapter in clip_briefs:
        chapter_id = chapter["chapter_id"]
        shortlist = [item for item in chapter_shortlists.get(chapter_id, []) if item["match_score"] > 0]
        chosen: list[dict[str, Any]] = []
        chosen_keys: set[str] = set()

        for item in shortlist:
            key = candidate_key(item)
            if key in globally_used_candidate_keys or key in chosen_keys:
                continue
            chosen.append(item)
            chosen_keys.add(key)
            globally_used_candidate_keys.add(key)
            if len(chosen) >= approved_per_chapter:
                break

        if not chosen and shortlist:
            for item in shortlist:
                key = candidate_key(item)
                if key in chosen_keys:
                    continue
                chosen.append(item)
                chosen_keys.add(key)
                if len(chosen) >= approved_per_chapter:
                    break

        selected[chapter_id] = chosen

    return selected


def build_query_sheet(
    *,
    content_id: str,
    clip_briefs: list[dict[str, Any]],
    chapter_shortlists: dict[str, list[dict[str, Any]]],
) -> str:
    lines = [
        "# Clip Query Sheet",
        "",
        f"- `content_id`: `{content_id}`",
        "- `policy`: 优先官方 / stock / public-domain 来源；不接入无授权创作者搬运片段，不使用浏览器 cookies 抓私有素材。",
        "",
    ]
    for entry in clip_briefs:
        chapter_id = entry["chapter_id"]
        lines.append(f"## {chapter_id}")
        lines.append("")
        lines.append(f"- `shot_intent`: {entry['shot_intent']}")
        lines.append("- `queries`:")
        for query in entry["queries"]:
            lines.append(f"  - `{query}`")
        if entry.get("provider_queries"):
            lines.append("- `provider_queries`:")
            for provider_name, provider_queries in sorted(entry["provider_queries"].items()):
                lines.append(f"  - `{provider_name}`:")
                for query in provider_queries:
                    lines.append(f"    - `{query}`")
        lines.append("- `preferred_sources`:")
        if entry["source_types"]:
            for source_type in entry["source_types"]:
                lines.append(f"  - `{source_type}`")
        else:
            lines.append("  - `stock-library`")
        lines.append("- `fallback`:")
        lines.append(f"  - {entry['fallback'] or '自制图卡 / 录屏 / 截图动效'}")
        if entry["required_coverage_seconds"] > 0:
            lines.append(f"- `required_coverage_seconds`: `{entry['required_coverage_seconds']}`")
        shortlist = chapter_shortlists.get(chapter_id, [])
        if shortlist:
            lines.append("- `matched_results`:")
            for result in shortlist:
                lines.append(
                    f"  - `{result['provider']}` / `{result['provider_asset_id']}` / score `{result['match_score']}` / {result['title']}"
                )
        if entry["direct_source_urls"]:
            lines.append("- `direct_source_urls`:")
            for direct_url in entry["direct_source_urls"]:
                lines.append(f"  - `{direct_url}`")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def download_with_ytdlp(binary: str, source_url: str, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_binary = resolve_executable_path(binary, display_name="yt-dlp")
    command = [resolved_binary, "--no-progress", "--no-part", "-o", str(target_path), source_url]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        raise RuntimeError(stderr or str(exc)) from exc


def download_candidate_asset(
    *,
    item: dict[str, Any],
    project_root: Path,
    yt_dlp_bin: str,
    base_dir_name: str,
    index: int,
    source_track: str,
) -> dict[str, Any]:
    extension = Path(urlparse(str(item["download_url"] or item["page_url"] or "")).path).suffix or ".mp4"
    target_dir = project_root / "assets" / base_dir_name / str(item["chapter_id"])
    target_dir.mkdir(parents=True, exist_ok=True)
    clip_id = item.get("clip_id") or f"{item['provider']}-{item['provider_asset_id']}"
    target_path = target_dir / f"{slugify(str(item['provider']))}-{slugify(str(clip_id))}{extension}"
    source_url = str(item.get("source_url") or item.get("page_url") or item.get("download_url") or "")
    if item["provider"] == "yt-dlp":
        download_with_ytdlp(yt_dlp_bin, source_url, target_path)
        asset_bytes = target_path.read_bytes()
    else:
        asset_bytes = read_bytes_from_url(str(item["download_url"]))
        target_path.write_bytes(asset_bytes)
    return {
        "clip_id": clip_id,
        "chapter_id": item["chapter_id"],
        "provider": item["provider"],
        "source_url": source_url,
        "download_url": item["download_url"],
        "local_path": relative_to_project(target_path, project_root),
        "file_size_bytes": len(asset_bytes),
        "license_status": item["license_status"],
        "license_basis": item["license_basis"],
        "source_type": item.get("source_type") or "",
        "source_track": source_track,
        "attribution_required": item["attribution_required"],
        "attribution_text": item["attribution_text"],
        "usage_scope": item.get("usage_scope") or ["b-roll"],
        "uploader": item.get("uploader") or "",
        "uploader_url": item.get("uploader_url") or "",
    }


def compute_chapter_coverage_report(
    *,
    content_id: str,
    generated_at: str,
    clip_briefs: list[dict[str, Any]],
    chapter_shortlists: dict[str, list[dict[str, Any]]],
    approved_manifest_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    approved_by_chapter: dict[str, list[dict[str, Any]]] = {}
    for entry in approved_manifest_entries:
        approved_by_chapter.setdefault(str(entry["chapter_id"]), []).append(entry)

    chapter_reports: list[dict[str, Any]] = []
    overall_status = "pass"

    for chapter in clip_briefs:
        chapter_id = chapter["chapter_id"]
        shortlist = chapter_shortlists.get(chapter_id, [])
        approved = approved_by_chapter.get(chapter_id, [])
        shortlist_duration = sum(float(item.get("duration_seconds") or 0) for item in shortlist)
        approved_duration = sum(float(item.get("duration_seconds") or 0) for item in approved)
        required_coverage_seconds = float(chapter.get("required_coverage_seconds") or 0)
        minimum_candidates = int(chapter.get("minimum_candidates") or 2)
        max_single_asset_seconds = float(chapter.get("max_single_asset_seconds") or 30)
        longest_asset_seconds = max([float(item.get("duration_seconds") or 0) for item in approved], default=0.0)
        single_asset_risk = required_coverage_seconds > 0 and longest_asset_seconds >= required_coverage_seconds >= max_single_asset_seconds

        issues: list[str] = []
        status = "pass"
        if required_coverage_seconds <= 0:
            status = "revise"
            issues.append("required_coverage_seconds_missing")
        if len(shortlist) < minimum_candidates:
            status = "revise" if status == "pass" else status
            issues.append("candidate_count_below_target")
        if required_coverage_seconds > 0 and approved_duration < required_coverage_seconds:
            status = "block"
            issues.append("approved_duration_below_required_coverage")
        if single_asset_risk:
            status = "revise" if status == "pass" else status
            issues.append("single_asset_static_risk")
        if not chapter.get("fallback"):
            status = "revise" if status == "pass" else status
            issues.append("fallback_missing")

        if status == "block":
            overall_status = "block"
        elif status == "revise" and overall_status == "pass":
            overall_status = "revise"

        chapter_reports.append(
            {
                "chapter_id": chapter_id,
                "required_coverage_seconds": required_coverage_seconds,
                "shortlist_candidate_count": len(shortlist),
                "approved_candidate_count": len(approved),
                "shortlist_duration_seconds": round(shortlist_duration, 3),
                "approved_duration_seconds": round(approved_duration, 3),
                "longest_approved_asset_seconds": round(longest_asset_seconds, 3),
                "minimum_candidates": minimum_candidates,
                "max_single_asset_seconds": max_single_asset_seconds,
                "has_fallback": bool(chapter.get("fallback")),
                "single_asset_risk": single_asset_risk,
                "status": status,
                "issues": issues,
            }
        )

    return {
        "content_id": content_id,
        "generated_at": generated_at,
        "overall_status": overall_status,
        "coverage_summary": {
            "chapter_count": len(chapter_reports),
            "pass_count": len([item for item in chapter_reports if item["status"] == "pass"]),
            "revise_count": len([item for item in chapter_reports if item["status"] == "revise"]),
            "block_count": len([item for item in chapter_reports if item["status"] == "block"]),
        },
        "chapters": chapter_reports,
    }


def main() -> int:
    args = parse_args()
    prefer_http_proxy_over_all_proxy()
    project_root = resolve_project_root(args)
    if not project_root.exists():
        raise FileNotFoundError(f"project root does not exist: {project_root}")

    content_packet_path = detect_content_packet(project_root)
    content_packet = load_json(content_packet_path)
    packet = primary_packet(content_packet)
    clip_briefs = normalize_clip_briefs(content_packet)
    providers = instantiate_providers(args.providers, yt_dlp_bin=args.yt_dlp_bin)

    provider_summary: dict[str, dict[str, int]] = {
        provider.name: {"queries_attempted": 0, "results_found": 0, "query_failures": 0, "download_failures": 0}
        for provider in providers
    }
    provider_errors: list[dict[str, Any]] = []
    chapter_results: dict[str, dict[str, dict[str, Any]]] = {}

    for chapter in clip_briefs:
        chapter_id = chapter["chapter_id"]
        chapter_results[chapter_id] = {}
        for provider in providers:
            chapter_queries = chapter_queries_for_provider(chapter, provider.name)
            for query in chapter_queries:
                provider_summary[provider.name]["queries_attempted"] += 1
                try:
                    results = provider.search(query, args.max_results_per_query)
                except Exception as exc:
                    provider_summary[provider.name]["query_failures"] += 1
                    provider_errors.append(
                        error_payload(
                            provider=provider.name,
                            chapter_id=chapter_id,
                            stage="search",
                            target=query,
                            exc=exc,
                        )
                    )
                    continue
                provider_summary[provider.name]["results_found"] += len(results)
                for result in results:
                    candidate = candidate_payload(chapter, query, result)
                    existing = chapter_results[chapter_id].get(candidate_key(candidate))
                    if existing is None or candidate["match_score"] > existing["match_score"]:
                        chapter_results[chapter_id][candidate_key(candidate)] = candidate
        direct_source_urls = chapter["direct_source_urls"]
        if direct_source_urls:
            for provider in providers:
                if provider.name != "yt-dlp":
                    continue
                yt_dlp_provider = provider
                for source_url in direct_source_urls:
                    provider_summary[provider.name]["queries_attempted"] += 1
                    try:
                        result = yt_dlp_provider.inspect_url(source_url, chapter["source_types"])
                    except Exception as exc:
                        provider_summary[provider.name]["query_failures"] += 1
                        provider_errors.append(
                            error_payload(
                                provider=provider.name,
                                chapter_id=chapter_id,
                                stage="inspect_url",
                                target=source_url,
                                exc=exc,
                            )
                        )
                        continue
                    provider_summary[provider.name]["results_found"] += 1
                    candidate = candidate_payload(chapter, source_url, result)
                    candidate["match_score"] = 1.0
                    chapter_results[chapter_id][candidate_key(candidate)] = candidate

    chapter_exploration_shortlists: dict[str, list[dict[str, Any]]] = {}
    chapter_shortlists: dict[str, list[dict[str, Any]]] = {}
    for chapter in clip_briefs:
        chapter_id = chapter["chapter_id"]
        ranked = sorted(
            chapter_results.get(chapter_id, {}).values(),
            key=lambda item: (item["match_score"], provider_priority(item.get("provider")), item["duration_seconds"] or 0),
            reverse=True,
        )
        chapter_exploration_shortlists[chapter_id] = diversify_ranked_candidates(
            ranked,
            limit=args.max_exploration_per_chapter,
        )
        production_ranked = [
            item for item in ranked if is_production_eligible(item)
        ]
        chapter_shortlists[chapter_id] = diversify_ranked_candidates(
            production_ranked,
            limit=args.max_shortlist_per_chapter,
        )
    chapter_approved_candidates = choose_chapter_approved_candidates(
        clip_briefs=clip_briefs,
        chapter_shortlists=chapter_shortlists,
        approved_per_chapter=args.approved_per_chapter,
    )

    approved_manifest_entries: list[dict[str, Any]] = []
    hold_items: list[dict[str, Any]] = []
    attribution_notes: list[str] = []
    assembly_suggestions: list[dict[str, Any]] = []
    fallback_options: list[dict[str, Any]] = []

    for chapter in clip_briefs:
        chapter_id = chapter["chapter_id"]
        shortlist = chapter_shortlists.get(chapter_id, [])
        approved_for_chapter = chapter_approved_candidates.get(chapter_id, [])
        if approved_for_chapter:
            recommended_clip_ids: list[str] = []
            for item in approved_for_chapter:
                clip_id = f"{item['provider']}-{item['provider_asset_id']}"
                recommended_clip_ids.append(clip_id)
                approved_manifest_entries.append(
                    {
                        "clip_id": clip_id,
                        "chapter_id": chapter_id,
                        "shot_purpose": item["shot_purpose"],
                        "duration_seconds": item["duration_seconds"],
                        "source_type": item["source_type"],
                        "source_name": item["provider"],
                        "source_url": item["page_url"],
                        "download_url": item["download_url"],
                        "license_status": item["license_status"],
                        "license_basis": item["license_basis"],
                        "attribution_required": item["attribution_required"],
                        "attribution_text": item["attribution_text"],
                        "usage_scope": ["b-roll"],
                        "in_point": "",
                        "out_point": "",
                        "editorial_risk": "low",
                        "usage_notes": item["usage_notes"],
                        "fallback_query": item["fallback_query"],
                        "fallback_clip_id": "",
                        "uploader": item.get("uploader") or "",
                        "uploader_url": item.get("uploader_url") or "",
                    }
                )
                if item["attribution_required"]:
                    attribution_notes.append(
                        f"{clip_id}: {item['attribution_text'] or 'Credit the source before publish.'}"
                    )
            assembly_suggestions.append(
                {
                    "chapter_id": chapter_id,
                    "recommended_clip_ids": recommended_clip_ids,
                    "editing_notes": chapter["shot_intent"],
                }
            )
        else:
            hold_items.append(
                {
                    "clip_id": f"hold-{chapter_id}",
                    "reason": "No approved external footage candidate with positive relevance score.",
                    "next_action": chapter["fallback"] or "Fallback to screenshots, screen recording, graphics, or brand-owned footage.",
                }
            )
        fallback_options.append(
            {
                "chapter_id": chapter_id,
                "fallback_type": "screen-capture",
                "description": chapter["fallback"] or "Fallback to screenshots, screen recording, graphics, or brand-owned footage.",
            }
        )

    clip_queries = [
        {
            "chapter_id": chapter["chapter_id"],
            "shot_purpose": chapter["shot_intent"],
            "keywords": {
                "zh": [],
                "en": chapter["queries"],
                "variants": chapter["queries"],
            },
            "source_types": chapter["source_types"] or ["stock-library"],
        }
        for chapter in clip_briefs
    ]

    flat_results = [
        item
        for chapter in clip_briefs
        for item in chapter_shortlists.get(chapter["chapter_id"], [])
    ]
    exploration_results = [
        item
        for chapter in clip_briefs
        for item in chapter_exploration_shortlists.get(chapter["chapter_id"], [])
    ]

    generated_at = datetime.now(timezone.utc).isoformat()
    content_id = str(packet.get("content_id") or project_root.name)
    deliverable_type = str(packet.get("deliverable_type") or "")
    platform = str((packet.get("platforms") or [packet.get("platform") or ""])[0] or "")

    source_manifest_payload = {
        "project_id": str(packet.get("project_id") or ""),
        "content_id": content_id,
        "deliverable_type": deliverable_type or "midlong-video",
        "platform": platform,
        "status": "sourced" if approved_manifest_entries else "needs_fallback",
        "generated_at": generated_at,
        "source_policy": {
            "allowed_source_types": ALLOWED_SOURCE_TYPES,
            "blocked_source_types": BLOCKED_SOURCE_TYPES,
        },
        "clip_queries": clip_queries,
        "source_shortlist": flat_results,
        "source_manifest": approved_manifest_entries,
        "license_summary": {
            "approved_count": len([item for item in approved_manifest_entries if item["license_status"] == "approved"]),
            "hold_count": len([item for item in approved_manifest_entries if item["license_status"] == "hold"]) + len(hold_items),
            "rejected_count": len([item for item in approved_manifest_entries if item["license_status"] == "rejected"]),
            "needs_attribution_count": len([item for item in approved_manifest_entries if item["attribution_required"]]),
        },
        "attribution_notes": sorted(set(attribution_notes)),
        "hold_items": hold_items,
        "assembly_suggestions": assembly_suggestions,
        "fallback_options": fallback_options,
        "provider_errors": provider_errors,
    }

    ingest_assets: list[dict[str, Any]] = []
    download_errors: list[dict[str, Any]] = []
    approved_to_download = approved_manifest_entries
    if args.download_limit > 0:
        approved_to_download = approved_to_download[: args.download_limit]

    if args.download_approved:
        downloaded_clip_ids: set[str] = set()
        for index, item in enumerate(approved_to_download, start=1):
            clip_id = str(item.get("clip_id") or "")
            if clip_id in downloaded_clip_ids:
                continue
            try:
                ingest_assets.append(
                    download_candidate_asset(
                        item={
                            **item,
                            "provider": item["source_name"],
                            "source_url": item["source_url"],
                        },
                        project_root=project_root,
                        yt_dlp_bin=args.yt_dlp_bin,
                        base_dir_name="external",
                        index=index,
                        source_track="production",
                    )
                )
                if clip_id:
                    downloaded_clip_ids.add(clip_id)
            except Exception as exc:
                provider_name = str(item.get("source_name") or item.get("provider") or "unknown")
                if provider_name in provider_summary:
                    provider_summary[provider_name]["download_failures"] += 1
                download_errors.append(
                    error_payload(
                        provider=provider_name,
                        chapter_id=str(item.get("chapter_id") or ""),
                        stage="download",
                        target=str(item.get("download_url") or item.get("source_url") or ""),
                        clip_id=str(item.get("clip_id") or ""),
                        exc=exc,
                    )
                )

        local_paths: dict[str, str] = {}
        for record in ingest_assets:
            local_paths.setdefault(record["clip_id"], record["local_path"])
        source_manifest_payload = {
            **source_manifest_payload,
            "source_manifest": [
                {**entry, "local_asset_path": local_paths.get(entry["clip_id"], "")}
                for entry in approved_manifest_entries
            ],
        }

    exploration_ingest_assets: list[dict[str, Any]] = []
    exploration_download_errors: list[dict[str, Any]] = []
    if args.download_exploration:
        approved_keys = {item["clip_id"] for item in approved_manifest_entries}
        exploration_candidates_by_chapter = {
            chapter["chapter_id"]: [
                {
                    **item,
                    "clip_id": f"{item['provider']}-{item['provider_asset_id']}",
                    "source_url": item["page_url"],
                    "usage_scope": ["b-roll"],
                }
                for item in chapter_exploration_shortlists.get(chapter["chapter_id"], [])
                if f"{item['provider']}-{item['provider_asset_id']}" not in approved_keys
            ]
            for chapter in clip_briefs
        }
        exploration_to_download = distribute_candidates_by_chapter(
            clip_briefs=clip_briefs,
            chapter_candidates=exploration_candidates_by_chapter,
            limit=args.exploration_download_limit,
        )
        if args.exploration_download_limit > 0:
            exploration_to_download = exploration_to_download[: args.exploration_download_limit]
        downloaded_exploration_clip_ids: set[str] = set()
        for index, item in enumerate(exploration_to_download, start=1):
            clip_id = str(item.get("clip_id") or "")
            if clip_id in downloaded_exploration_clip_ids:
                continue
            try:
                exploration_ingest_assets.append(
                    download_candidate_asset(
                        item=item,
                        project_root=project_root,
                        yt_dlp_bin=args.yt_dlp_bin,
                        base_dir_name="exploration",
                        index=index,
                        source_track="exploration",
                    )
                )
                if clip_id:
                    downloaded_exploration_clip_ids.add(clip_id)
            except Exception as exc:
                provider_name = str(item.get("provider") or "unknown")
                if provider_name in provider_summary:
                    provider_summary[provider_name]["download_failures"] += 1
                exploration_download_errors.append(
                    error_payload(
                        provider=provider_name,
                        chapter_id=str(item.get("chapter_id") or ""),
                        stage="download_exploration",
                        target=str(item.get("download_url") or item.get("source_url") or ""),
                        clip_id=str(item.get("clip_id") or ""),
                        exc=exc,
                    )
                )

    source_shortlist_payload = {
        "content_id": content_id,
        "generated_at": generated_at,
        "providers": [provider.name for provider in providers],
        "provider_errors": provider_errors,
        "results": flat_results,
        "chapters": [
            {
                "chapter_id": chapter["chapter_id"],
                "shot_intent": chapter["shot_intent"],
                "fallback": chapter["fallback"],
                "results": chapter_shortlists.get(chapter["chapter_id"], []),
            }
            for chapter in clip_briefs
        ],
    }
    exploration_shortlist_payload = {
        "content_id": content_id,
        "generated_at": generated_at,
        "providers": [provider.name for provider in providers],
        "provider_errors": provider_errors,
        "results": exploration_results,
        "chapters": [
            {
                "chapter_id": chapter["chapter_id"],
                "shot_intent": chapter["shot_intent"],
                "fallback": chapter["fallback"],
                "results": chapter_exploration_shortlists.get(chapter["chapter_id"], []),
            }
            for chapter in clip_briefs
        ],
    }
    coverage_report_payload = compute_chapter_coverage_report(
        content_id=content_id,
        generated_at=generated_at,
        clip_briefs=clip_briefs,
        chapter_shortlists=chapter_shortlists,
        approved_manifest_entries=approved_manifest_entries,
    )

    ingest_manifest_payload = {
        "content_id": content_id,
        "generated_at": generated_at,
        "download_approved": bool(args.download_approved),
        "download_limit": args.download_limit,
        "provider_summary": provider_summary,
        "ingested_assets": ingest_assets,
        "download_errors": download_errors,
    }
    exploration_ingest_payload = {
        "content_id": content_id,
        "generated_at": generated_at,
        "download_exploration": bool(args.download_exploration),
        "download_limit": args.exploration_download_limit,
        "provider_summary": provider_summary,
        "ingested_assets": exploration_ingest_assets,
        "download_errors": exploration_download_errors,
    }

    source_manifest_path = project_root / args.source_manifest_output
    source_shortlist_path = project_root / args.source_shortlist_output
    asset_ingest_path = project_root / args.asset_ingest_output
    exploration_shortlist_path = project_root / args.exploration_shortlist_output
    exploration_ingest_path = project_root / args.exploration_ingest_output
    coverage_report_path = project_root / args.coverage_report_output
    query_sheet_path = project_root / args.query_sheet_output

    for output_path in (
        source_manifest_path,
        source_shortlist_path,
        asset_ingest_path,
        exploration_shortlist_path,
        exploration_ingest_path,
        coverage_report_path,
        query_sheet_path,
    ):
        output_path.parent.mkdir(parents=True, exist_ok=True)

    source_manifest_path.write_text(json.dumps(source_manifest_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    source_shortlist_path.write_text(json.dumps(source_shortlist_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    asset_ingest_path.write_text(json.dumps(ingest_manifest_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    exploration_shortlist_path.write_text(json.dumps(exploration_shortlist_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    exploration_ingest_path.write_text(json.dumps(exploration_ingest_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    coverage_report_path.write_text(json.dumps(coverage_report_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    query_sheet_path.write_text(
        build_query_sheet(content_id=content_id, clip_briefs=clip_briefs, chapter_shortlists=chapter_exploration_shortlists),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "project_root": str(project_root),
                "content_packet": str(content_packet_path),
                "providers": [provider.name for provider in providers],
                "provider_summary": provider_summary,
                "source_manifest": str(source_manifest_path),
                "source_shortlist": str(source_shortlist_path),
                "asset_ingest_manifest": str(asset_ingest_path),
                "exploration_shortlist": str(exploration_shortlist_path),
                "exploration_ingest_manifest": str(exploration_ingest_path),
                "chapter_coverage_report": str(coverage_report_path),
                "query_sheet": str(query_sheet_path),
                "approved_count": len(source_manifest_payload["source_manifest"]),
                "ingested_count": len(ingest_assets),
                "exploration_ingested_count": len(exploration_ingest_assets),
                "failed_download_count": len(download_errors),
                "exploration_failed_download_count": len(exploration_download_errors),
                "provider_error_count": len(provider_errors),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
