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
