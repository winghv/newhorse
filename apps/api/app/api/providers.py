"""
Provider CRUD and model management API
"""
import uuid
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.provider import Provider, ProviderModel
from app.services.crypto import encrypt_api_key, decrypt_api_key, mask_api_key
from app.core.terminal_ui import ui

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class ProviderResponse(BaseModel):
    id: str
    name: str
    protocol: str
    base_url: Optional[str] = None
    api_key_masked: str
    has_api_key: bool
    is_builtin: bool
    enabled: bool
    models: list

    model_config = {"from_attributes": True}


class ProviderCreate(BaseModel):
    name: str
    protocol: str
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _provider_to_response(p: Provider) -> dict:
    """Convert a Provider ORM object to a response dict with masked key."""
    plain_key = decrypt_api_key(p.api_key) if p.api_key else ""
    return {
        "id": p.id,
        "name": p.name,
        "protocol": p.protocol,
        "base_url": p.base_url,
        "api_key_masked": mask_api_key(plain_key),
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


# ---------------------------------------------------------------------------
# Provider endpoints
# ---------------------------------------------------------------------------

@router.get("/")
def list_providers(db: Session = Depends(get_db)):
    """List all providers with masked API keys."""
    providers = (
        db.query(Provider)
        .order_by(Provider.is_builtin.desc(), Provider.name)
        .all()
    )
    return [_provider_to_response(p) for p in providers]


@router.post("/")
def create_provider(body: ProviderCreate, db: Session = Depends(get_db)):
    """Create a custom provider."""
    provider = Provider(
        id=str(uuid.uuid4())[:8],
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
    ui.success(f"Provider created: {provider.name}", "ProvidersAPI")
    return _provider_to_response(provider)


@router.patch("/{provider_id}")
def update_provider(
    provider_id: str,
    body: ProviderUpdate,
    db: Session = Depends(get_db),
):
    """Update a provider. Built-in providers cannot change base_url but CAN change api_key."""
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
    ui.success(f"Provider updated: {provider.name}", "ProvidersAPI")
    return _provider_to_response(provider)


@router.delete("/{provider_id}")
def delete_provider(provider_id: str, db: Session = Depends(get_db)):
    """Delete a provider. Built-in providers cannot be deleted."""
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    if provider.is_builtin:
        raise HTTPException(status_code=400, detail="Cannot delete built-in provider")

    db.delete(provider)
    db.commit()
    ui.success(f"Provider deleted: {provider.name}", "ProvidersAPI")
    return {"success": True}


# ---------------------------------------------------------------------------
# Model endpoints (nested under provider)
# ---------------------------------------------------------------------------

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
def add_model(provider_id: str, body: ModelCreate, db: Session = Depends(get_db)):
    """Add a model to a provider."""
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    # If new model is default, unset other defaults first
    if body.is_default:
        for m in provider.models:
            m.is_default = False

    model = ProviderModel(
        id=str(uuid.uuid4())[:8],
        provider_id=provider_id,
        model_id=body.model_id,
        display_name=body.display_name,
        is_default=body.is_default,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    ui.success(f"Model added: {model.display_name} -> {provider.name}", "ProvidersAPI")
    return {
        "id": model.id,
        "model_id": model.model_id,
        "display_name": model.display_name,
        "is_default": model.is_default,
    }


@router.patch("/{provider_id}/models/{model_id}")
def update_model(
    provider_id: str,
    model_id: str,
    body: ModelUpdate,
    db: Session = Depends(get_db),
):
    """Update a model."""
    model = (
        db.query(ProviderModel)
        .filter(ProviderModel.id == model_id, ProviderModel.provider_id == provider_id)
        .first()
    )
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    if body.model_id is not None:
        model.model_id = body.model_id

    if body.display_name is not None:
        model.display_name = body.display_name

    if body.is_default is not None:
        if body.is_default:
            # Unset other defaults in same provider
            db.query(ProviderModel).filter(
                ProviderModel.provider_id == provider_id,
                ProviderModel.id != model_id,
            ).update({"is_default": False})
        model.is_default = body.is_default

    db.commit()
    db.refresh(model)
    return {
        "id": model.id,
        "model_id": model.model_id,
        "display_name": model.display_name,
        "is_default": model.is_default,
    }


@router.delete("/{provider_id}/models/{model_id}")
def delete_model(provider_id: str, model_id: str, db: Session = Depends(get_db)):
    """Remove a model."""
    model = (
        db.query(ProviderModel)
        .filter(ProviderModel.id == model_id, ProviderModel.provider_id == provider_id)
        .first()
    )
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    db.delete(model)
    db.commit()
    ui.success(f"Model deleted: {model.display_name}", "ProvidersAPI")
    return {"success": True}


# ---------------------------------------------------------------------------
# Verify endpoint
# ---------------------------------------------------------------------------

@router.post("/{provider_id}/verify", response_model=VerifyResponse)
def verify_provider(provider_id: str, db: Session = Depends(get_db)):
    """Test provider connectivity by sending a minimal request."""
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    if not provider.api_key:
        return VerifyResponse(success=False, error="No API key configured")

    plain_key = decrypt_api_key(provider.api_key)

    # Pick first model, or fall back to a sensible default
    model_id = provider.models[0].model_id if provider.models else None
    if not model_id:
        return VerifyResponse(success=False, error="No models configured for this provider")

    try:
        start = time.time()

        if provider.protocol == "anthropic":
            import anthropic

            kwargs = {"api_key": plain_key}
            if provider.base_url:
                kwargs["base_url"] = provider.base_url

            client = anthropic.Anthropic(**kwargs)
            client.messages.create(
                model=model_id,
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}],
            )

        elif provider.protocol == "openai":
            import openai

            kwargs = {"api_key": plain_key}
            if provider.base_url:
                kwargs["base_url"] = provider.base_url

            client = openai.OpenAI(**kwargs)
            client.chat.completions.create(
                model=model_id,
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}],
            )

        else:
            return VerifyResponse(success=False, error=f"Unknown protocol: {provider.protocol}")

        latency = int((time.time() - start) * 1000)
        ui.success(f"Provider verified: {provider.name} ({latency}ms)", "ProvidersAPI")
        return VerifyResponse(success=True, latency_ms=latency)

    except Exception as e:
        ui.warning(f"Provider verify failed: {provider.name} - {e}", "ProvidersAPI")
        return VerifyResponse(success=False, error=str(e))
