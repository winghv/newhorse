"""
Base CLI adapter for Agent implementations.

This module provides the abstract contract for CLI providers and common utilities.
Subclasses implement specific agent behaviors while reusing shared functionality.
"""
from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, PermissionMode
from claude_agent_sdk.types import (
    SystemMessage,
    AssistantMessage,
    UserMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
)

from app.models.messages import Message
from app.common.types import AgentType
from app.core.terminal_ui import ui
from app.core.config import settings


# Model mapping from friendly names to full model IDs
MODEL_MAPPING: Dict[str, str] = {
    "sonnet-4": "claude-sonnet-4-20250514",
    "sonnet-4.5": "claude-sonnet-4-5-20250929",
    "opus-4": "claude-opus-4-20250514",
    "opus-4.5": "claude-opus-4-5-20251101",
    "haiku-3.5": "claude-3-5-haiku-20241022",
    # Full names
    "claude-sonnet-4-20250514": "claude-sonnet-4-20250514",
    "claude-sonnet-4-5-20250929": "claude-sonnet-4-5-20250929",
    "claude-opus-4-20250514": "claude-opus-4-20250514",
    "claude-opus-4-5-20251101": "claude-opus-4-5-20251101",
    "claude-3-5-haiku-20241022": "claude-3-5-haiku-20241022",
}


class BaseCLI(ABC):
    """Abstract base class for Agent adapters.

    Provides common functionality for Claude Agent SDK integration.
    Subclasses implement specific agent configurations.
    """

    def __init__(self, cli_type: AgentType):
        self.cli_type = cli_type
        self.cli = None
        self.current_project_id: Optional[str] = None
        self.session_start_time: Optional[datetime] = None

    @abstractmethod
    async def check_availability(self) -> Dict[str, Any]:
        """Check if the agent is available and configured."""
        pass

    @abstractmethod
    def init_claude_option(
        self,
        project_id: str,
        claude_session_id: Optional[str],
        model: Optional[str] = None,
        force_new_session: bool = False,
        user_config: Optional[Dict[str, str]] = None
    ) -> ClaudeAgentOptions:
        """Initialize Claude Agent options for this agent type."""
        pass

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
        permission_mode: PermissionMode = "default",
        user_config: Optional[Dict[str, str]] = None,
    ) -> AsyncGenerator[Message, None]:
        """Execute instruction using Claude Agent SDK with streaming."""

        self.current_project_id = project_id
        self.session_start_time = datetime.now(timezone.utc)

        ui.info("Starting Claude Agent SDK execution", "Agent")
        ui.debug(f"Project ID: {project_id}", "Agent")

        # Process images if provided
        processed_instruction = instruction
        if images:
            image_refs = []
            for i, img in enumerate(images):
                path = img.get('path') if isinstance(img, dict) else getattr(img, 'path', None)
                if path:
                    image_refs.append(f"Image #{i+1}: {path}")
            if image_refs:
                processed_instruction = f"{instruction}\n\nUploaded files:\n{chr(10).join(image_refs)}"

        # Resolve model
        cli_model = MODEL_MAPPING.get(model, "claude-sonnet-4-5-20250929") if model else "claude-sonnet-4-5-20250929"
        project_path = os.path.join(settings.projects_root, project_id)
        os.makedirs(project_path, exist_ok=True)

        # Check for /clear command
        is_clear_command = instruction.strip().lower() == "/clear"

        # Initialize options
        options = self.init_claude_option(
            project_id=project_id,
            model=model,
            claude_session_id=claude_session_id,
            force_new_session=is_clear_command,
            user_config=user_config
        )

        options.permission_mode = "bypassPermissions"
        ui.info(f"Using model: {options.model}", "Agent")

        got_assistant_content = False
        attempted_resume = options.resume is not None
        held_result_msg = None

        async for msg in self._run_streaming(
            options, processed_instruction, project_id, session_id,
            cli_model, is_clear_command, log_callback,
        ):
            if msg.role == "assistant" and msg.message_type == "chat":
                got_assistant_content = True
            # Hold back session_complete on potential stale resume
            if msg.message_type == "session_complete" and attempted_resume and not got_assistant_content:
                held_result_msg = msg
                continue
            yield msg

        # Detect stale session resume: 0ms result with no assistant content
        if not got_assistant_content and attempted_resume and not is_clear_command:
            ui.info("Stale session detected, retrying with fresh session", "Agent")
            log_callback({"claude_session_id": None})
            options.resume = None

            async for msg in self._run_streaming(
                options, processed_instruction, project_id, session_id,
                cli_model, is_clear_command, log_callback,
            ):
                yield msg
        elif held_result_msg:
            yield held_result_msg

    async def _run_streaming(
        self,
        options: ClaudeAgentOptions,
        instruction: str,
        project_id: str,
        session_id: Optional[str],
        cli_model: str,
        is_clear_command: bool,
        log_callback: Callable[[dict], Any],
    ) -> AsyncGenerator[Message, None]:
        """Run a single streaming session with the Claude Agent SDK."""
        async with ClaudeSDKClient(options=options) as client:
            self.cli = client
            await self.cli.query(instruction)

            async for message_obj in self.cli.receive_messages():
                # Handle SystemMessage
                if isinstance(message_obj, SystemMessage) or "SystemMessage" in str(type(message_obj)):
                    subtype = getattr(message_obj, "subtype", None)

                    if hasattr(message_obj, "subtype") and message_obj.subtype == 'init':
                        if is_clear_command:
                            log_callback({"claude_session_id": None})
                            ui.info("Session cleared", "Agent")
                        else:
                            claude_session_id = message_obj.data.get('session_id')
                            log_callback({"claude_session_id": claude_session_id})

                    if subtype == "init" and is_clear_command:
                        yield Message(
                            id=str(uuid.uuid4()),
                            project_id=project_id,
                            role="system",
                            message_type="system",
                            content="✨ Conversation cleared, new session started",
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
                        content=f"Agent initialized (Model: {cli_model})",
                        metadata_json={"cli_type": self.cli_type.value, "hidden_from_ui": True},
                        session_id=session_id,
                        created_at=datetime.utcnow(),
                    )

                # Handle AssistantMessage
                elif isinstance(message_obj, AssistantMessage) or "AssistantMessage" in str(type(message_obj)):
                    content = ""
                    if hasattr(message_obj, "content") and isinstance(message_obj.content, list):
                        for block in message_obj.content:
                            if isinstance(block, TextBlock):
                                content += block.text
                            elif isinstance(block, ToolUseBlock):
                                tool_message = Message(
                                    id=str(uuid.uuid4()),
                                    project_id=project_id,
                                    role="assistant",
                                    message_type="tool_use",
                                    content=self._create_tool_summary(block.name, block.input),
                                    metadata_json={
                                        "cli_type": self.cli_type.value,
                                        "tool_name": block.name,
                                        "tool_input": block.input,
                                        "tool_id": block.id,
                                    },
                                    session_id=session_id,
                                    created_at=datetime.utcnow(),
                                )
                                ui.info(self._get_tool_display(block.name, block.input), "")
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

                # Handle ResultMessage
                elif isinstance(message_obj, ResultMessage) or "ResultMessage" in str(type(message_obj)):
                    duration_ms = getattr(message_obj, 'duration_ms', 0)
                    total_cost_usd = getattr(message_obj, 'total_cost_usd', 0)
                    num_turns = getattr(message_obj, 'num_turns', 0)
                    usage = getattr(message_obj, 'usage', None)

                    usage_dict = self._serialize_usage(usage)
                    total_tokens = usage_dict.get('input_tokens', 0) + usage_dict.get('output_tokens', 0)

                    result_parts = [f"🎉 Session complete, ⏱️ {self._format_duration(duration_ms)}"]
                    if total_tokens > 0:
                        result_parts.append(f"📊 Tokens: {total_tokens:,}")
                    if num_turns > 0:
                        result_parts.append(f"🔄 Turns: {num_turns}")
                    if total_cost_usd and total_cost_usd > 0:
                        result_parts.append(f"💰 Cost: ${total_cost_usd:.4f}")

                    result_content = " | ".join(result_parts)
                    ui.success(result_content, "Agent")

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

    async def interrupt(self):
        """Interrupt the current execution."""
        if self.cli is not None:
            await self.cli.interrupt()

    def _create_tool_summary(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """Create a summary for tool usage."""
        normalized = self._normalize_tool_name(tool_name)

        if normalized == "Read":
            path = tool_input.get("file_path") or tool_input.get("path", "")
            filename = path.split("/")[-1] if path else "file"
            return f"📖 **Read** `{filename}`"
        elif normalized == "Write":
            path = tool_input.get("file_path") or tool_input.get("path", "")
            filename = path.split("/")[-1] if path else "file"
            return f"✏️ **Write** `{filename}`"
        elif normalized == "Edit":
            path = tool_input.get("file_path") or tool_input.get("path", "")
            filename = path.split("/")[-1] if path else "file"
            return f"📝 **Edit** `{filename}`"
        elif normalized == "Bash":
            cmd = tool_input.get("command", "")[:40]
            return f"**Bash** `{cmd}...`" if len(cmd) == 40 else f"**Bash** `{cmd}`"
        elif normalized == "Grep":
            pattern = tool_input.get("pattern", "")
            return f"🔍 **Search** `{pattern}`"
        elif normalized == "Glob":
            pattern = tool_input.get("pattern", "")
            return f"🔎 **Glob** `{pattern}`"
        elif normalized == "WebSearch":
            query = tool_input.get("query", "")[:40]
            return f"🌐 **WebSearch** `{query}`"
        elif normalized == "Task":
            desc = tool_input.get("description", "")[:40]
            return f"🤖 **Task** `{desc}`"
        else:
            return f"**{tool_name}** `executing...`"

    def _get_tool_display(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """Get a clean display string for tool usage."""
        normalized = self._normalize_tool_name(tool_name)

        if normalized == "Read":
            path = tool_input.get("file_path") or tool_input.get("path", "")
            filename = path.split("/")[-1] if path else "file"
            return f"Reading {filename}"
        elif normalized == "Write":
            path = tool_input.get("file_path") or tool_input.get("path", "")
            filename = path.split("/")[-1] if path else "file"
            return f"Writing {filename}"
        elif normalized == "Bash":
            cmd = tool_input.get("command", "").split()[0] if tool_input.get("command") else "command"
            return f"Running {cmd}"
        else:
            return f"Using {tool_name}"

    def _normalize_tool_name(self, tool_name: str) -> str:
        """Normalize tool names to unified labels."""
        mapping = {
            "read_file": "Read", "read": "Read",
            "write_file": "Write", "write": "Write",
            "edit_file": "Edit", "edit": "Edit",
            "shell": "Bash", "run_terminal_command": "Bash",
            "search_file_content": "Grep", "grep": "Grep",
            "find_files": "Glob", "glob": "Glob",
            "web_search": "WebSearch", "google_web_search": "WebSearch",
        }
        return mapping.get(tool_name.lower(), tool_name)

    def _format_duration(self, duration_ms: float) -> str:
        """Format duration in milliseconds to readable string."""
        if duration_ms >= 1000:
            seconds = duration_ms / 1000
            if seconds >= 60:
                minutes = int(seconds // 60)
                remaining = seconds % 60
                return f"{minutes}m {remaining:.1f}s"
            return f"{seconds:.2f}s"
        return f"{int(duration_ms)}ms"

    def _serialize_usage(self, usage: Any) -> Dict[str, Any]:
        """Serialize usage object to dictionary."""
        if usage is None:
            return {}
        try:
            if hasattr(usage, '__dict__'):
                return {
                    'input_tokens': getattr(usage, 'input_tokens', 0),
                    'output_tokens': getattr(usage, 'output_tokens', 0),
                }
            elif isinstance(usage, dict):
                return usage
        except Exception:
            pass
        return {}
