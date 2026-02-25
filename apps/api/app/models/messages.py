"""
Message model
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, JSON

from app.db.base import Base


class Message(Base):
    """Message model for storing chat messages"""

    __tablename__ = "messages"

    id = Column(String(64), primary_key=True)
    project_id = Column(String(64), nullable=False)
    session_id = Column(String(64), nullable=True)
    role = Column(String(32), nullable=False)  # user, assistant, system
    message_type = Column(String(32), default="chat")  # chat, tool_use, system
    content = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    model_id = Column(String(128), nullable=True)
    provider_id = Column(String(8), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
