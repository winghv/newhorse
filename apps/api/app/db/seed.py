"""
Seed built-in providers and their default models.
Runs on startup — skips if providers already exist.
"""
import uuid

from sqlalchemy.orm import Session as DBSession
from app.db.base import SessionLocal
from app.models.provider import Provider, ProviderModel
from app.core.terminal_ui import ui


def _short_id() -> str:
    return str(uuid.uuid4())[:8]


BUILTIN_PROVIDERS = [
    {
        "name": "Anthropic",
        "protocol": "anthropic",
        "base_url": None,
        "models": [
            ("claude-sonnet-4-5-20250929", "Sonnet 4.5", True),
            ("claude-opus-4-5-20251101", "Opus 4.5", False),
            ("claude-3-5-haiku-20241022", "Haiku 3.5", False),
        ],
    },
    {
        "name": "OpenAI",
        "protocol": "openai",
        "base_url": None,
        "models": [
            ("gpt-4o", "GPT-4o", True),
            ("gpt-4o-mini", "GPT-4o Mini", False),
        ],
    },
    {
        "name": "Deepseek",
        "protocol": "openai",
        "base_url": "https://api.deepseek.com",
        "models": [
            ("deepseek-chat", "Deepseek V3", True),
            ("deepseek-reasoner", "Deepseek R1", False),
        ],
    },
    {
        "name": "Qwen",
        "protocol": "openai",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": [
            ("qwen-plus", "Qwen Plus", True),
            ("qwen-turbo", "Qwen Turbo", False),
            ("qwen-max", "Qwen Max", False),
        ],
    },
    {
        "name": "GLM",
        "protocol": "openai",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": [
            ("glm-4-plus", "GLM-4 Plus", True),
            ("glm-4-flash", "GLM-4 Flash", False),
        ],
    },
]


def seed_providers():
    """Seed built-in providers if they don't exist yet."""
    db: DBSession = SessionLocal()
    try:
        existing = db.query(Provider).filter(Provider.is_builtin == True).count()
        if existing > 0:
            ui.debug(f"Built-in providers already seeded ({existing})", "Seed")
            return

        for p in BUILTIN_PROVIDERS:
            provider = Provider(
                id=_short_id(),
                name=p["name"],
                protocol=p["protocol"],
                base_url=p["base_url"],
                api_key=None,
                is_builtin=True,
                enabled=True,
            )
            db.add(provider)
            db.flush()

            for model_id, display_name, is_default in p["models"]:
                model = ProviderModel(
                    id=_short_id(),
                    provider_id=provider.id,
                    model_id=model_id,
                    display_name=display_name,
                    is_default=is_default,
                )
                db.add(model)

        db.commit()
        ui.success(f"Seeded {len(BUILTIN_PROVIDERS)} built-in providers", "Seed")
    except Exception as e:
        db.rollback()
        ui.error(f"Failed to seed providers: {e}", "Seed")
    finally:
        db.close()
