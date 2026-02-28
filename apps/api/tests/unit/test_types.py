"""Tests for shared types and enums."""
from app.common.types import AgentType, ProviderProtocol


class TestAgentType:
    def test_hello_value(self):
        assert AgentType.HELLO.value == "hello"

    def test_from_value_valid(self):
        assert AgentType.from_value("hello") == AgentType.HELLO

    def test_from_value_invalid(self):
        assert AgentType.from_value("nonexistent") is None


class TestProviderProtocol:
    def test_values(self):
        assert ProviderProtocol.ANTHROPIC.value == "anthropic"
        assert ProviderProtocol.OPENAI.value == "openai"

    def test_from_value_valid(self):
        assert ProviderProtocol.from_value("openai") == ProviderProtocol.OPENAI

    def test_from_value_invalid(self):
        assert ProviderProtocol.from_value("gemini") is None
