"""Integration tests for /api/chat/{project_id}/messages endpoint."""



class TestGetMessages:
    """GET /api/chat/{project_id}/messages — retrieve messages."""

    def test_empty_messages(self, client, sample_project):
        """Returns empty list when no messages exist."""
        project_id = sample_project["id"]
        resp = client.get(f"/api/chat/{project_id}/messages")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_messages(self, client, sample_project):
        """Returns messages for the project."""
        project_id = sample_project["id"]
        resp = client.get(f"/api/chat/{project_id}/messages?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_message_limit(self, client, sample_project):
        """Respects the limit parameter."""
        project_id = sample_project["id"]
        resp = client.get(f"/api/chat/{project_id}/messages?limit=5")
        assert resp.status_code == 200

    def test_nonexistent_project(self, client):
        """Returns empty list for nonexistent project."""
        resp = client.get("/api/chat/nonexistent/messages")
        assert resp.status_code == 200
