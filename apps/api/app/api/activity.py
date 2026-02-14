"""
Activity API router
"""
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.messages import Message
from app.models.projects import Project

router = APIRouter()


class ActivityItem(BaseModel):
    project_id: str
    project_name: str
    role: str
    content: Optional[str]
    message_type: str
    created_at: datetime

    class Config:
        from_attributes = True


class ActivityResponse(BaseModel):
    activities: List[ActivityItem]


@router.get("/recent", response_model=ActivityResponse)
def get_recent_activity(limit: int = 10, db: Session = Depends(get_db)):
    """Get recent activity across all projects."""
    rows = (
        db.query(Message, Project.name)
        .join(Project, Message.project_id == Project.id)
        .filter(Message.message_type == "chat")
        .order_by(Message.created_at.desc())
        .limit(limit)
        .all()
    )

    activities = []
    for msg, project_name in rows:
        content = msg.content or ""
        if len(content) > 80:
            content = content[:80] + "..."

        activities.append(ActivityItem(
            project_id=msg.project_id,
            project_name=project_name,
            role=msg.role,
            content=content,
            message_type=msg.message_type,
            created_at=msg.created_at,
        ))

    return ActivityResponse(activities=activities)
