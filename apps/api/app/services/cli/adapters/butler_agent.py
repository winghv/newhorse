"""
Butler Agent — personal assistant that delegates tasks to specialist agents.

Uses custom MCP tool (delegate_task) to run specialist agent sub-sessions.
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from claude_agent_sdk.types import (
    SystemMessage,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

from app.common.types import AgentType
from app.core.config import settings
from app.core.terminal_ui import ui
from app.models.messages import Message
from app.services.cli.base import BaseCLI, MODEL_MAPPING
from app.services.cli.config_loader import load_agent_config
from app.services.cli.delegation import create_delegation_tool
from app.common.messages import get_message


class ButlerAgent(BaseCLI):
    """Butler Agent — delegates tasks to specialist agents via MCP tools."""

    def __init__(self):
        super().__init__(AgentType.BUTLER)

    async def check_availability(self) -> Dict[str, Any]:
        return {
            "available": True,
            "configured": True,
            "models": list(MODEL_MAPPING.keys()),
            "default_model": "sonnet-4.5",
        }

    def init_claude_option(
        self,
        project_id: str,
        claude_session_id: Optional[str],
        model: Optional[str] = None,
        force_new_session: bool = False,
        user_config: Optional[Dict[str, str]] = None,
        agent_type: Optional[str] = None,
    ) -> ClaudeAgentOptions:
        """Initialize Claude Agent options with delegation MCP tool."""
        project_path = os.path.join(settings.projects_root, project_id)

        # Load butler config from template
        config = load_agent_config(project_path, agent_type="butler")

        ui.info(f"Initializing Butler for project: {project_id}", "Butler")

        # Resolve model
        if model:
            cli_model = MODEL_MAPPING.get(model, config.model)
        else:
            cli_model = MODEL_MAPPING.get(config.model, config.model)

        # Create delegation MCP tool server (event callback set later in execute_with_streaming)
        self._delegation_server = create_delegation_tool(project_id)

        # Skills directories
        add_dirs = []
        global_skills_dir = os.path.join(settings.project_root, "extensions", "skills")
        if os.path.exists(global_skills_dir):
            add_dirs.append(global_skills_dir)

        options = ClaudeAgentOptions(
            system_prompt=config.system_prompt,
            cwd=project_path,
            model=cli_model,
            allowed_tools=config.allowed_tools,
            mcp_servers={"butler-tools": self._delegation_server},
            add_dirs=add_dirs,
            resume=claude_session_id if not force_new_session else None,
        )

        return options

    async def execute_with_streaming(
        self,
        instruction: str,
        project_id: str,
        log_callback: Callable[[dict], Any],
        session_id: Optional[str] = None,
        claude_session_id: Optional[str] = None,
        images: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        is_initial_prompt: bool = False,
        permission_mode: str = "default",
        user_config: Optional[Dict[str, str]] = None,
        agent_type: Optional[str] = None,
        locale: str = "en",
    ) -> AsyncGenerator[Message, None]:
        """Override to inject delegation event callback into the MCP tool."""
        self._delegation_events: List[dict] = []

        def on_delegation_event(event: dict):
            self._delegation_events.append(event)

        # Recreate delegation tool with event callback
        self._delegation_server = create_delegation_tool(project_id, on_event=on_delegation_event)

        self.current_project_id = project_id
        self.session_start_time = datetime.now(timezone.utc)
        self.current_agent_type = agent_type or "butler"

        project_path = os.path.join(settings.projects_root, project_id)
        os.makedirs(project_path, exist_ok=True)

        processed_instruction = instruction
        if images:
            image_refs = []
            for i, img in enumerate(images):
                path = img.get('path') if isinstance(img, dict) else getattr(img, 'path', None)
                if path:
                    image_refs.append(f"Image #{i+1}: {path}")
            if image_refs:
                processed_instruction = f"{instruction}\n\nUploaded files:\n{chr(10).join(image_refs)}"

        cli_model = MODEL_MAPPING.get(model, "claude-sonnet-4-5-20250929") if model else "claude-sonnet-4-5-20250929"

        is_clear_command = instruction.strip().lower() == "/clear"

        options = self.init_claude_option(
            project_id=project_id,
            model=model,
            claude_session_id=claude_session_id,
            force_new_session=is_clear_command,
            user_config=user_config,
            agent_type=agent_type,
        )
        # Inject the delegation server with callback
        options.mcp_servers = {"butler-tools": self._delegation_server}
        options.permission_mode = "bypassPermissions"

        abs_project_path = os.path.abspath(project_path)
        cwd_instruction = (
            f"\n\n## Working Directory\n"
            f"Your current working directory is: {abs_project_path}\n"
            f"IMPORTANT: All file operations MUST use relative paths."
        )
        options.system_prompt = (options.system_prompt or "") + cwd_instruction

        ui.info(f"Butler using model: {options.model}", "Butler")

        got_assistant_content = False
        attempted_resume = options.resume is not None

        try:
            async for msg in self._run_butler_streaming(
                options, processed_instruction, project_id, session_id,
                cli_model, is_clear_command, log_callback, locale,
            ):
                if msg.role == "assistant" and msg.message_type == "chat":
                    got_assistant_content = True
                yield msg
        except Exception as e:
            if attempted_resume:
                ui.info(f"Butler session resume failed ({e}), retrying fresh", "Butler")
                log_callback({"claude_session_id": None})
                options.resume = None
                async for msg in self._run_butler_streaming(
                    options, processed_instruction, project_id, session_id,
                    cli_model, is_clear_command, log_callback, locale,
                ):
                    yield msg
                return
            raise

        if not got_assistant_content and attempted_resume and not is_clear_command:
            ui.info("Butler stale session, retrying fresh", "Butler")
            log_callback({"claude_session_id": None})
            options.resume = None
            async for msg in self._run_butler_streaming(
                options, processed_instruction, project_id, session_id,
                cli_model, is_clear_command, log_callback, locale,
            ):
                yield msg

    async def _run_butler_streaming(
        self,
        options: ClaudeAgentOptions,
        instruction: str,
        project_id: str,
        session_id: Optional[str],
        cli_model: str,
        is_clear_command: bool,
        log_callback: Callable[[dict], Any],
        locale: str = "en",
    ) -> AsyncGenerator[Message, None]:
        """Butler-specific streaming that also drains delegation events."""
        async with ClaudeSDKClient(options=options) as client:
            self.cli = client
            await self.cli.query(instruction)

            async for message_obj in self.cli.receive_messages():
                # Drain any delegation events and yield them as messages
                while self._delegation_events:
                    event = self._delegation_events.pop(0)
                    event_type = event.get("type", "")

                    if event_type in ("delegation_start", "delegation_complete"):
                        yield Message(
                            id=str(uuid.uuid4()),
                            project_id=project_id,
                            role="system",
                            message_type=event_type,
                            content=self._format_delegation_event(event),
                            metadata_json=event,
                            session_id=session_id,
                            created_at=datetime.utcnow(),
                        )
                    elif event_type == "tool_use":
                        yield Message(
                            id=str(uuid.uuid4()),
                            project_id=project_id,
                            role="system",
                            message_type="delegation_update",
                            content=self._format_tool_event(event),
                            metadata_json=event,
                            session_id=session_id,
                            created_at=datetime.utcnow(),
                        )

                # Process Butler's own messages (same as base _run_streaming)
                if isinstance(message_obj, SystemMessage) or "SystemMessage" in str(type(message_obj)):
                    subtype = getattr(message_obj, "subtype", None)
                    if hasattr(message_obj, "subtype") and message_obj.subtype == 'init':
                        if is_clear_command:
                            log_callback({"claude_session_id": None})
                        else:
                            claude_session_id = message_obj.data.get('session_id')
                            log_callback({"claude_session_id": claude_session_id})

                    if subtype == "init" and is_clear_command:
                        yield Message(
                            id=str(uuid.uuid4()),
                            project_id=project_id,
                            role="system",
                            message_type="system",
                            content=get_message("session_cleared", locale),
                            metadata_json={"cli_type": self.cli_type.value, "subtype": "init"},
                            session_id=session_id,
                            created_at=datetime.utcnow(),
                        )
                        continue

                    yield Message(
                        id=str(uuid.uuid4()),
                        project_id=project_id,
                        role="system",
                        message_type="system",
                        content=get_message("agent_initialized", locale, model=cli_model),
                        metadata_json={"cli_type": self.cli_type.value, "hidden_from_ui": True},
                        session_id=session_id,
                        created_at=datetime.utcnow(),
                    )

                elif isinstance(message_obj, AssistantMessage) or "AssistantMessage" in str(type(message_obj)):
                    content = ""
                    if hasattr(message_obj, "content") and isinstance(message_obj.content, list):
                        for block in message_obj.content:
                            if isinstance(block, TextBlock):
                                content += block.text
                            elif isinstance(block, ToolUseBlock):
                                tool_name = block.name

                                tool_message = Message(
                                    id=str(uuid.uuid4()),
                                    project_id=project_id,
                                    role="assistant",
                                    message_type="tool_use",
                                    content=self._create_tool_summary(tool_name, block.input),
                                    metadata_json={
                                        "cli_type": self.cli_type.value,
                                        "tool_name": tool_name,
                                        "tool_input": block.input,
                                        "tool_id": block.id,
                                    },
                                    session_id=session_id,
                                    created_at=datetime.utcnow(),
                                )
                                ui.info(self._get_tool_display(tool_name, block.input), "")
                                yield tool_message

                    if content and content.strip():
                        yield Message(
                            id=str(uuid.uuid4()),
                            project_id=project_id,
                            role="assistant",
                            message_type="chat",
                            content=content.strip(),
                            metadata_json={"cli_type": self.cli_type.value},
                            session_id=session_id,
                            created_at=datetime.utcnow(),
                        )

                elif isinstance(message_obj, ResultMessage) or "ResultMessage" in str(type(message_obj)):
                    # Drain remaining delegation events
                    while self._delegation_events:
                        event = self._delegation_events.pop(0)
                        event_type = event.get("type", "")
                        if event_type in ("delegation_start", "delegation_complete", "tool_use"):
                            msg_type = "delegation_update" if event_type == "tool_use" else event_type
                            yield Message(
                                id=str(uuid.uuid4()),
                                project_id=project_id,
                                role="system",
                                message_type=msg_type,
                                content=self._format_delegation_event(event) if event_type != "tool_use" else self._format_tool_event(event),
                                metadata_json=event,
                                session_id=session_id,
                                created_at=datetime.utcnow(),
                            )

                    duration_ms = getattr(message_obj, 'duration_ms', 0)
                    total_cost_usd = getattr(message_obj, 'total_cost_usd', 0)
                    num_turns = getattr(message_obj, 'num_turns', 0)
                    usage = getattr(message_obj, 'usage', None)
                    usage_dict = self._serialize_usage(usage)
                    total_tokens = usage_dict.get('input_tokens', 0) + usage_dict.get('output_tokens', 0)

                    result_parts = [f"Session complete, {self._format_duration(duration_ms)}"]
                    if total_tokens > 0:
                        result_parts.append(f"Tokens: {total_tokens:,}")
                    if num_turns > 0:
                        result_parts.append(f"Turns: {num_turns}")
                    if total_cost_usd and total_cost_usd > 0:
                        result_parts.append(f"Cost: ${total_cost_usd:.4f}")

                    result_content = " | ".join(result_parts)
                    ui.success(result_content, "Butler")

                    yield Message(
                        id=str(uuid.uuid4()),
                        project_id=project_id,
                        role="system",
                        message_type="session_complete",
                        content=result_content,
                        metadata_json={
                            "cli_type": self.cli_type.value,
                            "duration_ms": duration_ms,
                            "total_cost_usd": total_cost_usd,
                            "usage": usage_dict,
                            "num_turns": num_turns,
                        },
                        session_id=session_id,
                        created_at=datetime.utcnow(),
                    )
                    break

    def _format_delegation_event(self, event: dict) -> str:
        event_type = event.get("type", "")
        agent = event.get("agent_type", "unknown")
        task = event.get("task", "")

        if event_type == "delegation_start":
            return f"Delegating to {agent}: {task[:100]}"
        elif event_type == "delegation_complete":
            if event.get("error"):
                return f"{agent} failed: {event['error'][:100]}"
            return f"{agent} completed task"
        return str(event)

    def _format_tool_event(self, event: dict) -> str:
        tool_name = event.get("tool_name", "unknown")
        return f"[sub-agent] {tool_name}"
