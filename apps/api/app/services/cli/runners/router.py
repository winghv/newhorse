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
    ) -> dict | None:
        """
        Resolve the provider, model, api_key, and base_url to use.

        Priority:
        1. Explicit provider_id + model_id from message
        2. Project override_provider_id
        3. Match model_id to a provider via provider_models table
        4. First enabled provider with an API key (global default)

        Returns dict with: provider_id, provider_name, protocol, base_url, api_key, model_id
        Returns None if no provider found.
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
                    Provider.api_key != None,
                ).order_by(Provider.is_builtin.desc()).first()

            if not provider:
                ui.warning("No enabled provider found", "Router")
                return None

            # Resolve model
            resolved_model_id = model_id
            if not resolved_model_id:
                if project and project.selected_model:
                    resolved_model_id = project.selected_model
                else:
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
