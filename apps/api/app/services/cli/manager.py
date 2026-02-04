"""
Agent Manager - Manages agent lifecycle and routing.
"""
from typing import Dict, Optional, Any

from app.common.types import AgentType
from app.core.terminal_ui import ui
from .adapters.hello_agent import HelloAgent
from .base import BaseCLI


class AgentManager:
    """Manages agent instances and routing."""

    def __init__(self):
        self._agents: Dict[AgentType, BaseCLI] = {}

    def get_agent(self, agent_type: AgentType) -> BaseCLI:
        """Get or create an agent instance."""
        if agent_type not in self._agents:
            self._agents[agent_type] = self._create_agent(agent_type)
        return self._agents[agent_type]

    def _create_agent(self, agent_type: AgentType) -> BaseCLI:
        """Create a new agent instance."""
        if agent_type == AgentType.HELLO:
            ui.info("Creating Hello Agent", "AgentManager")
            return HelloAgent()
        else:
            ui.warning(f"Unknown agent type: {agent_type}, using Hello Agent", "AgentManager")
            return HelloAgent()

    async def check_availability(self, agent_type: AgentType) -> Dict[str, Any]:
        """Check if an agent is available."""
        agent = self.get_agent(agent_type)
        return await agent.check_availability()

    def get_available_agents(self) -> Dict[str, Dict[str, Any]]:
        """Get list of available agent types."""
        return {
            AgentType.HELLO.value: {
                "name": "Hello Agent",
                "description": "A friendly demonstration agent",
                "type": AgentType.HELLO.value,
            }
        }


# Global manager instance
agent_manager = AgentManager()
