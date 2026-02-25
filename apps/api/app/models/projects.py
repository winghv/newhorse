"""
Project model
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text

from app.db.base import Base


class Project(Base):
    """Project model for storing agent projects"""

    __tablename__ = "projects"

    id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    repo_path = Column(String(512), nullable=True)
    status = Column(String(32), default="active")
    preferred_cli = Column(String(64), default="hello")
    selected_model = Column(String(64), default="claude-sonnet-4-5-20250929")
    override_provider_id = Column(String(8), nullable=True)
    override_api_key = Column(Text, nullable=True)  # Fernet-encrypted
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
