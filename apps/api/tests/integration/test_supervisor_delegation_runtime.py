"""Behavior-level verification for supervisor-led specialist delegation."""

import asyncio
from typing import Any

from claude_agent_sdk.types import AssistantMessage, ResultMessage, SystemMessage, TextBlock
from mcp import types as mcp_types

import app.services.cli.delegation as delegation_module
import app.services.cli.adapters.butler_agent as butler_module
from app.services.cli.adapters.butler_agent import ButlerAgent


def test_delegate_task_handler_emits_start_and_complete_events(monkeypatch):
    """Delegation handler should emit lifecycle events around specialist execution."""

    async def fake_run_specialist_agent(**_: Any) -> str:
        return "benchmark artifacts ready"

    monkeypatch.setattr(
        delegation_module,
        "run_specialist_agent",
        fake_run_specialist_agent,
    )

    events: list[dict[str, Any]] = []
    server = delegation_module.create_delegation_tool("project-123", on_event=events.append)
    handler = server["instance"].request_handlers[mcp_types.CallToolRequest]
    request = mcp_types.CallToolRequest(
        params=mcp_types.CallToolRequestParams(
            name="delegate_task",
            arguments={
                "agent": "benchmark-analyst",
                "task": "产出 benchmark deck",
                "context": "需要结构化输出",
            },
        )
    )

    result = asyncio.run(handler(request))

    assert result.root.isError is False
    assert "[benchmark-analyst] Task completed." in result.root.content[0].text
    assert [event["type"] for event in events] == [
        "delegation_start",
        "delegation_complete",
    ]
    assert events[0]["agent_type"] == "benchmark-analyst"
    assert events[1]["result_preview"] == "benchmark artifacts ready"


def test_media_ops_supervisor_runtime_surfaces_delegation_events(
    client, sample_project, monkeypatch
):
    """Supervisor-led projects should expose real delegation events through Butler runtime."""

    project_id = sample_project["id"]
    apply_resp = client.post(
        f"/api/agents/projects/{project_id}/config/from-template?template_id=media-ops-supervisor"
    )
    assert apply_resp.status_code == 200

    async def fake_run_specialist_agent(**_: Any) -> str:
        return "angle brief ready"

    monkeypatch.setattr(
        delegation_module,
        "run_specialist_agent",
        fake_run_specialist_agent,
    )

    observed: dict[str, Any] = {}

    class FakeClaudeSDKClient:
        def __init__(self, options):
            self.options = options
            observed["system_prompt"] = options.system_prompt
            observed["mcp_servers"] = options.mcp_servers
            observed["allowed_tools"] = options.allowed_tools

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def query(self, instruction):
            observed["instruction"] = instruction

        async def receive_messages(self):
            yield SystemMessage(subtype="init", data={"session_id": "session-1"})
            handler = self.options.mcp_servers["butler-tools"]["instance"].request_handlers[
                mcp_types.CallToolRequest
            ]
            request = mcp_types.CallToolRequest(
                params=mcp_types.CallToolRequestParams(
                    name="delegate_task",
                    arguments={
                        "agent": "angle-designer",
                        "task": "收敛 angle brief",
                        "context": "给出结构化产物",
                    },
                )
            )
            await handler(request)
            yield AssistantMessage(content=[TextBlock("已委派 specialist")], model="fake-model")
            yield ResultMessage(
                subtype="success",
                duration_ms=12,
                duration_api_ms=10,
                is_error=False,
                num_turns=1,
                session_id="session-1",
                total_cost_usd=0.0,
                usage={"input_tokens": 10, "output_tokens": 5},
                result="done",
            )

    monkeypatch.setattr(butler_module, "ClaudeSDKClient", FakeClaudeSDKClient)

    agent = ButlerAgent()
    websocket_events: list[dict[str, Any]] = []
    log_updates: list[dict[str, Any]] = []

    async def fake_ws_send(message: dict[str, Any]) -> None:
        websocket_events.append(message)

    agent._ws_send_fn = fake_ws_send

    async def collect_messages():
        messages = []
        async for msg in agent.execute_with_streaming(
            instruction="请先推进角度设计阶段",
            project_id=project_id,
            log_callback=log_updates.append,
            session_id="session-under-test",
            locale="zh",
        ):
            messages.append(msg)
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        return messages

    messages = asyncio.run(collect_messages())

    assert "默认通过 `delegate_task` 调用团队成员" in observed["system_prompt"]
    assert "默认不得直接产出完整脚本" in observed["system_prompt"]
    assert "butler-tools" in observed["mcp_servers"]
    assert "mcp__butler-tools__delegate_task" in observed["allowed_tools"]
    assert any(update.get("claude_session_id") == "session-1" for update in log_updates)
    assert any(msg.content == "已委派 specialist" for msg in messages)

    event_types = [event["type"] for event in websocket_events]
    assert "delegation_start" in event_types
    assert "delegation_complete" in event_types
    start_event = next(event for event in websocket_events if event["type"] == "delegation_start")
    complete_event = next(event for event in websocket_events if event["type"] == "delegation_complete")
    assert start_event["metadata"]["agent_type"] == "angle-designer"
    assert "Delegating to angle-designer" in start_event["content"]
    assert complete_event["metadata"]["agent_type"] == "angle-designer"
    assert "angle-designer completed task" in complete_event["content"]
