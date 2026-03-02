"""Integration tests for /api/agents/ endpoints."""

import pytest


class TestListAgents:
    """GET /api/agents/ — list available agents."""

    def test_returns_agents(self, client):
        """Returns dict of available agent types."""
        resp = client.get("/api/agents/")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert len(data) >= 1

    def test_agent_structure(self, client):
        """Agent has expected fields."""
        resp = client.get("/api/agents/")
        data = resp.json()
        if data:
            # data is a dict like {'hello': {'name': '...', 'description': '...', 'type': '...'}}
            agent_key = list(data.keys())[0]
            agent = data[agent_key]
            assert "name" in agent
            assert "description" in agent


class TestGetAgentModels:
    """GET /api/agents/{agent_type}/models — list models for agent.

    Note: This endpoint does not exist yet and returns 404.
    """

    def test_endpoint_not_found(self, client):
        """Endpoint /api/agents/{agent_type}/models does not exist - returns 404."""
        resp = client.get("/api/agents/hello/models")
        # This endpoint needs to be implemented
        assert resp.status_code == 404
