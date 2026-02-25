"""
Abstract base class for model runners.
Each runner wraps a specific SDK (Anthropic, OpenAI, Gemini, etc.).
"""
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.models.messages import Message


class BaseRunner(ABC):
    """Abstract runner for a provider protocol."""

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url

    @abstractmethod
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
        """Stream response messages from the model."""
        ...
