"""
Delegation model — tracks tasks delegated by the Butler to specialist agents.
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey

from app.db.base import Base


class Delegation(Base):
    """Records each task the Butler delegates to a specialist agent."""

    __tablename__ = "delegations"

    id = Column(String(64), primary_key=True)
    project_id = Column(String(64), ForeignKey("projects.id"), nullable=False)
    agent_type = Column(String(64), nullable=False)
    task = Column(Text, nullable=False)
    context = Column(Text, nullable=True)
    status = Column(String(32), default="pending")
    result = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
