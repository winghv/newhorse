"""
Delegation Executor — runs specialist agent sessions when Butler calls delegate_task.

Uses Claude Agent SDK's @tool decorator to create an in-process MCP server
that the Butler agent can call like any other tool.
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    tool,
    create_sdk_mcp_server,
)
from claude_agent_sdk.types import AssistantMessage, ResultMessage, TextBlock, ToolUseBlock

from app.core.config import settings
from app.core.terminal_ui import ui
from app.services.cli.config_loader import load_agent_config, AgentConfig
from app.services.cli.base import MODEL_MAPPING

# Valid specialist agent types
SPECIALIST_AGENTS = {"planner", "coder", "researcher", "reviewer", "writer"}


async def run_specialist_agent(
    agent_type: str,
    task: str,
    context: str,
    project_id: str,
    on_event: Optional[Callable[[dict], Any]] = None,
) -> str:
    """Run a specialist agent session and collect the text result.

    Args:
        agent_type: One of SPECIALIST_AGENTS
        task: The task instruction for the specialist
        context: Additional context from previous tasks
        project_id: Project workspace to operate in
        on_event: Optional callback for progress events (tool_use, text, etc.)

    Returns:
        Concatenated text output from the specialist agent
    """
    project_path = os.path.join(settings.projects_root, project_id)
    os.makedirs(project_path, exist_ok=True)

    # Load specialist agent config from template
    default_config = AgentConfig(
        name=agent_type.capitalize(),
        description=f"{agent_type} specialist",
        system_prompt=f"You are a {agent_type} specialist.",
    )
    config = load_agent_config(project_path, agent_type=agent_type, default_config=default_config)

    cli_model = MODEL_MAPPING.get(config.model, config.model)

    # Build instruction with context
    instruction = task
    if context:
        instruction = f"## Context from previous work\n\n{context}\n\n## Your Task\n\n{task}"

    # Add working directory constraint
    abs_project_path = os.path.abspath(project_path)
    system_prompt = (config.system_prompt or "") + (
        f"\n\n## Working Directory\n"
        f"Your current working directory is: {abs_project_path}\n"
        f"All file operations MUST use relative paths."
    )

    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
        cwd=project_path,
        model=cli_model,
        allowed_tools=config.allowed_tools,
        permission_mode="bypassPermissions",
    )

    ui.info(f"Starting specialist [{agent_type}]: {task[:80]}...", "Delegation")

    collected_text = []

    async with ClaudeSDKClient(options=options) as client:
        await client.query(instruction)

        async for message_obj in client.receive_messages():
            if isinstance(message_obj, AssistantMessage):
                if hasattr(message_obj, "content") and isinstance(message_obj.content, list):
                    for block in message_obj.content:
                        if isinstance(block, TextBlock) and block.text.strip():
                            collected_text.append(block.text.strip())
                            if on_event:
                                on_event({"type": "text", "content": block.text.strip()})
                        elif isinstance(block, ToolUseBlock):
                            if on_event:
                                on_event({
                                    "type": "tool_use",
                                    "tool_name": block.name,
                                    "tool_input": block.input,
                                })

            elif isinstance(message_obj, ResultMessage):
                duration_ms = getattr(message_obj, "duration_ms", 0)
                cost = getattr(message_obj, "total_cost_usd", 0)
                ui.success(
                    f"Specialist [{agent_type}] done — {duration_ms}ms, ${cost:.4f}",
                    "Delegation",
                )
                if on_event:
                    on_event({
                        "type": "complete",
                        "duration_ms": duration_ms,
                        "cost": cost,
                    })
                break

    result = "\n\n".join(collected_text)
    return result if result else "(Specialist produced no text output)"


def create_delegation_tool(project_id: str, on_event: Optional[Callable[[dict], Any]] = None):
    """Create the delegate_task MCP tool bound to a specific project.

    Returns an MCP server that can be passed to ClaudeAgentOptions.mcp_servers.
    """
    @tool(
        "delegate_task",
        "Delegate a task to a specialist agent on your team. "
        "Available agents: planner, coder, researcher, reviewer, writer. "
        "The specialist will execute the task in the project workspace and return results.",
        {
            "agent": str,
            "task": str,
            "context": str,
        },
    )
    async def delegate_task(args: Dict[str, Any]) -> Dict[str, Any]:
        agent_type = args.get("agent", "")
        task = args.get("task", "")
        context = args.get("context", "")

        if agent_type not in SPECIALIST_AGENTS:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: Unknown agent '{agent_type}'. Available: {', '.join(sorted(SPECIALIST_AGENTS))}",
                    }
                ]
            }

        if not task:
            return {
                "content": [
                    {"type": "text", "text": "Error: 'task' is required."}
                ]
            }

        # Notify frontend: delegation starting
        delegation_id = str(uuid.uuid4())[:8]
        if on_event:
            on_event({
                "type": "delegation_start",
                "delegation_id": delegation_id,
                "agent_type": agent_type,
                "task": task,
            })

        try:
            # Run the specialist agent
            result = await run_specialist_agent(
                agent_type=agent_type,
                task=task,
                context=context,
                project_id=project_id,
                on_event=lambda evt: on_event({**evt, "delegation_id": delegation_id}) if on_event else None,
            )

            # Notify frontend: delegation complete
            if on_event:
                on_event({
                    "type": "delegation_complete",
                    "delegation_id": delegation_id,
                    "agent_type": agent_type,
                    "task": task,
                    "result_preview": result[:200],
                })

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"[{agent_type}] Task completed.\n\nResult:\n{result}",
                    }
                ]
            }

        except Exception as e:
            ui.error(f"Specialist [{agent_type}] failed: {e}", "Delegation")
            if on_event:
                on_event({
                    "type": "delegation_complete",
                    "delegation_id": delegation_id,
                    "agent_type": agent_type,
                    "task": task,
                    "error": str(e),
                })
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: Specialist [{agent_type}] failed — {e}",
                    }
                ]
            }

    server = create_sdk_mcp_server(
        name="butler-tools",
        version="1.0.0",
        tools=[delegate_task],
    )
    return server
