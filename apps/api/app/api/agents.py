"""
Agents API router
"""
from fastapi import APIRouter

from app.services.cli import agent_manager

router = APIRouter()


@router.get("/")
def list_agents():
    """List available agents."""
    return agent_manager.get_available_agents()


@router.get("/{agent_type}/availability")
async def check_availability(agent_type: str):
    """Check agent availability."""
    from app.common.types import AgentType

    agent_enum = AgentType.from_value(agent_type)
    if not agent_enum:
        return {"available": False, "error": f"Unknown agent type: {agent_type}"}

    return await agent_manager.check_availability(agent_enum)
