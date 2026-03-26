"""Integration tests for /api/agents/ endpoints."""



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


class TestAgentTemplates:
    """Template listing and application behavior."""

    def test_builtin_template_exposes_preferred_cli(self, client):
        """Built-in templates can declare a runtime/preferred_cli."""
        resp = client.get("/api/agents/templates")
        assert resp.status_code == 200

        templates = resp.json()["templates"]
        media_team = next((tpl for tpl in templates if tpl["id"] == "media-ops-butler"), None)

        assert media_team is not None
        assert media_team["preferred_cli"] == "butler"

    def test_template_detail_preserves_preferred_cli(self, client):
        """Template detail returns preferred_cli for butler-backed templates."""
        resp = client.get("/api/agents/templates/media-ops-butler")
        assert resp.status_code == 200

        data = resp.json()
        assert data["config"]["preferred_cli"] == "butler"

    def test_applying_template_updates_project_runtime_and_model(self, client, sample_project):
        """Applying a template syncs project preferred_cli and selected_model."""
        project_id = sample_project["id"]

        resp = client.post(
            f"/api/agents/projects/{project_id}/config/from-template?template_id=media-ops-butler"
        )
        assert resp.status_code == 200

        project_resp = client.get(f"/api/projects/{project_id}")
        assert project_resp.status_code == 200

        project = project_resp.json()
        assert project["preferred_cli"] == "butler"
        assert project["selected_model"] == "claude-sonnet-4-5-20250929"

    def test_saving_project_config_preserves_preferred_cli(self, client, sample_project):
        """Editing project config should not erase the template runtime."""
        project_id = sample_project["id"]

        apply_resp = client.post(
            f"/api/agents/projects/{project_id}/config/from-template?template_id=media-ops-butler"
        )
        assert apply_resp.status_code == 200

        save_resp = client.post(
            f"/api/agents/projects/{project_id}/config",
            json={
                "name": "Media Ops Butler",
                "description": "updated",
                "system_prompt": "updated prompt",
                "skills": ["media-ops-orchestration"],
                "model": "claude-sonnet-4-5-20250929",
                "allowed_tools": ["Read", "Glob", "Grep"],
            },
        )
        assert save_resp.status_code == 200
        assert save_resp.json()["config"]["preferred_cli"] == "butler"

        project_resp = client.get(f"/api/projects/{project_id}")
        assert project_resp.status_code == 200
        assert project_resp.json()["preferred_cli"] == "butler"
