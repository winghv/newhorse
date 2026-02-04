"""
CLI services module
"""
from .manager import agent_manager, AgentManager
from .base import BaseCLI

__all__ = ["agent_manager", "AgentManager", "BaseCLI"]
