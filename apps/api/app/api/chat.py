"""
Chat API router with WebSocket support
"""
import json
import os
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
from app.core.config import settings
from app.core.terminal_ui import ui
from app.services.cli.config_loader import load_agent_config, save_user_template, save_project_config

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
            db_for_project = SessionLocal()
            try:
                project = db_for_project.query(Project).filter(Project.id == project_id).first()
                agent_type = project.preferred_cli if project else "hello"
            finally:
                db_for_project.close()

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
                agent_type=agent_type,
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

            # Post-processing: if system-agent, check for generated config
            if agent_type == "system-agent":
                project_path = os.path.join(settings.projects_root, project_id)
                config_path = os.path.join(project_path, ".claude", "agent.yaml")

                if os.path.exists(config_path):
                    config = load_agent_config(project_path)
                    ui.info(f"System agent generated config: {config.name}", "Chat")

                    # Save as user template
                    template_id = save_user_template(config)

                    # Create new project using this template
                    new_project_id = str(uuid.uuid4())[:8]
                    new_project_path = os.path.join(settings.projects_root, new_project_id)
                    os.makedirs(new_project_path, exist_ok=True)

                    # Save config to new project
                    config.config_source = f"project:{new_project_id}"
                    save_project_config(new_project_path, config)

                    # Create DB record for new project
                    db_new = SessionLocal()
                    try:
                        new_project = Project(
                            id=new_project_id,
                            name=config.name,
                            description=config.description,
                            repo_path=new_project_path,
                            preferred_cli="hello",
                            selected_model=config.model,
                            status="active",
                        )
                        db_new.add(new_project)
                        db_new.commit()
                    except Exception as e:
                        db_new.rollback()
                        ui.error(f"Failed to create project from template: {e}", "Chat")
                    finally:
                        db_new.close()

                    # Send agent_created event to frontend
                    await manager.send_message({
                        "id": f"agent-created-{template_id}",
                        "role": "system",
                        "content": f"Agent \"{config.name}\" 已创建",
                        "type": "agent_created",
                        "metadata": {
                            "template_id": template_id,
                            "template_name": config.name,
                            "new_project_id": new_project_id,
                        },
                        "created_at": datetime.utcnow().isoformat(),
                    }, project_id)

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
