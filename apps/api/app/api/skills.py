"""
Skills API router - list, upload (zip), and delete custom skills.
"""
import io
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

import yaml
from fastapi import APIRouter, HTTPException, Query, UploadFile, File

from app.core.config import settings, PROJECT_ROOT
from app.core.terminal_ui import ui

router = APIRouter()

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_ZIP_ENTRIES = 50

GLOBAL_SKILLS_DIR = PROJECT_ROOT / "extensions" / "skills"


def _project_skills_dir(project_id: str) -> Path:
    return Path(settings.projects_root) / project_id / ".claude" / "skills"


def _parse_skill_frontmatter(skill_dir: Path) -> Optional[dict]:
    """Read SKILL.md from *skill_dir* and return parsed frontmatter dict, or None."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return None
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return None

    # Extract YAML between first pair of '---' fences
    if not text.startswith("---"):
        return None
    end = text.find("---", 3)
    if end == -1:
        return None
    front = text[3:end].strip()
    if not front:
        return None
    try:
        meta = yaml.safe_load(front)
    except yaml.YAMLError:
        return None
    if not isinstance(meta, dict):
        return None

    return {
        "id": skill_dir.name,
        "name": meta.get("name", skill_dir.name),
        "description": meta.get("description", ""),
        "version": meta.get("version", ""),
    }


@router.get("")
def list_skills(project_id: Optional[str] = Query(None)):
    """List global and (optionally) project-level skills."""
    skills: list[dict] = []

    # Global skills
    if GLOBAL_SKILLS_DIR.is_dir():
        for child in sorted(GLOBAL_SKILLS_DIR.iterdir()):
            if child.is_dir():
                info = _parse_skill_frontmatter(child)
                if info:
                    info["scope"] = "global"
                    skills.append(info)

    # Project skills
    if project_id:
        proj_dir = _project_skills_dir(project_id)
        if proj_dir.is_dir():
            for child in sorted(proj_dir.iterdir()):
                if child.is_dir():
                    info = _parse_skill_frontmatter(child)
                    if info:
                        info["scope"] = "project"
                        skills.append(info)

    return {"skills": skills}


@router.post("/upload")
async def upload_skill(
    file: UploadFile = File(...),
    scope: str = Query("project"),
    project_id: Optional[str] = Query(None),
    overwrite: bool = Query(False),
):
    """Upload a skill as a .zip file."""
    # --- basic validation -------------------------------------------------
    if scope not in ("project", "global"):
        raise HTTPException(400, "scope must be 'project' or 'global'")
    if scope == "project" and not project_id:
        raise HTTPException(400, "project_id is required for project scope")

    filename = file.filename or ""
    if not filename.lower().endswith(".zip"):
        raise HTTPException(400, "Only .zip files are accepted")

    data = await file.read()
    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(400, f"File exceeds {MAX_UPLOAD_SIZE // (1024*1024)} MB limit")

    # --- zip safety checks ------------------------------------------------
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise HTTPException(400, "Invalid zip file")

    entries = zf.namelist()
    if len(entries) > MAX_ZIP_ENTRIES:
        raise HTTPException(400, f"Zip contains more than {MAX_ZIP_ENTRIES} entries")

    for entry in entries:
        if entry.startswith("/") or ".." in entry.split("/"):
            raise HTTPException(400, f"Unsafe path in zip: {entry}")

    # --- determine skill_id and locate SKILL.md ---------------------------
    # Filter out macOS resource fork entries before analysing structure
    clean_entries = [e for e in entries if not e.startswith("__MACOSX/") and not e.startswith("._")]

    # Check if all entries share a single top-level directory
    top_dirs = {e.split("/")[0] for e in clean_entries if "/" in e}
    root_files = [e for e in clean_entries if "/" not in e and e != ""]

    skill_md_found = False
    has_top_dir = False
    skill_id = ""

    if len(top_dirs) == 1 and not root_files:
        # Everything under one directory
        has_top_dir = True
        skill_id = top_dirs.pop()
        skill_md_found = f"{skill_id}/SKILL.md" in entries or f"{skill_id}/SKILL.md" in clean_entries
    else:
        # Files at root level
        skill_md_found = "SKILL.md" in clean_entries

    if not skill_md_found:
        raise HTTPException(400, "Zip must contain a SKILL.md file")

    # Parse frontmatter from the zip
    if has_top_dir:
        md_content = zf.read(f"{skill_id}/SKILL.md").decode("utf-8")
    else:
        md_content = zf.read("SKILL.md").decode("utf-8")

    meta = _parse_frontmatter_text(md_content)
    if not meta or not meta.get("name") or not meta.get("description"):
        raise HTTPException(400, "SKILL.md frontmatter must contain 'name' and 'description'")

    if not has_top_dir:
        # Use sanitised name as directory
        skill_id = meta["name"].lower().replace(" ", "-")

    # --- determine target path --------------------------------------------
    if scope == "global":
        target = GLOBAL_SKILLS_DIR / skill_id
    else:
        target = _project_skills_dir(project_id) / skill_id  # type: ignore[arg-type]

    if target.exists() and not overwrite:
        raise HTTPException(409, f"Skill '{skill_id}' already exists. Use ?overwrite=true to replace.")

    # --- extract to temp then move ----------------------------------------
    with tempfile.TemporaryDirectory() as tmpdir:
        zf.extractall(tmpdir)
        src = Path(tmpdir) / skill_id if has_top_dir else Path(tmpdir)

        if target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(str(src), str(target))

    ui.success(f"Skill '{skill_id}' uploaded ({scope})", "SkillsAPI")

    return {
        "success": True,
        "skill": {
            "id": skill_id,
            "name": meta.get("name", skill_id),
            "description": meta.get("description", ""),
            "version": meta.get("version", ""),
            "scope": scope,
        },
    }


@router.delete("/{skill_id}")
def delete_skill(
    skill_id: str,
    scope: str = Query("project"),
    project_id: Optional[str] = Query(None),
):
    """Delete a project-level skill. Global skills cannot be deleted via API."""
    if scope != "project":
        raise HTTPException(403, "Only project-level skills can be deleted via API")
    if not project_id:
        raise HTTPException(400, "project_id is required")

    # Prevent path traversal
    if "/" in skill_id or "\\" in skill_id or ".." in skill_id:
        raise HTTPException(400, "Invalid skill_id")

    target = _project_skills_dir(project_id) / skill_id
    if not target.exists():
        raise HTTPException(404, f"Skill '{skill_id}' not found")

    shutil.rmtree(target)
    ui.info(f"Skill '{skill_id}' deleted from project {project_id}", "SkillsAPI")

    return {"success": True}


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _parse_frontmatter_text(text: str) -> Optional[dict]:
    """Parse YAML frontmatter from raw markdown text."""
    if not text.startswith("---"):
        return None
    end = text.find("---", 3)
    if end == -1:
        return None
    front = text[3:end].strip()
    if not front:
        return None
    try:
        return yaml.safe_load(front)
    except yaml.YAMLError:
        return None
