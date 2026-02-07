"""
Newhorse Configuration
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel


def find_project_root() -> Path:
    """Find the project root directory."""
    current_path = Path(__file__).resolve()

    for parent in [current_path] + list(current_path.parents):
        if (parent / 'apps').is_dir() and (parent / 'package.json').exists():
            return parent

    api_dir = current_path.parent.parent.parent
    if api_dir.name == 'api' and api_dir.parent.name == 'apps':
        return api_dir.parent.parent

    return Path.cwd()


PROJECT_ROOT = find_project_root()
load_dotenv(os.path.join(PROJECT_ROOT, ".env"), override=True)


class Settings(BaseModel):
    """Application settings"""

    api_port: int = int(os.getenv("API_PORT", "8080"))

    # Database
    database_url: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{PROJECT_ROOT / 'data' / 'newhorse.db'}",
    )

    # Projects storage
    projects_root: str = os.getenv(
        "PROJECTS_ROOT",
        str(PROJECT_ROOT / "data" / "projects")
    )

    # User-created agent templates
    agents_root: str = os.getenv(
        "AGENTS_ROOT",
        str(PROJECT_ROOT / "data" / "agents")
    )

    # Claude sessions path
    claude_sessions_root: str = os.getenv(
        "CLAUDE_SESSIONS_ROOT",
        str(Path.home() / ".claude" / "projects")
    )

    # Environment
    environment: str = os.getenv("THS_TIER", "dev")

    # Database pool settings
    db_pool_size: int = int(os.getenv("DB_POOL_SIZE", "10"))
    db_max_overflow: int = int(os.getenv("DB_MAX_OVERFLOW", "5"))

    # Async DB
    use_async_db: bool = os.getenv("USE_ASYNC_DB", "true").lower() in ("true", "1", "yes")

    # Project root path
    project_root: str = str(PROJECT_ROOT)


settings = Settings()
