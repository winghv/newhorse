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
from app.services.cli.runners.router import ProviderRouter

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
            provider_id = message_data.get("provider_id")

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

            # Record config file mtime before agent execution (for system-agent detection)
            config_mtime_before = 0
            if agent_type == "system-agent":
                project_path = os.path.join(settings.projects_root, project_id)
                config_path = os.path.join(project_path, ".claude", "agent.yaml")
                if os.path.exists(config_path):
                    config_mtime_before = os.path.getmtime(config_path)

            def log_callback(data: dict):
                if "claude_session_id" in data:
                    session_store[project_id] = data["claude_session_id"]

            # Resolve provider and model
            resolved = ProviderRouter.resolve(
                model_id=model,
                provider_id=provider_id,
                project_id=project_id,
            )

            runner = ProviderRouter.get_runner(resolved) if resolved else None

            # Stream responses
            session_id = str(uuid.uuid4())
            try:
                if runner:
                    # Non-Anthropic path: use runner directly
                    async for msg in runner.stream_response(
                        instruction=content,
                        project_id=project_id,
                        session_id=session_id,
                        model=resolved["model_id"],
                        system_prompt=None,
                        cwd=os.path.join(settings.projects_root, project_id),
                    ):
                        msg.model_id = resolved["model_id"]
                        msg.provider_id = resolved["provider_id"]
                        if msg.metadata_json is None:
                            msg.metadata_json = {}
                        msg.metadata_json["provider_name"] = resolved["provider_name"]

                        await manager.send_message({
                            "id": msg.id,
                            "role": msg.role,
                            "content": msg.content,
                            "type": msg.message_type,
                            "metadata": msg.metadata_json,
                            "created_at": msg.created_at.isoformat() if msg.created_at else None,
                        }, project_id)

                        db = SessionLocal()
                        try:
                            db.add(msg)
                            db.commit()
                        except Exception as e:
                            db.rollback()
                            ui.error(f"Failed to save message: {e}", "Chat")
                        finally:
                            db.close()
                else:
                    # Anthropic path: use Claude Agent SDK via agent
                    if resolved and resolved["protocol"] == "anthropic":
                        if resolved["api_key"]:
                            os.environ["ANTHROPIC_API_KEY"] = resolved["api_key"]
                        if resolved["base_url"]:
                            os.environ["ANTHROPIC_BASE_URL"] = resolved["base_url"]

                    async for msg in agent.execute_with_streaming(
                        instruction=content,
                        project_id=project_id,
                        log_callback=log_callback,
                        session_id=session_id,
                        claude_session_id=claude_session_id,
                        model=resolved["model_id"] if resolved else model,
                        agent_type=agent_type,
                    ):
                        if resolved:
                            msg.model_id = resolved["model_id"]
                            msg.provider_id = resolved["provider_id"]
                            if msg.metadata_json and isinstance(msg.metadata_json, dict):
                                msg.metadata_json["provider_name"] = resolved["provider_name"]

                        await manager.send_message({
                            "id": msg.id,
                            "role": msg.role,
                            "content": msg.content,
                            "type": msg.message_type,
                            "metadata": msg.metadata_json,
                            "created_at": msg.created_at.isoformat() if msg.created_at else None,
                        }, project_id)

                        db = SessionLocal()
                        try:
                            db.add(msg)
                            db.commit()
                        except Exception as e:
                            db.rollback()
                            ui.error(f"Failed to save message: {e}", "Chat")
                        finally:
                            db.close()
            except Exception as agent_err:
                ui.error(f"Agent execution failed: {agent_err}", "Chat")
                # Clear stale session so next message starts fresh
                session_store.pop(project_id, None)

                error_msg = Message(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    role="system",
                    message_type="error",
                    content=f"Agent error: {agent_err}",
                    session_id=session_id,
                    created_at=datetime.utcnow(),
                )
                await manager.send_message({
                    "id": error_msg.id,
                    "role": "system",
                    "content": error_msg.content,
                    "type": "error",
                    "metadata": {"cli_type": "hello"},
                    "created_at": error_msg.created_at.isoformat(),
                }, project_id)
                db = SessionLocal()
                try:
                    db.add(error_msg)
                    db.commit()
                except Exception:
                    db.rollback()
                finally:
                    db.close()

            # Post-processing: if system-agent, check for newly generated config
            if agent_type == "system-agent":
                project_path = os.path.join(settings.projects_root, project_id)
                config_path = os.path.join(project_path, ".claude", "agent.yaml")

                if os.path.exists(config_path):
                    config_mtime_after = os.path.getmtime(config_path)

                    # Only process if the file was created/modified during this execution
                    if config_mtime_after > config_mtime_before:
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
                                preferred_cli=template_id,
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
                                "template_description": config.description,
                                "template_model": config.model,
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
