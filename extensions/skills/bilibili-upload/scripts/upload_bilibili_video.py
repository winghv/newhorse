#!/usr/bin/env python3
"""Upload a Bilibili video via biliup, with optional cover support."""

from __future__ import annotations

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


SCHEDULE_FORMAT = "%Y-%m-%d %H:%M"


def normalize_system(system_name: str | None = None) -> str:
    system_value = (system_name or platform.system()).strip().lower()
    if system_value == "darwin":
        return "macos"
    return system_value


def normalize_machine(machine_name: str | None = None) -> str:
    machine_value = (machine_name or platform.machine()).strip().lower()
    aliases = {
        "amd64": "x86_64",
        "x64": "x86_64",
        "arm64": "aarch64",
    }
    return aliases.get(machine_value, machine_value)


def build_platform_key() -> str:
    return f"{normalize_system()}-{normalize_machine()}"


def build_biliup_runtime_path() -> Path:
    executable_name = "biliup.exe" if normalize_system() == "windows" else "biliup"
    return Path.home() / ".social-auto-upload" / "tools" / "biliup" / build_platform_key() / executable_name


def find_fallback_biliup_binary() -> Path | None:
    runtime_root = Path.home() / ".social-auto-upload" / "tools" / "biliup"
    if not runtime_root.exists():
        return None

    candidates = [
        path.resolve()
        for path in runtime_root.rglob("*")
        if path.is_file() and path.name in {"biliup", "biliup.exe"}
    ]
    if not candidates:
        return None

    preferred_key = build_platform_key()
    candidates.sort(key=lambda item: (preferred_key not in str(item), len(str(item))))
    return candidates[0]


def resolve_biliup_binary() -> Path:
    direct_path = build_biliup_runtime_path()
    if direct_path.exists():
        return direct_path.resolve()

    fallback = find_fallback_biliup_binary()
    if fallback is not None:
        return fallback

    raise FileNotFoundError(
        "Unable to find biliup runtime under ~/.social-auto-upload/tools/biliup. "
        "Run a Bilibili command via sau once to bootstrap biliup."
    )


def discover_sau_source_roots() -> list[Path]:
    roots: list[Path] = []
    env_root = (Path.home() / ".local" / "src")

    explicit_root = None
    for key in ("SAU_SOURCE_ROOT", "SOCIAL_AUTO_UPLOAD_SOURCE_ROOT"):
        value = os.environ.get(key)
        if value:
            explicit_root = Path(value).expanduser().resolve()
            break
    if explicit_root is not None:
        roots.append(explicit_root)

    sau_executable = shutil.which("sau")
    if sau_executable:
        try:
            first_line = Path(sau_executable).read_text(encoding="utf-8").splitlines()[0]
        except (OSError, IndexError):
            first_line = ""
        if first_line.startswith("#!"):
            python_path = Path(first_line[2:].strip()).expanduser()
            tool_root = python_path.resolve().parents[1]
            site_packages = list((tool_root / "lib").glob("python*/site-packages"))
            for site_package_root in site_packages:
                for finder in site_package_root.glob("__editable___social_auto_upload_*_finder.py"):
                    try:
                        payload = finder.read_text(encoding="utf-8")
                    except OSError:
                        continue
                    match = re.search(r"'sau_cli': '([^']+)'", payload)
                    if match:
                        roots.append(Path(match.group(1)).resolve().parent)

    if env_root.exists():
        candidates = sorted(
            (path.resolve() for path in env_root.glob("social-auto-upload*") if path.is_dir()),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        roots.extend(candidates)

    deduped: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if root in seen:
            continue
        seen.add(root)
        deduped.append(root)
    return deduped


def resolve_account_file(account_name: str) -> Path:
    file_name = f"bilibili_{account_name}.json"
    source_roots = discover_sau_source_roots()
    candidates = [root / "cookies" / file_name for root in source_roots]

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    searched = ", ".join(str(path.parent) for path in candidates) or "no candidate directories found"
    raise FileNotFoundError(
        f"Unable to locate Bilibili account file for '{account_name}'. "
        f"Expected {file_name}. Searched: {searched}. "
        f"Run `sau bilibili login --account {account_name}` first."
    )


def existing_file(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"File not found: {value}")
    return path


def parse_schedule(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.strptime(value, SCHEDULE_FORMAT)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    schedule_help = SCHEDULE_FORMAT.replace("%", "%%")
    parser.add_argument("--account", required=True, help="Bilibili account name configured in sau.")
    parser.add_argument("--file", required=True, type=existing_file, help="Video file to upload.")
    parser.add_argument("--title", required=True, help="Video title.")
    parser.add_argument("--desc", required=True, help="Video description.")
    parser.add_argument("--tid", required=True, type=int, help="Bilibili partition id.")
    parser.add_argument("--tags", default="", help="Comma-separated tags.")
    parser.add_argument("--schedule", default=None, help=f"Schedule time in {schedule_help}.")
    parser.add_argument("--thumbnail", type=existing_file, help="Optional cover image.")
    return parser.parse_args()


def build_command(args: argparse.Namespace) -> list[str]:
    account_file = resolve_account_file(args.account)
    biliup_binary = resolve_biliup_binary()
    command = [
        str(biliup_binary),
        "-u",
        str(account_file),
        "upload",
        str(args.file),
        "--title",
        args.title,
        "--desc",
        args.desc,
        "--tid",
        str(args.tid),
    ]

    tags = [item.strip().lstrip("#") for item in args.tags.split(",") if item.strip()]
    if tags:
        command.extend(["--tag", ",".join(tags)])

    schedule_at = parse_schedule(args.schedule)
    if schedule_at is not None:
        command.extend(["--dtime", str(int(schedule_at.timestamp()))])

    if args.thumbnail is not None:
        command.extend(["--cover", str(args.thumbnail)])

    return command


def main() -> int:
    args = parse_args()
    command = build_command(args)
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
