"""
Preview API - Static file serving for project previews.

Serves static files (HTML, CSS, JS, images) from project directories
for in-browser preview functionality.
"""
import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.terminal_ui import ui


router = APIRouter()

# Initialize mimetypes
mimetypes.init()

# Additional MIME types not in the standard library
EXTRA_MIME_TYPES = {
    ".md": "text/markdown",
    ".tsx": "text/typescript-jsx",
    ".ts": "text/typescript",
    ".jsx": "text/javascript-jsx",
    ".vue": "text/x-vue",
    ".svelte": "text/x-svelte",
    ".yaml": "text/yaml",
    ".yml": "text/yaml",
    ".toml": "text/toml",
}


def _get_mime_type(file_path: Path) -> str:
    """Get MIME type for a file."""
    ext = file_path.suffix.lower()

    # Check extra types first
    if ext in EXTRA_MIME_TYPES:
        return EXTRA_MIME_TYPES[ext]

    # Use standard mimetypes library
    mime_type, _ = mimetypes.guess_type(str(file_path))
    return mime_type or "application/octet-stream"


def _validate_project_path(project_id: str, file_path: str) -> Path:
    """Validate and resolve project file path.

    Security: Prevents directory traversal attacks.
    """
    project_root = Path(settings.projects_root) / project_id

    if not project_root.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    # Resolve the full path
    full_path = (project_root / file_path).resolve()

    # Security check: ensure path is within project directory
    try:
        full_path.relative_to(project_root.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied: path outside project directory")

    return full_path


@router.get("/{project_id}/{file_path:path}")
async def serve_preview_file(project_id: str, file_path: str):
    """Serve a static file from a project directory.

    This endpoint serves files with appropriate MIME types for browser preview.
    Supports HTML, CSS, JS, images, SVG, and other static assets.
    """
    full_path = _validate_project_path(project_id, file_path)

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if full_path.is_dir():
        # Try to serve index.html from directory
        index_path = full_path / "index.html"
        if index_path.exists():
            full_path = index_path
        else:
            raise HTTPException(status_code=400, detail="Cannot serve directory")

    mime_type = _get_mime_type(full_path)

    ui.debug(f"Serving preview: {file_path} ({mime_type})", "Preview")

    # For text files, we might want to set proper encoding
    if mime_type.startswith("text/"):
        return FileResponse(
            path=full_path,
            media_type=mime_type,
            headers={"Content-Type": f"{mime_type}; charset=utf-8"}
        )

    return FileResponse(path=full_path, media_type=mime_type)


@router.get("/{project_id}")
async def serve_project_index(project_id: str):
    """Serve the index.html of a project if it exists."""
    return await serve_preview_file(project_id, "index.html")
