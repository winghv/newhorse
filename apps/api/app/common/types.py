"""
Common types and enums
"""
from enum import Enum


class AgentType(str, Enum):
    """Available agent types"""

    # Hello World demo agent
    HELLO = "hello"

    @classmethod
    def from_value(cls, value: str):
        """Get enum from value string"""
        for item in cls:
            if item.value == value:
                return item
        return None


class ProviderProtocol(str, Enum):
    """Supported provider API protocols"""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    # Future: GEMINI = "gemini"

    @classmethod
    def from_value(cls, value: str):
        for item in cls:
            if item.value == value:
                return item
        return None
