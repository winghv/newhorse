"""
Session model
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey

from app.db.base import Base


class Session(Base):
    """Session model for storing chat sessions"""

    __tablename__ = "sessions"

    id = Column(String(64), primary_key=True)
    project_id = Column(String(64), ForeignKey("projects.id"), nullable=False)
    claude_session_id = Column(String(128), nullable=True)
    status = Column(String(32), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
