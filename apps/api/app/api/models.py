"""
Aggregated model list API
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
        Provider.enabled
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
