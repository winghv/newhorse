"""
Chat API router with WebSocket support
"""
import json
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db, SessionLocal
from app.models.projects import Project
from app.models.messages import Message
from app.services.cli import agent_manager
from app.common.types import AgentType
from app.core.terminal_ui import ui

router = APIRouter()


class ChatMessage(BaseModel):
    content: str
    model: Optional[str] = None


class ConnectionManager:
    """WebSocket connection manager."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, project_id: str):
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        self.active_connections[project_id].append(websocket)
        ui.info(f"WebSocket connected: {project_id}", "Chat")

    def disconnect(self, websocket: WebSocket, project_id: str):
        if project_id in self.active_connections:
            if websocket in self.active_connections[project_id]:
                self.active_connections[project_id].remove(websocket)
        ui.info(f"WebSocket disconnected: {project_id}", "Chat")

    async def send_message(self, message: dict, project_id: str):
        if project_id in self.active_connections:
            for ws in self.active_connections[project_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    pass


manager = ConnectionManager()


# Store claude_session_id per project (in production, use Redis or DB)
session_store: dict[str, str] = {}


@router.websocket("/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    """WebSocket endpoint for real-time chat."""
    await manager.connect(websocket, project_id)

    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)

            content = message_data.get("content", "")
            model = message_data.get("model")

            if not content:
                continue

            ui.info(f"Received message: {content[:50]}...", "Chat")

            # Persist user message to database
            db = SessionLocal()
            try:
                user_msg = Message(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    role="user",
                    message_type="chat",
                    content=content,
                )
                db.add(user_msg)
                db.commit()
            except Exception as e:
                db.rollback()
                ui.error(f"Failed to save user message: {e}", "Chat")
            finally:
                db.close()

            # Get project to determine agent type
            # For simplicity, we use the default Hello agent here
            agent = agent_manager.get_agent(AgentType.HELLO)

            # Get or create session
            claude_session_id = session_store.get(project_id)

            def log_callback(data: dict):
                if "claude_session_id" in data:
                    session_store[project_id] = data["claude_session_id"]

            # Stream responses
            async for msg in agent.execute_with_streaming(
                instruction=content,
                project_id=project_id,
                log_callback=log_callback,
                session_id=str(uuid.uuid4()),
                claude_session_id=claude_session_id,
                model=model,
            ):
                await manager.send_message({
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "type": msg.message_type,
                    "metadata": msg.metadata_json,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                }, project_id)

                # Persist assistant/system messages to database
                db = SessionLocal()
                try:
                    db.add(msg)
                    db.commit()
                except Exception as e:
                    db.rollback()
                    ui.error(f"Failed to save message: {e}", "Chat")
                finally:
                    db.close()

    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)
    except Exception as e:
        ui.error(f"WebSocket error: {e}", "Chat")
        manager.disconnect(websocket, project_id)


@router.get("/{project_id}/messages")
def get_messages(project_id: str, limit: int = 50, db: Session = Depends(get_db)):
    """Get chat messages for a project."""
    messages = db.query(Message).filter(
        Message.project_id == project_id
    ).order_by(Message.created_at.desc()).limit(limit).all()

    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "type": m.message_type,
            "metadata": m.metadata_json,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in reversed(messages)
    ]
