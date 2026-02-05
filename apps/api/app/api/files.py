"""
Files API - File browser endpoints for project files.

Provides read-only file tree browsing and file content viewing.
"""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.core.terminal_ui import ui


router = APIRouter()


class FileNode(BaseModel):
    """File tree node representation."""
    name: str
    type: str  # "file" or "directory"
    path: str
    children: Optional[List["FileNode"]] = None


class FileTreeResponse(BaseModel):
    """Response for file tree endpoint."""
    tree: List[FileNode]


class FileContentResponse(BaseModel):
    """Response for file content endpoint."""
    content: str
    encoding: str = "utf-8"
    size: int
    mime_type: Optional[str] = None


class FileSaveRequest(BaseModel):
    """Request body for saving file content."""
    content: str


def _validate_project_path(project_id: str, file_path: str = "") -> Path:
    """Validate and resolve project file path.

    Security: Prevents directory traversal attacks.
    """
    project_root = Path(settings.projects_root) / project_id

    if not project_root.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    # Resolve the full path
    if file_path:
        full_path = (project_root / file_path).resolve()
    else:
        full_path = project_root.resolve()

    # Security check: ensure path is within project directory
    try:
        full_path.relative_to(project_root.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied: path outside project directory")

    return full_path


def _get_mime_type(filename: str) -> Optional[str]:
    """Get MIME type based on file extension."""
    ext = Path(filename).suffix.lower()
    mime_types = {
        ".html": "text/html",
        ".htm": "text/html",
        ".css": "text/css",
        ".js": "application/javascript",
        ".json": "application/json",
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".py": "text/x-python",
        ".ts": "text/typescript",
        ".tsx": "text/typescript-jsx",
        ".jsx": "text/javascript-jsx",
        ".yaml": "text/yaml",
        ".yml": "text/yaml",
        ".xml": "application/xml",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".ico": "image/x-icon",
    }
    return mime_types.get(ext)


def _build_file_tree(directory: Path, base_path: Path) -> List[FileNode]:
    """Build file tree recursively.

    Args:
        directory: Current directory to scan
        base_path: Project root for relative paths
    """
    nodes = []

    try:
        entries = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
    except PermissionError:
        return nodes

    for entry in entries:
        # Skip hidden files and common ignore patterns
        if entry.name.startswith(".") or entry.name in ("__pycache__", "node_modules", ".git"):
            continue

        relative_path = str(entry.relative_to(base_path))

        if entry.is_dir():
            children = _build_file_tree(entry, base_path)
            nodes.append(FileNode(
                name=entry.name,
                type="directory",
                path=relative_path,
                children=children
            ))
        else:
            nodes.append(FileNode(
                name=entry.name,
                type="file",
                path=relative_path
            ))

    return nodes


@router.get("/{project_id}/files", response_model=FileTreeResponse)
async def get_file_tree(project_id: str):
    """Get the file tree for a project.

    Returns a hierarchical tree of all files and directories in the project.
    Hidden files and common ignore patterns (node_modules, __pycache__) are excluded.
    """
    project_path = _validate_project_path(project_id)

    ui.debug(f"Building file tree for project: {project_id}", "Files")

    tree = _build_file_tree(project_path, project_path)

    return FileTreeResponse(tree=tree)


@router.get("/{project_id}/files/{file_path:path}", response_model=FileContentResponse)
async def get_file_content(project_id: str, file_path: str):
    """Get the content of a specific file.

    Returns the file content as text. Binary files are not supported.
    """
    full_path = _validate_project_path(project_id, file_path)

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if full_path.is_dir():
        raise HTTPException(status_code=400, detail="Cannot read directory as file")

    ui.debug(f"Reading file: {file_path}", "Files")

    # Check file size (limit to 1MB for safety)
    file_size = full_path.stat().st_size
    if file_size > 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 1MB)")

    try:
        content = full_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=415, detail="Binary file not supported")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

    return FileContentResponse(
        content=content,
        encoding="utf-8",
        size=file_size,
        mime_type=_get_mime_type(full_path.name)
    )


@router.put("/{project_id}/files/{file_path:path}")
async def save_file_content(project_id: str, file_path: str, request: FileSaveRequest):
    """Save content to a file.

    Creates the file if it doesn't exist, or overwrites existing content.
    Parent directories are created automatically.
    """
    full_path = _validate_project_path(project_id, file_path)

    ui.info(f"Saving file: {file_path}", "Files")

    # Create parent directories if needed
    full_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        full_path.write_text(request.content, encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")

    return {"success": True, "path": file_path}
