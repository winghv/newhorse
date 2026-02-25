# Multi-Provider Model Configuration — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Support multiple AI providers (Anthropic, OpenAI, Deepseek, Qwen, GLM) with custom base_url/api_key overrides, where model selection takes effect immediately in chat.

**Architecture:** Two-SDK approach — AnthropicRunner wraps existing Claude Agent SDK (full agent capabilities), OpenAIRunner uses OpenAI SDK for streaming chat completions. A Router dispatches based on provider protocol. Provider/model config stored in DB with Fernet-encrypted API keys.

**Tech Stack:** FastAPI, SQLAlchemy, OpenAI Python SDK, cryptography (Fernet), Next.js 14, React, Tailwind CSS

**Design Doc:** `docs/plans/2026-02-24-multi-provider-model-config-design.md`

---

## Phase 1: Backend Foundation

### Task 1: Add dependencies and ProviderProtocol enum

**Files:**
- Modify: `apps/api/requirements.txt`
- Modify: `apps/api/app/common/types.py`

**Step 1: Add Python dependencies**

In `apps/api/requirements.txt`, add after the `claude-agent-sdk` line:

```
# Multi-provider support
openai>=1.30
cryptography>=42.0
```

Run: `cd apps/api && pip install openai cryptography`

**Step 2: Add ProviderProtocol enum**

In `apps/api/app/common/types.py`, add after the `AgentType` class:

```python
class ProviderProtocol(str, Enum):
    """Supported provider API protocols"""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    # Future: GEMINI = "gemini"

    @classmethod
    def from_value(cls, value: str):
        for item in cls:
            if item.value == value:
                return item
        return None
```

**Step 3: Commit**

```bash
git add apps/api/requirements.txt apps/api/app/common/types.py
git commit -m "feat: add openai/cryptography deps and ProviderProtocol enum"
```

---

### Task 2: Create crypto utility

**Files:**
- Create: `apps/api/app/services/crypto.py`
- Modify: `apps/api/app/core/config.py`
- Modify: `.env.example`

**Step 1: Add ENCRYPTION_KEY to config**

In `apps/api/app/core/config.py`, add to the `Settings` class:

```python
encryption_key: str = os.getenv("ENCRYPTION_KEY", "")
```

In `.env.example`, add at the end:

```bash
# Encryption key for API key storage (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
ENCRYPTION_KEY=
```

**Step 2: Create crypto module**

Create `apps/api/app/services/crypto.py`:

```python
"""
API Key encryption/decryption using Fernet symmetric encryption.
Falls back to plaintext storage if ENCRYPTION_KEY is not set (dev mode).
"""
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.core.terminal_ui import ui


def _get_fernet() -> Fernet | None:
    """Get Fernet instance if encryption key is configured."""
    if not settings.encryption_key:
        return None
    try:
        return Fernet(settings.encryption_key.encode())
    except Exception as e:
        ui.warning(f"Invalid ENCRYPTION_KEY: {e}", "Crypto")
        return None


def encrypt_api_key(plaintext: str) -> str:
    """Encrypt an API key. Returns plaintext if no encryption key configured."""
    if not plaintext:
        return ""
    f = _get_fernet()
    if f is None:
        return plaintext
    return f.encrypt(plaintext.encode()).decode()


def decrypt_api_key(ciphertext: str) -> str:
    """Decrypt an API key. Returns as-is if not encrypted or no key configured."""
    if not ciphertext:
        return ""
    f = _get_fernet()
    if f is None:
        return ciphertext
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        # Not encrypted (legacy or dev mode) — return as-is
        return ciphertext


def mask_api_key(key: str) -> str:
    """Mask an API key for display: show first 12 chars + ***"""
    if not key:
        return ""
    if len(key) <= 12:
        return "***"
    return key[:12] + "***"
```

**Step 3: Commit**

```bash
git add apps/api/app/services/crypto.py apps/api/app/core/config.py .env.example
git commit -m "feat: add Fernet crypto utility for API key encryption"
```

---

### Task 3: Create Provider and ProviderModel data models

**Files:**
- Create: `apps/api/app/models/provider.py`
- Modify: `apps/api/app/models/__init__.py`

**Step 1: Create provider models**

Create `apps/api/app/models/provider.py`:

```python
"""
Provider and ProviderModel models
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class Provider(Base):
    """AI provider configuration (e.g. Anthropic, OpenAI, Deepseek)"""

    __tablename__ = "providers"

    id = Column(String(8), primary_key=True)
    name = Column(String(255), nullable=False)
    protocol = Column(String(32), nullable=False)  # "anthropic" or "openai"
    base_url = Column(String(512), nullable=True)   # None = SDK default
    api_key = Column(Text, nullable=True)            # Fernet-encrypted
    is_builtin = Column(Boolean, default=False)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    models = relationship("ProviderModel", back_populates="provider", cascade="all, delete-orphan")


class ProviderModel(Base):
    """Available model for a provider"""

    __tablename__ = "provider_models"

    id = Column(String(8), primary_key=True)
    provider_id = Column(String(8), ForeignKey("providers.id", ondelete="CASCADE"), nullable=False)
    model_id = Column(String(128), nullable=False)      # e.g. "claude-sonnet-4-5-20250929"
    display_name = Column(String(128), nullable=False)   # e.g. "Sonnet 4.5"
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    provider = relationship("Provider", back_populates="models")
```

**Step 2: Register models in `__init__.py`**

In `apps/api/app/models/__init__.py`, update to:

```python
"""
Models module
"""
from .projects import Project
from .sessions import Session
from .messages import Message
from .provider import Provider, ProviderModel

__all__ = ["Project", "Session", "Message", "Provider", "ProviderModel"]
```

**Step 3: Commit**

```bash
git add apps/api/app/models/provider.py apps/api/app/models/__init__.py
git commit -m "feat: add Provider and ProviderModel data models"
```

---

### Task 4: Seed built-in providers and add DB migration helper

**Files:**
- Create: `apps/api/app/db/seed.py`
- Create: `apps/api/app/db/migrate.py`
- Modify: `apps/api/app/main.py`

**Step 1: Create migration helper**

The project uses `Base.metadata.create_all()` which creates new tables but won't add columns to existing ones. We need a helper for adding columns to `projects` and `messages`.

Create `apps/api/app/db/migrate.py`:

```python
"""
Lightweight schema migration for SQLite development.
Adds missing columns to existing tables.
"""
from sqlalchemy import inspect, text
from app.db.base import engine
from app.core.terminal_ui import ui


def _column_exists(inspector, table: str, column: str) -> bool:
    columns = [c["name"] for c in inspector.get_columns(table)]
    return column in columns


def run_migrations():
    """Add any missing columns to existing tables."""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    with engine.connect() as conn:
        # Projects table: add override_provider_id, override_api_key
        if "projects" in existing_tables:
            if not _column_exists(inspector, "projects", "override_provider_id"):
                conn.execute(text("ALTER TABLE projects ADD COLUMN override_provider_id VARCHAR(8)"))
                ui.info("Added projects.override_provider_id", "Migration")
            if not _column_exists(inspector, "projects", "override_api_key"):
                conn.execute(text("ALTER TABLE projects ADD COLUMN override_api_key TEXT"))
                ui.info("Added projects.override_api_key", "Migration")

        # Messages table: add model_id, provider_id
        if "messages" in existing_tables:
            if not _column_exists(inspector, "messages", "model_id"):
                conn.execute(text("ALTER TABLE messages ADD COLUMN model_id VARCHAR(128)"))
                ui.info("Added messages.model_id", "Migration")
            if not _column_exists(inspector, "messages", "provider_id"):
                conn.execute(text("ALTER TABLE messages ADD COLUMN provider_id VARCHAR(8)"))
                ui.info("Added messages.provider_id", "Migration")

        conn.commit()
```

**Step 2: Create seed data**

Create `apps/api/app/db/seed.py`:

```python
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
            db.flush()  # Get provider.id

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
```

**Step 3: Wire into startup**

In `apps/api/app/main.py`, add imports after existing imports (line 14):

```python
from app.db.migrate import run_migrations
from app.db.seed import seed_providers
```

In the `on_startup()` function, after `Base.metadata.create_all(bind=engine)` (after line 71), add:

```python
    # Run lightweight migrations (add columns to existing tables)
    run_migrations()

    # Seed built-in providers
    seed_providers()
```

**Step 4: Commit**

```bash
git add apps/api/app/db/seed.py apps/api/app/db/migrate.py apps/api/app/main.py
git commit -m "feat: add provider seed data and migration helper"
```

---

### Task 5: Extend Project and Message models

**Files:**
- Modify: `apps/api/app/models/projects.py`
- Modify: `apps/api/app/models/messages.py`
- Modify: `apps/api/app/api/projects.py`

**Step 1: Add override fields to Project model**

In `apps/api/app/models/projects.py`, add two columns after `selected_model` (after line 22):

```python
    override_provider_id = Column(String(8), nullable=True)
    override_api_key = Column(Text, nullable=True)  # Fernet-encrypted
```

**Step 2: Add tracking fields to Message model**

In `apps/api/app/models/messages.py`, add after `metadata_json` (after line 21):

```python
    model_id = Column(String(128), nullable=True)
    provider_id = Column(String(8), nullable=True)
```

**Step 3: Update ProjectResponse schema**

In `apps/api/app/api/projects.py`, find the `ProjectResponse` Pydantic model and add:

```python
    override_provider_id: Optional[str] = None
```

Do NOT expose `override_api_key` in the response (security).

Also update the PATCH endpoint handler to accept the new fields. Find the PATCH handler and add handling for:

```python
if "override_provider_id" in data:
    project.override_provider_id = data["override_provider_id"]
if "override_api_key" in data:
    from app.services.crypto import encrypt_api_key
    raw_key = data["override_api_key"]
    project.override_api_key = encrypt_api_key(raw_key) if raw_key else None
```

**Step 4: Commit**

```bash
git add apps/api/app/models/projects.py apps/api/app/models/messages.py apps/api/app/api/projects.py
git commit -m "feat: extend Project and Message models for multi-provider"
```

---

### Task 6: Create Provider CRUD API

**Files:**
- Create: `apps/api/app/api/providers.py`
- Modify: `apps/api/app/api/__init__.py`
- Modify: `apps/api/app/main.py`

**Step 1: Create providers API router**

Create `apps/api/app/api/providers.py`:

```python
"""
Provider management API
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.provider import Provider, ProviderModel
from app.services.crypto import encrypt_api_key, decrypt_api_key, mask_api_key
from app.core.terminal_ui import ui

router = APIRouter()


# --- Pydantic Schemas ---

class ProviderResponse(BaseModel):
    id: str
    name: str
    protocol: str
    base_url: Optional[str] = None
    api_key_masked: str = ""
    has_api_key: bool = False
    is_builtin: bool = False
    enabled: bool = True
    models: list = []

class ProviderCreate(BaseModel):
    name: str
    protocol: str  # "anthropic" or "openai"
    base_url: Optional[str] = None
    api_key: Optional[str] = None

class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    enabled: Optional[bool] = None

class ModelCreate(BaseModel):
    model_id: str
    display_name: str
    is_default: bool = False

class ModelUpdate(BaseModel):
    model_id: Optional[str] = None
    display_name: Optional[str] = None
    is_default: Optional[bool] = None

class VerifyResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    latency_ms: Optional[int] = None


# --- Helpers ---

def _provider_to_response(p: Provider) -> dict:
    raw_key = decrypt_api_key(p.api_key) if p.api_key else ""
    return {
        "id": p.id,
        "name": p.name,
        "protocol": p.protocol,
        "base_url": p.base_url,
        "api_key_masked": mask_api_key(raw_key),
        "has_api_key": bool(p.api_key),
        "is_builtin": p.is_builtin,
        "enabled": p.enabled,
        "models": [
            {
                "id": m.id,
                "model_id": m.model_id,
                "display_name": m.display_name,
                "is_default": m.is_default,
            }
            for m in p.models
        ],
    }


def _short_id() -> str:
    return str(uuid.uuid4())[:8]


# --- Provider Endpoints ---

@router.get("/")
def list_providers(db: Session = Depends(get_db)):
    """List all providers with masked API keys."""
    providers = db.query(Provider).order_by(Provider.is_builtin.desc(), Provider.created_at).all()
    return [_provider_to_response(p) for p in providers]


@router.post("/")
def create_provider(body: ProviderCreate, db: Session = Depends(get_db)):
    """Create a custom provider."""
    provider = Provider(
        id=_short_id(),
        name=body.name,
        protocol=body.protocol,
        base_url=body.base_url,
        api_key=encrypt_api_key(body.api_key) if body.api_key else None,
        is_builtin=False,
        enabled=True,
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    ui.info(f"Created provider: {provider.name}", "Providers")
    return _provider_to_response(provider)


@router.patch("/{provider_id}")
def update_provider(provider_id: str, body: ProviderUpdate, db: Session = Depends(get_db)):
    """Update a provider."""
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    if body.name is not None:
        provider.name = body.name
    if body.base_url is not None:
        if provider.is_builtin:
            raise HTTPException(status_code=400, detail="Cannot change base_url of built-in provider")
        provider.base_url = body.base_url
    if body.api_key is not None:
        provider.api_key = encrypt_api_key(body.api_key) if body.api_key else None
    if body.enabled is not None:
        provider.enabled = body.enabled

    db.commit()
    db.refresh(provider)
    return _provider_to_response(provider)


@router.delete("/{provider_id}")
def delete_provider(provider_id: str, db: Session = Depends(get_db)):
    """Delete a custom provider (built-in cannot be deleted)."""
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    if provider.is_builtin:
        raise HTTPException(status_code=400, detail="Cannot delete built-in provider")

    db.delete(provider)
    db.commit()
    return {"ok": True}


# --- Model Endpoints ---

@router.get("/{provider_id}/models")
def list_models(provider_id: str, db: Session = Depends(get_db)):
    """List models for a provider."""
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return [
        {
            "id": m.id,
            "model_id": m.model_id,
            "display_name": m.display_name,
            "is_default": m.is_default,
        }
        for m in provider.models
    ]


@router.post("/{provider_id}/models")
def create_model(provider_id: str, body: ModelCreate, db: Session = Depends(get_db)):
    """Add a model to a provider."""
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    # If setting as default, unset other defaults
    if body.is_default:
        db.query(ProviderModel).filter(
            ProviderModel.provider_id == provider_id,
            ProviderModel.is_default == True
        ).update({"is_default": False})

    model = ProviderModel(
        id=_short_id(),
        provider_id=provider_id,
        model_id=body.model_id,
        display_name=body.display_name,
        is_default=body.is_default,
    )
    db.add(model)
    db.commit()
    return {"id": model.id, "model_id": model.model_id, "display_name": model.display_name, "is_default": model.is_default}


@router.patch("/{provider_id}/models/{model_id}")
def update_model(provider_id: str, model_id: str, body: ModelUpdate, db: Session = Depends(get_db)):
    """Update a model."""
    model = db.query(ProviderModel).filter(
        ProviderModel.id == model_id,
        ProviderModel.provider_id == provider_id
    ).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    if body.model_id is not None:
        model.model_id = body.model_id
    if body.display_name is not None:
        model.display_name = body.display_name
    if body.is_default is not None:
        if body.is_default:
            db.query(ProviderModel).filter(
                ProviderModel.provider_id == provider_id,
                ProviderModel.is_default == True,
                ProviderModel.id != model_id
            ).update({"is_default": False})
        model.is_default = body.is_default

    db.commit()
    return {"id": model.id, "model_id": model.model_id, "display_name": model.display_name, "is_default": model.is_default}


@router.delete("/{provider_id}/models/{model_id}")
def delete_model(provider_id: str, model_id: str, db: Session = Depends(get_db)):
    """Remove a model from a provider."""
    model = db.query(ProviderModel).filter(
        ProviderModel.id == model_id,
        ProviderModel.provider_id == provider_id
    ).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    db.delete(model)
    db.commit()
    return {"ok": True}


# --- Verify Endpoint ---

@router.post("/{provider_id}/verify")
async def verify_provider(provider_id: str, db: Session = Depends(get_db)):
    """Verify provider connectivity by sending a minimal request."""
    import time

    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    raw_key = decrypt_api_key(provider.api_key) if provider.api_key else ""
    if not raw_key:
        return VerifyResponse(success=False, error="No API key configured")

    # Find default model for this provider
    default_model = db.query(ProviderModel).filter(
        ProviderModel.provider_id == provider_id,
        ProviderModel.is_default == True
    ).first()
    if not default_model:
        default_model = db.query(ProviderModel).filter(
            ProviderModel.provider_id == provider_id
        ).first()
    if not default_model:
        return VerifyResponse(success=False, error="No models configured for this provider")

    start = time.time()

    try:
        if provider.protocol == "anthropic":
            import anthropic
            client = anthropic.Anthropic(
                api_key=raw_key,
                base_url=provider.base_url or "https://api.anthropic.com",
            )
            client.messages.create(
                model=default_model.model_id,
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}],
            )
        elif provider.protocol == "openai":
            from openai import OpenAI
            client = OpenAI(
                api_key=raw_key,
                base_url=provider.base_url or "https://api.openai.com/v1",
            )
            client.chat.completions.create(
                model=default_model.model_id,
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}],
            )

        latency = int((time.time() - start) * 1000)
        return VerifyResponse(success=True, latency_ms=latency)

    except Exception as e:
        latency = int((time.time() - start) * 1000)
        return VerifyResponse(success=False, error=str(e), latency_ms=latency)
```

**Step 2: Create aggregated models endpoint**

Create `apps/api/app/api/models.py`:

```python
"""
Aggregated model list API — returns all models grouped by enabled provider.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.provider import Provider

router = APIRouter()


@router.get("/")
def list_all_models(db: Session = Depends(get_db)):
    """List all models from enabled providers, grouped by provider."""
    providers = db.query(Provider).filter(
        Provider.enabled == True
    ).order_by(Provider.is_builtin.desc(), Provider.name).all()

    result = []
    for p in providers:
        if not p.models:
            continue
        result.append({
            "provider_id": p.id,
            "provider_name": p.name,
            "protocol": p.protocol,
            "has_api_key": bool(p.api_key),
            "models": [
                {
                    "id": m.id,
                    "model_id": m.model_id,
                    "display_name": m.display_name,
                    "is_default": m.is_default,
                }
                for m in p.models
            ],
        })
    return result
```

**Step 3: Register routes**

In `apps/api/app/api/__init__.py`, add:

```python
from .providers import router as providers_router
from .models import router as models_router
```

Update `__all__` to include `"providers_router"` and `"models_router"`.

In `apps/api/app/main.py`, add to imports:

```python
from app.api import providers_router, models_router
```

Add after the existing `include_router` calls:

```python
app.include_router(providers_router, prefix="/api/providers", tags=["providers"])
app.include_router(models_router, prefix="/api/models", tags=["models"])
```

**Step 4: Commit**

```bash
git add apps/api/app/api/providers.py apps/api/app/api/models.py apps/api/app/api/__init__.py apps/api/app/main.py
git commit -m "feat: add provider CRUD and aggregated models API"
```

---

## Phase 2: Backend Model Routing

### Task 7: Create Runner abstraction

**Files:**
- Create: `apps/api/app/services/cli/runners/__init__.py`
- Create: `apps/api/app/services/cli/runners/base_runner.py`

**Step 1: Create runners module**

Create `apps/api/app/services/cli/runners/__init__.py`:

```python
"""
Model runners — dispatch to different SDKs based on provider protocol.
"""
from .router import ProviderRouter

__all__ = ["ProviderRouter"]
```

**Step 2: Create base runner**

Create `apps/api/app/services/cli/runners/base_runner.py`:

```python
"""
Abstract base class for model runners.
Each runner wraps a specific SDK (Anthropic, OpenAI, Gemini, etc.).
"""
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.models.messages import Message


class BaseRunner(ABC):
    """Abstract runner for a provider protocol."""

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url

    @abstractmethod
    async def stream_response(
        self,
        instruction: str,
        project_id: str,
        session_id: Optional[str],
        model: str,
        system_prompt: Optional[str] = None,
        cwd: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[Message, None]:
        """Stream response messages from the model."""
        ...
```

**Step 3: Commit**

```bash
git add apps/api/app/services/cli/runners/
git commit -m "feat: add runner base abstraction"
```

---

### Task 8: Create OpenAIRunner

**Files:**
- Create: `apps/api/app/services/cli/runners/openai_runner.py`

**Step 1: Implement OpenAI runner**

Create `apps/api/app/services/cli/runners/openai_runner.py`:

```python
"""
OpenAI-protocol runner — handles OpenAI, Deepseek, Qwen, GLM, and any
OpenAI-compatible API via streaming chat completions.
"""
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

from openai import OpenAI

from app.models.messages import Message
from app.core.terminal_ui import ui
from .base_runner import BaseRunner


class OpenAIRunner(BaseRunner):
    """Runner for OpenAI-compatible APIs."""

    async def stream_response(
        self,
        instruction: str,
        project_id: str,
        session_id: Optional[str],
        model: str,
        system_prompt: Optional[str] = None,
        cwd: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[Message, None]:
        """Stream chat completion from an OpenAI-compatible API."""
        import time

        client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url or "https://api.openai.com/v1",
        )

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if cwd:
            messages.append({"role": "system", "content": f"Working directory: {cwd}"})

        # Append history
        if history:
            for h in history:
                messages.append({"role": h["role"], "content": h["content"]})

        # Current instruction
        messages.append({"role": "user", "content": instruction})

        ui.info(f"OpenAI runner: model={model}, messages={len(messages)}", "Runner")

        start = time.time()
        full_content = ""

        try:
            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
            )

            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    full_content += delta.content

            duration_ms = int((time.time() - start) * 1000)

            if full_content.strip():
                yield Message(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    role="assistant",
                    message_type="chat",
                    content=full_content.strip(),
                    metadata_json={"cli_type": "openai_runner", "model": model},
                    session_id=session_id,
                    created_at=datetime.utcnow(),
                )

            # Usage info
            usage = getattr(chunk, "usage", None) if 'chunk' in dir() else None
            usage_str = ""
            if usage:
                total = (usage.prompt_tokens or 0) + (usage.completion_tokens or 0)
                usage_str = f" | Tokens: {total:,}"

            yield Message(
                id=str(uuid.uuid4()),
                project_id=project_id,
                role="system",
                message_type="session_complete",
                content=f"Session complete, {duration_ms / 1000:.2f}s{usage_str}",
                metadata_json={
                    "cli_type": "openai_runner",
                    "duration_ms": duration_ms,
                    "model": model,
                },
                session_id=session_id,
                created_at=datetime.utcnow(),
            )

        except Exception as e:
            ui.error(f"OpenAI runner error: {e}", "Runner")
            yield Message(
                id=str(uuid.uuid4()),
                project_id=project_id,
                role="system",
                message_type="error",
                content=f"Model error: {e}",
                metadata_json={"cli_type": "openai_runner", "model": model},
                session_id=session_id,
                created_at=datetime.utcnow(),
            )
```

**Step 2: Commit**

```bash
git add apps/api/app/services/cli/runners/openai_runner.py
git commit -m "feat: add OpenAI-protocol runner with streaming"
```

---

### Task 9: Create Router and integrate into execution flow

**Files:**
- Create: `apps/api/app/services/cli/runners/router.py`
- Modify: `apps/api/app/services/cli/base.py`
- Modify: `apps/api/app/services/cli/adapters/hello_agent.py`
- Modify: `apps/api/app/api/chat.py`

This is the most critical task — it connects everything together.

**Step 1: Create the Provider Router**

Create `apps/api/app/services/cli/runners/router.py`:

```python
"""
Provider Router — resolves provider+model from DB and dispatches to the correct runner.
"""
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from app.db.base import SessionLocal
from app.models.provider import Provider, ProviderModel
from app.models.projects import Project
from app.services.crypto import decrypt_api_key
from app.core.terminal_ui import ui
from .openai_runner import OpenAIRunner


class ProviderRouter:
    """Resolve provider and model from database, return appropriate runner."""

    @staticmethod
    def resolve(
        model_id: Optional[str] = None,
        provider_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> dict:
        """
        Resolve the provider, model, api_key, and base_url to use.

        Priority:
        1. Explicit provider_id + model_id from message
        2. Project override_provider_id
        3. Match model_id to a provider via provider_models table
        4. First enabled provider with an API key (global default)

        Returns dict with: provider, model_id, api_key, base_url, protocol
        Returns None if model is an Anthropic model handled by Claude SDK.
        """
        db: DBSession = SessionLocal()
        try:
            project = None
            if project_id:
                project = db.query(Project).filter(Project.id == project_id).first()

            # Step 1: If explicit provider_id given, use it
            provider = None
            if provider_id:
                provider = db.query(Provider).filter(Provider.id == provider_id, Provider.enabled == True).first()

            # Step 2: Fall back to project override
            if not provider and project and project.override_provider_id:
                provider = db.query(Provider).filter(
                    Provider.id == project.override_provider_id, Provider.enabled == True
                ).first()

            # Step 3: If model_id given, find which provider owns it
            if not provider and model_id:
                pm = db.query(ProviderModel).filter(ProviderModel.model_id == model_id).first()
                if pm:
                    provider = db.query(Provider).filter(
                        Provider.id == pm.provider_id, Provider.enabled == True
                    ).first()

            # Step 4: Global default — first enabled provider with a key
            if not provider:
                provider = db.query(Provider).filter(
                    Provider.enabled == True,
                    Provider.api_key != None
                ).order_by(Provider.is_builtin.desc()).first()

            if not provider:
                ui.warning("No enabled provider found", "Router")
                return None

            # Resolve model
            resolved_model_id = model_id
            if not resolved_model_id:
                # Use project selected_model
                if project and project.selected_model:
                    resolved_model_id = project.selected_model
                else:
                    # Use provider default model
                    default_m = db.query(ProviderModel).filter(
                        ProviderModel.provider_id == provider.id,
                        ProviderModel.is_default == True
                    ).first()
                    resolved_model_id = default_m.model_id if default_m else None

            # Resolve API key (project override > provider)
            raw_key = ""
            if project and project.override_api_key:
                raw_key = decrypt_api_key(project.override_api_key)
            elif provider.api_key:
                raw_key = decrypt_api_key(provider.api_key)

            return {
                "provider_id": provider.id,
                "provider_name": provider.name,
                "protocol": provider.protocol,
                "base_url": provider.base_url,
                "api_key": raw_key,
                "model_id": resolved_model_id,
            }
        finally:
            db.close()

    @staticmethod
    def get_runner(resolved: dict):
        """Get the appropriate runner instance for a resolved provider."""
        protocol = resolved["protocol"]

        if protocol == "openai":
            return OpenAIRunner(
                api_key=resolved["api_key"],
                base_url=resolved["base_url"],
            )
        elif protocol == "anthropic":
            # Anthropic uses Claude Agent SDK — handled by BaseCLI directly
            return None
        else:
            ui.warning(f"Unknown protocol: {protocol}", "Router")
            return None
```

**Step 2: Update BaseCLI to remove MODEL_MAPPING**

In `apps/api/app/services/cli/base.py`:

Replace the `MODEL_MAPPING` dict (lines 32-45) with:

```python
# Legacy model mapping — kept for backward compatibility during transition.
# New code should use ProviderRouter to resolve models.
MODEL_MAPPING: Dict[str, str] = {
    "sonnet-4": "claude-sonnet-4-20250514",
    "sonnet-4.5": "claude-sonnet-4-5-20250929",
    "opus-4": "claude-opus-4-20250514",
    "opus-4.5": "claude-opus-4-5-20251101",
    "haiku-3.5": "claude-3-5-haiku-20241022",
    "claude-sonnet-4-20250514": "claude-sonnet-4-20250514",
    "claude-sonnet-4-5-20250929": "claude-sonnet-4-5-20250929",
    "claude-opus-4-20250514": "claude-opus-4-20250514",
    "claude-opus-4-5-20251101": "claude-opus-4-5-20251101",
    "claude-3-5-haiku-20241022": "claude-3-5-haiku-20241022",
}
```

No structural changes to `execute_with_streaming` or `_run_streaming` — they continue to handle the Anthropic path. The OpenAI path is handled separately in `chat.py`.

**Step 3: Update chat.py to use ProviderRouter**

In `apps/api/app/api/chat.py`, this is the key integration point. The WebSocket endpoint needs to:
1. Receive optional `provider_id` from client message
2. Use ProviderRouter to resolve provider + model
3. If protocol is `openai`, use OpenAIRunner directly
4. If protocol is `anthropic`, use existing Claude Agent SDK path

Add import at top of `chat.py`:

```python
from app.services.cli.runners.router import ProviderRouter
```

In the WebSocket handler, after parsing `model` from message_data (line 77), add:

```python
            provider_id = message_data.get("provider_id")
```

Then replace the agent execution block (lines 130-187) with logic that checks the provider protocol:

```python
            # Resolve provider and model
            resolved = ProviderRouter.resolve(
                model_id=model,
                provider_id=provider_id,
                project_id=project_id,
            )

            runner = ProviderRouter.get_runner(resolved) if resolved else None

            session_id = str(uuid.uuid4())
            try:
                if runner:
                    # Non-Anthropic path: use runner directly
                    async for msg in runner.stream_response(
                        instruction=content,
                        project_id=project_id,
                        session_id=session_id,
                        model=resolved["model_id"],
                        system_prompt=None,
                        cwd=os.path.join(settings.projects_root, project_id),
                    ):
                        # Tag message with model/provider info
                        msg.model_id = resolved["model_id"]
                        msg.provider_id = resolved["provider_id"]
                        if msg.metadata_json is None:
                            msg.metadata_json = {}
                        msg.metadata_json["provider_name"] = resolved["provider_name"]

                        await manager.send_message({
                            "id": msg.id,
                            "role": msg.role,
                            "content": msg.content,
                            "type": msg.message_type,
                            "metadata": msg.metadata_json,
                            "created_at": msg.created_at.isoformat() if msg.created_at else None,
                        }, project_id)

                        db = SessionLocal()
                        try:
                            db.add(msg)
                            db.commit()
                        except Exception as e:
                            db.rollback()
                            ui.error(f"Failed to save message: {e}", "Chat")
                        finally:
                            db.close()
                else:
                    # Anthropic path: use Claude Agent SDK via agent
                    # If we have a resolved anthropic provider, set env vars for SDK
                    if resolved and resolved["protocol"] == "anthropic":
                        if resolved["api_key"]:
                            os.environ["ANTHROPIC_API_KEY"] = resolved["api_key"]
                        if resolved["base_url"]:
                            os.environ["ANTHROPIC_BASE_URL"] = resolved["base_url"]

                    async for msg in agent.execute_with_streaming(
                        instruction=content,
                        project_id=project_id,
                        log_callback=log_callback,
                        session_id=session_id,
                        claude_session_id=claude_session_id,
                        model=resolved["model_id"] if resolved else model,
                        agent_type=agent_type,
                    ):
                        # Tag message with model/provider info
                        if resolved:
                            msg.model_id = resolved["model_id"]
                            msg.provider_id = resolved["provider_id"]
                            if msg.metadata_json and isinstance(msg.metadata_json, dict):
                                msg.metadata_json["provider_name"] = resolved["provider_name"]

                        await manager.send_message({
                            "id": msg.id,
                            "role": msg.role,
                            "content": msg.content,
                            "type": msg.message_type,
                            "metadata": msg.metadata_json,
                            "created_at": msg.created_at.isoformat() if msg.created_at else None,
                        }, project_id)

                        db = SessionLocal()
                        try:
                            db.add(msg)
                            db.commit()
                        except Exception as e:
                            db.rollback()
                            ui.error(f"Failed to save message: {e}", "Chat")
                        finally:
                            db.close()
            except Exception as agent_err:
                # ... existing error handling (lines 158-187) stays the same
```

The existing error handling block and post-processing system-agent block remain unchanged.

**Step 4: Commit**

```bash
git add apps/api/app/services/cli/runners/ apps/api/app/api/chat.py apps/api/app/services/cli/base.py
git commit -m "feat: add provider router and integrate into chat execution"
```

---

## Phase 3: Frontend

### Task 10: Create ModelSelector component

**Files:**
- Create: `apps/web/components/ModelSelector.tsx`

**Step 1: Create the reusable grouped model dropdown**

This component fetches `/api/models` and displays a grouped dropdown. It's used in both the chat page and AgentConfig panel.

Create `apps/web/components/ModelSelector.tsx`:

```tsx
"use client";

import { useState, useEffect, useRef } from "react";
import { ChevronDown } from "lucide-react";

interface Model {
  id: string;
  model_id: string;
  display_name: string;
  is_default: boolean;
}

interface ProviderGroup {
  provider_id: string;
  provider_name: string;
  protocol: string;
  has_api_key: boolean;
  models: Model[];
}

interface ModelSelectorProps {
  value?: string;              // current model_id
  providerId?: string;         // current provider_id
  onChange: (modelId: string, providerId: string) => void;
  className?: string;
}

export default function ModelSelector({ value, providerId, onChange, className = "" }: ModelSelectorProps) {
  const [groups, setGroups] = useState<ProviderGroup[]>([]);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch("/api/models")
      .then((r) => r.json())
      .then(setGroups)
      .catch(() => {});
  }, []);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Find current display name
  const currentLabel = (() => {
    for (const g of groups) {
      for (const m of g.models) {
        if (m.model_id === value && (providerId ? g.provider_id === providerId : true)) {
          return `${m.display_name}`;
        }
      }
    }
    return value || "Select model";
  })();

  // Filter to only providers with API key configured
  const available = groups.filter((g) => g.has_api_key);

  return (
    <div ref={ref} className={`relative ${className}`}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-800 border border-zinc-700 hover:border-zinc-600 text-sm text-zinc-300 transition-colors"
      >
        <span className="truncate max-w-[160px]">{currentLabel}</span>
        <ChevronDown className="w-3.5 h-3.5 text-zinc-500" />
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-64 max-h-80 overflow-y-auto rounded-lg bg-zinc-800 border border-zinc-700 shadow-xl">
          {available.length === 0 && (
            <div className="px-3 py-2 text-sm text-zinc-500">No providers configured</div>
          )}
          {available.map((g) => (
            <div key={g.provider_id}>
              <div className="px-3 py-1.5 text-xs font-medium text-zinc-500 uppercase tracking-wide bg-zinc-850">
                {g.provider_name}
              </div>
              {g.models.map((m) => (
                <button
                  key={`${g.provider_id}-${m.model_id}`}
                  onClick={() => {
                    onChange(m.model_id, g.provider_id);
                    setOpen(false);
                  }}
                  className={`w-full text-left px-3 py-2 text-sm hover:bg-zinc-700 transition-colors ${
                    m.model_id === value && g.provider_id === providerId
                      ? "text-blue-400 bg-zinc-750"
                      : "text-zinc-300"
                  }`}
                >
                  {m.display_name}
                  <span className="ml-2 text-xs text-zinc-600">{m.model_id}</span>
                </button>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add apps/web/components/ModelSelector.tsx
git commit -m "feat: add ModelSelector grouped dropdown component"
```

---

### Task 11: Create ProviderSettings component

**Files:**
- Create: `apps/web/components/ProviderSettings.tsx`

**Step 1: Create the provider management component**

This is the main component for the settings page. It handles provider list, API key editing, model CRUD, and connectivity verification.

Create `apps/web/components/ProviderSettings.tsx`:

```tsx
"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import {
  CheckCircle,
  XCircle,
  Plus,
  Trash2,
  Pencil,
  Loader2,
  ChevronDown,
  ChevronRight,
  Shield,
} from "lucide-react";

interface ModelItem {
  id: string;
  model_id: string;
  display_name: string;
  is_default: boolean;
}

interface ProviderItem {
  id: string;
  name: string;
  protocol: string;
  base_url: string | null;
  api_key_masked: string;
  has_api_key: boolean;
  is_builtin: boolean;
  enabled: boolean;
  models: ModelItem[];
}

export default function ProviderSettings() {
  const [providers, setProviders] = useState<ProviderItem[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [verifying, setVerifying] = useState<string | null>(null);
  const [verifyResults, setVerifyResults] = useState<Record<string, { success: boolean; error?: string; latency_ms?: number }>>({});
  const [editingKey, setEditingKey] = useState<Record<string, string>>({});
  const [editingUrl, setEditingUrl] = useState<Record<string, string>>({});
  const [showAddProvider, setShowAddProvider] = useState(false);
  const [newProvider, setNewProvider] = useState({ name: "", protocol: "openai", base_url: "", api_key: "" });
  // Model editing state
  const [editingModel, setEditingModel] = useState<{ providerId: string; model?: ModelItem } | null>(null);
  const [modelForm, setModelForm] = useState({ model_id: "", display_name: "", is_default: false });

  const fetchProviders = () => {
    fetch("/api/providers")
      .then((r) => r.json())
      .then(setProviders)
      .catch(() => toast.error("Failed to load providers"));
  };

  useEffect(() => {
    fetchProviders();
  }, []);

  const handleSaveKey = async (id: string) => {
    const key = editingKey[id];
    if (key === undefined) return;
    const res = await fetch(`/api/providers/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_key: key }),
    });
    if (res.ok) {
      toast.success("API Key saved");
      setEditingKey((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      fetchProviders();
    } else {
      toast.error("Failed to save");
    }
  };

  const handleSaveUrl = async (id: string) => {
    const url = editingUrl[id];
    if (url === undefined) return;
    const res = await fetch(`/api/providers/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ base_url: url }),
    });
    if (res.ok) {
      toast.success("Base URL saved");
      setEditingUrl((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      fetchProviders();
    } else {
      toast.error("Failed to save");
    }
  };

  const handleToggle = async (id: string, enabled: boolean) => {
    await fetch(`/api/providers/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    });
    fetchProviders();
  };

  const handleVerify = async (id: string) => {
    setVerifying(id);
    try {
      const res = await fetch(`/api/providers/${id}/verify`, { method: "POST" });
      const data = await res.json();
      setVerifyResults((prev) => ({ ...prev, [id]: data }));
      if (data.success) {
        toast.success(`Connected (${data.latency_ms}ms)`);
      } else {
        toast.error(data.error || "Verification failed");
      }
    } catch {
      toast.error("Verification request failed");
    }
    setVerifying(null);
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this provider?")) return;
    const res = await fetch(`/api/providers/${id}`, { method: "DELETE" });
    if (res.ok) {
      toast.success("Provider deleted");
      fetchProviders();
    } else {
      const data = await res.json();
      toast.error(data.detail || "Failed to delete");
    }
  };

  const handleAddProvider = async () => {
    const res = await fetch("/api/providers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newProvider),
    });
    if (res.ok) {
      toast.success("Provider created");
      setShowAddProvider(false);
      setNewProvider({ name: "", protocol: "openai", base_url: "", api_key: "" });
      fetchProviders();
    } else {
      toast.error("Failed to create provider");
    }
  };

  // Model CRUD
  const openModelEditor = (providerId: string, model?: ModelItem) => {
    setEditingModel({ providerId, model });
    setModelForm(model ? { model_id: model.model_id, display_name: model.display_name, is_default: model.is_default } : { model_id: "", display_name: "", is_default: false });
  };

  const handleSaveModel = async () => {
    if (!editingModel) return;
    const { providerId, model } = editingModel;

    if (model) {
      // Update
      await fetch(`/api/providers/${providerId}/models/${model.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(modelForm),
      });
    } else {
      // Create
      await fetch(`/api/providers/${providerId}/models`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(modelForm),
      });
    }
    setEditingModel(null);
    fetchProviders();
  };

  const handleDeleteModel = async (providerId: string, modelId: string) => {
    if (!confirm("Delete this model?")) return;
    await fetch(`/api/providers/${providerId}/models/${modelId}`, { method: "DELETE" });
    fetchProviders();
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-medium text-zinc-100">Providers</h2>
        <button
          onClick={() => setShowAddProvider(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-sm text-white transition-colors"
        >
          <Plus className="w-4 h-4" /> Add Custom Provider
        </button>
      </div>

      {/* Add provider form */}
      {showAddProvider && (
        <div className="p-4 rounded-lg bg-zinc-800 border border-zinc-700 space-y-3">
          <input
            placeholder="Provider name"
            value={newProvider.name}
            onChange={(e) => setNewProvider({ ...newProvider, name: e.target.value })}
            className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded text-sm text-zinc-200"
          />
          <select
            value={newProvider.protocol}
            onChange={(e) => setNewProvider({ ...newProvider, protocol: e.target.value })}
            className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded text-sm text-zinc-200"
          >
            <option value="anthropic">Anthropic Protocol</option>
            <option value="openai">OpenAI Protocol</option>
          </select>
          <input
            placeholder="Base URL (e.g. https://api.example.com)"
            value={newProvider.base_url}
            onChange={(e) => setNewProvider({ ...newProvider, base_url: e.target.value })}
            className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded text-sm text-zinc-200"
          />
          <input
            placeholder="API Key"
            type="password"
            value={newProvider.api_key}
            onChange={(e) => setNewProvider({ ...newProvider, api_key: e.target.value })}
            className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded text-sm text-zinc-200"
          />
          <div className="flex gap-2">
            <button onClick={handleAddProvider} className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded text-sm text-white">Save</button>
            <button onClick={() => setShowAddProvider(false)} className="px-3 py-1.5 bg-zinc-700 hover:bg-zinc-600 rounded text-sm text-zinc-300">Cancel</button>
          </div>
        </div>
      )}

      {/* Provider list */}
      {providers.map((p) => (
        <div key={p.id} className="rounded-lg bg-zinc-800/50 border border-zinc-700/50">
          {/* Header row */}
          <div
            className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-zinc-800 transition-colors rounded-t-lg"
            onClick={() => setExpandedId(expandedId === p.id ? null : p.id)}
          >
            {expandedId === p.id ? <ChevronDown className="w-4 h-4 text-zinc-500" /> : <ChevronRight className="w-4 h-4 text-zinc-500" />}
            <input
              type="checkbox"
              checked={p.enabled}
              onChange={(e) => { e.stopPropagation(); handleToggle(p.id, e.target.checked); }}
              className="rounded"
            />
            <span className="text-sm font-medium text-zinc-200 flex-1">{p.name}</span>
            {p.is_builtin && <Shield className="w-3.5 h-3.5 text-zinc-600" />}
            <span className="text-xs text-zinc-500">{p.has_api_key ? p.api_key_masked : "No key"}</span>
            {verifyResults[p.id] && (
              verifyResults[p.id].success
                ? <CheckCircle className="w-4 h-4 text-green-500" />
                : <XCircle className="w-4 h-4 text-red-500" />
            )}
          </div>

          {/* Expanded content */}
          {expandedId === p.id && (
            <div className="px-4 pb-4 space-y-3 border-t border-zinc-700/50">
              {/* API Key */}
              <div className="pt-3">
                <label className="block text-xs text-zinc-500 mb-1">API Key</label>
                <div className="flex gap-2">
                  <input
                    type="password"
                    placeholder={p.has_api_key ? "Enter new key to replace" : "Enter API key"}
                    value={editingKey[p.id] ?? ""}
                    onChange={(e) => setEditingKey({ ...editingKey, [p.id]: e.target.value })}
                    className="flex-1 px-3 py-1.5 bg-zinc-900 border border-zinc-700 rounded text-sm text-zinc-200"
                  />
                  <button
                    onClick={() => handleSaveKey(p.id)}
                    disabled={!editingKey[p.id]}
                    className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-30 rounded text-sm text-white"
                  >Save</button>
                </div>
              </div>

              {/* Base URL (custom providers only) */}
              {!p.is_builtin && (
                <div>
                  <label className="block text-xs text-zinc-500 mb-1">Base URL</label>
                  <div className="flex gap-2">
                    <input
                      placeholder="https://api.example.com"
                      value={editingUrl[p.id] ?? p.base_url ?? ""}
                      onChange={(e) => setEditingUrl({ ...editingUrl, [p.id]: e.target.value })}
                      className="flex-1 px-3 py-1.5 bg-zinc-900 border border-zinc-700 rounded text-sm text-zinc-200"
                    />
                    <button
                      onClick={() => handleSaveUrl(p.id)}
                      className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded text-sm text-white"
                    >Save</button>
                  </div>
                </div>
              )}

              {/* Models */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs text-zinc-500">Models</label>
                  <button
                    onClick={() => openModelEditor(p.id)}
                    className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300"
                  >
                    <Plus className="w-3 h-3" /> Add Model
                  </button>
                </div>
                <div className="space-y-1">
                  {p.models.map((m) => (
                    <div key={m.id} className="flex items-center gap-2 px-2 py-1.5 rounded bg-zinc-900/50 text-sm">
                      <span className="text-zinc-300 flex-1">{m.display_name}</span>
                      <span className="text-xs text-zinc-600 truncate max-w-[180px]">{m.model_id}</span>
                      {m.is_default && <span className="text-xs text-blue-400 bg-blue-400/10 px-1.5 rounded">default</span>}
                      <button onClick={() => openModelEditor(p.id, m)} className="p-0.5 hover:text-zinc-300 text-zinc-600"><Pencil className="w-3 h-3" /></button>
                      <button onClick={() => handleDeleteModel(p.id, m.id)} className="p-0.5 hover:text-red-400 text-zinc-600"><Trash2 className="w-3 h-3" /></button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-2 pt-1">
                <button
                  onClick={() => handleVerify(p.id)}
                  disabled={verifying === p.id || !p.has_api_key}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-700 hover:bg-zinc-600 disabled:opacity-30 rounded text-sm text-zinc-300"
                >
                  {verifying === p.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle className="w-3.5 h-3.5" />}
                  Verify Connection
                </button>
                {!p.is_builtin && (
                  <button
                    onClick={() => handleDelete(p.id)}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-red-900/30 hover:bg-red-900/50 rounded text-sm text-red-400"
                  >
                    <Trash2 className="w-3.5 h-3.5" /> Delete
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      ))}

      {/* Model edit dialog */}
      {editingModel && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-96 p-5 rounded-xl bg-zinc-800 border border-zinc-700 space-y-3">
            <h3 className="text-sm font-medium text-zinc-200">{editingModel.model ? "Edit Model" : "Add Model"}</h3>
            <input
              placeholder="Model ID (e.g. gpt-4o)"
              value={modelForm.model_id}
              onChange={(e) => setModelForm({ ...modelForm, model_id: e.target.value })}
              className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded text-sm text-zinc-200"
            />
            <input
              placeholder="Display Name (e.g. GPT-4o)"
              value={modelForm.display_name}
              onChange={(e) => setModelForm({ ...modelForm, display_name: e.target.value })}
              className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded text-sm text-zinc-200"
            />
            <label className="flex items-center gap-2 text-sm text-zinc-300">
              <input
                type="checkbox"
                checked={modelForm.is_default}
                onChange={(e) => setModelForm({ ...modelForm, is_default: e.target.checked })}
              />
              Set as default
            </label>
            <div className="flex justify-end gap-2">
              <button onClick={() => setEditingModel(null)} className="px-3 py-1.5 bg-zinc-700 hover:bg-zinc-600 rounded text-sm text-zinc-300">Cancel</button>
              <button
                onClick={handleSaveModel}
                disabled={!modelForm.model_id || !modelForm.display_name}
                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-30 rounded text-sm text-white"
              >Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add apps/web/components/ProviderSettings.tsx
git commit -m "feat: add ProviderSettings component with model CRUD"
```

---

### Task 12: Create Settings page and add Navbar entry

**Files:**
- Create: `apps/web/app/settings/page.tsx`
- Modify: `apps/web/app/chat/[projectId]/page.tsx` (navbar area)
- Modify: `apps/web/app/page.tsx` (navbar area)

**Step 1: Create settings page**

Create `apps/web/app/settings/page.tsx`:

```tsx
"use client";

import Link from "next/link";
import { ArrowLeft, Settings } from "lucide-react";
import ProviderSettings from "@/components/ProviderSettings";

export default function SettingsPage() {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      {/* Header */}
      <div className="border-b border-zinc-800">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center gap-4">
          <Link href="/" className="p-2 rounded-lg hover:bg-zinc-800 transition-colors">
            <ArrowLeft className="w-5 h-5 text-zinc-400" />
          </Link>
          <Settings className="w-5 h-5 text-zinc-400" />
          <h1 className="text-lg font-medium">Settings</h1>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-6 py-8">
        <ProviderSettings />
      </div>
    </div>
  );
}
```

**Step 2: Add settings link to homepage navbar**

In `apps/web/app/page.tsx`, find the top navigation/header area. Add a settings icon link next to any existing nav items. Look for the header area and add:

```tsx
<Link href="/settings" className="p-2 rounded-lg hover:bg-zinc-800 transition-colors" title="Settings">
  <Settings className="w-5 h-5 text-zinc-400" />
</Link>
```

Add `Settings` to the lucide-react import and `Link` from "next/link".

**Step 3: Add settings link to chat page navbar**

In `apps/web/app/chat/[projectId]/page.tsx`, find the top bar area and add the same settings link.

**Step 4: Commit**

```bash
git add apps/web/app/settings/ apps/web/app/page.tsx apps/web/app/chat/
git commit -m "feat: add settings page and navbar entry"
```

---

### Task 13: Integrate ModelSelector into chat page

**Files:**
- Modify: `apps/web/app/chat/[projectId]/page.tsx`

**Step 1: Add model selector state**

Add state variables near other state declarations:

```tsx
const [selectedModel, setSelectedModel] = useState<string>("");
const [selectedProviderId, setSelectedProviderId] = useState<string>("");
```

**Step 2: Add ModelSelector above input box**

Import `ModelSelector` from `@/components/ModelSelector`.

Find the input area (message input + send button) and add the ModelSelector component above it:

```tsx
<div className="flex items-center gap-2 px-4 py-1">
  <ModelSelector
    value={selectedModel}
    providerId={selectedProviderId}
    onChange={(modelId, providerId) => {
      setSelectedModel(modelId);
      setSelectedProviderId(providerId);
    }}
  />
</div>
```

**Step 3: Pass model and provider in WebSocket message**

Find where the WebSocket message is sent (the `ws.send()` call with content). Update the payload to include:

```tsx
ws.send(JSON.stringify({
  content: inputValue,
  model: selectedModel || undefined,
  provider_id: selectedProviderId || undefined,
}));
```

**Step 4: Add model tag to message bubbles**

In the message rendering section, for assistant messages, add a small tag showing the model used:

```tsx
{msg.metadata?.provider_name && (
  <span className="text-xs text-zinc-600 mt-1">
    {msg.metadata.provider_name} / {msg.metadata.model || ""}
  </span>
)}
```

**Step 5: Commit**

```bash
git add apps/web/app/chat/
git commit -m "feat: integrate model selector and model tags into chat"
```

---

### Task 14: Update AgentConfig panel

**Files:**
- Modify: `apps/web/components/AgentConfig.tsx`

**Step 1: Replace static AVAILABLE_MODELS with ModelSelector**

Remove the `AVAILABLE_MODELS` constant. Import `ModelSelector` from `@/components/ModelSelector`.

Replace the model `<select>` dropdown in the config form with:

```tsx
<div>
  <label className="block text-sm text-zinc-400 mb-1">Model</label>
  <ModelSelector
    value={config.model}
    onChange={(modelId, _providerId) => setConfig({ ...config, model: modelId })}
  />
</div>
```

**Step 2: Commit**

```bash
git add apps/web/components/AgentConfig.tsx
git commit -m "feat: use ModelSelector in AgentConfig panel"
```

---

## Phase 4: Verification

### Task 15: End-to-end verification

**Step 1: Start backend**

```bash
cd apps/api && pip install -r requirements.txt
npm run dev:api
```

Verify in logs:
- "Seeded 5 built-in providers" appears on first run
- No migration errors

**Step 2: Verify API endpoints**

```bash
# List providers
curl http://localhost:8080/api/providers | python -m json.tool

# List aggregated models
curl http://localhost:8080/api/models | python -m json.tool

# Set an API key on Anthropic provider (replace PROVIDER_ID with actual ID from list)
curl -X PATCH http://localhost:8080/api/providers/PROVIDER_ID \
  -H "Content-Type: application/json" \
  -d '{"api_key": "sk-ant-xxx"}'

# Verify connectivity
curl -X POST http://localhost:8080/api/providers/PROVIDER_ID/verify | python -m json.tool

# Add a model
curl -X POST http://localhost:8080/api/providers/PROVIDER_ID/models \
  -H "Content-Type: application/json" \
  -d '{"model_id": "claude-sonnet-4-20250514", "display_name": "Sonnet 4", "is_default": false}'
```

**Step 3: Start frontend**

```bash
npm run dev:web
```

Verify:
- Homepage shows settings gear icon
- `/settings` page loads with 5 built-in providers
- Can expand a provider, edit API key, add/edit/delete models
- Verify connection works
- Chat page shows model selector above input
- Selecting a different model sends it in WebSocket message
- Message bubbles show model tag for AI responses

**Step 4: Test model switching**

1. Configure Anthropic API key in settings
2. Open a chat, send a message — should use Claude (Anthropic runner)
3. Configure Deepseek API key
4. Switch to Deepseek V3 in chat model selector
5. Send a message — should use Deepseek (OpenAI runner)
6. Verify response appears normally with model tag

**Step 5: Final commit**

```bash
git add -A
git commit -m "feat: multi-provider model config with immediate switching"
```
