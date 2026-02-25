"""
OpenAI-protocol runner — handles OpenAI, Deepseek, Qwen, GLM, and any
OpenAI-compatible API via streaming chat completions.
"""
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

from openai import OpenAI

from app.models.messages import Message
from app.core.terminal_ui import ui
from .base_runner import BaseRunner


class OpenAIRunner(BaseRunner):
    """Runner for OpenAI-compatible APIs."""

    async def stream_response(
        self,
        instruction: str,
        project_id: str,
        session_id: Optional[str],
        model: str,
        system_prompt: Optional[str] = None,
        cwd: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[Message, None]:
        """Stream chat completion from an OpenAI-compatible API."""
        import time

        client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url or "https://api.openai.com/v1",
        )

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if cwd:
            messages.append({"role": "system", "content": f"Working directory: {cwd}"})

        # Append conversation history
        if history:
            for h in history:
                messages.append({"role": h["role"], "content": h["content"]})

        # Current instruction
        messages.append({"role": "user", "content": instruction})

        ui.info(f"OpenAI runner: model={model}, messages={len(messages)}", "Runner")

        start = time.time()
        full_content = ""
        last_chunk = None

        try:
            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
            )

            for chunk in stream:
                last_chunk = chunk
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    full_content += delta.content

            duration_ms = int((time.time() - start) * 1000)

            if full_content.strip():
                yield Message(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    role="assistant",
                    message_type="chat",
                    content=full_content.strip(),
                    metadata_json={"cli_type": "openai_runner", "model": model},
                    session_id=session_id,
                    created_at=datetime.utcnow(),
                )

            # Session complete message
            usage_str = ""
            if last_chunk and hasattr(last_chunk, "usage") and last_chunk.usage:
                total = (last_chunk.usage.prompt_tokens or 0) + (last_chunk.usage.completion_tokens or 0)
                usage_str = f" | Tokens: {total:,}"

            yield Message(
                id=str(uuid.uuid4()),
                project_id=project_id,
                role="system",
                message_type="session_complete",
                content=f"Session complete, {duration_ms / 1000:.2f}s{usage_str}",
                metadata_json={
                    "cli_type": "openai_runner",
                    "duration_ms": duration_ms,
                    "model": model,
                },
                session_id=session_id,
                created_at=datetime.utcnow(),
            )

        except Exception as e:
            ui.error(f"OpenAI runner error: {e}", "Runner")
            yield Message(
                id=str(uuid.uuid4()),
                project_id=project_id,
                role="system",
                message_type="error",
                content=f"Model error: {e}",
                metadata_json={"cli_type": "openai_runner", "model": model},
                session_id=session_id,
                created_at=datetime.utcnow(),
            )
