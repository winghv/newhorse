#!/usr/bin/env python3
"""Populate English translations for voiceover segments via MiniMax text/chat API."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_MODEL = "M2.7-highspeed"
DEFAULT_FALLBACK_MODELS = ("MiniMax-M2.7-highspeed", "MiniMax-M2.5", "MiniMax-M2", "MiniMax-M1", "MiniMax-Text-01")
DEFAULT_ENDPOINT = "/v1/text/chatcompletion_v2"
DEFAULT_TIMEOUT_SECONDS = 45.0
DEFAULT_MAX_RETRIES = 3
PROGRESS_FLUSH_INTERVAL = 10
DEFAULT_BATCH_SIZE = 10


class UnsupportedModelError(RuntimeError):
    """Raised when MiniMax reports the requested model is unavailable."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", help="Media package root directory.")
    parser.add_argument("--content-id", help="Content package id under the media-ops root.")
    parser.add_argument(
        "--media-ops-root",
        help="Root directory containing media packages. Defaults to repo-local data/media-ops.",
    )
    parser.add_argument(
        "--segments-file",
        help="Segments JSON path, relative to project root. Defaults to voiceover-profile render target.",
    )
    parser.add_argument(
        "--output",
        help="Optional output path. Defaults to in-place update of --segments-file.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"MiniMax text model id (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        help=f"MiniMax chat endpoint path (default: {DEFAULT_ENDPOINT}).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing translation_en values.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"HTTP timeout in seconds (default: {DEFAULT_TIMEOUT_SECONDS}).",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=DEFAULT_MAX_RETRIES,
        help=f"Max retries per segment (default: {DEFAULT_MAX_RETRIES}).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Number of segments to translate per request (default: {DEFAULT_BATCH_SIZE}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run API calls and report summary without writing output.",
    )
    args = parser.parse_args()
    if not args.project_root and not args.content_id:
        parser.error("one of --project-root or --content-id is required")
    if args.max_retries < 1:
        parser.error("--max-retries must be >= 1")
    if args.batch_size < 1:
        parser.error("--batch-size must be >= 1")
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


def resolve_candidate(project_root: Path, raw_path: str | None) -> Path | None:
    if not raw_path:
        return None
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = project_root / candidate
    return candidate.resolve()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_segments_path(project_root: Path, provided: str | None) -> Path:
    if provided:
        resolved = resolve_candidate(project_root, provided)
        if resolved is None:
            raise FileNotFoundError("segments file not found")
        return resolved
    profile_path = project_root / "content" / "postproduction" / "voiceover-profile.json"
    profile = load_json(profile_path) if profile_path.exists() else {}
    render_targets = profile.get("render_targets") if isinstance(profile.get("render_targets"), dict) else {}
    resolved = resolve_candidate(project_root, render_targets.get("segments_file"))
    if resolved and resolved.exists():
        return resolved
    fallback = project_root / "content" / "postproduction" / "voiceover-segments.json"
    if fallback.exists():
        return fallback.resolve()
    raise FileNotFoundError("voiceover segments file is required")


def ensure_env() -> tuple[str, str]:
    api_host = str(os.getenv("MINIMAX_API_HOST") or "").strip()
    api_key = str(os.getenv("MINIMAX_API_KEY") or "").strip()
    if not api_host:
        raise RuntimeError("MINIMAX_API_HOST is required")
    if not api_key:
        raise RuntimeError("MINIMAX_API_KEY is required")
    return api_host.rstrip("/"), api_key


def build_messages(text: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are a professional subtitle translator for Chinese knowledge videos. "
                "Translate into concise natural English suitable for on-screen subtitles. "
                "Return only the translated English sentence without explanations."
            ),
        },
        {
            "role": "user",
            "content": f"Translate this Chinese subtitle into English:\n{text.strip()}",
        },
    ]


def build_batch_messages(items: list[tuple[int, str]]) -> list[dict[str, str]]:
    lines = [f"{index}. {text.strip()}" for index, text in items]
    return [
        {
            "role": "system",
            "content": (
                "You are a professional subtitle translator for Chinese knowledge videos. "
                "Translate into concise natural English suitable for on-screen subtitles. "
                "Return only a JSON array. Each item must be an object with keys "
                '"index" and "translation_en". Do not add commentary or markdown fences.'
            ),
        },
        {
            "role": "user",
            "content": (
                "Translate the following Chinese subtitle lines into English and keep the same index numbers.\n"
                "Return JSON only.\n\n"
                + "\n".join(lines)
            ),
        },
    ]


def extract_translation(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    candidates: list[str] = []
    output_text = payload.get("output_text")
    if isinstance(output_text, str):
        candidates.append(output_text)
    reply = payload.get("reply")
    if isinstance(reply, str):
        candidates.append(reply)
    data = payload.get("data")
    if isinstance(data, dict):
        for key in ("reply", "text", "output_text", "content"):
            value = data.get(key)
            if isinstance(value, str):
                candidates.append(value)
        choices = data.get("choices")
        if isinstance(choices, list):
            for item in choices:
                if not isinstance(item, dict):
                    continue
                message = item.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str):
                        candidates.append(content)
    choices = payload.get("choices")
    if isinstance(choices, list):
        for item in choices:
            if not isinstance(item, dict):
                continue
            message = item.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    candidates.append(content)
    for raw in candidates:
        text = normalize_translation(raw)
        if text:
            return text
    return ""


def extract_base_status(payload: Any) -> tuple[int | None, str]:
    if not isinstance(payload, dict):
        return None, ""
    base_resp = payload.get("base_resp")
    if not isinstance(base_resp, dict):
        return None, ""
    status_code = base_resp.get("status_code")
    return (int(status_code), str(base_resp.get("status_msg") or "")) if isinstance(status_code, int) else (None, str(base_resp.get("status_msg") or ""))


def model_candidates(primary_model: str) -> list[str]:
    ordered = [primary_model, *DEFAULT_FALLBACK_MODELS]
    unique: list[str] = []
    for model in ordered:
        normalized = str(model or "").strip()
        if normalized and normalized not in unique:
            unique.append(normalized)
    return unique


def normalize_translation(text: str) -> str:
    normalized = " ".join(text.replace("\n", " ").split()).strip()
    if normalized.startswith('"') and normalized.endswith('"') and len(normalized) >= 2:
        normalized = normalized[1:-1].strip()
    if normalized.startswith("'") and normalized.endswith("'") and len(normalized) >= 2:
        normalized = normalized[1:-1].strip()
    return normalized


def extract_json_payload(raw_text: str) -> Any:
    normalized = raw_text.strip()
    if not normalized:
        raise RuntimeError("empty response content")
    candidates = [normalized]
    code_fence = re.findall(r"```(?:json)?\s*(.*?)```", normalized, flags=re.DOTALL | re.IGNORECASE)
    candidates.extend(item.strip() for item in code_fence if item.strip())
    bracket_match = re.search(r"(\[\s*.*\])", normalized, flags=re.DOTALL)
    if bracket_match:
        candidates.append(bracket_match.group(1).strip())
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    raise RuntimeError("response did not contain parseable JSON")


def request_translation(
    *,
    api_host: str,
    api_key: str,
    endpoint: str,
    model: str,
    text: str,
    timeout: float,
    max_retries: int,
) -> str:
    endpoint_path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
    url = f"{api_host}{endpoint_path}"
    last_error: Exception | None = None
    for candidate_model in model_candidates(model):
        payload = {
            "model": candidate_model,
            "messages": build_messages(text),
            "temperature": 0.1,
            "stream": False,
        }
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url=url,
            method="POST",
            data=raw,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
        for attempt in range(1, max_retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    body = response.read().decode("utf-8")
                    parsed = json.loads(body)
                    status_code, status_msg = extract_base_status(parsed)
                    if status_code not in (None, 0):
                        normalized_status = status_msg.lower()
                        if any(token in normalized_status for token in ("unknown model", "not support model")):
                            raise UnsupportedModelError(f"unsupported model: {candidate_model}")
                        raise RuntimeError(f"MiniMax error {status_code}: {status_msg}")
                    translation = extract_translation(parsed)
                    if not translation:
                        raise RuntimeError("MiniMax response missing translation content")
                    return translation
            except UnsupportedModelError as error:
                last_error = error
                break
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, RuntimeError) as error:
                last_error = error
                if attempt >= max_retries:
                    break
                time.sleep(1.2 * attempt)
    raise RuntimeError(f"translation request failed after {max_retries} attempts: {last_error}")


def request_translation_batch(
    *,
    api_host: str,
    api_key: str,
    endpoint: str,
    model: str,
    items: list[tuple[int, str]],
    timeout: float,
    max_retries: int,
) -> dict[int, str]:
    endpoint_path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
    url = f"{api_host}{endpoint_path}"
    last_error: Exception | None = None
    for candidate_model in model_candidates(model):
        payload = {
            "model": candidate_model,
            "messages": build_batch_messages(items),
            "temperature": 0.1,
            "stream": False,
        }
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url=url,
            method="POST",
            data=raw,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
        for attempt in range(1, max_retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    body = response.read().decode("utf-8")
                    parsed = json.loads(body)
                    status_code, status_msg = extract_base_status(parsed)
                    if status_code not in (None, 0):
                        normalized_status = status_msg.lower()
                        if any(token in normalized_status for token in ("unknown model", "not support model")):
                            raise UnsupportedModelError(f"unsupported model: {candidate_model}")
                        raise RuntimeError(f"MiniMax error {status_code}: {status_msg}")
                    content = extract_translation(parsed)
                    batch_payload = extract_json_payload(content)
                    if not isinstance(batch_payload, list):
                        raise RuntimeError("batch translation response must be a JSON array")
                    translations: dict[int, str] = {}
                    for item in batch_payload:
                        if not isinstance(item, dict):
                            continue
                        raw_index = item.get("index")
                        raw_translation = item.get("translation_en")
                        if not isinstance(raw_index, int) or not isinstance(raw_translation, str):
                            continue
                        translation = normalize_translation(raw_translation)
                        if translation:
                            translations[raw_index] = translation
                    expected_indexes = {index for index, _ in items}
                    if set(translations) != expected_indexes:
                        raise RuntimeError("batch translation response missing expected indexes")
                    return translations
            except UnsupportedModelError as error:
                last_error = error
                break
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, RuntimeError) as error:
                last_error = error
                if attempt >= max_retries:
                    break
                time.sleep(1.2 * attempt)
    raise RuntimeError(f"batch translation request failed after {max_retries} attempts: {last_error}")


def load_segments_payload(path: Path) -> tuple[Any, list[dict[str, Any]]]:
    payload = load_json(path)
    if isinstance(payload, list):
        return payload, payload
    if isinstance(payload, dict) and isinstance(payload.get("segments"), list):
        return payload, payload["segments"]
    raise ValueError("segments file must contain a JSON array or {\"segments\": [...]}")


def has_translation(segment: dict[str, Any]) -> bool:
    translation = segment.get("translation_en")
    return isinstance(translation, str) and bool(translation.strip())


def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args)
    segments_path = resolve_segments_path(project_root, args.segments_file)
    output_path = resolve_candidate(project_root, args.output) if args.output else segments_path
    if output_path is None:
        output_path = segments_path

    api_host, api_key = ensure_env()
    root_payload, segments = load_segments_payload(segments_path)

    updated = 0
    skipped_existing = 0
    skipped_empty = 0
    failures: list[dict[str, Any]] = []
    processed = 0
    pending_batch: list[tuple[int, str]] = []

    def flush_batch(batch: list[tuple[int, str]]) -> None:
        nonlocal updated, failures
        if not batch:
            return
        try:
            translations = request_translation_batch(
                api_host=api_host,
                api_key=api_key,
                endpoint=args.endpoint,
                model=args.model,
                items=batch,
                timeout=args.timeout,
                max_retries=args.max_retries,
            )
            for index, _ in batch:
                segment = segments[index]
                if not isinstance(segment, dict):
                    continue
                translated = translations.get(index)
                if translated:
                    segment["translation_en"] = translated
                    updated += 1
                else:
                    failures.append({"index": index, "text": str(segment.get("text") or "")[:80], "error": "missing translated item in batch"})
        except Exception as error:  # noqa: BLE001
            for index, text in batch:
                failures.append({"index": index, "text": text[:80], "error": str(error)})

    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            continue
        text = str(segment.get("text") or "").strip()
        if not text:
            skipped_empty += 1
            processed += 1
            continue
        if has_translation(segment) and not args.overwrite:
            skipped_existing += 1
            processed += 1
            continue
        pending_batch.append((index, text))
        processed += 1
        if len(pending_batch) >= args.batch_size:
            flush_batch(pending_batch)
            pending_batch = []
        if processed % PROGRESS_FLUSH_INTERVAL == 0:
            if pending_batch:
                flush_batch(pending_batch)
                pending_batch = []
            if not args.dry_run:
                write_json(output_path, root_payload)
            progress = {
                "event": "translation_progress",
                "processed": processed,
                "segments_total": len(segments),
                "translated_count": updated,
                "skipped_existing_count": skipped_existing,
                "failed_count": len(failures),
            }
            print(json.dumps(progress, ensure_ascii=False), flush=True)

    if pending_batch:
        flush_batch(pending_batch)

    if not args.dry_run:
        write_json(output_path, root_payload)

    summary = {
        "project_root": str(project_root),
        "segments_file": str(segments_path),
        "output": str(output_path),
        "model": args.model,
        "endpoint": args.endpoint,
        "segments_total": len(segments),
        "translated_count": updated,
        "skipped_existing_count": skipped_existing,
        "skipped_empty_count": skipped_empty,
        "failed_count": len(failures),
        "dry_run": args.dry_run,
        "failures": failures[:10],
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
